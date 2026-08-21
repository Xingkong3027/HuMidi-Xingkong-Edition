"""Optional high-density playback helpers.

The normal HuMidi execution path intentionally remains untouched.  When the
user enables Performance Optimization, this module provides two conservative
optimizations:

* collapse duplicate physical attacks that occur at the exact same playback
  timestamp (a keyboard cannot distinguish several identical key-downs at the
  same instant anyway), and
* reduce duplicate/redundant physical actions while preserving HuMidi's original
  pynput injection backend for Roblox compatibility.

The helpers are dependency-free so their planning behaviour can be unit tested
on non-Windows build machines.
"""

from __future__ import annotations

from collections import OrderedDict
import ctypes
import gc
import sys
from typing import Iterable, Sequence


Action = tuple[str, str]  # ("down" | "up", key token)
PressSpec = tuple[str, tuple[str, ...]]  # (base key, modifier tokens)


def unique_press_specs(presses: Iterable[PressSpec]) -> list[PressSpec]:
    """Keep one attack per unique physical key/modifier combination.

    Dense or octave-folded MIDI files can schedule the same mapped keyboard key
    dozens of times at one timestamp. Replaying all of those attacks serially
    only makes the playback thread late; physically, Windows cannot press an
    identical key several times at exactly the same instant.
    """
    seen: set[PressSpec] = set()
    result: list[PressSpec] = []
    for base_key, modifiers in presses:
        spec = (str(base_key), tuple(str(item) for item in modifiers))
        if spec in seen:
            continue
        seen.add(spec)
        result.append(spec)
    return result


def build_press_action_plan(
    presses: Sequence[PressSpec],
    initially_down: Iterable[str] = (),
) -> list[Action]:
    """Build a minimal ordered key action plan for one simultaneous batch.

    Presses are grouped by base key while preserving first-seen order. Duplicate
    variants are collapsed. If one base key represents both a shifted and an
    unshifted piano note at the same timestamp, the plan performs fast
    re-strikes inside the same optimized action sequence and leaves the base key held after
    the final variant, matching the legacy end state without 1 ms sleeps.
    """
    grouped: "OrderedDict[str, list[tuple[str, ...]]]" = OrderedDict()
    for base_key, modifiers in unique_press_specs(presses):
        grouped.setdefault(base_key, []).append(modifiers)

    down = {str(key) for key in initially_down}
    actions: list[Action] = []
    for base_key, variants in grouped.items():
        physically_down = base_key in down
        for modifiers in variants:
            if physically_down:
                actions.append(("up", base_key))
            for modifier in modifiers:
                actions.append(("down", modifier))
            actions.append(("down", base_key))
            for modifier in reversed(modifiers):
                actions.append(("up", modifier))
            physically_down = True
        down.add(base_key)
    return actions


def config_bool(value) -> bool:
    """Parse a persisted boolean without treating non-empty 'false' as true."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "enabled"}
    return False


class PlaybackPerformanceSession:
    """Temporarily reduce avoidable scheduling pauses during playback."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = bool(enabled)
        self._gc_was_enabled = False
        self._timer_resolution_set = False
        self._thread_priority_set = False
        self._active = False

    def start(self) -> None:
        if not self.enabled or self._active:
            return
        self._active = True
        self._gc_was_enabled = gc.isenabled()
        if self._gc_was_enabled:
            gc.disable()
        if sys.platform != "win32":
            return
        try:
            if ctypes.windll.winmm.timeBeginPeriod(1) == 0:
                self._timer_resolution_set = True
        except Exception:
            pass
        try:
            # THREAD_PRIORITY_ABOVE_NORMAL. This is intentionally not REALTIME
            # or HIGHEST, so the GUI and the rest of Windows stay responsive.
            current_thread = ctypes.windll.kernel32.GetCurrentThread()
            if ctypes.windll.kernel32.SetThreadPriority(current_thread, 1):
                self._thread_priority_set = True
        except Exception:
            pass

    def stop(self) -> None:
        if not self.enabled or not self._active:
            return
        self._active = False
        if sys.platform == "win32":
            if self._thread_priority_set:
                try:
                    current_thread = ctypes.windll.kernel32.GetCurrentThread()
                    ctypes.windll.kernel32.SetThreadPriority(current_thread, 0)
                except Exception:
                    pass
            if self._timer_resolution_set:
                try:
                    ctypes.windll.winmm.timeEndPeriod(1)
                except Exception:
                    pass
        if self._gc_was_enabled and not gc.isenabled():
            gc.enable()
