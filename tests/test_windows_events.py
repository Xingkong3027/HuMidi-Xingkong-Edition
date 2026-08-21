from __future__ import annotations

import unittest

from core.windows_events import wheel_delta_from_wparam


class WindowsMouseWheelTests(unittest.TestCase):
    def test_extracts_positive_and_negative_wheel_delta(self):
        self.assertEqual(wheel_delta_from_wparam(120 << 16), 120)
        self.assertEqual(wheel_delta_from_wparam((0xFF88 << 16)), -120)

    def test_ignores_low_word_key_flags(self):
        self.assertEqual(wheel_delta_from_wparam((240 << 16) | 0x0005), 240)


if __name__ == "__main__":
    unittest.main()
