import { DEFAULT_CONFIG, PEDAL_MAPPING, type PlaybackConfig } from "./types";
import { setGlobalHumanization, validSeed } from "./humanization";

type ConfigKey = Exclude<
  keyof PlaybackConfig,
  "midi_file" | "pedal_curve_on" | "pedal_curve_off"
>;

export const PERSISTED_NAMES: Record<ConfigKey, string> = {
  tempo: "tempo",
  transpose: "transpose",
  pedal_style: "pedal_style",
  use_88_key_layout: "use_88_key_layout",
  countdown: "countdown",
  release_pedal_on_start: "release_pedal_on_start",
  pedal_ai_mode: "pedal_ai_mode",
  countdown_seconds: "countdown_seconds",
  trim_enabled: "trim_enabled",
  trim_auto: "trim_auto",
  trim_start_seconds: "trim_start_seconds",
  trim_end_seconds: "trim_end_seconds",
  auto_pause: "auto_pause",
  performance_optimization: "performance_optimization",
  humanization_on: "humanization_on",
  humanization_mode: "humanization_mode",
  humanization_seed_mode: "humanization_seed_mode",
  random_seed: "humanization_seed",
  midi_clip_invalid_data: "midi_clip_invalid_data",
  debug_mode: "debug_mode",
  simulate_hands: "simulate_hands",
  enable_chord_roll: "enable_chord_roll",
  vary_timing: "enable_vary_timing",
  timing_variance: "value_timing_variance",
  vary_articulation: "enable_vary_articulation",
  articulation: "value_articulation",
  enable_drift_correction: "enable_hand_drift",
  drift_decay_factor: "value_hand_drift_decay",
  enable_mistakes: "enable_mistakes",
  mistake_chance: "value_mistake_chance",
  enable_tempo_sway: "enable_tempo_sway",
  tempo_sway_intensity: "value_tempo_sway_intensity",
  invert_tempo_sway: "invert_tempo_sway",
  use_midi_pedal: "use_midi_pedal",
  pedal_before_humanize: "pedal_before_humanize",
};

const CONFIG_KEYS = Object.keys(PERSISTED_NAMES) as ConfigKey[];
const PEDAL_STYLES: readonly unknown[] = Object.values(PEDAL_MAPPING);

function isValid(key: ConfigKey, value: unknown): boolean {
  if (key === "pedal_ai_mode") return ["auto", "custom"].includes(String(value));
  if (key === "random_seed") return value === null || validSeed(value);
  if (key === "humanization_mode")
    return ["disabled", "global", "individual"].includes(String(value));
  if (key === "humanization_seed_mode")
    return ["dynamic", "fixed_random", "fixed_custom"].includes(String(value));
  if (key === "countdown_seconds")
    return (
      typeof value === "number" &&
      Number.isInteger(value) &&
      value >= 1 &&
      value <= 10
    );
  if (key === "trim_start_seconds" || key === "trim_end_seconds")
    return typeof value === "number" && Number.isFinite(value) && value >= 0;
  if (key === "pedal_style") return PEDAL_STYLES.includes(value);
  const expected = typeof DEFAULT_CONFIG[key];
  return (
    typeof value === expected &&
    (expected !== "number" || Number.isFinite(value))
  );
}

export function configToPatch(config: PlaybackConfig): Record<string, unknown> {
  const patch: Record<string, unknown> = {};
  for (const key of CONFIG_KEYS) patch[PERSISTED_NAMES[key]] = config[key];
  return patch;
}

export function configFromSaved(
  saved: Record<string, unknown>,
): PlaybackConfig | undefined {
  setGlobalHumanization(saved.global_humanization);
  const restored: Record<string, unknown> = {};
  for (const key of CONFIG_KEYS) {
    let value = saved[PERSISTED_NAMES[key]];
    if (key === "random_seed" && typeof value === "string" && value.trim())
      value = Number(value);
    if (key === "performance_optimization" && typeof value === "string")
      value = ["1", "true", "yes", "on", "enabled"].includes(
        value.trim().toLowerCase(),
      );
    if (isValid(key, value)) restored[key] = value;
  }
  if (restored.humanization_mode === "disabled")
    restored.humanization_on = false;
  return Object.keys(restored).length > 0
    ? { ...DEFAULT_CONFIG, ...restored }
    : undefined;
}
