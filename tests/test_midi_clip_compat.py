import importlib.util
import struct
import sys
import tempfile
import types
import unittest
from pathlib import Path

# core.core only needs Key.ctrl/Key.shift while importing the parser module.
# Keep this parser regression test runnable in minimal CI environments that do
# not have an active desktop/pynput backend.
try:
    import pynput.keyboard  # noqa: F401
except Exception:
    pynput_module = types.ModuleType("pynput")
    keyboard_module = types.ModuleType("pynput.keyboard")

    class _DummyKey:
        ctrl = "ctrl"
        shift = "shift"

    keyboard_module.Key = _DummyKey
    pynput_module.keyboard = keyboard_module
    sys.modules.setdefault("pynput", pynput_module)
    sys.modules.setdefault("pynput.keyboard", keyboard_module)

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "_humidi_core_parser_clip_test", ROOT / "core" / "core.py"
)
_CORE = importlib.util.module_from_spec(_SPEC)
assert _SPEC and _SPEC.loader
_SPEC.loader.exec_module(_CORE)
MidiInvalidDataByteError = _CORE.MidiInvalidDataByteError
MidiParser = _CORE.MidiParser


class MidiClipCompatibilityTests(unittest.TestCase):
    @staticmethod
    def _invalid_pitch_bend_midi() -> bytes:
        # The second pitch-bend data byte is 0x80 (128), while MIDI data bytes
        # must be 0..127. The rest of the file contains one ordinary note.
        track = bytes(
            [
                0x00, 0xE0, 0x00, 0x80,
                0x00, 0x90, 0x3C, 0x40,
                0x83, 0x60, 0x80, 0x3C, 0x00,
                0x00, 0xFF, 0x2F, 0x00,
            ]
        )
        header = b"MThd" + struct.pack(">IHHH", 6, 0, 1, 480)
        return header + b"MTrk" + struct.pack(">I", len(track)) + track

    def test_strict_mode_reports_invalid_data_byte(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "invalid.mid"
            path.write_bytes(self._invalid_pitch_bend_midi())
            with self.assertRaises(MidiInvalidDataByteError):
                MidiParser.parse_structure(str(path))

    def test_clip_mode_repairs_and_parses_same_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "invalid.mid"
            path.write_bytes(self._invalid_pitch_bend_midi())
            tracks, _tempo_map = MidiParser.parse_structure(
                str(path), clip_invalid_data=True
            )
            self.assertEqual(len(tracks), 1)
            self.assertEqual(tracks[0].note_count, 1)
            self.assertEqual(tracks[0].notes[0].pitch, 60)


if __name__ == "__main__":
    unittest.main()
