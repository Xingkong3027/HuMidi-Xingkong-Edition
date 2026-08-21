import unittest

from core.performance import (
    PlaybackPerformanceSession,
    config_bool,
    build_press_action_plan,
    unique_press_specs,
)


class PerformanceOptimizationTests(unittest.TestCase):
    def test_duplicate_physical_attacks_are_collapsed(self):
        presses = [
            ("q", ()),
            ("q", ()),
            ("q", ("shift",)),
            ("q", ("shift",)),
            ("w", ()),
        ]
        self.assertEqual(
            unique_press_specs(presses),
            [("q", ()), ("q", ("shift",)), ("w", ())],
        )

    def test_modifier_variants_are_restruck_without_sleep_actions(self):
        actions = build_press_action_plan(
            [("q", ()), ("q", ("shift",)), ("q", ("shift",))]
        )
        self.assertEqual(
            actions,
            [
                ("down", "q"),
                ("up", "q"),
                ("down", "shift"),
                ("down", "q"),
                ("up", "shift"),
            ],
        )
        self.assertNotIn(("sleep", "0.001"), actions)

    def test_already_held_key_is_restruck_once(self):
        actions = build_press_action_plan([("a", ())], initially_down={"a"})
        self.assertEqual(actions, [("up", "a"), ("down", "a")])

    def test_disabled_session_is_a_safe_noop(self):
        session = PlaybackPerformanceSession(False)
        session.start()
        session.stop()

    def test_persisted_false_strings_do_not_enable_mode(self):
        self.assertFalse(config_bool(False))
        self.assertFalse(config_bool(0))
        self.assertFalse(config_bool("false"))
        self.assertFalse(config_bool("off"))
        self.assertTrue(config_bool(True))
        self.assertTrue(config_bool("true"))
        self.assertTrue(config_bool("1"))


if __name__ == "__main__":
    unittest.main()
