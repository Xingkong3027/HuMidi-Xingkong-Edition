//! Python playlists store tempo as a percentage; Rust playlists store a ratio.
//! Recognize schema fields/explicit units, never guess from the numeric magnitude.
use serde_json::{json, Value};

pub(super) fn declared_unit(manifest: &Value) -> Result<Option<&str>, String> {
    if let Some(unit) = manifest.get("tempo_unit").and_then(Value::as_str) {
        return match unit {
            "ratio" | "percent" => Ok(Some(unit)),
            _ => Err("歌单的速度单位不受支持".into()),
        };
    }
    // v1/v2 of the HuMidi Playlist interchange format predate the Rust fork.
    Ok(match manifest["version"].as_u64() {
        Some(1 | 2) => Some("percent"),
        _ => None,
    })
}

pub(super) fn normalize_settings(
    settings: &mut Value,
    declared: Option<&str>,
) -> Result<bool, String> {
    let Some(fields) = settings.as_object_mut() else {
        return Ok(false);
    };
    // xk.9/xk.10 background caching wrote absent legacy curve fields as null.
    // Both absence and null mean no custom curve, not an invalid sequence.
    for key in ["pedal_curve_on", "pedal_curve_off"] {
        if fields.get(key).is_none_or(Value::is_null) {
            fields.insert(key.into(), json!([]));
        }
    }
    let unit = fields
        .get("tempo_unit")
        .and_then(Value::as_str)
        .or(declared)
        .unwrap_or_else(|| {
            if fields.contains_key("humanization_seed")
                && !fields.contains_key("random_seed")
                && !fields.contains_key("humanization_on")
            {
                "percent"
            } else {
                "ratio"
            }
        });
    let percent = match unit {
        "percent" => true,
        "ratio" => false,
        _ => return Err("歌曲的速度单位不受支持".into()),
    };
    if percent {
        if let Some(value) = fields.get("tempo") {
            let tempo = value
                .as_f64()
                .filter(|v| v.is_finite() && *v > 0.0)
                .ok_or("旧版歌曲的速度必须是正数")?;
            fields.insert("tempo".into(), json!(tempo / 100.0));
        }
    }
    fields.insert("tempo_unit".into(), json!("ratio"));
    Ok(percent)
}

pub(super) fn normalize_song(song: &mut Value, declared: Option<&str>) -> Result<bool, String> {
    let migrated = normalize_settings(&mut song["playback_settings"], declared)?;
    if migrated {
        // Runtime hint for caches calculated by xk.9 using the wrong multiplier.
        // Remove it before persisting a newly calculated or edited song.
        song["_legacy_tempo_migrated"] = json!(true);
    }
    Ok(migrated)
}

pub(super) fn normalize_cache(cache: &mut Value, declared: Option<&str>) -> Result<(), String> {
    if let Some(settings) = cache
        .get_mut("metadata")
        .and_then(|m| m.get_mut("playback_settings"))
    {
        normalize_settings(settings, declared)?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn absent_and_null_curves_become_empty_while_custom_curves_survive() {
        let valid = json!([{"time":0.0,"value":0.6}]);
        let mut settings =
            json!({"tempo":1.0,"tempo_unit":"ratio","pedal_curve_on":null,"pedal_curve_off":valid});
        assert!(!normalize_settings(&mut settings, None).unwrap());
        assert_eq!(settings["pedal_curve_on"], json!([]));
        assert_eq!(settings["pedal_curve_off"], valid);
        let saved = settings.clone();
        normalize_settings(&mut settings, None).unwrap();
        assert_eq!(settings, saved);
        let mut empty = json!({});
        normalize_settings(&mut empty, None).unwrap();
        assert_eq!(empty["pedal_curve_on"], json!([]));
        assert_eq!(empty["pedal_curve_off"], json!([]));
    }
    #[test]
    fn python_schema_converts_small_and_large_percentages_exactly_once() {
        for (percent, ratio) in [(1.0, 0.01), (80.0, 0.8), (100.0, 1.0), (125.0, 1.25)] {
            let mut settings = json!({"tempo":percent,"humanization_seed":null,"articulation":0.95,"trim_start_seconds":2.0});
            assert!(normalize_settings(&mut settings, None).unwrap());
            assert_eq!(settings["tempo"], ratio);
            assert_eq!(settings["articulation"], 0.95);
            assert_eq!(settings["trim_start_seconds"], 2.0);
            assert!(!normalize_settings(&mut settings, None).unwrap());
            assert_eq!(settings["tempo"], ratio);
        }
    }
    #[test]
    fn native_ratios_and_explicit_units_override_legacy_context() {
        let mut native = json!({"tempo":100.0,"random_seed":null,"humanization_on":false});
        assert!(!normalize_settings(&mut native, None).unwrap());
        assert_eq!(native["tempo"], 100.0);
        let mut marked = json!({"tempo":0.01,"tempo_unit":"ratio","humanization_seed":null});
        assert!(!normalize_settings(&mut marked, Some("percent")).unwrap());
        assert_eq!(marked["tempo"], 0.01);
        let mut old = json!({"tempo":1.0,"tempo_unit":"percent"});
        assert!(normalize_settings(&mut old, None).unwrap());
        assert_eq!(old["tempo"], 0.01);
    }
    #[test]
    fn malformed_units_or_percentages_are_reported_per_song() {
        for settings in [
            json!({"tempo":0,"tempo_unit":"percent"}),
            json!({"tempo":"100","tempo_unit":"percent"}),
            json!({"tempo_unit":"unknown"}),
        ] {
            assert!(normalize_settings(&mut settings.clone(), None).is_err());
        }
    }
}
