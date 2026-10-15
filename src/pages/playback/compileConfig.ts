import type { PlaybackConfig } from "./types";

export const NOTES_CONFIG_KEYS: readonly (keyof PlaybackConfig)[] = [
  "humanization_on",
  "humanization_mode",
  "humanization_seed_mode",
  "random_seed",
  "trim_enabled",
  "trim_auto",
  "trim_start_seconds",
  "trim_end_seconds",
  "midi_clip_invalid_data",
  "simulate_hands",
  "vary_timing",
  "timing_variance",
  "vary_articulation",
  "articulation",
  "enable_drift_correction",
  "drift_decay_factor",
  "enable_chord_roll",
  "enable_tempo_sway",
  "tempo_sway_intensity",
  "invert_tempo_sway",
  "enable_mistakes",
  "mistake_chance",
  "tempo",
  "transpose",
  "use_88_key_layout",
];

export const PEDAL_CONFIG_KEYS: readonly (keyof PlaybackConfig)[] = [
  "performance_optimization",
  "pedal_style",
  "pedal_ai_mode",
  "pedal_curve_on",
  "pedal_curve_off",
  "use_midi_pedal",
  "pedal_before_humanize",
];

export function pickConfig(
  config: PlaybackConfig,
  keys: readonly (keyof PlaybackConfig)[],
): Partial<PlaybackConfig> {
  const picked: Record<string, unknown> = {};
  for (const key of keys) picked[key] = config[key];
  return picked as Partial<PlaybackConfig>;
}

function sameValue(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (typeof a !== "object" || typeof b !== "object") return false;
  return JSON.stringify(a) === JSON.stringify(b);
}

export function configDiffers(
  config: PlaybackConfig,
  compiled: Partial<PlaybackConfig> | null,
  keys: readonly (keyof PlaybackConfig)[],
): boolean {
  if (compiled === null) return false;
  return keys.some((key) => !sameValue(config[key], compiled[key]));
}
