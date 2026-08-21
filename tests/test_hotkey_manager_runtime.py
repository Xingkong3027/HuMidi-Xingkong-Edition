import importlib.util
import sys
import types
import unittest
from enum import Enum
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FakeSignal:
    def __init__(self, *_args):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self, *args):
        for callback in list(self.callbacks):
            callback(*args)


class FakeKey(Enum):
    f6 = "f6"
    f8 = "f8"
    esc = "esc"
    media_next = "media_next"
    media_previous = "media_previous"
    media_stop = "media_stop"
    media_play_pause = "media_play_pause"

    def __str__(self):
        return f"Key.{self.name}"


class FakeKeyCode:
    def __init__(self, char=None, vk=None):
        self.char = char
        self.vk = vk

    @classmethod
    def from_char(cls, value):
        return cls(char=value)

    @classmethod
    def from_vk(cls, value):
        return cls(vk=value)


class FakeListener:
    def __init__(self, on_press):
        self.on_press = on_press

    def start(self):
        return None

    def stop(self):
        return None


def load_manager_class():
    qtcore = types.ModuleType("PyQt6.QtCore")
    qtcore.QObject = object
    qtcore.pyqtSignal = lambda *args: FakeSignal(*args)
    pyqt = types.ModuleType("PyQt6")
    pyqt.QtCore = qtcore

    keyboard = types.ModuleType("pynput.keyboard")
    keyboard.Key = FakeKey
    keyboard.KeyCode = FakeKeyCode
    keyboard.Listener = FakeListener
    pynput = types.ModuleType("pynput")
    pynput.keyboard = keyboard

    previous = {name: sys.modules.get(name) for name in (
        "PyQt6", "PyQt6.QtCore", "pynput", "pynput.keyboard"
    )}
    sys.modules.update({
        "PyQt6": pyqt,
        "PyQt6.QtCore": qtcore,
        "pynput": pynput,
        "pynput.keyboard": keyboard,
    })
    try:
        spec = importlib.util.spec_from_file_location(
            "hotkey_manager_test_module", ROOT / "managers" / "HotkeyManager.py"
        )
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        return module.HotkeyManager
    finally:
        for name, value in previous.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value


class HotkeyManagerRuntimeTests(unittest.TestCase):
    def test_two_slots_round_trip_and_media_dispatch(self):
        Manager = load_manager_class()
        manager = Manager({
            "version": 2,
            "bindings": {
                "play_pause": [
                    {"type": "vk", "value": 0xB3},
                    {"type": "special", "value": "f8"},
                ],
                "stop": [{"type": "vk", "value": 0xB2}, None],
                "next": [{"type": "vk", "value": 0xB0}, None],
                "previous": [{"type": "vk", "value": 0xB1}, None],
            },
        })
        self.assertEqual(manager.display_for("play_pause", 0), "Media Play/Pause")
        self.assertEqual(manager.display_for("next", 0), "Media Next")
        serialized = manager.serialize_bindings()
        self.assertEqual(serialized["bindings"]["previous"][0]["value"], 0xB1)

        calls = []
        manager.next_requested.connect(lambda: calls.append("next"))
        manager.on_press(FakeKeyCode.from_vk(0xB0))
        self.assertEqual(calls, ["next"])

    def test_duplicate_binding_is_removed_from_previous_action(self):
        Manager = load_manager_class()
        manager = Manager(None)
        manager.start_binding("stop", 0)
        manager.on_press(FakeKey.f6)
        self.assertIsNone(manager.bindings["play_pause"][0])
        self.assertEqual(manager.bindings["stop"][0], FakeKey.f6)


if __name__ == "__main__":
    unittest.main()
