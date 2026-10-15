import { beforeEach, describe, expect, it, vi } from "vitest";
import { DEFAULT_CONFIG } from "./types";
import {
  extractHumanization,
  resolvePlaybackConfig,
  setGlobalHumanization,
  updatePerformanceConfig,
  validSeed,
  usesDynamicRandomness,
} from "./humanization";
import { configFromSaved, configToPatch } from "./persistedConfig";
import { configDiffers, NOTES_CONFIG_KEYS, pickConfig } from "./compileConfig";

describe("Xingkong humanization policy", () => {
  it("reuses compiled output in dynamic mode with no active random effects", () => {
    expect(usesDynamicRandomness(DEFAULT_CONFIG)).toBe(false);
    expect(
      usesDynamicRandomness({ ...DEFAULT_CONFIG, vary_timing: true }),
    ).toBe(true);
    expect(
      usesDynamicRandomness({
        ...DEFAULT_CONFIG,
        vary_timing: true,
        humanization_mode: "disabled",
      }),
    ).toBe(false);
    expect(
      usesDynamicRandomness({
        ...DEFAULT_CONFIG,
        vary_timing: true,
        humanization_seed_mode: "fixed_custom",
        random_seed: 42,
      }),
    ).toBe(false);
  });
  beforeEach(() => setGlobalHumanization(extractHumanization(DEFAULT_CONFIG)));
  it("preserves stored seeds and legacy numeric seed strings", () => {
    const restored = configFromSaved({
      humanization_mode: "individual",
      humanization_seed_mode: "fixed_random",
      humanization_seed: "12345",
    })!;
    expect(restored.random_seed).toBe(12345);
    expect(configFromSaved(configToPatch(restored))?.random_seed).toBe(12345);
    expect(
      updatePerformanceConfig(restored, { countdown_seconds: 8 }).random_seed,
    ).toBe(12345);
  });
  it("renews generated seeds for performance changes, retaining custom seeds", () => {
    vi.spyOn(crypto, "getRandomValues").mockImplementation((array) => {
      (array as Uint32Array)[0] = 999;
      return array;
    });
    const fixed = {
      ...DEFAULT_CONFIG,
      humanization_seed_mode: "fixed_random" as const,
      random_seed: 22,
    };
    expect(
      updatePerformanceConfig(fixed, { timing_variance: 0.04 }).random_seed,
    ).toBe(999);
    expect(
      updatePerformanceConfig(
        { ...fixed, humanization_seed_mode: "fixed_custom" },
        { timing_variance: 0.04 },
      ).random_seed,
    ).toBe(22);
    vi.restoreAllMocks();
  });
  it("disables all stochastic switches without erasing the user's values", () => {
    const current = {
      ...DEFAULT_CONFIG,
      humanization_mode: "disabled" as const,
      vary_timing: true,
      simulate_hands: true,
      enable_mistakes: true,
      random_seed: 2,
    };
    const effective = resolvePlaybackConfig(current);
    expect(effective).toMatchObject({
      humanization_on: false,
      vary_timing: false,
      simulate_hands: false,
      enable_mistakes: false,
      random_seed: null,
    });
    expect(current.vary_timing).toBe(true);
  });
  it("resolves the global preset only for global songs", () => {
    setGlobalHumanization({
      ...extractHumanization(DEFAULT_CONFIG),
      vary_timing: true,
      timing_variance: 0.055,
    });
    expect(
      resolvePlaybackConfig({ ...DEFAULT_CONFIG, humanization_mode: "global" })
        .timing_variance,
    ).toBe(0.055);
    expect(resolvePlaybackConfig(DEFAULT_CONFIG).timing_variance).toBe(0.01);
  });
  it("uses fresh stochastic compilation in dynamic mode and rejects unsafe seeds", () => {
    expect(
      resolvePlaybackConfig({ ...DEFAULT_CONFIG, random_seed: 44 }).random_seed,
    ).toBeNull();
    expect(validSeed(Number.MAX_SAFE_INTEGER + 1)).toBe(false);
    expect(validSeed(-1)).toBe(false);
    expect(validSeed(0)).toBe(true);
  });
  it("accepts persisted false correctly and bounds countdown", () => {
    expect(
      configFromSaved({
        performance_optimization: "false",
        countdown_seconds: 200,
      }),
    ).toMatchObject({ performance_optimization: false, countdown_seconds: 3 });
  });
  it("invalidates note compilation for trim and seed, not runtime countdown", () => {
    const compiled = pickConfig(DEFAULT_CONFIG, NOTES_CONFIG_KEYS);
    expect(
      configDiffers(
        { ...DEFAULT_CONFIG, trim_enabled: true },
        compiled,
        NOTES_CONFIG_KEYS,
      ),
    ).toBe(true);
    expect(
      configDiffers(
        { ...DEFAULT_CONFIG, random_seed: 5 },
        compiled,
        NOTES_CONFIG_KEYS,
      ),
    ).toBe(true);
    expect(
      configDiffers(
        { ...DEFAULT_CONFIG, countdown_seconds: 8 },
        compiled,
        NOTES_CONFIG_KEYS,
      ),
    ).toBe(false);
  });
});
