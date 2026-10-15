use humidi_tauri_lib::{
    core::config::PlaybackConfig, playlist::PlaylistStore, state::PlaybackSession,
};
use serde_json::{json, Value};
use std::{fs, io::Read};

#[test]
fn real_88_song_python_package_restores_parameters_and_roundtrips_once() {
    let Some(path) = std::env::var_os("HUMIDI_REGRESSION_PLAYLIST") else {
        return;
    };
    let original = fs::read(&path).unwrap();
    let mut zip = zip::ZipArchive::new(std::io::Cursor::new(&original)).unwrap();
    let manifest: Value = {
        let mut bytes = Vec::new();
        zip.by_name("playlist.json")
            .unwrap()
            .read_to_end(&mut bytes)
            .unwrap();
        serde_json::from_slice(&bytes).unwrap()
    };
    let entries = manifest["entries"].as_array().unwrap();
    let temp = tempfile::tempdir().unwrap();
    let store = PlaylistStore::new(temp.path().join("imported")).unwrap();
    let report = store.import(std::path::Path::new(&path)).unwrap();
    assert_eq!(report["imported"], 88);
    assert_eq!(report["errors"], json!([]));
    let items = store.list().unwrap();
    let mut details = Vec::new();
    for (entry, item) in entries.iter().zip(&items) {
        assert_eq!(item["name"], entry["metadata"]["name"]);
        let id = item["id"].as_str().unwrap();
        let song = store.song(id).unwrap();
        let before = &entry["song"]["playback_settings"];
        let after = &song["playback_settings"];
        assert_eq!(after["tempo"], before["tempo"].as_f64().unwrap() / 100.0);
        assert_eq!(after["tempo_unit"], "ratio");
        for (key, value) in before.as_object().unwrap() {
            if key != "tempo" {
                assert_eq!(&after[key], value, "{}: {key}", item["name"]);
            }
        }
        assert_eq!(song["selected_tracks"], entry["song"]["selected_tracks"]);
        let mut raw = Vec::new();
        zip.by_name(entry["midi_member"].as_str().unwrap())
            .unwrap()
            .read_to_end(&mut raw)
            .unwrap();
        let midi_path = store.midi_path(&song).unwrap();
        assert_eq!(fs::read(&midi_path).unwrap(), raw);
        assert_eq!(
            store.cache(id).unwrap()["metadata"]["playback_settings"]["tempo"],
            1.0
        );
        let mut config: PlaybackConfig = serde_json::from_value(after.clone()).unwrap();
        config.midi_file = midi_path.to_string_lossy().to_string();
        config.humanization_on = after["humanization_mode"] != "disabled";
        let selected = song["selected_tracks"]
            .as_array()
            .unwrap()
            .iter()
            .map(|t| {
                (
                    t["index"].as_i64().unwrap() as i32,
                    t["role"].as_str().unwrap().to_string(),
                )
            })
            .collect::<Vec<_>>();
        let mut session = PlaybackSession::default();
        humidi_tauri_lib::commands::compile_notes_logic(&config, &selected, &mut session).unwrap();
        assert!(session.total_dur > 0.0, "{}", item["name"]);
        if item["name"] == "ninelie" {
            assert!(
                (session.total_dur - 274.81640625).abs() < 1e-6,
                "first song duration {}",
                session.total_dur
            );
        }
        details.push(json!({"name":item["name"],"settings":after,"selected_tracks":song["selected_tracks"],"old_duration":entry["metadata"]["duration"],"compiled_duration":session.total_dur}));
    }
    for complete in [false, true] {
        let path = temp.path().join(if complete {
            "complete.humidiplaylist"
        } else {
            "normal.humidiplaylist"
        });
        store.export(&path, complete).unwrap();
        let restored = PlaylistStore::new(temp.path().join(if complete {
            "roundtrip-complete"
        } else {
            "roundtrip-normal"
        }))
        .unwrap();
        let report = restored.import(&path).unwrap();
        assert_eq!(report["imported"], 88);
        assert_eq!(report["errors"], json!([]));
        for item in restored.list().unwrap() {
            assert_eq!(
                restored.song(item["id"].as_str().unwrap()).unwrap()["playback_settings"]["tempo"],
                1.0
            );
        }
    }
    assert_eq!(fs::read(path).unwrap(), original);
    if let Some(output) = std::env::var_os("HUMIDI_REGRESSION_MIGRATION_REPORT") {
        fs::write(output,serde_json::to_vec_pretty(&json!({"imported":88,"errors":[],"verified_normal_and_complete_roundtrip":true,"songs":details})).unwrap()).unwrap();
    }
}

#[test]
fn v1_cache_only_percentages_keep_event_times_and_native_v3_ratios_stay_ratios() {
    let temp = tempfile::tempdir().unwrap();
    let path = temp.path().join("old.json");
    let event = json!({"time":5.0,"priority":2,"action":"press","key_char":"a","pitch":60});
    fs::write(&path,serde_json::to_vec(&json!({"format":"HuMidi Playlist","version":1,"entries":[{"metadata":{"name":"old"},"playback_data":{"metadata":{"playback_settings":{"tempo":80.0}},"compiled_events":[event]}}]})).unwrap()).unwrap();
    let store = PlaylistStore::new(temp.path().join("old-cache")).unwrap();
    assert_eq!(store.import(&path).unwrap()["imported"], 1);
    let id = store.list().unwrap()[0]["id"].as_str().unwrap().to_string();
    assert_eq!(store.song(&id).unwrap()["playback_settings"]["tempo"], 0.8);
    assert_eq!(store.cache(&id).unwrap()["compiled_events"][0]["time"], 5.0);
    assert_eq!(
        store.cache(&id).unwrap()["metadata"]["playback_settings"]["tempo"],
        0.8
    );
    let song = json!({"source":{"type":"sheet","sheet_text":"abc"},"playback_settings":{"tempo":1.25,"humanization_on":false,"random_seed":null},"selected_tracks":[]});
    let item = store.put(None, "native", song, None, None, 1.0).unwrap();
    assert_eq!(
        store.song(item["id"].as_str().unwrap()).unwrap()["playback_settings"]["tempo"],
        1.25
    );
}

#[test]
fn already_imported_xk9_python_settings_request_rebuild_and_are_saved_once() {
    let temp = tempfile::tempdir().unwrap();
    let store = PlaylistStore::new(temp.path().join("existing")).unwrap();
    let raw = json!({"source":{"type":"sheet","sheet_text":"abc"},"playback_settings":{"tempo":100.0,"humanization_seed":null,"humanization_mode":"disabled"},"selected_tracks":[],"cache_revision":4});
    fs::write(
        store.root.join("items/old.json"),
        serde_json::to_vec(&raw).unwrap(),
    )
    .unwrap();
    fs::write(
        store.root.join("cache/old.json"),
        b"{\"xingkong_cache_version\":4,\"config\":{\"tempo\":100}}",
    )
    .unwrap();
    fs::write(store.root.join("index.json"),b"{\"format\":\"HuMidi Playlist\",\"version\":3,\"items\":[{\"id\":\"old\",\"name\":\"old\"}]}").unwrap();
    assert_eq!(
        store.song("old").unwrap()["playback_settings"]["tempo"],
        1.0
    );
    assert_eq!(store.list().unwrap()[0]["cache_rebuild_required"], true);
    store
        .write_cache(
            "old",
            &json!({"xingkong_cache_version":4,"config":{"tempo":1.0}}),
        )
        .unwrap();
    let saved: Value =
        serde_json::from_slice(&fs::read(store.root.join("items/old.json")).unwrap()).unwrap();
    assert_eq!(saved["playback_settings"]["tempo"], 1.0);
    assert_eq!(saved["playback_settings"]["tempo_unit"], "ratio");
    assert!(saved.get("_legacy_tempo_migrated").is_none());
    assert_eq!(store.list().unwrap()[0]["cache_rebuild_required"], false);
}

#[test]
fn v1_library_directory_supplies_units_before_reading_unmarked_cache_only_items() {
    let temp = tempfile::tempdir().unwrap();
    let old = temp.path().join("old/playlist");
    fs::create_dir_all(old.join("items")).unwrap();
    fs::write(old.join("items/a.json"),serde_json::to_vec(&json!({"metadata":{"source_midi_filename":"a.mid","playback_settings":{"tempo":80.0}},"compiled_events":[]})).unwrap()).unwrap();
    fs::write(
        old.join("index.json"),
        b"{\"format\":\"HuMidi Playlist\",\"version\":1,\"items\":[{\"id\":\"a\",\"name\":\"a\"}]}",
    )
    .unwrap();
    let before = fs::read(old.join("items/a.json")).unwrap();
    let fresh = PlaylistStore::new(temp.path().join("fresh")).unwrap();
    assert_eq!(fresh.import_library(&old).unwrap()["imported"], 1);
    let id = fresh.list().unwrap()[0]["id"].as_str().unwrap().to_string();
    assert_eq!(fresh.song(&id).unwrap()["playback_settings"]["tempo"], 0.8);
    assert_eq!(
        fresh.cache(&id).unwrap()["metadata"]["playback_settings"]["tempo"],
        0.8
    );
    assert_eq!(fs::read(old.join("items/a.json")).unwrap(), before);
}
