#![allow(dead_code)]
pub mod core {
    pub use humidi_tauri_lib::core::{config, midi, models};
}
#[path = "fixtures/upstream_212_pedal.rs"]
mod upstream;
use humidi_tauri_lib::core::{
    config::PlaybackConfig,
    models::Note,
    pedal::{self, curve::ThresholdCurves},
};
fn notes() -> Vec<Note> {
    let mut n = Note::new(0, 60, 80, 0.0, 2.0);
    n.hand = "right".into();
    vec![n]
}
fn signature(
    events: &[humidi_tauri_lib::core::models::KeyEvent],
) -> Vec<(f64, i32, String, String)> {
    events
        .iter()
        .map(|e| (e.time, e.priority, e.action.clone(), e.key_char.clone()))
        .collect()
}
#[test]
fn onset_features_match_upstream_for_held_repeated_and_overlapping_notes() {
    let mut n = notes();
    n.push(Note::new(1, 60, 64, 2.0, 0.5));
    n.push(Note::new(2, 60, 64, 3.0, 0.5));
    n.push(Note::new(3, 61, 64, 0.5, 0.8));
    assert_eq!(
        pedal::build_input_features(&n, 50.0, 180),
        upstream::build_input_features(&n, 50.0, 180)
    );
}
#[test]
fn automatic_and_custom_pedal_events_match_upstream_and_auto_stays_auto() {
    let n = notes();
    let preds: Vec<f32> = (0..101)
        .map(|i| 0.5 + 0.45 * (i as f32 / 50.0 * std::f32::consts::TAU * 3.0).sin())
        .collect();
    let (expected, meta) = upstream::process_ai_predictions(preds.clone(), &n, 2.0, 50.0, None);
    let curves = meta.unwrap().curves;
    let mut cfg = PlaybackConfig {
        pedal_style: "ai".into(),
        pedal_ai_mode: "auto".into(),
        pedal_curve_on: curves.on.clone(),
        pedal_curve_off: curves.off.clone(),
        ..Default::default()
    };
    let actual = pedal::events_from_confidence(&cfg, &n, &preds).unwrap().0;
    assert_eq!(signature(&actual), signature(&expected));
    // Saved automatic display curves cannot silently turn a later regeneration into custom mode.
    assert_eq!(
        signature(&pedal::events_from_confidence(&cfg, &n, &preds).unwrap().0),
        signature(&expected)
    );
    cfg.pedal_ai_mode = "custom".into();
    let (expected, _) =
        upstream::process_ai_predictions(preds.clone(), &n, 2.0, 50.0, Some(&curves));
    assert_eq!(
        signature(&pedal::events_from_confidence(&cfg, &n, &preds).unwrap().0),
        signature(&expected)
    );
    cfg.pedal_curve_on.clear();
    cfg.pedal_curve_off.clear();
    assert_eq!(
        signature(&pedal::events_from_confidence(&cfg, &n, &preds).unwrap().0),
        signature(&expected)
    );
}
#[test]
fn older_saved_curves_are_preserved_as_custom_but_new_defaults_use_auto() {
    let cfg:PlaybackConfig=serde_json::from_value(serde_json::json!({"pedal_style":"ai","pedal_curve_on":[{"time":0,"value":0.6}],"pedal_curve_off":[{"time":0,"value":0.3}]})).unwrap();
    assert_eq!(cfg.pedal_ai_mode, "legacy");
    assert_eq!(PlaybackConfig::default().pedal_ai_mode, "auto");
    let curves = ThresholdCurves {
        on: cfg.pedal_curve_on.clone(),
        off: cfg.pedal_curve_off.clone(),
    };
    let n = notes();
    let preds: Vec<f32> = (0..101)
        .map(|i| 0.5 + 0.45 * (i as f32 / 50.0 * std::f32::consts::TAU * 3.0).sin())
        .collect();
    let (expected, _) =
        upstream::process_ai_predictions(preds.clone(), &n, 2.0, 50.0, Some(&curves));
    assert_eq!(
        signature(&pedal::events_from_confidence(&cfg, &n, &preds).unwrap().0),
        signature(&expected)
    );
}
