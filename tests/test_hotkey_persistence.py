import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HotkeyPersistenceIntegrationTests(unittest.TestCase):
    def test_main_loads_new_shortcuts_with_legacy_fallback(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('HotkeyManager(loaded_cfg.get("shortcuts", loaded_cfg.get("hotkey")))', source)

    def test_main_saves_shortcuts_and_legacy_primary_binding(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('config_data["shortcuts"] = self.hotkey_manager.serialize_bindings()', source)
        self.assertIn('config_data["hotkey"] = self.hotkey_manager.serialize_current_key()', source)
        dialog_method = source.split("def _change_hotkey", 1)[1].split("def _on_shortcuts_changed", 1)[0]
        self.assertIn("ShortcutSettingsDialog", dialog_method)
        self.assertIn("self._save_config()", dialog_method)

    def test_hotkey_manager_supports_two_slots_actions_and_media_keys(self):
        source = (ROOT / "managers" / "HotkeyManager.py").read_text(encoding="utf-8")
        self.assertIn('ACTIONS = ("play_pause", "stop", "next", "previous")', source)
        self.assertIn('"media_play_pause": 0xB3', source)
        self.assertIn('"media_previous": 0xB1', source)
        self.assertIn('"media_next": 0xB0', source)
        self.assertIn("def serialize_bindings", source)
        self.assertIn("def restore_bindings", source)
        self.assertIn("for slot in (0, 1)", source)
        self.assertIn("keyboard.KeyCode.from_vk", source)


if __name__ == "__main__":
    unittest.main()
