from __future__ import annotations

import copy
from typing import Iterable, Sequence

from core.models import Note


def selected_track_bounds(selected_tracks_info: Sequence, tempo_percent: float = 100.0) -> tuple[float, float]:
    """Return first note start and last note end for selected, non-ignored tracks.

    Track note times are stored at the original MIDI tempo. The returned values
    are expressed in the current playback timeline after applying tempo_percent.
    """
    starts: list[float] = []
    ends: list[float] = []
    for track, role in selected_tracks_info or []:
        if str(role) == "Ignore":
            continue
        for note in getattr(track, "notes", []) or []:
            starts.append(float(note.start_time))
            ends.append(float(note.end_time))
    if not starts:
        return 0.0, 0.0
    tempo_scale = max(0.01, float(tempo_percent or 100.0) / 100.0)
    return min(starts) / tempo_scale, max(ends) / tempo_scale


def trimmed_duration_hint(config: dict, selected_tracks_info: Sequence) -> float:
    """Estimate the resulting duration for playlist metadata."""
    start, end = selected_track_bounds(
        selected_tracks_info, float(config.get("tempo", 100.0) or 100.0)
    )
    if end <= start:
        return 0.0
    if not bool(config.get("trim_enabled", False)):
        return end
    if bool(config.get("trim_auto", False)):
        return max(0.0, end - start)
    trim_start = max(0.0, float(config.get("trim_start_seconds", 0.0) or 0.0))
    raw_end = float(config.get("trim_end_seconds", end) or end)
    trim_end = min(end, raw_end)
    if trim_end <= trim_start:
        return 0.0
    return max(0.0, trim_end - trim_start)


def _shift_tempo_map(tempo_map, trim_start: float, trim_end: float):
    """Crop and shift a TempoMap-like object without importing it here."""
    tempo_cls = type(tempo_map)
    active_tempo = int(tempo_map.get_tempo_at(trim_start))
    tempo_events = [(0.0, active_tempo)]
    for event_time, tempo in getattr(tempo_map, "events", []) or []:
        event_time = float(event_time)
        if trim_start < event_time <= trim_end:
            tempo_events.append((event_time - trim_start, int(tempo)))

    signatures = list(getattr(tempo_map, "time_signatures", []) or [])
    if signatures:
        active_signature = signatures[0]
        for signature in signatures:
            if float(signature[0]) <= trim_start:
                active_signature = signature
            else:
                break
        time_signatures = [(0.0, int(active_signature[1]), int(active_signature[2]))]
        for event_time, numerator, denominator in signatures:
            event_time = float(event_time)
            if trim_start < event_time <= trim_end:
                time_signatures.append(
                    (event_time - trim_start, int(numerator), int(denominator))
                )
    else:
        time_signatures = []
    return tempo_cls(tempo_events, time_signatures)


def apply_trim(notes: Iterable[Note], tempo_map, config: dict):
    """Apply manual or automatic trim and shift the remaining song to time zero.

    Returns ``(trimmed_notes, trimmed_tempo_map, trim_start, trim_end)``.
    Notes overlapping either boundary are clipped instead of discarded.
    """
    source_notes = sorted(list(notes), key=lambda note: note.start_time)
    if not source_notes or not bool(config.get("trim_enabled", False)):
        return source_notes, tempo_map, 0.0, max(
            (float(note.end_time) for note in source_notes), default=0.0
        )

    first_start = min(float(note.start_time) for note in source_notes)
    last_end = max(float(note.end_time) for note in source_notes)
    if bool(config.get("trim_auto", False)):
        trim_start, trim_end = first_start, last_end
    else:
        trim_start = max(0.0, float(config.get("trim_start_seconds", 0.0) or 0.0))
        trim_end = float(config.get("trim_end_seconds", last_end) or last_end)
        trim_end = min(last_end, trim_end)
        if trim_end <= trim_start:
            raise ValueError("Trim end must be later than trim start.")

    trimmed: list[Note] = []
    for note in source_notes:
        source_start = float(note.start_time)
        source_end = float(note.end_time)
        if source_end <= trim_start or source_start >= trim_end:
            continue
        clipped_start = max(source_start, trim_start)
        clipped_end = min(source_end, trim_end)
        if clipped_end <= clipped_start:
            continue
        copied = copy.deepcopy(note)
        copied.start_time = max(0.0, clipped_start - trim_start)
        copied.duration = max(0.01, clipped_end - clipped_start)
        trimmed.append(copied)

    if not trimmed:
        raise ValueError("The selected trim range contains no playable notes.")
    shifted_map = _shift_tempo_map(tempo_map, trim_start, trim_end)
    return trimmed, shifted_map, trim_start, trim_end
