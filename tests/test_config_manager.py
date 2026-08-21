import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from managers.ConfigManager import ConfigManager


class ConfigManagerTests(unittest.TestCase):
    def test_utf8_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("managers.ConfigManager.Path.home", return_value=Path(tmp)):
                manager = ConfigManager()
            manager.config_dir = Path(tmp)
            manager.config_path = manager.config_dir / "config.json"
            manager.save_dir = tmp
            manager.save({"language_selection": "zh_CN", "label": "简体中文"})
            raw = manager.config_path.read_text(encoding="utf-8")
            self.assertIn("简体中文", raw)
            loaded = manager.load()
            self.assertEqual(loaded["label"], "简体中文")
            self.assertEqual(json.loads(raw)["language_selection"], "zh_CN")


if __name__ == "__main__":
    unittest.main()
