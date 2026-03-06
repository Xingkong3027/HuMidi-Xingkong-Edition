from typing import TypedDict


class PlaybackConfig(TypedDict, total=False):
    """Typed schema for the playback configuration dict.

    All keys are optional (total=False) to match the .get(key, default) access
    pattern used throughout the codebase. This is a pure type annotation — at
    runtime the dict is still a plain dict and no existing code needs changing.
    Import it for type annotations on function signatures to get IDE autocomplete
    and static analysis coverage over config key names.
    """
    midi_file: str
    tempo: float
    pedal_style: str
    use_88_key_layout: bool
    simulate_hands: bool
    humanization_on: bool
    vary_timing: bool
    timing_variance: float
    vary_articulation: bool
    articulation: float
    enable_drift_correction: bool
    drift_decay_factor: float
    enable_chord_roll: bool
    enable_tempo_sway: bool
    tempo_sway_intensity: float
    invert_tempo_sway: bool
    enable_mistakes: bool
    mistake_chance: float
    countdown: bool
    auto_pause: bool
    debug_mode: bool
    use_ai_pedal: bool
