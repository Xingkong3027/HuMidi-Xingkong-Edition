#[path = "legacy_model.rs"]
mod legacy_model;
use candle_core::{Device, Result, Tensor};
use std::collections::HashMap;
use std::path::Path;
use std::sync::Mutex;

const HIDDEN: usize = 256;
pub const FEATURES: usize = 140;
const CHUNK: usize = 1024;
const STRIDE: usize = 512;

struct LstmWeights {
    w_ih: Tensor,
    w_hh: Vec<f32>,
    b_ih: Tensor,
    b_hh: Vec<f32>,
}

#[cfg(test)]
mod embedded_model_tests {
    use super::*;

    #[test]
    fn embedded_weights_support_inference_without_a_resource_path() {
        let model = PedalModel::load_embedded().expect("embedded pedal model is valid");
        let output = model
            .forward(&vec![0.0; FEATURES], 1)
            .expect("one-frame inference succeeds");
        assert_eq!(output.len(), 1);
        assert!(output[0].is_finite() && (0.0..=1.0).contains(&output[0]));
    }
}

pub struct PedalModel {
    tensors: HashMap<String, Tensor>,
    device: Device,
    weights: [LstmWeights; 4],
    last_prediction: Mutex<Option<(bool, Vec<f32>, Vec<f32>)>>,
}

fn sigmoid(x: &Tensor) -> Result<Tensor> {
    let ones = Tensor::ones_like(x)?;
    (ones + x.neg()?.exp()?)?.recip()
}

fn load_lstm_weights(
    tensors: &HashMap<String, Tensor>,
    layer: usize,
    reverse: bool,
) -> Result<LstmWeights> {
    let suffix = if reverse { "_reverse" } else { "" };
    let get = |name: String| tensors.get(&name).unwrap().clone();
    Ok(LstmWeights {
        w_ih: get(format!("lstm.weight_ih_l{layer}{suffix}")),
        w_hh: get(format!("lstm.weight_hh_l{layer}{suffix}"))
            .flatten_all()?
            .to_vec1()?,
        b_ih: get(format!("lstm.bias_ih_l{layer}{suffix}")),
        b_hh: get(format!("lstm.bias_hh_l{layer}{suffix}")).to_vec1()?,
    })
}

// Project all input frames with one matrix operation. The recurrent state must
// remain sequential, but does not need dozens of temporary tensors per frame.
fn lstm_direction(
    input: &Tensor,
    weights: &LstmWeights,
    reverse: bool,
    device: &Device,
) -> Result<Tensor> {
    let projected = input
        .matmul(&weights.w_ih.t()?)?
        .broadcast_add(&weights.b_ih)?
        .to_vec2::<f32>()?;
    let mut h = [0.0f32; HIDDEN];
    let mut c = [0.0f32; HIDDEN];
    let mut gates = [0.0f32; HIDDEN * 4];
    let mut output = vec![0.0; projected.len() * HIDDEN];
    for step in 0..projected.len() {
        let frame = if reverse {
            projected.len() - 1 - step
        } else {
            step
        };
        for (row, gate) in gates.iter_mut().enumerate() {
            let weights_row = &weights.w_hh[row * HIDDEN..(row + 1) * HIDDEN];
            // Independent accumulators allow the release compiler to vectorize
            // the matrix-vector product without changing the model architecture.
            let mut sums = [0.0f32; 8];
            for (x, w) in h.chunks_exact(8).zip(weights_row.chunks_exact(8)) {
                for lane in 0..8 {
                    sums[lane] += x[lane] * w[lane];
                }
            }
            *gate = projected[frame][row] + weights.b_hh[row] + sums.iter().sum::<f32>();
        }
        for cell in 0..HIDDEN {
            let sigmoid = |v: f32| 1.0 / (1.0 + (-v).exp());
            let i = sigmoid(gates[cell]);
            let f = sigmoid(gates[HIDDEN + cell]);
            let g = gates[HIDDEN * 2 + cell].tanh();
            let o = sigmoid(gates[HIDDEN * 3 + cell]);
            c[cell] = f * c[cell] + i * g;
            h[cell] = o * c[cell].tanh();
        }
        output[frame * HIDDEN..(frame + 1) * HIDDEN].copy_from_slice(&h);
    }
    Tensor::from_vec(output, (projected.len(), HIDDEN), device)
}
fn bilstm_layer(
    input: &Tensor,
    fwd: &LstmWeights,
    bwd: &LstmWeights,
    device: &Device,
) -> Result<Tensor> {
    let fwd_out = lstm_direction(input, fwd, false, device)?;
    let bwd_out = lstm_direction(input, bwd, true, device)?;
    Tensor::cat(&[&fwd_out, &bwd_out], 1)
}

impl PedalModel {
    /// Ship the AI weights inside the executable, including portable builds.
    pub fn load_embedded() -> Result<Self> {
        const WEIGHTS: &[u8] = include_bytes!("../../../resources/pedal_bilstm.safetensors");
        let device = Device::Cpu;
        let tensors = candle_core::safetensors::load_buffer(WEIGHTS, &device)?;
        Self::from_tensors(tensors, device)
    }

    pub fn load<P: AsRef<Path>>(path: P) -> Result<Self> {
        let device = Device::Cpu;
        let tensors = candle_core::safetensors::load(path, &device)?;
        Self::from_tensors(tensors, device)
    }

    fn from_tensors(tensors: HashMap<String, Tensor>, device: Device) -> Result<Self> {
        let weights = [
            load_lstm_weights(&tensors, 0, false)?,
            load_lstm_weights(&tensors, 0, true)?,
            load_lstm_weights(&tensors, 1, false)?,
            load_lstm_weights(&tensors, 1, true)?,
        ];
        Ok(Self {
            tensors,
            device,
            weights,
            last_prediction: Mutex::new(None),
        })
    }
    fn chunk_forward(&self, seq: &[f32], t_len: usize) -> Result<Vec<f32>> {
        let input = Tensor::from_slice(seq, (t_len, FEATURES), &self.device)?;
        let layer0 = bilstm_layer(&input, &self.weights[0], &self.weights[1], &self.device)?;
        let layer1 = bilstm_layer(&layer0, &self.weights[2], &self.weights[3], &self.device)?;
        let head_w = self.tensors.get("regression_head.weight").unwrap().t()?;
        let head_b = self.tensors.get("regression_head.bias").unwrap();
        let logits = layer1.matmul(&head_w)?.broadcast_add(head_b)?;
        sigmoid(&logits)?.flatten_all()?.to_vec1()
    }
    /// Cache confidence only: threshold changes still regenerate pedal events,
    /// and a changed input (including randomized notes) always reruns inference.
    pub fn cached_forward(&self, seq: &[f32], t_len: usize) -> Result<Vec<f32>> {
        self.cached_forward_with_mode(seq, t_len, true)
    }
    pub fn cached_forward_with_mode(
        &self,
        seq: &[f32],
        t_len: usize,
        optimized: bool,
    ) -> Result<Vec<f32>> {
        let mut cache = self
            .last_prediction
            .lock()
            .unwrap_or_else(|e| e.into_inner());
        if let Some((mode, input, prediction)) = cache.as_ref() {
            if *mode == optimized && input == seq && prediction.len() == t_len {
                return Ok(prediction.clone());
            }
        }
        let prediction = self.forward_with_mode(seq, t_len, optimized)?;
        *cache = if seq.len() <= 8_000_000 {
            Some((optimized, seq.to_vec(), prediction.clone()))
        } else {
            None
        };
        Ok(prediction)
    }
    pub fn forward(&self, seq: &[f32], t_len: usize) -> Result<Vec<f32>> {
        self.forward_with_mode(seq, t_len, true)
    }
    fn chunk_forward_with_mode(
        &self,
        seq: &[f32],
        t_len: usize,
        optimized: bool,
    ) -> Result<Vec<f32>> {
        if optimized {
            self.chunk_forward(seq, t_len)
        } else {
            legacy_model::chunk_forward(&self.tensors, &self.device, seq, t_len)
        }
    }
    pub fn forward_with_mode(
        &self,
        seq: &[f32],
        t_len: usize,
        optimized: bool,
    ) -> Result<Vec<f32>> {
        if t_len <= CHUNK {
            return self.chunk_forward_with_mode(seq, t_len, optimized);
        }

        let mut preds = vec![0.0f32; t_len];
        let mut counts = vec![0.0f32; t_len];

        let mut start = 0usize;
        while start < t_len {
            let end = (start + CHUNK).min(t_len);
            let chunk_len = end - start;
            let chunk_slice = &seq[start * FEATURES..end * FEATURES];

            let chunk_preds = if chunk_len < CHUNK {
                let mut padded = chunk_slice.to_vec();
                padded.resize(CHUNK * FEATURES, 0.0);
                let full_preds = self.chunk_forward_with_mode(&padded, CHUNK, optimized)?;
                full_preds[..chunk_len].to_vec()
            } else {
                self.chunk_forward_with_mode(chunk_slice, chunk_len, optimized)?
            };

            let center = chunk_preds.len() as f32 / 2.0;
            for (i, p) in chunk_preds.iter().enumerate() {
                // A zero weight at the first edge used to produce NaN on long songs.
                let weight = (1.0 - (i as f32 - center).abs() / center).max(f32::EPSILON);
                preds[start + i] += p * weight;
                counts[start + i] += weight;
            }

            start += STRIDE;
        }

        for i in 0..t_len {
            preds[i] /= counts[i];
        }
        Ok(preds)
    }
}
