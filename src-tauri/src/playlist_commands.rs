use crate::core::{
    config::PlaybackConfig,
    input_scan::scan_events,
    midi::TempoMap,
    models::{KeyEvent, Note},
};
use crate::{playlist::PlaylistStore, state::AppState};
use serde_json::{json, Value};
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use tauri::Manager;

static STORE_LOCK: Mutex<()> = Mutex::new(());
fn store(state: &AppState) -> Result<PlaylistStore, String> {
    let dir = state
        .config_manager
        .lock()
        .map_err(|e| e.to_string())?
        .config_dir
        .join("playlist");
    PlaylistStore::new(dir)
}
async fn run<R: tauri::Runtime, T: Send + 'static>(
    app: tauri::AppHandle<R>,
    work: impl FnOnce(&AppState, &PlaylistStore) -> Result<T, String> + Send + 'static,
) -> Result<T, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let _guard = STORE_LOCK.lock().map_err(|e| e.to_string())?;
        let state = app.state::<AppState>();
        let storage = store(&state)?;
        work(&state, &storage)
    })
    .await
    .map_err(|e| e.to_string())?
}
#[tauri::command]
pub async fn playlist_list<R: tauri::Runtime>(
    app: tauri::AppHandle<R>,
) -> Result<Vec<Value>, String> {
    run(app, |_, s| s.list()).await
}
#[tauri::command]
pub async fn playlist_get<R: tauri::Runtime>(
    app: tauri::AppHandle<R>,
    id: String,
) -> Result<Value, String> {
    run(app, move |_, s| s.get(&id)).await
}
#[tauri::command]
pub async fn playlist_put<R: tauri::Runtime>(
    app: tauri::AppHandle<R>,
    id: Option<String>,
    name: String,
    song: Value,
    midi_path: Option<String>,
    duration: f64,
) -> Result<Value, String> {
    run(app, move |_, s| {
        let bytes = if let Some(path) = midi_path.filter(|p| !p.is_empty()) {
            if std::fs::metadata(&path).map_err(|e| e.to_string())?.len() > 128 * 1024 * 1024 {
                return Err("MIDI 文件过大".into());
            }
            Some(std::fs::read(path).map_err(|e| e.to_string())?)
        } else {
            None
        };
        s.put(id.as_deref(), &name, song, bytes, None, duration)
    })
    .await
}
#[tauri::command]
pub async fn playlist_delete<R: tauri::Runtime>(
    app: tauri::AppHandle<R>,
    ids: Vec<String>,
) -> Result<(), String> {
    run(app, move |_, s| s.delete(&ids)).await
}
#[tauri::command]
pub async fn playlist_reorder<R: tauri::Runtime>(
    app: tauri::AppHandle<R>,
    ids: Vec<String>,
) -> Result<(), String> {
    run(app, move |_, s| s.reorder(&ids)).await
}
#[tauri::command]
pub async fn playlist_patch<R: tauri::Runtime>(
    app: tauri::AppHandle<R>,
    ids: Vec<String>,
    patch: Value,
) -> Result<(), String> {
    run(app, move |_, s| s.update_settings(&ids, &patch)).await
}
#[tauri::command]
pub async fn playlist_export<R: tauri::Runtime>(
    app: tauri::AppHandle<R>,
    path: String,
    complete: bool,
) -> Result<usize, String> {
    run(app, move |_, s| s.export(Path::new(&path), complete)).await
}
#[tauri::command]
pub async fn playlist_import<R: tauri::Runtime>(
    app: tauri::AppHandle<R>,
    path: String,
) -> Result<Value, String> {
    run(app, move |_, s| s.import(Path::new(&path))).await
}
#[tauri::command]
pub async fn playlist_import_library<R: tauri::Runtime>(
    app: tauri::AppHandle<R>,
    path: String,
) -> Result<Value, String> {
    run(app, move |_, s| s.import_library(Path::new(&path))).await
}
#[tauri::command]
pub async fn playlist_save_midi<R: tauri::Runtime>(
    app: tauri::AppHandle<R>,
    id: String,
    path: String,
) -> Result<(), String> {
    run(app, move |_, s| {
        let source = s
            .midi_path(&s.song(&id)?)
            .ok_or("此歌曲没有可用的 MIDI 源文件")?;
        let destination = PathBuf::from(path);
        if destination.exists() {
            return Err("目标文件已存在，请选择其他名称".into());
        }
        std::fs::copy(source, destination).map_err(|e| e.to_string())?;
        Ok(())
    })
    .await
}

fn cache_config(mut config: Value) -> Value {
    if let Some(map) = config.as_object_mut() {
        for key in [
            "midi_file",
            "countdown",
            "release_pedal_on_start",
            "countdown_seconds",
            "auto_pause",
            "debug_mode",
            "tempo_unit",
        ] {
            map.remove(key);
        }
    }
    if let Some(map) = config.as_object_mut() {
        map.insert("xk_compiler_revision".into(), json!(2));
        map.insert("xk_pedal_revision".into(), json!(3));
        map.insert("xk_pedal_model".into(), json!("2.1.2-onset"));
    }
    config
}
fn cache_from_session(
    session: &crate::state::PlaybackSession,
    config: &PlaybackConfig,
) -> Result<Value, String> {
    let events = session.merged_events.as_ref().ok_or("请先完成编译")?;
    scan_events(events)?;
    let map = session.tempo_map.as_ref().ok_or("没有时间轴")?;
    Ok(json!({
        "xingkong_cache_version": 4,
        "config": cache_config(serde_json::to_value(config).map_err(|e| e.to_string())?),
        "metadata": {"track_details":[], "compiled_pedal_count":events.iter().filter(|e|e.action=="pedal"&&e.key_char=="down").count(), "playback_settings":config},
        "compiled_events":events,
        "confidence":session.pedal_confidence, "confidence_fps":crate::core::pedal::FPS,
        "visualization": {"final_notes":session.final_notes, "played_notes":session.played_notes.as_ref().or(session.humanized_notes.as_ref()).or(session.final_notes.as_ref()), "total_dur":session.total_dur, "tempo_events":map.events(), "time_signatures":map.time_signatures(), "measure_boundaries":map.get_measure_boundaries(session.total_dur)}
    }))
}

#[tauri::command]
pub async fn playlist_cache_current<R: tauri::Runtime>(
    app: tauri::AppHandle<R>,
    id: String,
    config: PlaybackConfig,
) -> Result<(), String> {
    run(app, move |state, s| {
        let session = state.playback_session.lock().map_err(|e| e.to_string())?;
        s.write_cache(&id, &cache_from_session(&session, &config)?)
    })
    .await
}

/// A background job owns its own session. It never parses into AppState or stops playback.
/// Read/write locks are held briefly; the expensive inference runs outside the library lock.
#[tauri::command]
pub async fn playlist_prepare_cache<R: tauri::Runtime>(
    app: tauri::AppHandle<R>,
    id: String,
    mut config: PlaybackConfig,
) -> Result<(), String> {
    tauri::async_runtime::spawn_blocking(move || {
        let state = app.state::<AppState>();
        if config.pedal_ai_mode != "auto" && config.pedal_ai_mode != "custom" {
            config.pedal_ai_mode =
                if config.pedal_curve_on.is_empty() && config.pedal_curve_off.is_empty() {
                    "auto"
                } else {
                    "custom"
                }
                .into();
        }
        let (storage, snapshot, detail, prediction) = {
            let _guard = STORE_LOCK.lock().map_err(|e| e.to_string())?;
            let storage = store(&state)?;
            let snapshot = storage.song(&id)?;
            let wanted = cache_config(serde_json::to_value(&config).map_err(|e| e.to_string())?);
            if storage.cache(&id).is_ok_and(|cache| {
                cache["xingkong_cache_version"].as_u64() == Some(4) && cache["config"] == wanted
            }) {
                return Ok(());
            }
            let detail = storage.get(&id)?;
            let prediction = storage
                .prediction(&id)
                .ok()
                .filter(|p| prediction_matches(p, &snapshot, &wanted));
            (storage, snapshot, detail, prediction)
        };
        let random_effect = config.humanization_on
            && config.random_seed.is_none()
            && (config.vary_timing
                || config.vary_articulation
                || config.enable_chord_roll
                || config.enable_drift_correction
                || config.enable_tempo_sway
                || config.enable_mistakes);
        if random_effect {
            return Ok(());
        }
        let mut session = crate::state::PlaybackSession::default();
        if snapshot["source"]["type"] == "sheet" {
            let text = snapshot["source"]["sheet_text"]
                .as_str()
                .ok_or("曲谱内容缺失")?;
            let bpm = snapshot["source"]["bpm"].as_f64().unwrap_or(120.0);
            crate::commands::compile_notes_from_sheet_logic(&config, text, bpm, &mut session)?;
        } else {
            let Some(path) = detail["midi_path"].as_str() else {
                return Ok(());
            };
            config.midi_file = path.to_string();
            let selected: Vec<(i32, String)> = snapshot["selected_tracks"]
                .as_array()
                .ok_or("音轨信息缺失")?
                .iter()
                .map(|t| {
                    Ok((
                        t["index"].as_i64().ok_or("音轨编号无效")? as i32,
                        t["role"].as_str().unwrap_or("Auto-Detect").to_string(),
                    ))
                })
                .collect::<Result<_, String>>()?;
            crate::commands::compile_notes_logic(&config, &selected, &mut session)
                .map_err(|e| e.to_string())?;
        }
        let confidence: Option<Vec<f32>> =
            prediction.and_then(|p| serde_json::from_value(p["confidence"].clone()).ok());
        let model = if confidence.is_none() && !config.use_midi_pedal {
            crate::commands::pedal_model_for(&state, &config, || Err("使用内置模型".into()))?
        } else {
            None
        };
        let pedal = crate::commands::compile_pedal_with_confidence(
            &config,
            model.as_deref(),
            &mut session,
            false,
            confidence.as_deref(),
        )?;
        let mut song = snapshot.clone();
        if !pedal.curve_on.is_empty() && !pedal.curve_off.is_empty() {
            config.pedal_curve_on = pedal.curve_on;
            config.pedal_curve_off = pedal.curve_off;
            song["playback_settings"]["pedal_curve_on"] = json!(config.pedal_curve_on);
            song["playback_settings"]["pedal_curve_off"] = json!(config.pedal_curve_off);
        }
        let cache = cache_from_session(&session, &config)?;
        let _guard = STORE_LOCK.lock().map_err(|e| e.to_string())?;
        // An edit, removal or re-import while computing makes this result obsolete.
        let current = storage.song(&id)?;
        if !same_compilation_source(&current, &snapshot) {
            return Ok(());
        }
        let name = current["library_name"]
            .as_str()
            .or(detail["metadata"]["name"].as_str())
            .unwrap_or("MIDI");
        // Keep concurrent rename/runtime preference changes while updating only generated curves.
        let name = name.to_string();
        let mut updated = current;
        // Persist the resolved mode together with generated curves, including old songs
        // whose settings did not yet carry an explicit mode.
        updated["playback_settings"]["pedal_ai_mode"] = json!(config.pedal_ai_mode);
        updated["playback_settings"]["pedal_curve_on"] = json!(config.pedal_curve_on);
        updated["playback_settings"]["pedal_curve_off"] = json!(config.pedal_curve_off);
        storage.put(
            Some(&id),
            &name,
            updated,
            None,
            Some(cache),
            session.total_dur,
        )?;
        Ok(())
    })
    .await
    .map_err(|e| e.to_string())?
}

fn same_compilation_source(current: &Value, snapshot: &Value) -> bool {
    current["source"] == snapshot["source"]
        && current["selected_tracks"] == snapshot["selected_tracks"]
        && cache_config(current["playback_settings"].clone())
            == cache_config(snapshot["playback_settings"].clone())
}

#[tauri::command]
pub async fn playlist_restore_cache<R: tauri::Runtime>(
    app: tauri::AppHandle<R>,
    id: String,
    config: PlaybackConfig,
    allow_legacy: bool,
) -> Result<Value, String> {
    run(app, move |state, s| {
        let mut data = s.cache(&id)?;
        if !data["metadata"]["track_details"].is_array() {
            data["metadata"]["track_details"] = json!([]);
        }
        if !data["metadata"]["compiled_pedal_count"].is_number() {
            data["metadata"]["compiled_pedal_count"] = json!(0);
        }
        let new_cache = matches!(data["xingkong_cache_version"].as_u64(), Some(1 | 2 | 3 | 4));
        let current_cache = data["xingkong_cache_version"].as_u64() == Some(4);
        let requested = cache_config(serde_json::to_value(&config).map_err(|e| e.to_string())?);
        if current_cache && data["config"] != requested {
            return Err("缓存参数已变化，需要重新编译".into());
        }
        if !current_cache && !allow_legacy {
            return Err("旧版缓存将由原始 MIDI 重新编译".into());
        }
        crate::commands::shutdown_playback_now(state);
        let mut session = state.playback_session.lock().map_err(|e| e.to_string())?;
        let timeline = if new_cache {
            let mut events: Vec<KeyEvent> = serde_json::from_value(data["compiled_events"].clone())
                .map_err(|e| e.to_string())?;
            scan_events(&events)?;
            events.sort();
            let viz = &data["visualization"];
            let notes: Vec<Note> =
                serde_json::from_value(viz["final_notes"].clone()).map_err(|e| e.to_string())?;
            let played: Vec<Note> =
                serde_json::from_value(viz["played_notes"].clone()).map_err(|e| e.to_string())?;
            if notes.iter().chain(played.iter()).any(|n| {
                !n.start_time.is_finite()
                    || !n.duration.is_finite()
                    || n.start_time < 0.0
                    || n.duration < 0.0
                    || !(0..=127).contains(&n.pitch)
            }) {
                return Err("缓存音符数据无效".into());
            }
            let tempo: Vec<(f64, u32)> =
                serde_json::from_value(viz["tempo_events"].clone()).map_err(|e| e.to_string())?;
            let sigs: Vec<(f64, u8, u8)> = serde_json::from_value(viz["time_signatures"].clone())
                .map_err(|e| e.to_string())?;
            if tempo
                .iter()
                .any(|(t, b)| !t.is_finite() || *t < 0.0 || *b == 0)
                || sigs
                    .iter()
                    .any(|(t, n, d)| !t.is_finite() || *t < 0.0 || *n == 0 || *d == 0)
            {
                return Err("缓存节拍数据无效".into());
            }
            let duration = viz["total_dur"]
                .as_f64()
                .filter(|v| v.is_finite() && *v > 0.0)
                .ok_or("缓存时长无效")?;
            *session = crate::state::PlaybackSession::default();
            session.final_notes = Some(notes);
            session.humanized_notes = Some(played.clone());
            session.played_notes = Some(played);
            session.note_events = Some(events.iter().filter(|e| e.action != "pedal").cloned().collect());
            session.pedal_events = Some(events.iter().filter(|e| e.action == "pedal").cloned().collect());
            session.notes_config_snapshot = Some(crate::core::session_cache::extract_notes_config(&config));
            session.pedal_config_snapshot = Some(crate::core::session_cache::extract_pedal_config(&config));
            session.merged_events = Some(events);
            session.tempo_map = Some(TempoMap::new(tempo, sigs));
            session.total_dur = duration;
            let confidence: Vec<f32> = serde_json::from_value(data.get("confidence").cloned().unwrap_or(json!([]))).map_err(|e| e.to_string())?;
            if confidence.iter().any(|v| !v.is_finite() || *v < 0.0 || *v > 1.0) { return Err("缓存置信度无效".into()); }
            session.pedal_confidence = confidence;
            viz.clone()
        } else {
            serde_json::to_value(crate::commands::resume_from_save_logic(
                &data,
                &mut session,
            )?)
            .map_err(|e| e.to_string())?
        };
        let intervals = crate::commands::extract_pedal_intervals(
            session.merged_events.as_deref().unwrap_or(&[]),
        );
        Ok(json!({"timeline":timeline,"pedal_intervals":intervals, "confidence":session.pedal_confidence, "confidence_fps":crate::core::pedal::FPS, "curve_on":data["config"]["pedal_curve_on"], "curve_off":data["config"]["pedal_curve_off"]}))
    })
    .await
}

#[cfg(test)]
mod cache_regression_tests {
    use super::*;
    #[test]
    fn runtime_flags_keep_cache_and_note_edits_reject_a_stale_job() {
        let song = json!({"source":{"type":"sheet","sheet_text":"abc"}, "selected_tracks":[], "playback_settings":{"tempo":1.0,"countdown":true}});
        let mut runtime = song.clone();
        runtime["playback_settings"]["countdown"] = json!(false);
        assert!(same_compilation_source(&runtime, &song));
        runtime["playback_settings"]["tempo"] = json!(1.2);
        assert!(!same_compilation_source(&runtime, &song));
        runtime = song.clone();
        runtime["source"]["sheet_text"] = json!("xyz");
        assert!(!same_compilation_source(&runtime, &song));
    }
    #[test]
    fn performance_mode_isolates_predictions_and_old_compilation_revisions() {
        let config = PlaybackConfig::default();
        let wanted = cache_config(serde_json::to_value(&config).unwrap());
        let song = json!({"source":{"type":"sheet","sheet_text":"abc"},"selected_tracks":[]});
        let mut prediction = json!({"config":wanted,"source":song["source"],"selected_tracks":[]});
        assert!(prediction_matches(&prediction, &song, &wanted));
        let mut optimized = config.clone();
        optimized.performance_optimization = true;
        let other = cache_config(serde_json::to_value(&optimized).unwrap());
        assert_ne!(wanted, other);
        assert!(!prediction_matches(&prediction, &song, &other));
        prediction["config"]["pedal_curve_on"] = json!([{ "time":0.0,"value":0.9 }]);
        assert!(prediction_matches(&prediction, &song, &wanted));
        prediction["config"]
            .as_object_mut()
            .unwrap()
            .remove("xk_compiler_revision");
        assert!(!prediction_matches(&prediction, &song, &wanted));
    }
    #[test]
    fn independent_background_session_leaves_the_active_timeline_untouched() {
        let config = PlaybackConfig {
            pedal_style: "none".into(),
            ..Default::default()
        };
        let mut foreground = crate::state::PlaybackSession::default();
        crate::commands::compile_notes_from_sheet_logic(
            &config,
            "[et] w r",
            120.0,
            &mut foreground,
        )
        .unwrap();
        crate::commands::compile_pedal_isolated(&config, None, &mut foreground, false).unwrap();
        let before = serde_json::to_value(&foreground.merged_events).unwrap();
        let mut background = crate::state::PlaybackSession::default();
        crate::commands::compile_notes_from_sheet_logic(&config, "[yu] i o", 90.0, &mut background)
            .unwrap();
        crate::commands::compile_pedal_isolated(&config, None, &mut background, false).unwrap();
        assert_eq!(
            before,
            serde_json::to_value(&foreground.merged_events).unwrap()
        );
        assert_ne!(foreground.total_dur, background.total_dur);
        background.pedal_confidence = vec![0.2, 0.7];
        let cache = cache_from_session(&background, &config).unwrap();
        assert_eq!(cache["confidence"], json!([0.2f32, 0.7f32]));
        assert_eq!(cache["xingkong_cache_version"], 4);
    }
}

fn prediction_matches(prediction: &Value, song: &Value, wanted: &Value) -> bool {
    let mut existing = prediction["config"].clone();
    let mut requested = wanted.clone();
    for v in [&mut existing, &mut requested] {
        if let Some(map) = v.as_object_mut() {
            map.remove("pedal_curve_on");
            map.remove("pedal_curve_off");
            map.remove("pedal_ai_mode");
        }
    }
    prediction["source"] == song["source"]
        && prediction["selected_tracks"] == song["selected_tracks"]
        && existing == requested
}
