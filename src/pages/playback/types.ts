import type { ThresholdNode } from "../../lib/thresholdCurve";

export interface PlaybackConfig {
  midi_file: string;
  tempo: number;
  transpose: number;
  countdown: boolean;
  release_pedal_on_start: boolean;
  countdown_seconds: number;
  trim_enabled: boolean;
  trim_auto: boolean;
  trim_start_seconds: number;
  trim_end_seconds: number;
  auto_pause: boolean;
  performance_optimization: boolean;
  humanization_on: boolean;
  humanization_mode: "disabled" | "global" | "individual";
  humanization_seed_mode: "dynamic" | "fixed_random" | "fixed_custom";
  random_seed: number | null;
  midi_clip_invalid_data: boolean;
  use_88_key_layout: boolean;
  pedal_style: string;
  pedal_ai_mode: "auto" | "custom";
  pedal_curve_on: ThresholdNode[];
  pedal_curve_off: ThresholdNode[];
  debug_mode: boolean;
  simulate_hands: boolean;
  enable_chord_roll: boolean;
  vary_timing: boolean;
  timing_variance: number;
  vary_articulation: boolean;
  articulation: number;
  enable_drift_correction: boolean;
  drift_decay_factor: number;
  enable_mistakes: boolean;
  mistake_chance: number;
  enable_tempo_sway: boolean;
  tempo_sway_intensity: number;
  invert_tempo_sway: boolean;
  use_midi_pedal: boolean;
  pedal_before_humanize: boolean;
}

export const PEDAL_MAPPING: Record<string, string> = {
  None: "none",
  PedalAI: "ai",
  Adaptive: "hybrid",
  Rhythmic: "rhythmic",
  Harmonic: "legato",
};

export const DEFAULT_CONFIG: PlaybackConfig = {
  midi_file: "",
  tempo: 100,
  transpose: 0,
  countdown: true,
  release_pedal_on_start: false,
  countdown_seconds: 3,
  trim_enabled: false,
  trim_auto: true,
  trim_start_seconds: 0,
  trim_end_seconds: 0,
  auto_pause: true,
  performance_optimization: false,
  humanization_on: true,
  humanization_mode: "individual",
  humanization_seed_mode: "dynamic",
  random_seed: null,
  midi_clip_invalid_data: false,
  use_88_key_layout: false,
  pedal_style: "ai",
  pedal_ai_mode: "auto",
  pedal_curve_on: [],
  pedal_curve_off: [],
  debug_mode: false,
  simulate_hands: false,
  enable_chord_roll: false,
  vary_timing: false,
  timing_variance: 0.01,
  vary_articulation: false,
  articulation: 95,
  enable_drift_correction: false,
  drift_decay_factor: 25,
  enable_mistakes: false,
  mistake_chance: 0.5,
  enable_tempo_sway: false,
  tempo_sway_intensity: 0.015,
  invert_tempo_sway: false,
  use_midi_pedal: false,
  pedal_before_humanize: true,
};
