use tauri::{Emitter, State};

use crate::managers::hotkey_manager::RawKey;
use crate::managers::shortcuts::{ShortcutAction, ShortcutConfig, ShortcutEvent, CONFIG_KEY};
use crate::state::AppState;

#[tauri::command]
pub fn get_shortcuts(state: State<AppState>) -> Result<ShortcutConfig, String> {
    Ok(state.shortcuts.lock().map_err(|e| e.to_string())?.config())
}

#[tauri::command]
pub fn set_shortcuts(
    state: State<AppState>,
    shortcuts: ShortcutConfig,
) -> Result<ShortcutConfig, String> {
    let save_key = state
        .hotkey_manager
        .lock()
        .map_err(|e| e.to_string())?
        .format_save_hotkey_string();
    if shortcuts
        .bindings
        .values()
        .flatten()
        .flatten()
        .any(|k| k.eq_ignore_ascii_case(&save_key))
    {
        return Err("此快捷键已用于保存演奏，请先更改保存快捷键".into());
    }
    let saved = state
        .shortcuts
        .lock()
        .map_err(|e| e.to_string())?
        .set_config(shortcuts)?;
    crate::commands::patch_app_config(&state, &serde_json::json!({ CONFIG_KEY: saved }))?;
    Ok(saved)
}

#[tauri::command]
pub fn start_shortcut_binding(
    state: State<AppState>,
    action: ShortcutAction,
    slot: usize,
) -> Result<(), String> {
    state
        .hotkey_manager
        .lock()
        .map_err(|e| e.to_string())?
        .cancel_binding();
    state
        .shortcuts
        .lock()
        .map_err(|e| e.to_string())?
        .start_binding(action, slot)
}

#[tauri::command]
pub fn cancel_shortcut_binding(state: State<AppState>) -> Result<(), String> {
    state
        .hotkey_manager
        .lock()
        .map_err(|e| e.to_string())?
        .cancel_binding();
    state
        .shortcuts
        .lock()
        .map_err(|e| e.to_string())?
        .cancel_binding();
    Ok(())
}

#[derive(serde::Serialize)]
pub struct BindingResult {
    pub shortcuts: ShortcutConfig,
    pub save_label: String,
}

#[tauri::command]
pub fn finish_shortcut_binding<R: tauri::Runtime>(
    app: tauri::AppHandle<R>,
    state: State<AppState>,
    combo: String,
) -> Result<BindingResult, String> {
    let mut hotkey = state.hotkey_manager.lock().map_err(|e| e.to_string())?;
    let is_save = hotkey.is_listening_for_save_bind();
    let save_changed = if is_save {
        hotkey.finish_save_binding(&combo)?
    } else {
        false
    };
    let save_label = hotkey.format_save_hotkey_string();
    drop(hotkey);
    if save_changed {
        crate::commands::patch_app_config(&state, &serde_json::json!({"hotkey_save": save_label}))?;
        reserve_save_binding(&app, &state, &save_label);
        let _ = app.emit("hotkey_bound_save_updated", &save_label);
    } else if !is_save {
        let mut manager = state.shortcuts.lock().map_err(|e| e.to_string())?;
        if manager.is_binding() {
            if combo.eq_ignore_ascii_case(&save_label) {
                manager.cancel_binding();
                return Err("此快捷键已用于保存演奏，请先更改保存快捷键".into());
            }
            let changed = manager.finish_binding(&combo)?;
            let config = manager.config();
            drop(manager);
            if changed {
                crate::commands::patch_app_config(&state, &serde_json::json!({CONFIG_KEY:config}))?;
                let _ = app.emit("xk_shortcut_bound", config);
            }
        }
    }
    let shortcuts = state.shortcuts.lock().map_err(|e| e.to_string())?.config();
    Ok(BindingResult {
        shortcuts,
        save_label,
    })
}

/// Call after filtering injected input and before the legacy save-hotkey manager.
pub fn route<R: tauri::Runtime>(
    app: &tauri::AppHandle<R>,
    state: &AppState,
    raw: RawKey,
    is_press: bool,
) -> bool {
    let (save_binding_active, save_key) = state
        .hotkey_manager
        .lock()
        .map(|manager| {
            (
                manager.is_listening_for_save_bind(),
                manager.format_save_hotkey_string(),
            )
        })
        .unwrap_or((false, "Ctrl+S".into()));
    if save_binding_active && is_press && raw == RawKey::Named("Escape") {
        let mut hotkey = state.hotkey_manager.lock().unwrap();
        if hotkey.held_modifiers().is_empty() {
            hotkey.cancel_binding();
            let label = hotkey.format_save_hotkey_string();
            drop(hotkey);
            let _ = app.emit("hotkey_bound_save_updated", label);
            return true;
        }
    }
    let Ok(mut manager) = state.shortcuts.lock() else {
        return false;
    };
    let previous = manager.config();
    let (handled, event) = manager.handle(raw, is_press, save_binding_active);
    let config = manager.config();
    if event == Some(ShortcutEvent::Bound)
        && config
            .bindings
            .values()
            .flatten()
            .flatten()
            .any(|key| key.eq_ignore_ascii_case(&save_key))
    {
        let _ = manager.set_config(previous.clone());
        drop(manager);
        let _ = app.emit("xk_shortcut_bound", previous);
        let _ = app.emit(
            "xk_shortcut_error",
            "此快捷键已用于保存演奏，请先更改保存快捷键",
        );
        return handled;
    }
    drop(manager);
    match event {
        Some(ShortcutEvent::Trigger(action)) => {
            let _ = app.emit(action.channel(), ());
        }
        Some(ShortcutEvent::Bound) => {
            let _ = crate::commands::patch_app_config(
                state,
                &serde_json::json!({ CONFIG_KEY: config }),
            );
            let _ = app.emit("xk_shortcut_bound", config);
        }
        Some(ShortcutEvent::Cancelled) => {
            let _ = app.emit("xk_shortcut_bound", config);
        }
        None => {}
    }
    handled
}

/// Binding Save to an existing playback key moves that key out of the playback actions.
pub fn reserve_save_binding<R: tauri::Runtime>(
    app: &tauri::AppHandle<R>,
    state: &AppState,
    label: &str,
) {
    let Ok(mut manager) = state.shortcuts.lock() else {
        return;
    };
    let mut config = manager.config();
    let before = config.clone();
    for slots in config.bindings.values_mut() {
        for binding in slots {
            if binding
                .as_ref()
                .is_some_and(|s| s.eq_ignore_ascii_case(label))
            {
                *binding = None;
            }
        }
    }
    if before == config {
        return;
    }
    let Ok(saved) = manager.set_config(config) else {
        return;
    };
    drop(manager);
    let _ = crate::commands::patch_app_config(state, &serde_json::json!({CONFIG_KEY:saved}));
    let _ = app.emit("xk_shortcut_bound", saved);
}
