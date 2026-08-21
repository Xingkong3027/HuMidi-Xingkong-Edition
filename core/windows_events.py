from __future__ import annotations

import ctypes


def wheel_delta_from_wparam(wparam: int) -> int:
    """Return the signed WM_MOUSEWHEEL delta stored in wParam's high word."""

    return ctypes.c_short((int(wparam) >> 16) & 0xFFFF).value
