use humidi_tauri_lib::core::midi::MidiParser;
#[allow(dead_code)]
pub mod core {
    pub use humidi_tauri_lib::core::models;
}
#[allow(dead_code)]
#[path = "fixtures/upstream_midi_parser.rs"]
mod upstream;

#[test]
fn user_midi_preserves_upstream_notes_without_repair_or_disk_changes() {
    // The user's file is read only when explicitly provided to this regression.
    // Keep third-party music out of the distributable source tree.
    let Some(path) = std::env::var_os("HUMIDI_REGRESSION_MIDI") else {
        return;
    };
    let original = std::fs::read(&path).unwrap();
    let expected = upstream::MidiParser::parse_bytes(&original, 1.0).unwrap();
    let actual = MidiParser::parse_bytes(&original, 1.0).unwrap();
    let note_signature = |tracks: &[core::models::MidiTrack]| {
        tracks
            .iter()
            .flat_map(|t| &t.notes)
            .map(|n| {
                (
                    n.pitch,
                    n.velocity,
                    n.start_time.to_bits(),
                    n.duration.to_bits(),
                    n.original_track_index,
                    n.channel,
                )
            })
            .collect::<Vec<_>>()
    };
    assert_eq!(note_signature(&actual.0), note_signature(&expected.0));
    assert_eq!(actual.1.events(), expected.1.events());
    assert_eq!(actual.1.time_signatures(), expected.1.time_signatures());
    assert_eq!(actual.2, expected.2);
    assert_eq!(actual.3, expected.3);
    assert_eq!(std::fs::read(&path).unwrap(), original);
    eprintln!(
        "User MIDI: {} tracks, {} notes; notes, timing, tempo and pedal match upstream",
        actual.0.len(),
        note_signature(&actual.0).len()
    );
}

#[test]
fn actual_python_exports_and_library_migrate_with_playable_unmodified_midi() {
    let Some(folder) = std::env::var_os("HUMIDI_REGRESSION_OLD_EXPORTS") else {
        return;
    };
    let folder = std::path::PathBuf::from(folder);
    let original = std::fs::read(std::env::var_os("HUMIDI_REGRESSION_MIDI").unwrap()).unwrap();
    for (n, source) in [
        folder.join("normal.json"),
        folder.join("complete.humidiplaylist"),
        folder.join("old-config/playlist/index.json"),
        folder.join("old-config"),
    ]
    .iter()
    .enumerate()
    {
        let temp = tempfile::tempdir().unwrap();
        let store =
            humidi_tauri_lib::playlist::PlaylistStore::new(temp.path().join("playlist")).unwrap();
        let report = store.import(source).unwrap();
        assert_eq!(report["imported"], 2, "{source:?}: {report}");
        assert_eq!(report["errors"], serde_json::json!([]));
        let mut midi_count = 0;
        for item in store.list().unwrap() {
            let song = store.song(item["id"].as_str().unwrap()).unwrap();
            if song["source"]["type"] == "sheet" {
                assert_eq!(song["source"]["sheet_text"], "[abc] d");
            } else {
                let imported = std::fs::read(store.midi_path(&song).unwrap()).unwrap();
                assert_eq!(imported, original);
                assert!(!MidiParser::parse_bytes(&imported, 1.0)
                    .unwrap()
                    .0
                    .is_empty());
                assert_eq!(song["selected_tracks"][0]["index"], 1);
                assert_eq!(song["playback_settings"]["random_seed"], 42);
                midi_count += 1;
            }
        }
        assert_eq!(midi_count, 1, "migration {n}");
    }
}
