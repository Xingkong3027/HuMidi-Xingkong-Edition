import random
import numpy as np
from typing import List, Set, Dict, Optional

from core.models import Note, MusicalSection
from core.core import get_time_groups


class Humanizer:
    def __init__(self, config: Dict, debug_log: Optional[List[str]] = None):
        self.config = config
        self.debug_log = debug_log
        self.left_hand_drift = 0.0
        self.right_hand_drift = 0.0

    def apply_to_hand(self, notes: List[Note], hand: str, resync_points: Set[float]):
        if not any([self.config.get('vary_timing'), self.config.get('vary_articulation'),
                    self.config.get('enable_drift_correction'), self.config.get('enable_chord_roll')]):
            return

        time_groups = get_time_groups(notes)
        for group in time_groups:
            is_resync_point = round(group[0].start_time, 2) in resync_points

            if self.config.get('enable_drift_correction') and is_resync_point:
                if hand == 'left': self.left_hand_drift *= self.config.get('drift_decay_factor')
                else: self.right_hand_drift *= self.config.get('drift_decay_factor')

            group_timing_offset = 0.0
            if self.config.get('vary_timing'):
                sigma = self.config.get('timing_variance')
                group_timing_offset = random.gauss(0, sigma)
                group_timing_offset = max(-3*sigma, min(3*sigma, group_timing_offset))

            group_articulation = self.config.get('articulation')
            if self.config.get('vary_articulation'):
                group_articulation -= (random.random() * 0.1)

            if self.config.get('enable_chord_roll') and len(group) > 1:
                group.sort(key=lambda n: n.pitch)
                for i, note in enumerate(group):
                    note.start_time += (i * 0.006)

            for note in group:
                current_drift = self.left_hand_drift if hand == 'left' else self.right_hand_drift
                note.start_time += group_timing_offset
                if self.config.get('enable_drift_correction'):
                    note.start_time += current_drift

                note.duration *= group_articulation
                if note.duration < 0.03: note.duration = 0.03

            if self.config.get('enable_drift_correction'):
                if hand == 'left': self.left_hand_drift += group_timing_offset
                else: self.right_hand_drift += group_timing_offset

    def apply_tempo_rubato(self, all_notes: List[Note], sections: List[MusicalSection]):
        if not self.config.get('enable_tempo_sway'): return
        base_intensity = self.config.get('tempo_sway_intensity', 0.0)
        invert_sway = self.config.get('invert_tempo_sway', False)
        note_map = {note.id: note for note in all_notes}
        for section in sections:
            pace_multiplier = 1.0
            if section.pace_label == 'fast': pace_multiplier = 1.5 if invert_sway else 0.25
            elif section.pace_label == 'slow': pace_multiplier = 0.25 if invert_sway else 1.5
            section_duration = section.end_time - section.start_time
            if section_duration < 1.0: continue
            intensity = base_intensity * pace_multiplier
            for note in section.notes:
                if note.id in note_map:
                    rel_pos = (note.start_time - section.start_time) / section_duration
                    time_shift = np.sin(rel_pos * np.pi) * intensity
                    note_map[note.id].start_time -= time_shift
