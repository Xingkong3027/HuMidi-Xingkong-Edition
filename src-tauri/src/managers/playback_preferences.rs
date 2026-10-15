//! Application-owned runtime policy. Old song/cache fields never override it.
use crate::core::config::PlaybackConfig;
use serde_json::{json, Value};

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct PlaybackPreferences {
    pub release_pedal_on_start: bool,
    pub auto_pause: bool,
    pub debug_mode: bool,
    pub auto_focus_roblox: bool,
    pub pause_on_app_focus: bool,
}

impl PlaybackPreferences {
    pub fn from_config(config: &Value) -> Self {
        let old = |key: &str, default| {
            config.get(format!("xk_global_{key}"))
                .and_then(Value::as_bool)
                .or_else(|| config["xk_default_settings"].get(key).and_then(Value::as_bool))
                .or_else(|| config.get(key).and_then(Value::as_bool))
                .unwrap_or(default)
        };
        Self {
            release_pedal_on_start: old("release_pedal_on_start", false),
            auto_pause: old("auto_pause", true),
            debug_mode: old("debug_mode", false),
            auto_focus_roblox: super::window_focus::auto_focus_roblox(config),
            pause_on_app_focus: super::window_focus::pause_on_focus(config),
        }
    }

    pub fn apply(self, config: &mut PlaybackConfig, playlist: bool) {
        config.release_pedal_on_start = self.release_pedal_on_start;
        config.auto_pause = self.auto_pause && !playlist;
        config.debug_mode = self.debug_mode;
    }
}

pub fn migrate(config: &mut Value) {
    let settings = PlaybackPreferences::from_config(config);
    if let Some(map) = config.as_object_mut() {
        for (key, value) in [
            ("xk_global_release_pedal_on_start", settings.release_pedal_on_start),
            ("xk_global_auto_pause", settings.auto_pause),
            ("xk_global_debug_mode", settings.debug_mode),
        ] {
            map.insert(key.into(), json!(value));
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn migrates_saved_import_defaults_once_and_preserves_explicit_global_choices() {
        let mut data = json!({"release_pedal_on_start":false,"auto_pause":true,"debug_mode":false,
            "xk_default_settings":{"release_pedal_on_start":true,"auto_pause":false,"debug_mode":true},
            "auto_focus_roblox":true,"pause_on_app_focus":true});
        migrate(&mut data);
        let prefs = PlaybackPreferences::from_config(&data);
        assert!(prefs.release_pedal_on_start && prefs.debug_mode && prefs.auto_focus_roblox && prefs.pause_on_app_focus);
        assert!(!prefs.auto_pause);
        data["xk_default_settings"] = json!({"release_pedal_on_start":false,"auto_pause":true,"debug_mode":false});
        migrate(&mut data);
        assert_eq!(PlaybackPreferences::from_config(&data), prefs);
    }

    #[test]
    fn app_settings_win_over_conflicting_song_flags_for_every_playback_source() {
        for playlist in [false, true] {
            for release in [false, true] {
                for pause in [false, true] {
                    let prefs = PlaybackPreferences::from_config(&json!({"xk_global_release_pedal_on_start":release,"xk_global_auto_pause":pause,"xk_global_debug_mode":true}));
                    let mut song = PlaybackConfig { release_pedal_on_start: !release, auto_pause: !pause, debug_mode:false, ..Default::default() };
                    let original_tempo = song.tempo;
                    prefs.apply(&mut song, playlist);
                    assert_eq!(song.release_pedal_on_start, release);
                    assert_eq!(song.auto_pause, pause && !playlist);
                    assert!(song.debug_mode);
                    assert_eq!(song.tempo, original_tempo);
                }
            }
        }
    }

    #[test]
    fn unconfigured_and_invalid_values_have_documented_defaults() {
        let prefs = PlaybackPreferences::from_config(&json!({"xk_global_debug_mode":null,"xk_global_auto_pause":"false"}));
        assert!(prefs.auto_pause);
        assert!(!prefs.release_pedal_on_start && !prefs.debug_mode && !prefs.auto_focus_roblox && !prefs.pause_on_app_focus);
    }

    #[test]
    fn running_session_keeps_snapshot_while_the_next_start_uses_new_values() {
        let mut config = json!({"auto_focus_roblox":false,"pause_on_app_focus":false,"xk_global_release_pedal_on_start":false});
        let running = PlaybackPreferences::from_config(&config);
        config["auto_focus_roblox"] = json!(true);
        config["pause_on_app_focus"] = json!(true);
        config["xk_global_release_pedal_on_start"] = json!(true);
        assert!(!running.auto_focus_roblox && !running.pause_on_app_focus && !running.release_pedal_on_start);
        let next = PlaybackPreferences::from_config(&config);
        assert!(next.auto_focus_roblox && next.pause_on_app_focus && next.release_pedal_on_start);
    }

    #[test]
    fn old_package_roundtrips_strip_runtime_flags_without_changing_app_preferences() {
        let dir = tempfile::tempdir().unwrap();
        let store = crate::playlist::PlaylistStore::new(dir.path().join("a")).unwrap();
        let song = json!({"source":{"type":"sheet","sheet_text":"abc","bpm":120,"format_name":"Virtual Piano"},"selected_tracks":[],
            "playback_settings":{"tempo":1.0,"release_pedal_on_start":true,"debug_mode":true,"auto_pause":false,"auto_focus_roblox":true}});
        let item = store.put(None,"old",song,None,None,1.0).unwrap();
        let restored = store.song(item["id"].as_str().unwrap()).unwrap();
        for key in ["release_pedal_on_start","debug_mode","auto_pause","auto_focus_roblox"] {
            assert!(restored["playback_settings"].get(key).is_none());
        }
        for complete in [false,true] {
            let path=dir.path().join(format!("{complete}.humidiplaylist"));
            store.export(&path,complete).unwrap();
            let target=crate::playlist::PlaylistStore::new(dir.path().join(format!("import-{complete}"))).unwrap();
            assert_eq!(target.import(&path).unwrap()["imported"],1);
        }
        assert!(!PlaybackPreferences::from_config(&json!({})).release_pedal_on_start);
    }
}
