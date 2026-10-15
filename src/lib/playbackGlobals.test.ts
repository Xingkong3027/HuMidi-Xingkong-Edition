import { describe, expect, it } from "vitest";
import { readGlobalPlayback, SONG_IGNORED_GLOBAL_KEYS } from "./playbackGlobals";
import { songConfig, songSettings, playlistCompilationKey } from "./playlist";
import { configFromSaved, configToPatch } from "../pages/playback/persistedConfig";
import { DEFAULT_CONFIG } from "../pages/playback/types";

describe("application playback preferences versus song settings", () => {
  it("migrates old default settings with explicit global values taking priority", () => {
    expect(readGlobalPlayback({release_pedal_on_start:false,auto_pause:true,debug_mode:false,
      xk_default_settings:{release_pedal_on_start:true,auto_pause:false,debug_mode:true}}))
      .toEqual({releasePedalOnStart:true,pauseAtEnd:false,debugOutput:true});
    expect(readGlobalPlayback({xk_global_auto_pause:true,xk_global_debug_mode:false,
      xk_default_settings:{auto_pause:false,debug_mode:true}}))
      .toMatchObject({pauseAtEnd:true,debugOutput:false});
  });
  it("has documented defaults and ignores invalid legacy types", () => {
    expect(readGlobalPlayback({auto_pause:"false",debug_mode:1})).toEqual({releasePedalOnStart:false,pauseAtEnd:true,debugOutput:false});
  });
  it("does not restore or re-export runtime flags from songs and import defaults", () => {
    const old={...DEFAULT_CONFIG,release_pedal_on_start:true,auto_pause:false,debug_mode:true,
      auto_focus_roblox:true,pause_on_app_focus:true,tempo:1,tempo_unit:"ratio"};
    const restored=songConfig(old);
    expect(restored).toMatchObject({release_pedal_on_start:false,auto_pause:true,debug_mode:false,tempo:100});
    for (const key of SONG_IGNORED_GLOBAL_KEYS) expect(songSettings(restored)).not.toHaveProperty(key);
    const patch=configToPatch({...DEFAULT_CONFIG,release_pedal_on_start:true,auto_pause:false,debug_mode:true});
    for (const key of SONG_IGNORED_GLOBAL_KEYS) expect(patch).not.toHaveProperty(key);
    expect(configFromSaved({tempo:125,release_pedal_on_start:true,auto_pause:false,debug_mode:true})).toMatchObject({tempo:125,release_pedal_on_start:false,auto_pause:true,debug_mode:false});
  });
  it("does not invalidate musical caches when only runtime flags differ", () => {
    expect(playlistCompilationKey({...DEFAULT_CONFIG,release_pedal_on_start:true,auto_pause:false,debug_mode:true}))
      .toBe(playlistCompilationKey(DEFAULT_CONFIG));
  });
});
