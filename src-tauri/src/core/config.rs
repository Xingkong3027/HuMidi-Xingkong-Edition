use serde::{Deserialize, Serialize};

use crate::core::pedal::curve::ThresholdNode;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct PlaybackConfig {
    pub midi_file: String,
    pub midi_clip_invalid_data: bool,
    pub tempo: f64,
    pub transpose: i32,
    pub countdown: bool,
    pub release_pedal_on_start: bool,
    pub countdown_seconds: u32,
    pub trim_enabled: bool,
    pub trim_auto: bool,
    pub trim_start_seconds: f64,
    pub trim_end_seconds: f64,
    pub auto_pause: bool,
    pub performance_optimization: bool,
    pub humanization_on: bool,
    #[serde(alias = "humanization_seed")]
    pub random_seed: Option<u64>,
    pub use_88_key_layout: bool,
    pub pedal_style: String,
    #[serde(default = "legacy_pedal_ai_mode")]
    pub pedal_ai_mode: String,
    pub pedal_curve_on: Vec<ThresholdNode>,
    pub pedal_curve_off: Vec<ThresholdNode>,
    pub debug_mode: bool,
    pub simulate_hands: bool,
    pub vary_velocity: bool,
    pub enable_chord_roll: bool,
    pub vary_timing: bool,
    pub timing_variance: f64,
    pub vary_articulation: bool,
    pub articulation: f64,
    pub enable_drift_correction: bool,
    pub drift_decay_factor: f64,
    pub enable_mistakes: bool,
    pub mistake_chance: f64,
    pub enable_tempo_sway: bool,
    pub tempo_sway_intensity: f64,
    pub invert_tempo_sway: bool,
    pub use_midi_pedal: bool,
    pub use_ai_pedal: bool,
    pub pedal_before_humanize: bool,
}

impl Default for PlaybackConfig {
    fn default() -> Self {
        PlaybackConfig {
            midi_file: String::new(),
            midi_clip_invalid_data: false,
            tempo: 1.0,
            transpose: 0,
            countdown: true,
            release_pedal_on_start: false,
            countdown_seconds: 3,
            trim_enabled: false,
            trim_auto: true,
            trim_start_seconds: 0.0,
            trim_end_seconds: 0.0,
            auto_pause: true,
            performance_optimization: false,
            humanization_on: true,
            random_seed: None,
            use_88_key_layout: false,
            pedal_style: "none".to_string(),
            pedal_ai_mode: "auto".to_string(),
            pedal_curve_on: Vec::new(),
            pedal_curve_off: Vec::new(),
            debug_mode: false,
            simulate_hands: false,
            vary_velocity: false,
            enable_chord_roll: false,
            vary_timing: false,
            timing_variance: 0.0,
            vary_articulation: false,
            articulation: 0.0,
            enable_drift_correction: false,
            drift_decay_factor: 0.0,
            enable_mistakes: false,
            mistake_chance: 0.0,
            enable_tempo_sway: false,
            tempo_sway_intensity: 0.0,
            invert_tempo_sway: false,
            use_midi_pedal: false,
            use_ai_pedal: true,
            pedal_before_humanize: true,
        }
    }
}

fn legacy_pedal_ai_mode() -> String {
    "legacy".into()
}
