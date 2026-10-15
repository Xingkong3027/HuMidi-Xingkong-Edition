import { describe, it, expect } from "vitest";
import {
  nextSongId,
  songConfig,
  songSettings,
  playlistSourceLabel,
  playlistCompilationKey,
} from "./playlist";
import { DEFAULT_CONFIG } from "../pages/playback/types";
describe("playlist migration and sequencing", () => {
  it.each([null, undefined, {}])("restores missing or invalid legacy curve containers (%s) without losing valid curves", (invalid) => {
    const valid = [{time:0,value:0.6}];
    const restored = songConfig({tempo:1,tempo_unit:"ratio",pedal_curve_on:invalid,pedal_curve_off:valid,pedal_ai_mode:"custom"});
    expect(restored.pedal_curve_on).toEqual([]);
    expect(restored.pedal_curve_off).toEqual(valid);
    expect(restored.pedal_ai_mode).toBe("custom");
    expect(songConfig(songSettings(restored))).toMatchObject(restored);
  });
  it("identifies names lost by older edits without presenting storage IDs as filenames", () => {
    expect(
      playlistSourceLabel({
        id: "copy",
        source_type: "midi",
        source_label: "e03382803a676d8d57c62ffa49bcfba4.mid",
      }),
    ).toBe("MIDI 原件（编号文件）");
    expect(
      playlistSourceLabel({
        id: "abc",
        source_type: "midi",
        source_label: "abc.mid",
      }),
    ).toBe("MIDI 原件（原文件名未保留）");
    expect(
      playlistSourceLabel({
        id: "abc",
        source_type: "midi",
        source_label: "告白气球.mid",
      }),
    ).toBe("告白气球.mid");
  });
  it("restores archive ratios without double conversion", () => {
    const c = {
      ...DEFAULT_CONFIG,
      tempo: 125,
      articulation: 91,
      drift_decay_factor: 37,
    };
    expect(songConfig(songSettings(c))).toMatchObject(c);
  });
  it("restores real Python percent tempos and keeps its other units unchanged", () => {
    for (const tempo of [1, 80, 100, 125]) {
      const legacy = { tempo, humanization_seed: null, humanization_mode: "disabled", articulation: 0.95, drift_decay_factor: 0.25, trim_enabled: true, trim_start_seconds: 2.68359375, pedal_style: "hybrid" };
      const restored = songConfig(legacy);
      expect(restored).toMatchObject({ tempo, articulation: 95, drift_decay_factor: 25, trim_enabled: true, trim_start_seconds: 2.68359375, pedal_style: "hybrid", humanization_on: false });
      expect(songConfig(songSettings(restored))).toMatchObject(restored);
    }
  });
  it("respects explicit units instead of guessing from the magnitude", () => {
    expect(songConfig({ tempo: 1, tempo_unit: "percent" }).tempo).toBe(1);
    expect(songConfig({ tempo: 100, tempo_unit: "ratio", humanization_seed: null }).tempo).toBe(10000);
    expect(songConfig({ tempo: 0.8, random_seed: null, humanization_on: false }).tempo).toBe(80);
  });
  it("retains legacy fixed seeds", () => {
    expect(
      songConfig({
        humanization_seed: 123,
        humanization_seed_mode: "fixed_custom",
        humanization_mode: "disabled",
      }),
    ).toMatchObject({ random_seed: 123, humanization_on: false });
  });
  it("stops at sequence end and wraps only repeat mode", () => {
    const items = [{ id: "a" }, { id: "b" }];
    expect(nextSongId(items, "b", "sequential")).toBeNull();
    expect(nextSongId(items, "b", "repeat_all")).toBe("a");
    expect(nextSongId(items, "a", "single")).toBeNull();
    expect(nextSongId(items, "a", "repeat_one")).toBe("a");
    expect(nextSongId(items, "a", "shuffle", 1, () => 0)).toBe("b");
  });
});

it("isolates performance AI modes but reuses caches for countdown changes", () => {
  const key = playlistCompilationKey(DEFAULT_CONFIG);
  expect(playlistCompilationKey({ ...DEFAULT_CONFIG, countdown: !DEFAULT_CONFIG.countdown })).toBe(key);
  expect(playlistCompilationKey({ ...DEFAULT_CONFIG, performance_optimization: !DEFAULT_CONFIG.performance_optimization })).not.toBe(key);
});

it("preserves legacy custom curves while keeping explicit automatic mode automatic",()=>{
  const curves={pedal_curve_on:[{time:0,value:.6}],pedal_curve_off:[{time:0,value:.3}]};
  expect(songConfig(curves).pedal_ai_mode).toBe("custom");
  expect(songConfig({...curves,pedal_ai_mode:"auto"}).pedal_ai_mode).toBe("auto");
  expect(songConfig({}).pedal_ai_mode).toBe("auto");
});
it("startup pedal release does not invalidate a song's compiled cache",()=>{
  expect(playlistCompilationKey({...DEFAULT_CONFIG,release_pedal_on_start:true})).toBe(playlistCompilationKey(DEFAULT_CONFIG));
});
