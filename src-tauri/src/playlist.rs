//! Xingkong playlist storage. v3 retains the Python song/cache member layout;
//! tempo units are migrated explicitly, and caches are validated before playback.
use crate::core::atomic_write::write_json_atomic;
use serde_json::{json, Value};
use std::collections::HashSet;
use std::fs;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
mod migration;

const MAX_FILE: u64 = 128 * 1024 * 1024;
const MAX_PACKAGE: u64 = 1024 * 1024 * 1024;
const MAX_ITEMS: usize = 10000;

pub struct PlaylistStore {
    pub root: PathBuf,
}

fn string<'a>(v: &'a Value, key: &str) -> &'a str {
    v[key].as_str().unwrap_or("")
}
fn read_json(path: &Path) -> Result<Value, String> {
    if fs::metadata(path).map_err(|e| e.to_string())?.len() > MAX_FILE {
        return Err("文件超过 128 MB 限制".into());
    }
    serde_json::from_slice(&fs::read(path).map_err(|e| e.to_string())?).map_err(|e| e.to_string())
}
fn write_json(path: &Path, value: &Value) -> Result<(), String> {
    write_json_atomic(path, value).map_err(|e| e.to_string())
}
fn id_valid(id: &str) -> bool {
    !id.is_empty()
        && id.len() <= 80
        && id
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'_')
}
fn new_id() -> String {
    format!("{:032x}", rand::random::<u128>())
}
fn now() -> String {
    chrono::Utc::now().to_rfc3339()
}
fn check_source(bytes: &[u8]) -> Result<(), String> {
    if bytes.len() as u64 > MAX_FILE || !bytes.starts_with(b"MThd") {
        return Err("不是有效的 MIDI 文件（缺少 MThd 文件头）".into());
    }
    Ok(())
}

impl PlaylistStore {
    pub fn new(root: PathBuf) -> Result<Self, String> {
        for sub in ["items", "midi", "cache", "predictions"] {
            fs::create_dir_all(root.join(sub)).map_err(|e| e.to_string())?;
        }
        Ok(Self { root })
    }
    fn path(&self, sub: &str, id: &str) -> Result<PathBuf, String> {
        if !id_valid(id) {
            return Err("无效的歌曲编号".into());
        }
        Ok(self.root.join(sub).join(format!("{id}.json")))
    }
    fn index(&self) -> Result<Vec<Value>, String> {
        let path = self.root.join("index.json");
        if !path.exists() {
            return Ok(vec![]);
        }
        match read_json(&path).and_then(|v| {
            v["items"]
                .as_array()
                .cloned()
                .ok_or_else(|| "歌单索引损坏".into())
        }) {
            Ok(items) => Ok(items),
            Err(_) => {
                fs::copy(
                    &path,
                    self.root.join(format!("index.corrupt.{}.json", new_id())),
                )
                .map_err(|e| e.to_string())?;
                let backup = self.root.join("index.backup.json");

                let mut recovered = read_json(&backup)
                    .ok()
                    .and_then(|v| v["items"].as_array().cloned())
                    .unwrap_or_default();
                for entry in fs::read_dir(self.root.join("items"))
                    .map_err(|e| e.to_string())?
                    .flatten()
                {
                    let p = entry.path();
                    let id = p.file_stem().and_then(|v| v.to_str()).unwrap_or("");
                    if !id_valid(id) || recovered.iter().any(|i| string(i, "id") == id) {
                        continue;
                    }
                    if let Ok(song) = self.song(id) {
                        recovered.push(json!({"id":id,"name":song["library_name"].as_str().or(song["source"]["original_filename"].as_str()).filter(|s|!s.is_empty()).unwrap_or(id),"duration":0.0,"created_at":now(),"modified_at":now(),"humanization_mode":song["playback_settings"]["humanization_mode"],"random_seed_mode":song["playback_settings"]["humanization_seed_mode"]}));
                    }
                }
                write_json(
                    &path,
                    &json!({"format":"HuMidi Playlist","version":3,"items":recovered}),
                )?;
                Ok(recovered)
            }
        }
    }
    fn save_index(&self, items: &[Value]) -> Result<(), String> {
        let current = self.root.join("index.json");
        if let Ok(valid) = read_json(&current) {
            if valid["items"].is_array() {
                write_json(&self.root.join("index.backup.json"), &valid)?;
            }
        }
        write_json(
            &current,
            &json!({"format":"HuMidi Playlist","version":3,"items":items}),
        )
    }
    pub fn list(&self) -> Result<Vec<Value>, String> {
        let mut items = self.index()?;
        for item in &mut items {
            let id = string(item, "id").to_owned();
            let song = match self.song(&id) {
                Ok(song) => song,
                Err(e) => {
                    item["error"] = json!(e);
                    item["midi_available"] = json!(false);
                    item["sheet_available"] = json!(false);
                    item["cache_available"] = json!(false);
                    continue;
                }
            };
            item["source_type"] = json!(if string(&song["source"], "type") == "sheet" {
                "sheet"
            } else {
                "midi"
            });
            let settings = &song["playback_settings"];
            item["humanization_active"] = if settings["humanization_mode"] == "global" {
                Value::Null
            } else {
                json!(
                    settings["humanization_mode"] != "disabled"
                        && settings["humanization_on"] != false
                        && [
                            "simulate_hands",
                            "vary_timing",
                            "vary_articulation",
                            "enable_chord_roll",
                            "enable_drift_correction",
                            "enable_tempo_sway",
                            "enable_mistakes"
                        ]
                        .iter()
                        .any(|key| settings[*key] == true)
                )
            };
            item["random_effect_active"] = json!([
                "vary_timing",
                "vary_articulation",
                "enable_chord_roll",
                "enable_drift_correction",
                "enable_tempo_sway",
                "enable_mistakes"
            ]
            .iter()
            .any(|key| settings[*key] == true));
            item["midi_available"] = json!(self.midi_path(&song).is_some());
            item["sheet_available"] = json!(!string(&song["source"], "sheet_text").is_empty());
            item["cache_available"] =
                json!(self.path("cache", &id)?.exists() || song.get("legacy_playback").is_some());
            // Read the lightweight song marker, not every large compiled-event file.
            item["cache_rebuild_required"] = json!(
                (item["midi_available"] == true || item["sheet_available"] == true)
                    && item["cache_available"] == true
                    && (song["cache_revision"].as_u64() != Some(4)
                        || song["_legacy_tempo_migrated"] == true)
            );
        }
        Ok(items)
    }
    pub fn song(&self, id: &str) -> Result<Value, String> {
        self.song_with_unit(id, None)
    }
    fn song_with_unit(&self, id: &str, declared: Option<&str>) -> Result<Value, String> {
        let mut raw = read_json(&self.path("items", id)?)?;
        if raw.get("compiled_events").is_some() {
            // v1 cache-only entries stay readable without altering the original library.
            let metadata = &raw["metadata"];
            let mut song = json!({"song_version":3,"source":{"type":"midi","original_filename":metadata["source_midi_filename"],"original_path":"","local_midi_filename":""},"playback_settings":metadata["playback_settings"],"selected_tracks":[],"legacy_cache_only":true,"legacy_playback":raw});
            migration::normalize_song(&mut song, declared)?;
            migration::normalize_cache(&mut song["legacy_playback"], declared)?;
            return Ok(song);
        }
        if !raw.is_object() {
            return Err("歌曲数据格式错误".into());
        }
        migration::normalize_song(&mut raw, declared)?;
        Ok(raw)
    }
    pub fn midi_path(&self, song: &Value) -> Option<PathBuf> {
        if string(&song["source"], "type") == "sheet" {
            return None;
        }
        let local = string(&song["source"], "local_midi_filename");
        if !local.is_empty() && !local.contains(['/', '\\', ':']) && local != "." && local != ".." {
            let p = self.root.join("midi").join(local);
            if p.is_file() {
                return Some(p);
            }
        }
        let path = PathBuf::from(string(&song["source"], "original_path"));
        if path.is_file() {
            Some(path)
        } else {
            None
        }
    }
    pub fn get(&self, id: &str) -> Result<Value, String> {
        let song = self.song(id)?;
        let metadata = self
            .list()?
            .into_iter()
            .find(|v| string(v, "id") == id)
            .ok_or("歌曲不存在")?;
        let path = self
            .midi_path(&song)
            .map(|p| p.to_string_lossy().to_string());
        Ok(
            json!({"metadata":metadata,"song":song,"midi_path":path,"cache_path":self.path("cache",id)?.to_string_lossy()}),
        )
    }
    pub fn put(
        &self,
        id: Option<&str>,
        name: &str,
        mut song: Value,
        midi_bytes: Option<Vec<u8>>,
        mut cache: Option<Value>,
        duration: f64,
    ) -> Result<Value, String> {
        if !song.is_object()
            || !song["source"].is_object()
            || !song["playback_settings"].is_object()
        {
            return Err("歌曲缺少来源或播放参数".into());
        }
        migration::normalize_song(&mut song, None)?;
        let migrated = song["_legacy_tempo_migrated"] == true;
        song.as_object_mut()
            .unwrap()
            .remove("_legacy_tempo_migrated");
        if let Some(data) = cache.as_mut() {
            migration::normalize_cache(data, None)?;
        }
        let mut items = self.index()?;
        let item_id = id.map(str::to_string).unwrap_or_else(new_id);
        if !id_valid(&item_id) {
            return Err("无效的歌曲编号".into());
        }
        if id.is_some() && !items.iter().any(|i| string(i, "id") == item_id) {
            return Err("歌曲不存在".into());
        }
        if items.len() >= MAX_ITEMS && id.is_none() {
            return Err("歌单最多容纳 10000 首歌曲".into());
        }
        if name.trim().is_empty() {
            return Err("歌曲名称不能为空".into());
        }
        let previous = if id.is_some() {
            Some(self.song(&item_id)?)
        } else {
            None
        };
        let new_source = midi_bytes.is_some();
        let sheet = string(&song["source"], "type") == "sheet";
        if sheet {
            if string(&song["source"], "sheet_text").trim().is_empty() {
                return Err("曲谱内容不能为空".into());
            }
        } else if let Some(bytes) = midi_bytes {
            check_source(&bytes)?;
            let filename = format!("{item_id}.mid");
            fs::write(self.root.join("midi").join(&filename), bytes).map_err(|e| e.to_string())?;
            song["source"]["local_midi_filename"] = json!(filename);
            song["source"]["midi_revision"] = json!(new_id());
        } else if let Some(old) = previous.as_ref() {
            // Updating settings without MIDI bytes must retain the owned source.
            if !sheet && old["source"]["local_midi_filename"].is_string() {
                song["source"]["local_midi_filename"] =
                    old["source"]["local_midi_filename"].clone();
            }
        }
        song["song_version"] = json!(3);
        song["library_name"] = json!(name.trim());
        if let Some(settings) = song["playback_settings"].as_object_mut() {
            settings.remove("midi_file");
        }
        let unchanged = previous.as_ref().is_some_and(|old| {
            old["source"] == song["source"]
                && compilation_settings(old["playback_settings"].clone())
                    == compilation_settings(song["playback_settings"].clone())
                && old["selected_tracks"] == song["selected_tracks"]
        }) && !new_source
            && !migrated;
        let cache_path = self.path("cache", &item_id)?;
        if let Some(cache) = cache {
            song["cache_revision"] = if migrated {
                Value::Null
            } else {
                cache["xingkong_cache_version"].clone()
            };
            write_json(&cache_path, &cache)?;
        } else if !unchanged && cache_path.exists() {
            if !new_source {
                if let (Some(old), Ok(data)) = (previous.as_ref(), read_json(&cache_path)) {
                    self.write_prediction(&item_id, old, &data)?;
                }
            }
            fs::remove_file(&cache_path).map_err(|e| e.to_string())?;
        }
        if new_source {
            let _ = fs::remove_file(self.path("predictions", &item_id)?);
        }
        if !unchanged && !cache_path.exists() {
            song.as_object_mut().unwrap().remove("cache_revision");
        } else if unchanged && song.get("cache_revision").is_none() {
            if let Some(old) = previous.as_ref() {
                song["cache_revision"] = old["cache_revision"].clone();
            }
        }
        song["cache_available"] = json!(cache_path.exists());
        write_json(&self.path("items", &item_id)?, &song)?;
        let original = string(&song["source"], "original_filename");
        let mut metadata = json!({"id":item_id,"name":name.trim(),"source_midi_filename":original,"source_type":if sheet {"sheet"}else{"midi"},"source_label":if sheet {"Virtual Piano"}else{original},"created_at":now(),"modified_at":now(),"duration":duration.max(0.0),"humanization_mode":song["playback_settings"]["humanization_mode"],"random_seed_mode":song["playback_settings"]["humanization_seed_mode"]});
        if let Some(index) = items.iter().position(|v| string(v, "id") == item_id) {
            metadata["created_at"] = items[index]["created_at"].clone();
            items[index] = metadata.clone();
        } else {
            items.push(metadata.clone());
        }
        self.save_index(&items)?;
        Ok(metadata)
    }
    pub fn update_settings(&self, ids: &[String], patch: &Value) -> Result<(), String> {
        if !patch.is_object() {
            return Err("参数必须是对象".into());
        }
        for id in ids {
            self.song(id)?;
        }
        for id in ids {
            let mut song = self.song(id)?;
            let changed = patch.as_object().unwrap().keys().any(|k| {
                k.starts_with("humanization_")
                    || [
                        "simulate_hands",
                        "enable_chord_roll",
                        "vary_timing",
                        "timing_variance",
                        "vary_articulation",
                        "articulation",
                        "enable_drift_correction",
                        "drift_decay_factor",
                        "enable_tempo_sway",
                        "tempo_sway_intensity",
                        "invert_tempo_sway",
                        "enable_mistakes",
                        "mistake_chance",
                    ]
                    .contains(&k.as_str())
            });
            for (key, value) in patch.as_object().unwrap() {
                song["playback_settings"][key] = value.clone();
            }
            if changed
                && song["playback_settings"]["humanization_seed_mode"] == "fixed_random"
                && patch.get("random_seed").is_none()
            {
                song["playback_settings"]["random_seed"] = json!(rand::random::<u32>());
                song["playback_settings"]
                    .as_object_mut()
                    .unwrap()
                    .remove("humanization_seed");
            }
            let item = self.get(id)?;
            self.put(
                Some(id),
                string(&item["metadata"], "name"),
                song,
                None,
                None,
                item["metadata"]["duration"].as_f64().unwrap_or(0.0),
            )?;
        }
        Ok(())
    }
    pub fn delete(&self, ids: &[String]) -> Result<(), String> {
        let set: HashSet<&str> = ids.iter().map(String::as_str).collect();
        for id in &set {
            self.path("items", id)?;
        }
        let items = self.index()?;
        let retained: Vec<_> = items
            .into_iter()
            .filter(|i| !set.contains(string(i, "id")))
            .collect();
        // Commit index first. An interrupted cleanup leaves harmless orphan files.
        self.save_index(&retained)?;
        for id in set {
            if let Ok(song) = self.song(id) {
                let local = string(&song["source"], "local_midi_filename");
                if local == format!("{id}.mid") || local == format!("{id}.midi") {
                    let _ = fs::remove_file(self.root.join("midi").join(local));
                }
            }
            let _ = fs::remove_file(self.path("items", id)?);
            let _ = fs::remove_file(self.path("cache", id)?);
            let _ = fs::remove_file(self.path("predictions", id)?);
        }
        Ok(())
    }
    pub fn reorder(&self, ids: &[String]) -> Result<(), String> {
        let items = self.index()?;
        let unique: HashSet<_> = ids.iter().collect();
        if unique.len() != items.len() || ids.len() != items.len() {
            return Err("排序必须包含全部歌曲且不能重复".into());
        }
        let ordered: Result<Vec<_>, _> = ids
            .iter()
            .map(|id| {
                items
                    .iter()
                    .find(|i| string(i, "id") == id)
                    .cloned()
                    .ok_or("排序包含未知歌曲")
            })
            .collect();
        self.save_index(&ordered?)
    }
    pub fn cache(&self, id: &str) -> Result<Value, String> {
        self.cache_with_unit(id, None)
    }
    fn cache_with_unit(&self, id: &str, declared: Option<&str>) -> Result<Value, String> {
        let p = self.path("cache", id)?;
        if p.exists() {
            let mut data = read_json(&p)?;
            migration::normalize_cache(&mut data, declared)?;
            Ok(data)
        } else {
            let song = self.song_with_unit(id, declared)?;
            song.get("legacy_playback")
                .cloned()
                .ok_or_else(|| "歌曲没有缓存".into())
        }
    }
    pub fn write_cache(&self, id: &str, data: &Value) -> Result<(), String> {
        let mut song = self.song(id)?;
        song.as_object_mut()
            .unwrap()
            .remove("_legacy_tempo_migrated");
        self.write_prediction(id, &song, data)?;
        write_json(&self.path("cache", id)?, data)?;
        song["cache_revision"] = data["xingkong_cache_version"].clone();
        song["cache_available"] = json!(true);
        write_json(&self.path("items", id)?, &song)
    }
    fn write_prediction(&self, id: &str, song: &Value, data: &Value) -> Result<(), String> {
        if data["confidence"].as_array().is_some_and(|a| !a.is_empty()) {
            write_json(
                &self.path("predictions", id)?,
                &json!({"config":data["config"], "confidence":data["confidence"], "source":song["source"], "selected_tracks":song["selected_tracks"]}),
            )?;
        }
        Ok(())
    }
    pub fn prediction(&self, id: &str) -> Result<Value, String> {
        read_json(&self.path("predictions", id)?)
    }

    pub fn export(&self, path: &Path, complete: bool) -> Result<usize, String> {
        let items = self.index()?;
        let mut entries = Vec::new();
        let mut zip_bytes = std::io::Cursor::new(Vec::new());
        let mut archive = zip::ZipWriter::new(&mut zip_bytes);
        let options = zip::write::SimpleFileOptions::default()
            .compression_method(zip::CompressionMethod::Deflated);
        for metadata in &items {
            let id = string(metadata, "id");
            let mut song = self.song(id)?;
            let mut entry =
                json!({"metadata":metadata,"song":{},"midi_member":"","cache_member":""});
            if !complete
                && self.midi_path(&song).is_none()
                && string(&song["source"], "type") != "sheet"
            {
                let mut data = self.cache(id)?;
                migration::normalize_cache(&mut data, None)?;
                entry["playback_data"] = data;
            }
            if complete {
                if let Some(p) = self.midi_path(&song) {
                    if fs::metadata(&p).map_err(|e| e.to_string())?.len() > MAX_FILE {
                        return Err("MIDI 文件过大".into());
                    }
                    let member = format!("songs/{id}.mid");
                    archive
                        .start_file(&member, options)
                        .map_err(|e| e.to_string())?;
                    archive
                        .write_all(&fs::read(p).map_err(|e| e.to_string())?)
                        .map_err(|e| e.to_string())?;
                    entry["midi_member"] = json!(member);
                }
                if let Ok(mut data) = self.cache(id) {
                    migration::normalize_cache(&mut data, None)?;
                    if let Some(s) = data["metadata"]["playback_settings"].as_object_mut() {
                        s.remove("midi_file");
                    }
                    let member = format!("cache/{id}.json");
                    archive
                        .start_file(&member, options)
                        .map_err(|e| e.to_string())?;
                    archive
                        .write_all(&serde_json::to_vec(&data).map_err(|e| e.to_string())?)
                        .map_err(|e| e.to_string())?;
                    entry["cache_member"] = json!(member);
                }
                song["source"]["original_path"] = json!("");
            } else if let Some(p) = self.midi_path(&song) {
                song["source"]["original_path"] = json!(p.to_string_lossy());
            }
            song["source"]["local_midi_filename"] = json!("");
            if let Some(s) = song["playback_settings"].as_object_mut() {
                s.remove("midi_file");
            }
            if let Some(s) = song.as_object_mut() {
                s.remove("legacy_playback");
                s.remove("_legacy_tempo_migrated");
            }
            entry["song"] = song;
            entries.push(entry);
        }
        let manifest = json!({"format":"HuMidi Playlist","version":3,"tempo_unit":"ratio","producer":{"engine":"rust","version":env!("CARGO_PKG_VERSION")},"export_type":if complete {"complete"}else{"normal"},"exported_at":now(),"entries":entries});
        if complete {
            archive
                .start_file("playlist.json", options)
                .map_err(|e| e.to_string())?;
            archive
                .write_all(&serde_json::to_vec(&manifest).map_err(|e| e.to_string())?)
                .map_err(|e| e.to_string())?;
            archive.finish().map_err(|e| e.to_string())?;
            let temp = path.with_extension(format!("{}.tmp", new_id()));
            fs::write(&temp, zip_bytes.into_inner()).map_err(|e| e.to_string())?;
            if let Err(e) = fs::rename(&temp, path) {
                let _ = fs::remove_file(temp);
                return Err(e.to_string());
            }
        } else {
            write_json(path, &manifest)?;
        }
        Ok(items.len())
    }
    pub fn import_library(&self, path: &Path) -> Result<Value, String> {
        if path.is_file() {
            return self.import(path);
        }
        let library_path = path.join("playlist");
        let path =
            if !path.join("index.json").is_file() && library_path.join("index.json").is_file() {
                library_path.as_path()
            } else {
                path
            };
        if !path.join("index.json").is_file() {
            return Err("未找到旧版歌库。请选择含 index.json 的 playlist 文件夹或其上级数据目录；已有导出文件请使用“选择歌单文件”。".into());
        }
        let old = PlaylistStore {
            root: path.to_path_buf(),
        };
        let data = read_json(&path.join("index.json"))?;
        let declared = migration::declared_unit(&data)?;
        let items = data["items"].as_array().ok_or("旧版索引格式无效")?;
        if items.len() > MAX_ITEMS {
            return Err("歌曲数量超过限制".into());
        }
        let mut imported = 0;
        let mut errors = Vec::new();
        for item in items {
            let id = string(item, "id");
            let result = (|| {
                let mut song = old.song_with_unit(id, declared)?;
                let bytes = if let Some(p) = old.midi_path(&song) {
                    if fs::metadata(&p).map_err(|e| e.to_string())?.len() > MAX_FILE {
                        return Err("MIDI 文件过大".into());
                    }
                    Some(fs::read(p).map_err(|e| e.to_string())?)
                } else {
                    None
                };
                let cache = old.cache_with_unit(id, declared).ok();
                song["source"]["local_midi_filename"] = json!("");
                if bytes.is_none() && string(&song["source"], "type") != "sheet" {
                    song["legacy_cache_only"] = json!(true);
                }
                self.put(
                    None,
                    string(item, "name"),
                    song,
                    bytes,
                    cache,
                    item["duration"].as_f64().unwrap_or(0.0),
                )?;
                Ok::<_, String>(())
            })();
            match result {
                Ok(()) => imported += 1,
                Err(e) => errors.push(format!("{}：{}", string(item, "name"), e)),
            }
        }
        Ok(json!({"imported":imported,"errors":errors}))
    }
    pub fn import(&self, path: &Path) -> Result<Value, String> {
        if path.is_dir() {
            return self.import_library(path);
        }
        if fs::metadata(path).map_err(|e| e.to_string())?.len() > MAX_PACKAGE {
            return Err("歌单包超过 1 GB 限制".into());
        }
        let bytes = fs::read(path).map_err(|e| e.to_string())?;
        let mut archive = if bytes.starts_with(b"PK") {
            Some(zip::ZipArchive::new(std::io::Cursor::new(&bytes)).map_err(|e| e.to_string())?)
        } else {
            None
        };
        let manifest: Value = if let Some(ref mut zip) = archive {
            serde_json::from_slice(&zip_member(zip, "playlist.json")?).map_err(|e| e.to_string())?
        } else {
            serde_json::from_slice(&bytes).map_err(|e| e.to_string())?
        };
        if manifest["format"] != "HuMidi Playlist" || manifest["version"].as_u64().unwrap_or(0) > 3
        {
            return Err("不支持的歌单格式或版本".into());
        }
        let declared = migration::declared_unit(&manifest)?;
        // An internal library index is also a JSON file. Recognize it here so
        // the regular file picker can migrate its adjacent items/MIDI/cache.
        if archive.is_none() && manifest["items"].is_array() && !manifest["entries"].is_array() {
            if path.file_name().and_then(|name| name.to_str()) == Some("index.json") {
                return self.import_library(path.parent().ok_or("无法定位旧版歌库目录")?);
            }
            return Err("这是歌库索引；请选择原歌库中的 index.json 或 playlist 文件夹。".into());
        }
        let entries = manifest["entries"].as_array().ok_or("歌单缺少歌曲列表")?;
        if entries.len() > MAX_ITEMS {
            return Err("歌单歌曲数量超过限制".into());
        }
        let mut imported = 0;
        let mut errors = Vec::new();
        let mut total_bytes = 0u64;
        for (index, entry) in entries.iter().enumerate() {
            let result = (|| -> Result<(), String> {
                let mut cache = entry.get("playback_data").cloned();
                let mut song = entry["song"].clone();
                if let Some(ref data) = cache.as_ref().filter(|_| !song.is_object()) {
                    song = json!({"source":{"type":"midi","original_filename":data["metadata"]["source_midi_filename"]},"playback_settings":data["metadata"]["playback_settings"],"selected_tracks":[],"legacy_cache_only":true});
                }
                if !song.is_object() {
                    return Err("缺少歌曲数据".into());
                }
                let mut midi = None;
                if let Some(ref mut zip) = archive {
                    let m = string(entry, "midi_member");
                    if !m.is_empty() {
                        midi = Some(zip_member(zip, m)?);
                    }
                    let c = string(entry, "cache_member");
                    if !c.is_empty() {
                        let b = zip_member(zip, c)?;
                        total_bytes += b.len() as u64;
                        cache = Some(serde_json::from_slice(&b).map_err(|e| e.to_string())?);
                    }
                    // Never follow an absolute local path supplied by a complete package.
                    song["source"]["original_path"] = json!("");
                } else {
                    let p = PathBuf::from(string(&song["source"], "original_path"));
                    if p.is_file() && string(&song["source"], "type") != "sheet" {
                        if fs::metadata(&p).map_err(|e| e.to_string())?.len() > MAX_FILE {
                            return Err("MIDI 文件过大".into());
                        }
                        midi = Some(fs::read(p).map_err(|e| e.to_string())?);
                    }
                }
                if let Some(ref b) = midi {
                    total_bytes += b.len() as u64;
                }
                if total_bytes > MAX_PACKAGE {
                    return Err("解压数据超过 1 GB 限制".into());
                }
                migration::normalize_song(&mut song, declared)?;
                if let Some(data) = cache.as_mut() {
                    migration::normalize_cache(data, declared)?;
                }
                song["source"]["local_midi_filename"] = json!("");
                if !song["playback_settings"].is_object() {
                    song["playback_settings"] = json!({});
                }
                let name = entry["metadata"]["name"]
                    .as_str()
                    .filter(|s| !s.trim().is_empty())
                    .unwrap_or("导入的歌曲");
                self.put(
                    None,
                    name,
                    song,
                    midi,
                    cache,
                    entry["metadata"]["duration"].as_f64().unwrap_or(0.0),
                )?;
                Ok(())
            })();
            match result {
                Ok(()) => imported += 1,
                Err(e) => errors.push(format!("第 {} 首：{}", index + 1, e)),
            }
            if total_bytes > MAX_PACKAGE {
                break;
            }
        }
        Ok(json!({"imported":imported,"errors":errors}))
    }
}

fn zip_member<R: Read + std::io::Seek>(
    archive: &mut zip::ZipArchive<R>,
    name: &str,
) -> Result<Vec<u8>, String> {
    if name.starts_with(['/', '\\'])
        || name.contains(':')
        || name.split(['/', '\\']).any(|s| s == "..")
    {
        return Err("歌单包包含不安全的文件路径".into());
    }
    let mut file = archive.by_name(name).map_err(|e| e.to_string())?;
    if file.size() > MAX_FILE {
        return Err("歌单包中的文件超过 128 MB 限制".into());
    }
    let mut bytes = Vec::new();
    (&mut file)
        .take(MAX_FILE + 1)
        .read_to_end(&mut bytes)
        .map_err(|e| e.to_string())?;
    if bytes.len() as u64 > MAX_FILE {
        return Err("解压文件超过大小限制".into());
    }
    Ok(bytes)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn song() -> Value {
        json!({"source":{"type":"sheet","sheet_text":"[abc] d","format_name":"Virtual Piano","bpm":120},"playback_settings":{"tempo":1.0},"selected_tracks":[]})
    }
    #[test]
    fn roundtrip_and_batch_edit_preserve_unmodified_fields() {
        let d = tempfile::tempdir().unwrap();
        let s = PlaylistStore::new(d.path().join("a")).unwrap();
        let a = s.put(None, "曲谱", song(), None, None, 12.0).unwrap();
        let id = string(&a, "id").to_owned();
        s.update_settings(&[id.clone()], &json!({"countdown_seconds":7}))
            .unwrap();
        assert_eq!(s.song(&id).unwrap()["playback_settings"]["tempo"], 1.0);
        let p = d.path().join("pack.humidiplaylist");
        s.export(&p, true).unwrap();
        let t = PlaylistStore::new(d.path().join("b")).unwrap();
        assert_eq!(t.import(&p).unwrap()["imported"], 1);
        assert_eq!(t.list().unwrap()[0]["name"], "曲谱");
        assert!(s.reorder(&[id.clone(), id.clone()]).is_err());
        assert!(s.song("../secret").is_err());
        s.delete(&[id]).unwrap();
        assert!(s.list().unwrap().is_empty());
    }
    #[test]
    fn midi_copy_and_complete_export_strip_paths() {
        let d = tempfile::tempdir().unwrap();
        let s = PlaylistStore::new(d.path().join("a")).unwrap();
        let midi = b"MThd\0\0\0\x06\0\0\0\x01\0\x60MTrk\0\0\0\x04\0\xff\x2f\0".to_vec();
        let v = json!({"source":{"type":"midi","original_path":"C:/private/test.mid","original_filename":"测试.mid"},"playback_settings":{"midi_file":"C:/private/test.mid"},"selected_tracks":[]});
        let a = s
            .put(None, "测试", v, Some(midi.clone()), None, 0.0)
            .unwrap();
        assert_eq!(
            fs::read(s.midi_path(&s.song(string(&a, "id")).unwrap()).unwrap()).unwrap(),
            midi
        );
        let p = d.path().join("pack.humidiplaylist");
        s.export(&p, true).unwrap();
        let mut z = zip::ZipArchive::new(fs::File::open(p).unwrap()).unwrap();
        let manifest = String::from_utf8(zip_member(&mut z, "playlist.json").unwrap()).unwrap();
        assert!(!manifest.contains("private"));
    }
    #[test]
    fn rename_preserves_cache_but_parameter_change_invalidates_it() {
        let d = tempfile::tempdir().unwrap();
        let s = PlaylistStore::new(d.path().join("library")).unwrap();
        let v = s
            .put(
                None,
                "first",
                song(),
                None,
                Some(json!({"compiled_events":[]})),
                1.0,
            )
            .unwrap();
        let id = string(&v, "id");
        s.put(Some(id), "renamed", s.song(id).unwrap(), None, None, 1.0)
            .unwrap();
        assert!(s.cache(id).is_ok());
        s.update_settings(&[id.to_string()], &json!({"tempo":2.0}))
            .unwrap();
        assert!(s.cache(id).is_err());
    }
    #[test]
    fn editing_settings_preserves_unicode_source_and_owned_midi_without_a_new_copy() {
        let d = tempfile::tempdir().unwrap();
        let s = PlaylistStore::new(d.path().join("library")).unwrap();
        let midi = b"MThd\0\0\0\x06\0\0\0\x01\0\x60MTrk\0\0\0\x04\0\xff\x2f\0".to_vec();
        let original = json!({"source":{"type":"midi","original_path":"C:/歌曲/告白气球.mid","original_filename":"告白气球.mid"},"playback_settings":{"tempo":1.0},"selected_tracks":[]});
        let item = s
            .put(
                None,
                "告白气球",
                original.clone(),
                Some(midi.clone()),
                None,
                20.0,
            )
            .unwrap();
        let id = string(&item, "id");
        let mut edited = original;
        edited["playback_settings"]["tempo"] = json!(1.2);
        s.put(Some(id), "告白气球", edited, None, None, 20.0)
            .unwrap();
        assert_eq!(s.list().unwrap().len(), 1);
        assert_eq!(
            s.song(id).unwrap()["source"]["original_filename"],
            "告白气球.mid"
        );
        assert_eq!(
            fs::read(s.midi_path(&s.song(id).unwrap()).unwrap()).unwrap(),
            midi
        );
    }
    #[test]
    fn legacy_library_and_cache_only_normal_package_keep_original_files() {
        let d = tempfile::tempdir().unwrap();
        let old = PlaylistStore::new(d.path().join("old")).unwrap();
        let raw = json!({"metadata":{"source_midi_filename":"cached.mid","playback_settings":{"tempo":1.0}},"compiled_events":[{"time":0,"priority":1,"action":"press","key_char":"a","pitch":60}]});
        write_json(&old.path("items", "old-id").unwrap(), &raw).unwrap();
        old.save_index(&[json!({"id":"old-id","name":"旧曲目","duration":2})])
            .unwrap();
        let before = fs::read(old.path("items", "old-id").unwrap()).unwrap();
        let fresh = PlaylistStore::new(d.path().join("fresh")).unwrap();
        assert_eq!(fresh.import_library(&old.root).unwrap()["imported"], 1);
        assert_eq!(
            fs::read(old.path("items", "old-id").unwrap()).unwrap(),
            before
        );
        let pack = d.path().join("normal.humidiplaylist");
        fresh.export(&pack, false).unwrap();
        let again = PlaylistStore::new(d.path().join("again")).unwrap();
        assert_eq!(again.import(&pack).unwrap()["imported"], 1);
        let items = again.list().unwrap();
        assert_eq!(items[0]["cache_available"], true);
        assert!(again.cache(string(&items[0], "id")).is_ok());
    }
    #[test]
    fn single_file_legacy_v1_v3_json_and_zip_are_detected_by_contents() {
        let d = tempfile::tempdir().unwrap();
        let raw = json!({"metadata":{"source_midi_filename":"cached.mid","playback_settings":{"tempo":1.0}},"compiled_events":[]});
        let v1 = d.path().join("v1.json");
        write_json(&v1, &json!({"format":"HuMidi Playlist","version":1,"entries":[{"metadata":{"name":"旧版缓存"},"playback_data":raw}]})).unwrap();
        let target = PlaylistStore::new(d.path().join("v1-target")).unwrap();
        assert_eq!(target.import(&v1).unwrap()["imported"], 1);
        let item = &target.list().unwrap()[0];
        assert!(target.cache(string(item, "id")).is_ok());
        let old = PlaylistStore::new(d.path().join("old")).unwrap();
        old.put(None, "中文曲谱", song(), None, None, 2.0).unwrap();
        for complete in [false, true] {
            // Python v3 exports have the same manifest and ZIP members. Neither
            // version nor filename suffix should force the user into a folder picker.
            let pack = d.path().join(if complete {
                "complete.json"
            } else {
                "normal.humidiplaylist"
            });
            old.export(&pack, complete).unwrap();
            let fresh = PlaylistStore::new(d.path().join(if complete {
                "zip-target"
            } else {
                "json-target"
            }))
            .unwrap();
            assert_eq!(fresh.import(&pack).unwrap()["imported"], 1);
            assert_eq!(fresh.list().unwrap()[0]["name"], "中文曲谱");
        }
    }
    #[test]
    fn index_file_folder_and_parent_directory_all_migrate_without_touching_source() {
        let d = tempfile::tempdir().unwrap();
        let old = PlaylistStore::new(d.path().join("old/playlist")).unwrap();
        let midi = b"MThd\0\0\0\x06\0\0\0\x01\0\x60MTrk\0\0\0\x04\0\xff\x2f\0".to_vec();
        let song = json!({"source":{"type":"midi","original_filename":"原件.mid"},"playback_settings":{"midi_clip_invalid_data":true},"selected_tracks":[]});
        old.put(
            None,
            "原件",
            song,
            Some(midi.clone()),
            Some(json!({"compiled_events":[]})),
            0.0,
        )
        .unwrap();
        let index = old.root.join("index.json");
        let before = fs::read(&index).unwrap();
        for (n, path) in [
            index.clone(),
            old.root.clone(),
            old.root.parent().unwrap().to_path_buf(),
        ]
        .iter()
        .enumerate()
        {
            let target = PlaylistStore::new(d.path().join(format!("target-{n}"))).unwrap();
            let report = target.import(path).unwrap();
            assert_eq!(report["imported"], 1);
            assert_eq!(report["errors"], json!([]));
            let song = target
                .song(string(&target.list().unwrap()[0], "id"))
                .unwrap();
            assert_eq!(song["playback_settings"]["midi_clip_invalid_data"], true);
            assert_eq!(fs::read(target.midi_path(&song).unwrap()).unwrap(), midi);
        }
        assert_eq!(fs::read(index).unwrap(), before);
    }
    #[test]
    fn corrupt_index_is_backed_up_and_valid_item_files_survive() {
        let d = tempfile::tempdir().unwrap();
        let s = PlaylistStore::new(d.path().join("library")).unwrap();
        s.put(None, "A", song(), None, None, 1.0).unwrap();
        fs::write(s.root.join("index.json"), b"{invalid").unwrap();
        assert_eq!(s.list().unwrap().len(), 1);
        assert!(fs::read_dir(&s.root).unwrap().flatten().any(|e| e
            .file_name()
            .to_string_lossy()
            .starts_with("index.corrupt.")));
    }
}

fn compilation_settings(mut value: Value) -> Value {
    if let Some(map) = value.as_object_mut() {
        for key in [
            "countdown",
            "release_pedal_on_start",
            "countdown_seconds",
            "auto_pause",
            "debug_mode",
            "midi_file",
            "xk_humanization_basis",
            "tempo_unit",
        ] {
            map.remove(key);
        }
    }
    value
}

#[cfg(test)]
mod runtime_cache_tests {
    use super::*;
    #[test]
    fn performance_mode_edit_invalidates_compiled_pedal_cache() {
        let d = tempfile::tempdir().unwrap();
        let store = PlaylistStore::new(d.path().join("library")).unwrap();
        let song = json!({"song_version":3,"source":{"type":"sheet","sheet_text":"abc"},"selected_tracks":[],"playback_settings":{"performance_optimization":false}});
        let item = store
            .put(None, "Test", song, None, Some(json!({"marker":true})), 2.0)
            .unwrap();
        let id = item["id"].as_str().unwrap();
        store
            .update_settings(&[id.to_string()], &json!({"performance_optimization":true}))
            .unwrap();
        assert!(store.cache(id).is_err());
    }
    #[test]
    fn countdown_only_save_preserves_compiled_cache() {
        let d = tempfile::tempdir().unwrap();
        let store = PlaylistStore::new(d.path().join("library")).unwrap();
        let song = json!({"song_version":3,"source":{"type":"sheet","sheet_text":"abc"},"selected_tracks":[],"playback_settings":{"countdown":true,"tempo":1.0}});
        let item = store
            .put(None, "Test", song, None, Some(json!({"marker":true})), 2.0)
            .unwrap();
        let id = item["id"].as_str().unwrap();
        store
            .update_settings(&[id.to_string()], &json!({"countdown":false}))
            .unwrap();
        assert_eq!(store.cache(id).unwrap()["marker"], true);
        store
            .update_settings(&[id.to_string()], &json!({"tempo":1.2}))
            .unwrap();
        assert!(store.cache(id).is_err());
    }
}
