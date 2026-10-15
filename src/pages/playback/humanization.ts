import { DEFAULT_CONFIG, type PlaybackConfig } from "./types";

export const HUMANIZATION_KEYS = [
  "simulate_hands",
  "enable_chord_roll",
  "vary_timing",
  "timing_variance",
  "vary_articulation",
  "articulation",
  "enable_drift_correction",
  "drift_decay_factor",
  "enable_mistakes",
  "mistake_chance",
  "enable_tempo_sway",
  "tempo_sway_intensity",
  "invert_tempo_sway",
] as const satisfies readonly (keyof PlaybackConfig)[];
export type HumanizationPreset = Pick<
  PlaybackConfig,
  (typeof HUMANIZATION_KEYS)[number]
>;
export function extractHumanization(
  config: PlaybackConfig,
): HumanizationPreset {
  return Object.fromEntries(
    HUMANIZATION_KEYS.map((key) => [key, config[key]]),
  ) as unknown as HumanizationPreset;
}
let globalPreset: HumanizationPreset = extractHumanization(DEFAULT_CONFIG);
export function getGlobalHumanization(): HumanizationPreset {
  return { ...globalPreset };
}
export function setGlobalHumanization(raw: unknown): void {
  if (!raw || typeof raw !== "object") return;
  const values = raw as Record<string, unknown>;
  globalPreset = Object.fromEntries(
    HUMANIZATION_KEYS.map((key) => {
      const value = values[key];
      const valid =
        typeof value === typeof DEFAULT_CONFIG[key] &&
        (typeof value !== "number" || Number.isFinite(value));
      return [key, valid ? value : DEFAULT_CONFIG[key]];
    }),
  ) as unknown as HumanizationPreset;
}
export function newRandomSeed(): number {
  const values = new Uint32Array(1);
  crypto.getRandomValues(values);
  return values[0];
}
export function validSeed(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
}
/** Dynamic mode only invalidates a performance when an active effect draws randomness. */
export function usesDynamicRandomness(config: PlaybackConfig): boolean {
  const c = resolvePlaybackConfig(config);
  return (
    c.humanization_on &&
    c.random_seed === null &&
    [
      c.vary_timing,
      c.vary_articulation,
      c.enable_chord_roll,
      c.enable_drift_correction,
      c.enable_tempo_sway,
      c.enable_mistakes,
    ].some(Boolean)
  );
}
/** Resolve UI-only policy fields into the effective compilation settings. */
export function resolvePlaybackConfig(config: PlaybackConfig): PlaybackConfig {
  const resolved = {
    ...config,
    ...(config.humanization_mode === "global" ? globalPreset : {}),
  };
  resolved.humanization_on =
    config.humanization_on && config.humanization_mode !== "disabled";
  resolved.random_seed =
    config.humanization_seed_mode === "dynamic"
      ? null
      : validSeed(config.random_seed)
        ? config.random_seed
        : 1;
  if (!resolved.humanization_on) {
    for (const key of HUMANIZATION_KEYS) {
      if (typeof resolved[key] === "boolean")
        (resolved as unknown as Record<string, unknown>)[key] = false;
    }
    resolved.random_seed = null;
  }
  return resolved;
}

/** Only interactive setting changes renew generated seeds; restoring a song uses setConfig. */
export function updatePerformanceConfig(
  current: PlaybackConfig,
  patch: Partial<PlaybackConfig>,
): PlaybackConfig {
  const result = { ...current, ...patch };
  if (patch.humanization_mode !== undefined)
    result.humanization_on = patch.humanization_mode !== "disabled";
  if (
    patch.humanization_on !== undefined &&
    patch.humanization_mode === undefined
  ) {
    result.humanization_mode = patch.humanization_on
      ? "individual"
      : "disabled";
  }
  if (result.humanization_seed_mode === "dynamic") result.random_seed = null;
  else if (
    result.humanization_seed_mode === "fixed_random" &&
    (!validSeed(result.random_seed) ||
      HUMANIZATION_KEYS.some((key) => key in patch) ||
      "humanization_mode" in patch ||
      "humanization_seed_mode" in patch)
  )
    result.random_seed = newRandomSeed();
  else if (!validSeed(result.random_seed)) result.random_seed = 1;
  return result;
}
