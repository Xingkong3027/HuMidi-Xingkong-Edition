use humidi_tauri_lib::invoke_handler;
use humidi_tauri_lib::managers::config_manager::ConfigManager;
use humidi_tauri_lib::state::AppState;
use serde_json::{json, Value};
use tauri::ipc::{CallbackFn, InvokeBody, InvokeResponseBody};
use tauri::test::{get_ipc_response, mock_builder, mock_context, noop_assets, INVOKE_KEY};
use tauri::webview::InvokeRequest;
use tauri::{App, WebviewWindow, WebviewWindowBuilder};

const NO_SUCH_COMMAND: &str = "no_such_command";

struct Harness {
    _app: App<tauri::test::MockRuntime>,
    window: WebviewWindow<tauri::test::MockRuntime>,
    _dir: tempfile::TempDir,
}

impl Harness {
    fn new() -> Self {
        let dir = tempfile::tempdir().unwrap();
        let app = mock_builder()
            .invoke_handler(invoke_handler())
            .manage(AppState::from_config_manager(ConfigManager {
                save_dir: dir.path().join("saves"),
                midi_dir: std::path::PathBuf::new(),
                config_dir: dir.path().to_path_buf(),
                config_path: dir.path().join("config.json"),
            }))
            .build(mock_context(noop_assets()))
            .unwrap();
        let window = WebviewWindowBuilder::new(&app, "main", Default::default())
            .build()
            .unwrap();
        Harness {
            _app: app,
            window,
            _dir: dir,
        }
    }

    fn invoke(&self, cmd: &str, body: Value) -> Result<Value, Value> {
        let request = InvokeRequest {
            cmd: cmd.to_string(),
            callback: CallbackFn(0),
            error: CallbackFn(1),
            url: self.window.url().unwrap(),
            body: InvokeBody::Json(body),
            headers: Default::default(),
            invoke_key: INVOKE_KEY.to_string(),
        };
        get_ipc_response(&self.window, request).map(|response| match response {
            InvokeResponseBody::Json(text) => serde_json::from_str(&text).unwrap(),
            InvokeResponseBody::Raw(_) => Value::Null,
        })
    }
}

fn is_not_found(error: &Value) -> bool {
    error.to_string().contains("not found")
}

#[test]
fn a_command_that_does_not_exist_is_refused_as_not_found() {
    let harness = Harness::new();
    let error = harness.invoke(NO_SUCH_COMMAND, json!({})).unwrap_err();
    assert!(is_not_found(&error), "{error}");
}

#[test]
fn forward_key_is_registered_and_takes_code_and_pressed_the_way_the_frontend_sends_them() {
    let harness = Harness::new();
    harness.invoke("start_binding", json!({})).unwrap();
    harness
        .invoke("forward_key", json!({ "code": "KeyG", "pressed": true }))
        .unwrap();
    assert_eq!(
        harness.invoke("get_hotkeys", json!({})).unwrap(),
        json!(["G", "Ctrl+S"])
    );
}

#[test]
fn forward_key_ignores_a_code_with_no_hotkey_meaning() {
    let harness = Harness::new();
    assert_eq!(
        harness.invoke(
            "forward_key",
            json!({ "code": "NumpadEnter", "pressed": true })
        ),
        Ok(Value::Null)
    );
    assert_eq!(
        harness.invoke("get_hotkeys", json!({})).unwrap(),
        json!(["F6", "Ctrl+S"])
    );
}

#[test]
fn forward_key_refuses_a_request_missing_its_arguments_without_calling_it_unknown() {
    let harness = Harness::new();
    let error = harness.invoke("forward_key", json!({})).unwrap_err();
    assert!(!is_not_found(&error), "{error}");
}

#[test]
fn the_other_hotkey_commands_are_registered() {
    let harness = Harness::new();
    assert_eq!(
        harness.invoke("start_save_binding", json!({})),
        Ok(Value::Null)
    );
    harness
        .invoke("forward_key", json!({ "code": "KeyD", "pressed": true }))
        .unwrap();
    assert_eq!(
        harness.invoke("get_hotkeys", json!({})).unwrap(),
        json!(["F6", "D"])
    );
}

#[test]
fn background_cache_keeps_missing_legacy_curves_playable_through_ipc() {
    let harness = Harness::new();
    let store =
        humidi_tauri_lib::playlist::PlaylistStore::new(harness._dir.path().join("playlist"))
            .unwrap();
    let song = json!({"source":{"type":"sheet","sheet_text":"[et] w r","bpm":120},"selected_tracks":[],"playback_settings":{"tempo":100,"humanization_seed":null,"humanization_mode":"disabled","pedal_style":"hybrid"}});
    let item = store.put(None, "legacy", song, None, None, 1.0).unwrap();
    let id = item["id"].as_str().unwrap();
    let config = json!({"tempo":1,"humanization_on":false,"pedal_style":"hybrid","pedal_ai_mode":"auto","use_ai_pedal":false,"pedal_curve_on":[],"pedal_curve_off":[]});
    harness
        .invoke("playlist_prepare_cache", json!({"id":id,"config":config}))
        .unwrap();
    let detail = harness.invoke("playlist_get", json!({"id":id})).unwrap();
    let settings = &detail["song"]["playback_settings"];
    assert_eq!(settings["pedal_curve_on"], json!([]));
    assert_eq!(settings["pedal_curve_off"], json!([]));
    let mut restored = config;
    restored["pedal_curve_on"] = settings["pedal_curve_on"].clone();
    restored["pedal_curve_off"] = settings["pedal_curve_off"].clone();
    let timeline = harness
        .invoke(
            "compile_notes_from_sheet",
            json!({"config":restored,"sheetText":"[et] w r","bpm":120}),
        )
        .unwrap();
    assert!(timeline["total_dur"].as_f64().unwrap() > 0.0);
    harness
        .invoke("compile_pedal", json!({"config":restored}))
        .unwrap();
    harness
        .invoke(
            "playlist_restore_cache",
            json!({"id":id,"config":restored,"allowLegacy":false}),
        )
        .unwrap();
    let persisted: Value = serde_json::from_slice(
        &std::fs::read(store.root.join(format!("items/{id}.json"))).unwrap(),
    )
    .unwrap();
    assert_eq!(persisted["playback_settings"]["pedal_curve_on"], json!([]));
}

#[test]
fn previously_written_null_curves_are_read_and_exported_without_reimporting() {
    let harness = Harness::new();
    let store =
        humidi_tauri_lib::playlist::PlaylistStore::new(harness._dir.path().join("playlist"))
            .unwrap();
    let item = store.put(None,"affected",json!({"source":{"type":"sheet","sheet_text":"et"},"selected_tracks":[],"playback_settings":{"tempo":1,"tempo_unit":"ratio","random_seed":null,"humanization_on":false}}),None,None,1.0).unwrap();
    let id = item["id"].as_str().unwrap();
    let path = store.root.join(format!("items/{id}.json"));
    let mut damaged: Value = serde_json::from_slice(&std::fs::read(&path).unwrap()).unwrap();
    damaged["playback_settings"]["pedal_curve_on"] = Value::Null;
    damaged["playback_settings"]["pedal_curve_off"] = Value::Null;
    std::fs::write(&path, serde_json::to_vec(&damaged).unwrap()).unwrap();
    let detail = harness.invoke("playlist_get", json!({"id":id})).unwrap();
    assert_eq!(
        detail["song"]["playback_settings"]["pedal_curve_on"],
        json!([])
    );
    assert_eq!(
        detail["song"]["playback_settings"]["pedal_curve_off"],
        json!([])
    );
    let export = harness._dir.path().join("fixed.json");
    harness
        .invoke("playlist_export", json!({"path":export,"complete":false}))
        .unwrap();
    let data: Value = serde_json::from_slice(&std::fs::read(export).unwrap()).unwrap();
    assert_eq!(
        data["entries"][0]["song"]["playback_settings"]["pedal_curve_on"],
        json!([])
    );
}

#[test]
fn real_88_song_import_background_refresh_frontend_json_and_playback_compilation() {
    let Some(package) = std::env::var_os("HUMIDI_REGRESSION_PLAYLIST") else {
        return;
    };
    let Some(bridge) = std::env::var_os("HUMIDI_REGRESSION_FRONTEND_BRIDGE") else {
        return;
    };
    let harness = Harness::new();
    let before_bytes = std::fs::read(&package).unwrap();
    let import = harness
        .invoke("playlist_import", json!({"path":package.to_string_lossy()}))
        .unwrap();
    assert_eq!(import["imported"], 88);
    assert_eq!(import["errors"], json!([]));
    let items = harness.invoke("playlist_list", json!({})).unwrap();
    let details = items
        .as_array()
        .unwrap()
        .iter()
        .map(|item| {
            harness
                .invoke("playlist_get", json!({"id":item["id"]}))
                .unwrap()
        })
        .collect::<Vec<_>>();
    let convert = |details: &[Value], label: &str| -> Vec<Value> {
        let input = harness._dir.path().join(format!("{label}-details.json"));
        let output = harness._dir.path().join(format!("{label}-frontend.json"));
        std::fs::write(&input, serde_json::to_vec(details).unwrap()).unwrap();
        let child = std::process::Command::new("node")
            .arg(&bridge)
            .arg(&input)
            .arg(&output)
            .output()
            .unwrap();
        assert!(
            child.status.success(),
            "{}",
            String::from_utf8_lossy(&child.stderr)
        );
        serde_json::from_slice(&std::fs::read(output).unwrap()).unwrap()
    };
    let original_configs = convert(&details, "imported");
    for request in &original_configs {
        harness
            .invoke(
                "playlist_prepare_cache",
                json!({"id":request["id"],"config":request["config"]}),
            )
            .unwrap();
    }
    let after = details
        .iter()
        .map(|d| {
            harness
                .invoke("playlist_get", json!({"id":d["metadata"]["id"]}))
                .unwrap()
        })
        .collect::<Vec<_>>();
    let configs = convert(&after, "after-background");
    let mut results = Vec::new();
    for ((request, original), detail) in configs.iter().zip(&original_configs).zip(&after) {
        for key in ["pedal_curve_on", "pedal_curve_off"] {
            assert!(detail["song"]["playback_settings"][key].is_array());
            let persisted: Value = serde_json::from_slice(
                &std::fs::read(harness._dir.path().join(format!(
                    "playlist/items/{}.json",
                    request["id"].as_str().unwrap()
                )))
                .unwrap(),
            )
            .unwrap();
            assert!(persisted["playback_settings"][key].is_array());
        }
        assert_eq!(request["config"], original["config"], "{}", request["name"]);
        assert_eq!(request["config"]["tempo"], 1.0);
        let timeline = harness.invoke("compile_notes",json!({"config":request["config"],"selectedTracksInfo":request["selectedTracksInfo"]})).unwrap();
        assert_eq!(timeline["total_dur"], detail["metadata"]["duration"]);
        let pedal = harness
            .invoke("compile_pedal", json!({"config":request["config"]}))
            .unwrap();
        let cached = harness
            .invoke(
                "playlist_restore_cache",
                json!({"id":request["id"],"config":request["config"],"allowLegacy":false}),
            )
            .unwrap();
        assert_eq!(cached["timeline"], timeline, "{}", request["name"]);
        assert_eq!(cached["pedal_intervals"], pedal["pedal_intervals"]);
        results.push(json!({"name":request["name"],"duration":timeline["total_dur"],"notes":timeline["final_notes"].as_array().unwrap().len(),"config_preserved":true,"cache_matches_foreground":true}));
    }
    assert_eq!(std::fs::read(package).unwrap(), before_bytes);
    if let Some(path) = std::env::var_os("HUMIDI_REGRESSION_IPC_REPORT") {
        std::fs::write(path,serde_json::to_vec_pretty(&json!({"songs":results,"imported":88,"errors":[],"frontend_source_executed":true,"real_ipc":true,"real_keyboard_injection":false})).unwrap()).unwrap();
    }
}
