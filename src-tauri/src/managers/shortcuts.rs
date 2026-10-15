use std::collections::{BTreeMap, HashSet};

use serde::{Deserialize, Serialize};

use super::hotkey_manager::{format_combo, normalize, parse_combo, Modifier, RawKey};

pub const CONFIG_KEY: &str = "xk_shortcuts";

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ShortcutAction {
    PlayPause,
    Stop,
    Next,
    Previous,
}

pub const ACTIONS: [ShortcutAction; 4] = [
    ShortcutAction::PlayPause,
    ShortcutAction::Stop,
    ShortcutAction::Next,
    ShortcutAction::Previous,
];

impl ShortcutAction {
    pub fn channel(self) -> &'static str {
        match self {
            Self::PlayPause => "hotkey_toggle_requested",
            Self::Stop => "hotkey_stop_requested",
            Self::Next => "hotkey_next_requested",
            Self::Previous => "hotkey_previous_requested",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ShortcutConfig {
    pub version: u32,
    pub bindings: BTreeMap<ShortcutAction, [Option<String>; 2]>,
}

impl Default for ShortcutConfig {
    fn default() -> Self {
        Self {
            version: 3,
            bindings: [
                (ShortcutAction::PlayPause, [Some("F6".into()), None]),
                (ShortcutAction::Stop, [Some("F7".into()), None]),
                (ShortcutAction::Next, [None, None]),
                (ShortcutAction::Previous, [None, None]),
            ]
            .into_iter()
            .collect(),
        }
    }
}

fn legacy_key(value: &serde_json::Value) -> Option<String> {
    let text = if let Some(text) = value.as_str() {
        text.to_owned()
    } else {
        let v = &value["value"];
        match value["type"].as_str()? {
            "special" | "char" | "display" => v.as_str()?.to_owned(),
            "vk" => match v.as_u64()? {
                0xB0 => "MediaNext".into(),
                0xB1 => "MediaPrevious".into(),
                0xB2 => "MediaStop".into(),
                0xB3 => "MediaPlayPause".into(),
                n if (0x70..=0x87).contains(&n) => format!("F{}", n - 0x70 + 1),
                n if (0x41..=0x5A).contains(&n) || (0x30..=0x39).contains(&n) => {
                    char::from_u32(n as u32)?.to_string()
                }
                _ => return None,
            },
            _ => return None,
        }
    };
    let mapped = match text.to_lowercase().as_str() {
        "media_next" => "MediaNext",
        "enter" | "return" => "Enter",
        "tab" => "Tab",
        "backspace" => "Backspace",
        "delete" => "Delete",
        "up" => "Up",
        "down" => "Down",
        "left" => "Left",
        "right" => "Right",
        "media_previous" => "MediaPrevious",
        "media_play_pause" => "MediaPlayPause",
        "media_stop" => "MediaStop",
        "esc" => "Escape",
        "space" => "Space",
        _ => &text,
    };
    if mapped.len() > 1
        && mapped.starts_with(['f', 'F'])
        && mapped[1..].bytes().all(|c| c.is_ascii_digit())
    {
        canonical_combo(&mapped.to_uppercase()).ok()
    } else {
        canonical_combo(mapped).ok()
    }
}
fn canonical_combo(text: &str) -> Result<String, String> {
    let (modifiers, key) = parse_combo(text.trim()).ok_or_else(|| format!("无效快捷键：{text}"))?;
    if let RawKey::Char(c) = key {
        if !c.is_ascii_graphic() || c == '+' {
            return Err("快捷键必须使用键盘字母、数字、标点或功能键".into());
        }
    }
    Ok(format_combo(&modifiers, key))
}

impl ShortcutConfig {
    pub fn validated(mut self) -> Result<Self, String> {
        if self.version == 2 {
            // Earlier releases assigned these defaults without a user choice.
            for (action, key) in [
                (ShortcutAction::Next, "F8"),
                (ShortcutAction::Previous, "F9"),
            ] {
                if self.bindings.get(&action) == Some(&[Some(key.into()), None]) {
                    self.bindings.insert(action, [None, None]);
                }
            }
            self.version = 3;
        } else if self.version != 3 {
            return Err("不支持的快捷键配置版本".into());
        }
        let mut seen = HashSet::new();
        // A full config has deterministic conflict resolution: the later slot wins.
        for action in ACTIONS.into_iter().rev() {
            let slots = self.bindings.entry(action).or_insert([None, None]);
            for slot in slots.iter_mut().rev() {
                if let Some(text) = slot {
                    let canonical = canonical_combo(text)?;
                    *slot = if seen.insert(canonical.clone()) {
                        Some(canonical)
                    } else {
                        None
                    };
                }
            }
        }
        Ok(self)
    }

    pub fn set_slot(
        &mut self,
        action: ShortcutAction,
        slot: usize,
        binding: Option<&str>,
    ) -> Result<(), String> {
        if slot >= 2 {
            return Err("快捷键槽位必须是 0 或 1".into());
        }
        let canonical = binding.map(canonical_combo).transpose()?;
        if let Some(ref key) = canonical {
            for slots in self.bindings.values_mut() {
                for old in slots {
                    if old.as_ref() == Some(key) {
                        *old = None;
                    }
                }
            }
        }
        self.bindings.entry(action).or_insert([None, None])[slot] = canonical;
        Ok(())
    }

    fn matching_action(&self, combo: &str) -> Option<ShortcutAction> {
        self.bindings.iter().find_map(|(action, slots)| {
            slots
                .iter()
                .any(|s| s.as_deref() == Some(combo))
                .then_some(*action)
        })
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ShortcutEvent {
    Trigger(ShortcutAction),
    Bound,
    Cancelled,
}

pub struct ShortcutManager {
    config: ShortcutConfig,
    held_modifiers: HashSet<RawKey>,
    pressed: HashSet<RawKey>,
    consumed: HashSet<RawKey>,
    capture: Option<(ShortcutAction, usize)>,
}

impl Default for ShortcutManager {
    fn default() -> Self {
        Self {
            config: ShortcutConfig::default(),
            held_modifiers: HashSet::new(),
            pressed: HashSet::new(),
            consumed: HashSet::new(),
            capture: None,
        }
    }
}

impl ShortcutManager {
    pub fn from_config(config: &serde_json::Value) -> Self {
        let mut manager = Self::default();
        if let Some(stored) = config
            .get(CONFIG_KEY)
            .and_then(|v| serde_json::from_value::<ShortcutConfig>(v.clone()).ok())
            .and_then(|v| v.validated().ok())
        {
            manager.config = stored;
        } else if let Some(old) = config.get("shortcuts").or(config.get("hotkey")) {
            let map = old.get("bindings").unwrap_or(old);
            if map.is_object() && map.get("play_pause").is_some() {
                let mut restored = ShortcutConfig::default();
                for (action, key) in [
                    (ShortcutAction::PlayPause, "play_pause"),
                    (ShortcutAction::Stop, "stop"),
                    (ShortcutAction::Next, "next"),
                    (ShortcutAction::Previous, "previous"),
                ] {
                    if let Some(slots) = map[key].as_array() {
                        for slot in 0..2 {
                            let _ = restored.set_slot(
                                action,
                                slot,
                                slots.get(slot).and_then(legacy_key).as_deref(),
                            );
                        }
                    }
                }
                manager.config = restored;
            } else if let Some(key) = legacy_key(old) {
                let _ = manager
                    .config
                    .set_slot(ShortcutAction::PlayPause, 0, Some(&key));
            }
        } else if let Some(legacy) = config.get("hotkey_playback").and_then(|v| v.as_str()) {
            let _ = manager
                .config
                .set_slot(ShortcutAction::PlayPause, 0, Some(legacy));
        }
        manager
    }

    pub fn config(&self) -> ShortcutConfig {
        self.config.clone()
    }

    pub fn set_config(&mut self, config: ShortcutConfig) -> Result<ShortcutConfig, String> {
        let mut changed = Vec::new();
        for action in ACTIONS {
            for slot in 0..2 {
                let proposed = config
                    .bindings
                    .get(&action)
                    .and_then(|slots| slots[slot].as_deref())
                    .map(canonical_combo)
                    .transpose()?;
                let previous = self
                    .config
                    .bindings
                    .get(&action)
                    .and_then(|slots| slots[slot].as_ref());
                if proposed.as_ref() != previous {
                    changed.push((action, slot, proposed));
                }
            }
        }
        let mut validated = config.validated()?;
        // A changed slot wins over an unchanged conflicting binding even when
        // the frontend submits the whole settings object.
        for (action, slot, binding) in changed {
            validated.set_slot(action, slot, binding.as_deref())?;
        }
        self.config = validated;
        self.capture = None;
        Ok(self.config())
    }

    pub fn start_binding(&mut self, action: ShortcutAction, slot: usize) -> Result<(), String> {
        if slot >= 2 {
            return Err("快捷键槽位必须是 0 或 1".into());
        }
        self.capture = Some((action, slot));
        Ok(())
    }

    pub fn cancel_binding(&mut self) {
        self.capture = None;
    }

    /// Foreground capture can finish the same pending binding as the OS hook.
    /// Only the first completion wins; a duplicate event must not bind twice.
    pub fn finish_binding(&mut self, combo: &str) -> Result<bool, String> {
        let Some((action, slot)) = self.capture else {
            return Ok(false);
        };
        self.config.set_slot(action, slot, Some(combo))?;
        let (_, key) = parse_combo(combo).ok_or("无效快捷键")?;
        // DOM completion may beat the queued OS press. Consume that press until release.
        self.pressed.insert(normalize(key));
        self.consumed.insert(normalize(key));
        self.capture = None;
        Ok(true)
    }

    pub fn is_binding(&self) -> bool {
        self.capture.is_some()
    }

    /// Returns whether the event belongs to an edition shortcut. Physical left
    /// and right modifiers are tracked separately, and auto-repeat never fires twice.
    pub fn handle(
        &mut self,
        raw: RawKey,
        is_press: bool,
        suspend_actions: bool,
    ) -> (bool, Option<ShortcutEvent>) {
        let key = normalize(raw);
        if matches!(key, RawKey::Mod(_)) {
            if is_press {
                self.held_modifiers.insert(raw);
            } else {
                self.held_modifiers.remove(&raw);
            }
            // Let the legacy save manager see every modifier transition, even
            // during capture, so neither manager can retain a stale Ctrl/Shift.
            return (false, None);
        }
        if !is_press {
            self.pressed.remove(&key);
            return (self.consumed.remove(&key), None);
        }
        if !self.pressed.insert(key) {
            return (self.consumed.contains(&key), None);
        }
        let modifiers: HashSet<Modifier> = self
            .held_modifiers
            .iter()
            .filter_map(|raw| {
                if let RawKey::Mod(m) = normalize(*raw) {
                    Some(m)
                } else {
                    None
                }
            })
            .collect();
        if let Some((action, slot)) = self.capture {
            self.consumed.insert(key);
            self.capture = None;
            if key == RawKey::Named("Escape") && modifiers.is_empty() {
                return (true, Some(ShortcutEvent::Cancelled));
            }
            let combo = format_combo(&modifiers, key);
            if self.config.set_slot(action, slot, Some(&combo)).is_ok() {
                return (true, Some(ShortcutEvent::Bound));
            }
            return (true, Some(ShortcutEvent::Cancelled));
        }
        if suspend_actions {
            return (false, None);
        }
        let combo = format_combo(&modifiers, key);
        if let Some(action) = self.config.matching_action(&combo) {
            self.consumed.insert(key);
            return (true, Some(ShortcutEvent::Trigger(action)));
        }
        (false, None)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn navigation_defaults_are_unbound_and_old_defaults_upgrade_without_losing_custom_keys() {
        let config = ShortcutConfig::default();
        assert_eq!(config.bindings[&ShortcutAction::Next], [None, None]);
        assert_eq!(config.bindings[&ShortcutAction::Previous], [None, None]);
        let mut old = config.clone();
        old.version = 2;
        old.bindings
            .insert(ShortcutAction::Next, [Some("F8".into()), None]);
        old.bindings.insert(
            ShortcutAction::Previous,
            [Some("Ctrl+MediaPrevious".into()), None],
        );
        let restored = ShortcutManager::from_config(&serde_json::json!({CONFIG_KEY:old})).config();
        assert_eq!(restored.version, 3);
        assert_eq!(restored.bindings[&ShortcutAction::Next], [None, None]);
        assert_eq!(
            restored.bindings[&ShortcutAction::Previous][0].as_deref(),
            Some("Ctrl+MediaPrevious")
        );
        let mut deliberate = config;
        deliberate
            .bindings
            .insert(ShortcutAction::Previous, [Some("F9".into()), None]);
        assert_eq!(deliberate.clone().validated().unwrap(), deliberate);
    }
    #[test]
    fn foreground_and_hook_capture_race_never_triggers_the_new_binding() {
        let mut manager = ShortcutManager::default();
        manager.start_binding(ShortcutAction::Next, 0).unwrap();
        assert!(manager.finish_binding("MediaNext").unwrap());
        assert!(!manager.finish_binding("F6").unwrap());
        assert_eq!(
            manager.handle(RawKey::Named("MediaNext"), true, false),
            (true, None)
        );
        manager.handle(RawKey::Named("MediaNext"), false, false);
        assert_eq!(
            manager.handle(RawKey::Named("MediaNext"), true, false).1,
            Some(ShortcutEvent::Trigger(ShortcutAction::Next))
        );
    }

    #[test]
    fn duplicate_binding_moves_to_the_new_slot() {
        let mut config = ShortcutConfig::default();
        config
            .set_slot(ShortcutAction::Next, 1, Some("F6"))
            .unwrap();
        assert_eq!(config.bindings[&ShortcutAction::PlayPause][0], None);
        assert_eq!(
            config.bindings[&ShortcutAction::Next][1].as_deref(),
            Some("F6")
        );
    }

    #[test]
    fn auto_repeat_fires_once_until_released() {
        let mut manager = ShortcutManager::default();
        let key = RawKey::Named("F6");
        assert_eq!(
            manager.handle(key, true, false),
            (
                true,
                Some(ShortcutEvent::Trigger(ShortcutAction::PlayPause))
            )
        );
        assert_eq!(manager.handle(key, true, false), (true, None));
        assert_eq!(manager.handle(key, false, false), (true, None));
        assert!(manager.handle(key, true, false).1.is_some());
    }

    #[test]
    fn editing_an_earlier_action_moves_a_duplicate_out_of_a_later_action() {
        let mut manager = ShortcutManager::default();
        manager
            .config
            .set_slot(ShortcutAction::Next, 0, Some("F8"))
            .unwrap();
        let mut proposed = manager.config();
        proposed
            .bindings
            .get_mut(&ShortcutAction::PlayPause)
            .unwrap()[0] = Some("F8".into());
        manager.set_config(proposed).unwrap();
        assert_eq!(
            manager.config.bindings[&ShortcutAction::PlayPause][0].as_deref(),
            Some("F8")
        );
        assert_eq!(manager.config.bindings[&ShortcutAction::Next][0], None);
    }

    #[test]
    fn capture_never_also_triggers_and_escape_cancels() {
        let mut manager = ShortcutManager::default();
        manager.start_binding(ShortcutAction::Next, 1).unwrap();
        assert_eq!(
            manager.handle(RawKey::Named("F6"), true, false),
            (true, Some(ShortcutEvent::Bound))
        );
        assert_eq!(manager.config.bindings[&ShortcutAction::PlayPause][0], None);
        manager.start_binding(ShortcutAction::Stop, 1).unwrap();
        assert_eq!(
            manager.handle(RawKey::Named("Escape"), true, false),
            (true, Some(ShortcutEvent::Cancelled))
        );
        assert_eq!(manager.config.bindings[&ShortcutAction::Stop][1], None);
    }

    #[test]
    fn media_keys_and_two_physical_modifier_keys_work() {
        let mut manager = ShortcutManager::default();
        manager
            .config
            .set_slot(ShortcutAction::Next, 1, Some("Ctrl+MediaNext"))
            .unwrap();
        manager.handle(RawKey::ModLeft(Modifier::Ctrl), true, false);
        manager.handle(RawKey::ModRight(Modifier::Ctrl), true, false);
        manager.handle(RawKey::ModLeft(Modifier::Ctrl), false, false);
        assert_eq!(
            manager.handle(RawKey::Named("MediaNext"), true, false).1,
            Some(ShortcutEvent::Trigger(ShortcutAction::Next))
        );
    }

    #[test]
    fn config_roundtrip_preserves_second_slot_and_unbound_actions() {
        let mut config = ShortcutConfig::default();
        config.set_slot(ShortcutAction::Stop, 0, None).unwrap();
        config
            .set_slot(ShortcutAction::Previous, 1, Some("Alt+MediaPrevious"))
            .unwrap();
        let manager = ShortcutManager::from_config(&serde_json::json!({ CONFIG_KEY: config }));
        assert_eq!(manager.config(), config);
    }

    #[test]
    fn invalid_config_does_not_replace_valid_config() {
        let mut manager = ShortcutManager::default();
        let original = manager.config();
        let mut invalid = original.clone();
        invalid.bindings.get_mut(&ShortcutAction::Next).unwrap()[0] = Some("Hyper+Q".into());
        assert!(manager.set_config(invalid).is_err());
        assert_eq!(manager.config(), original);
    }
    #[test]
    fn restores_python_dual_slots_and_media_virtual_keys() {
        let manager = ShortcutManager::from_config(
            &serde_json::json!({"shortcuts":{"version":2,"bindings":{"play_pause":[{"type":"special","value":"f10"},{"type":"vk","value":179}],"stop":[{"type":"char","value":"z"},null]}}}),
        );
        assert_eq!(
            manager.config().bindings[&ShortcutAction::PlayPause],
            [Some("F10".into()), Some("MediaPlayPause".into())]
        );
        assert_eq!(
            manager.config().bindings[&ShortcutAction::Stop][0],
            Some("Z".into())
        );
    }
}
