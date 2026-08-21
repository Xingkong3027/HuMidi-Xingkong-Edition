import unittest
from types import SimpleNamespace

from core.models import Note
from core.trimming import apply_trim, selected_track_bounds, trimmed_duration_hint


class TempoMap:
    def __init__(self, events, time_signatures):
        self.events = sorted(events)
        self.time_signatures = sorted(time_signatures)

    def get_tempo_at(self, time_value):
        active = 500000
        for event_time, tempo in self.events:
            if event_time <= time_value:
                active = tempo
            else:
                break
        return active


class TrimmingTests(unittest.TestCase):
    @staticmethod
    def note(note_id, start, duration, pitch=60):
        return Note(note_id, pitch, 80, start, duration, "unknown", 0, 0)

    def test_auto_trim_removes_leading_silence_and_shifts_tempo_map(self):
        notes = [self.note(1, 5.0, 1.0), self.note(2, 8.0, 2.0)]
        tempo = TempoMap([(0.0, 500000), (6.0, 400000)], [(0.0, 4, 4)])
        trimmed, shifted, start, end = apply_trim(
            notes, tempo, {"trim_enabled": True, "trim_auto": True}
        )
        self.assertEqual((start, end), (5.0, 10.0))
        self.assertEqual([round(n.start_time, 3) for n in trimmed], [0.0, 3.0])
        self.assertEqual(shifted.events[0], (0.0, 500000))
        self.assertIn((1.0, 400000), shifted.events)

    def test_manual_trim_clips_boundary_notes(self):
        notes = [self.note(1, 2.0, 4.0), self.note(2, 7.0, 4.0)]
        tempo = TempoMap([(0.0, 500000)], [])
        trimmed, _shifted, start, end = apply_trim(
            notes,
            tempo,
            {
                "trim_enabled": True,
                "trim_auto": False,
                "trim_start_seconds": 4.0,
                "trim_end_seconds": 9.0,
            },
        )
        self.assertEqual((start, end), (4.0, 9.0))
        self.assertEqual(len(trimmed), 2)
        self.assertAlmostEqual(trimmed[0].start_time, 0.0)
        self.assertAlmostEqual(trimmed[0].duration, 2.0)
        self.assertAlmostEqual(trimmed[1].start_time, 3.0)
        self.assertAlmostEqual(trimmed[1].duration, 2.0)

    def test_selected_bounds_and_duration_respect_tempo_and_auto_trim(self):
        track = SimpleNamespace(notes=[self.note(1, 6.0, 2.0), self.note(2, 10.0, 2.0)])
        selection = [(track, "Auto-Detect")]
        self.assertEqual(selected_track_bounds(selection, 200.0), (3.0, 6.0))
        self.assertEqual(
            trimmed_duration_hint(
                {"tempo": 200.0, "trim_enabled": True, "trim_auto": True},
                selection,
            ),
            3.0,
        )

    def test_invalid_manual_range_is_rejected(self):
        notes = [self.note(1, 1.0, 1.0)]
        with self.assertRaises(ValueError):
            apply_trim(
                notes,
                TempoMap([(0.0, 500000)], []),
                {
                    "trim_enabled": True,
                    "trim_auto": False,
                    "trim_start_seconds": 2.0,
                    "trim_end_seconds": 1.0,
                },
            )


if __name__ == "__main__":
    unittest.main()
