import random
import sys
import types
import unittest

from core.models import Note


# Humanizer only needs get_time_groups from core.core. Stub that small helper so
# this deterministic-randomness test does not require Windows keyboard packages.
def _get_time_groups(notes, tolerance=0.01):
    groups = []
    for note in sorted(notes, key=lambda item: item.start_time):
        if groups and abs(groups[-1][0].start_time - note.start_time) <= tolerance:
            groups[-1].append(note)
        else:
            groups.append([note])
    return groups


_core_stub = types.ModuleType("core.core")
_core_stub.get_time_groups = _get_time_groups
sys.modules.setdefault("core.core", _core_stub)

from core.humanizer import Humanizer  # noqa: E402


class HumanizerSeedTests(unittest.TestCase):
    @staticmethod
    def _notes():
        return [
            Note(1, 60, 90, 0.0, 0.5, "right", 0, 0),
            Note(2, 64, 90, 0.0, 0.5, "right", 0, 0),
            Note(3, 67, 90, 0.5, 0.5, "right", 0, 0),
        ]

    @staticmethod
    def _config():
        return {
            "vary_timing": True,
            "timing_variance": 0.01,
            "vary_articulation": True,
            "articulation": 0.95,
            "enable_drift_correction": True,
            "drift_decay_factor": 0.25,
            "enable_chord_roll": True,
        }

    def _humanize(self, seed):
        notes = self._notes()
        Humanizer(self._config(), rng=random.Random(seed)).apply_to_hand(notes, "right", set())
        return [(note.pitch, note.start_time, note.duration) for note in notes]

    def test_same_seed_repeats_exact_performance(self):
        self.assertEqual(self._humanize(123456), self._humanize(123456))

    def test_different_seeds_change_performance(self):
        self.assertNotEqual(self._humanize(123456), self._humanize(654321))


if __name__ == "__main__":
    unittest.main()
