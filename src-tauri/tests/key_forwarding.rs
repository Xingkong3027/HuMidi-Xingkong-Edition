use humidi_tauri_lib::{
    commands::{deliver_key, forward_key},
    core::keyboard_driver::Key,
    managers::{
        config_manager::ConfigManager,
        hotkey_manager::{dom_code_to_raw, RawKey},
        key_delivery::KeySource,
        shortcuts::ShortcutAction,
    },
    state::AppState,
};
use std::sync::{Arc, Mutex};
use tauri::{Listener, Manager};
fn harness() -> (
    tauri::App<tauri::test::MockRuntime>,
    Arc<Mutex<Vec<String>>>,
    tempfile::TempDir,
) {
    let dir = tempfile::tempdir().unwrap();
    let app = tauri::test::mock_app();
    app.manage(AppState::from_config_manager(ConfigManager {
        save_dir: dir.path().join("saves"),
        midi_dir: Default::default(),
        config_dir: dir.path().into(),
        config_path: dir.path().join("config.json"),
    }));
    let seen = Arc::new(Mutex::new(Vec::new()));
    for name in [
        "hotkey_toggle_requested",
        "hotkey_next_requested",
        "hotkey_save_requested",
    ] {
        let output = seen.clone();
        app.listen(name, move |_| output.lock().unwrap().push(name.into()));
    }
    (app, seen, dir)
}
#[test]
fn normal_shortcut_fires_once_in_both_event_orders() {
    for order in [
        [KeySource::Page, KeySource::GlobalHook],
        [KeySource::GlobalHook, KeySource::Page],
    ] {
        let (app, seen, _dir) = harness();
        let state = app.state::<AppState>();
        for source in order {
            deliver_key(app.handle(), &state, RawKey::Named("F6"), true, source);
        }
        assert_eq!(*seen.lock().unwrap(), vec!["hotkey_toggle_requested"]);
        for source in order {
            deliver_key(app.handle(), &state, RawKey::Named("F6"), false, source);
        }
        for source in order {
            deliver_key(app.handle(), &state, RawKey::Named("F6"), true, source);
        }
        assert_eq!(seen.lock().unwrap().len(), 2);
    }
}
#[test]
fn global_save_is_inert_until_its_window_event_confirms_it() {
    let (app, seen, _dir) = harness();
    let state = app.state::<AppState>();
    for code in ["ControlLeft", "KeyS"] {
        deliver_key(
            app.handle(),
            &state,
            dom_code_to_raw(code).unwrap(),
            true,
            KeySource::GlobalHook,
        );
    }
    assert!(seen.lock().unwrap().is_empty());
    for code in ["ControlLeft", "KeyS"] {
        forward_key(app.handle().clone(), app.state(), code.into(), true).unwrap();
    }
    assert_eq!(*seen.lock().unwrap(), vec!["hotkey_save_requested"]);
}
#[test]
fn media_key_mapping_reaches_the_existing_next_song_binding() {
    let (app, seen, _dir) = harness();
    let state = app.state::<AppState>();
    let mut cfg = state.shortcuts.lock().unwrap().config();
    cfg.set_slot(ShortcutAction::Next, 0, Some("MediaNext"))
        .unwrap();
    state.shortcuts.lock().unwrap().set_config(cfg).unwrap();
    forward_key(
        app.handle().clone(),
        app.state(),
        "MediaTrackNext".into(),
        true,
    )
    .unwrap();
    assert_eq!(*seen.lock().unwrap(), vec!["hotkey_next_requested"]);
    assert_eq!(
        dom_code_to_raw("NumpadEnter"),
        Some(RawKey::Named("NumEnter"))
    );
    assert_eq!(dom_code_to_raw("F24"), Some(RawKey::Named("F24")));
}
#[test]
fn injected_key_echo_is_ignored_from_both_sources() {
    let (app, seen, _dir) = harness();
    let state = app.state::<AppState>();
    forward_key(
        app.handle().clone(),
        app.state(),
        "ControlLeft".into(),
        true,
    )
    .unwrap();
    state.injected_echoes.expect(Key::Char('s'), true);
    deliver_key(
        app.handle(),
        &state,
        RawKey::Char('s'),
        true,
        KeySource::GlobalHook,
    );
    forward_key(app.handle().clone(), app.state(), "KeyS".into(), true).unwrap();
    assert!(seen.lock().unwrap().is_empty());
    forward_key(app.handle().clone(), app.state(), "KeyS".into(), false).unwrap();
    forward_key(app.handle().clone(), app.state(), "KeyS".into(), true).unwrap();
    assert_eq!(*seen.lock().unwrap(), vec!["hotkey_save_requested"]);
}
