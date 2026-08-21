from __future__ import annotations

from copy import deepcopy
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal as Signal
from pynput import keyboard
from pynput.keyboard import Key


class HotkeyManager(QObject):
    """Global keyboard shortcut router.

    Each action accepts up to two bindings.  The manager keeps compatibility
    with the old single ``hotkey`` value, while the new serialized format is
    stored under ``shortcuts``.
    """

    play_pause_requested = Signal()
    stop_requested = Signal()
    next_requested = Signal()
    previous_requested = Signal()

    # Compatibility signals used by older integrations.
    toggle_requested = Signal()
    bound_updated = Signal(str)

    binding_captured = Signal(str, int, str)
    bindings_changed = Signal()

    ACTIONS = ("play_pause", "stop", "next", "previous")
    ACTION_LABELS = {
        "play_pause": "Play / Pause",
        "stop": "Stop",
        "next": "Next Song",
        "previous": "Previous Song",
    }

    MEDIA_SPECIAL_TO_VK = {
        "media_next": 0xB0,
        "media_previous": 0xB1,
        "media_stop": 0xB2,
        "media_play_pause": 0xB3,
    }
    MEDIA_VK_TO_DISPLAY = {
        0xB0: "Media Next",
        0xB1: "Media Previous",
        0xB2: "Media Stop",
        0xB3: "Media Play/Pause",
    }

    def __init__(self, saved_bindings=None):
        super().__init__()
        self.bindings: dict[str, list[Any | None]] = self._default_bindings()
        self.listener = None
        self._binding_target: tuple[str, int] | None = None
        self.restore_bindings(saved_bindings, reset=True)
        self._start_listener()

    @staticmethod
    def _default_bindings() -> dict[str, list[Any | None]]:
        return {
            "play_pause": [Key.f6, None],
            "stop": [None, None],
            "next": [None, None],
            "previous": [None, None],
        }

    @property
    def current_key(self):
        """Compatibility alias for the first play/pause shortcut."""
        return self.bindings["play_pause"][0] or Key.f6

    @property
    def listening_for_bind(self) -> bool:
        return self._binding_target is not None

    def _start_listener(self):
        try:
            self.listener = keyboard.Listener(on_press=self.on_press)
            self.listener.start()
        except Exception:
            # A listener can be unavailable in headless test environments.  The
            # shortcut data model remains usable and the GUI can still start.
            self.listener = None

    def shutdown(self) -> None:
        if self.listener is not None:
            try:
                self.listener.stop()
            except Exception:
                pass
            self.listener = None

    # ------------------------------------------------------------------
    # Formatting / normalization

    @classmethod
    def _key_token(cls, key) -> tuple[str, Any] | None:
        if key is None:
            return None
        if isinstance(key, Key):
            name = str(key).replace("Key.", "")
            media_vk = cls.MEDIA_SPECIAL_TO_VK.get(name)
            if media_vk is not None:
                return ("vk", media_vk)
            return ("special", name)
        char = getattr(key, "char", None)
        if char:
            return ("char", str(char).lower())
        vk = getattr(key, "vk", None)
        if vk is not None:
            return ("vk", int(vk))
        return ("display", str(key))

    @classmethod
    def _format_key_string(cls, key) -> str:
        if key is None:
            return "Not Set"
        token = cls._key_token(key)
        if token and token[0] == "vk" and int(token[1]) in cls.MEDIA_VK_TO_DISPLAY:
            return cls.MEDIA_VK_TO_DISPLAY[int(token[1])]
        if isinstance(key, Key):
            name = str(key).replace("Key.", "")
            friendly = {
                "space": "Space",
                "enter": "Enter",
                "esc": "Esc",
                "page_up": "Page Up",
                "page_down": "Page Down",
                "print_screen": "Print Screen",
                "scroll_lock": "Scroll Lock",
                "pause": "Pause/Break",
            }
            if name in friendly:
                return friendly[name]
            if name.startswith("f") and name[1:].isdigit():
                return name.upper()
            return name.replace("_", " ").title()
        char = getattr(key, "char", None)
        if char:
            return str(char).upper()
        vk = getattr(key, "vk", None)
        if vk is not None:
            if int(vk) in cls.MEDIA_VK_TO_DISPLAY:
                return cls.MEDIA_VK_TO_DISPLAY[int(vk)]
            return f"VK 0x{int(vk):02X}"
        return str(key)

    def display_for(self, action: str, slot: int) -> str:
        try:
            key = self.bindings[action][slot]
        except (KeyError, IndexError):
            return "Not Set"
        return self._format_key_string(key)

    def primary_display(self, action: str) -> str:
        values = [self._format_key_string(k) for k in self.bindings.get(action, []) if k is not None]
        return " / ".join(values) if values else ""

    # ------------------------------------------------------------------
    # Serialization

    @classmethod
    def _serialize_key(cls, key) -> dict | None:
        if key is None:
            return None
        if isinstance(key, Key):
            return {"type": "special", "value": str(key).replace("Key.", "")}
        char = getattr(key, "char", None)
        if char:
            return {"type": "char", "value": str(char)}
        vk = getattr(key, "vk", None)
        if vk is not None:
            return {"type": "vk", "value": int(vk)}
        return {"type": "display", "value": cls._format_key_string(key)}

    @classmethod
    def _deserialize_key(cls, raw):
        if raw is None:
            return None
        if isinstance(raw, str):
            named = getattr(Key, raw.lower(), None)
            if named is not None:
                return named
            if len(raw) == 1:
                return keyboard.KeyCode.from_char(raw)
            return None
        if not isinstance(raw, dict):
            return None
        binding_type = str(raw.get("type", "")).lower()
        value = raw.get("value")
        try:
            if binding_type == "special" and isinstance(value, str):
                named = getattr(Key, value.lower(), None)
                if named is not None:
                    return named
                media_vk = cls.MEDIA_SPECIAL_TO_VK.get(value.lower())
                if media_vk is not None:
                    return keyboard.KeyCode.from_vk(media_vk)
            if binding_type == "char" and isinstance(value, str) and value:
                return keyboard.KeyCode.from_char(value[0])
            if binding_type == "vk":
                return keyboard.KeyCode.from_vk(int(value))
        except (TypeError, ValueError, AttributeError):
            return None
        return None

    def serialize_bindings(self) -> dict:
        return {
            "version": 2,
            "bindings": {
                action: [self._serialize_key(key) for key in self.bindings[action]]
                for action in self.ACTIONS
            },
        }

    def serialize_current_key(self) -> dict:
        """Legacy serializer for builds expecting a single hotkey."""
        return self._serialize_key(self.current_key) or {"type": "special", "value": "f6"}

    def restore_binding(self, saved_binding) -> bool:
        """Legacy single-hotkey restore entry point."""
        key = self._deserialize_key(saved_binding)
        if key is None:
            return False
        self.bindings["play_pause"][0] = key
        return True

    def restore_bindings(self, saved_bindings, reset: bool = False) -> bool:
        if reset:
            self.bindings = self._default_bindings()
        if not saved_bindings:
            return False

        # Old format: a single serialized key or a plain string.
        if isinstance(saved_bindings, str) or (
            isinstance(saved_bindings, dict) and "type" in saved_bindings
        ):
            restored = self.restore_binding(saved_bindings)
            if restored:
                self.bindings_changed.emit()
            return restored

        if not isinstance(saved_bindings, dict):
            return False
        raw_map = saved_bindings.get("bindings", saved_bindings)
        if not isinstance(raw_map, dict):
            return False

        any_restored = False
        for action in self.ACTIONS:
            raw_slots = raw_map.get(action)
            if not isinstance(raw_slots, list):
                continue
            values: list[Any | None] = [None, None]
            for slot, raw in enumerate(raw_slots[:2]):
                values[slot] = self._deserialize_key(raw)
                any_restored = any_restored or values[slot] is not None
            self.bindings[action] = values
        self.bindings_changed.emit()
        return any_restored

    def snapshot(self) -> dict:
        return deepcopy(self.serialize_bindings())

    # ------------------------------------------------------------------
    # Capture and dispatch

    def start_binding(self, action: str = "play_pause", slot: int = 0):
        if action not in self.ACTIONS or slot not in (0, 1):
            raise ValueError("Invalid shortcut target")
        self._binding_target = (action, slot)

    def cancel_binding(self) -> None:
        self._binding_target = None

    def clear_binding(self, action: str, slot: int) -> None:
        if action not in self.ACTIONS or slot not in (0, 1):
            return
        self.bindings[action][slot] = None
        self.bindings_changed.emit()

    def _remove_duplicate(self, token, except_action: str, except_slot: int) -> None:
        if token is None:
            return
        for action in self.ACTIONS:
            for slot in (0, 1):
                if action == except_action and slot == except_slot:
                    continue
                if self._key_token(self.bindings[action][slot]) == token:
                    self.bindings[action][slot] = None

    def on_press(self, key):
        if self._binding_target is not None:
            action, slot = self._binding_target
            self._binding_target = None
            token = self._key_token(key)
            self._remove_duplicate(token, action, slot)
            self.bindings[action][slot] = key
            display = self._format_key_string(key)
            self.binding_captured.emit(action, slot, display)
            self.bound_updated.emit(display)
            self.bindings_changed.emit()
            return

        token = self._key_token(key)
        if token is None:
            return
        for action in self.ACTIONS:
            if any(self._key_token(bound) == token for bound in self.bindings[action] if bound is not None):
                if action == "play_pause":
                    self.play_pause_requested.emit()
                    self.toggle_requested.emit()
                elif action == "stop":
                    self.stop_requested.emit()
                elif action == "next":
                    self.next_requested.emit()
                elif action == "previous":
                    self.previous_requested.emit()
                return
