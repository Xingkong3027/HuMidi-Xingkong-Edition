#[allow(dead_code)]
#[path = "fixtures/upstream_pedal_model.rs"]
mod upstream;
use humidi_tauri_lib::core::{
    compiler::compile_note_events_with_played,
    config::PlaybackConfig,
    models::Note,
    pedal::model::{PedalModel, FEATURES},
};
#[test]
fn compatible_ai_matches_upstream_and_modes_do_not_mix_cached_predictions() {
    let path =
        std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("resources/pedal_bilstm.safetensors");
    let original = upstream::PedalModel::load(&path).unwrap();
    let current = PedalModel::load_embedded().unwrap();
    let mut input = vec![0.; FEATURES * 8];
    for i in 0..8 {
        input[i * FEATURES + 60] = 1.;
        input[i * FEATURES + 128] = 1.;
    }
    let expected = original.forward(&input, 8).unwrap();
    assert_eq!(
        current.cached_forward_with_mode(&input, 8, false).unwrap(),
        expected
    );
    let optimized = current.cached_forward_with_mode(&input, 8, true).unwrap();
    assert_eq!(optimized, current.forward(&input, 8).unwrap());
    assert_eq!(
        current.cached_forward_with_mode(&input, 8, false).unwrap(),
        expected
    );
}
#[test]
fn short_midi_notes_keep_their_release_time_with_both_performance_modes() {
    let mut note = Note::new(1, 60, 64, 1.5, 0.000390625);
    note.hand = "right".into();
    for mode in [false, true] {
        let cfg = PlaybackConfig {
            performance_optimization: mode,
            humanization_on: false,
            ..Default::default()
        };
        let (events, _, played) = compile_note_events_with_played(&cfg, &[note.clone()], &[]);
        assert_eq!(played[0].duration, note.duration);
        assert_eq!(events[0].time, note.start_time);
        assert_eq!(events[1].time, note.end_time());
    }
}
