/** Runtime preferences are never owned by a song or its import defaults. */
export const SONG_IGNORED_GLOBAL_KEYS = [
  "release_pedal_on_start", "auto_pause", "debug_mode",
  "auto_focus_roblox", "pause_on_app_focus",
] as const;

export function withoutPlaybackGlobals<T extends Record<string, unknown>>(value: T): Record<string, unknown> {
  const result = { ...value };
  for (const key of SONG_IGNORED_GLOBAL_KEYS) delete result[key];
  // Ignore settings injected by third-party/older packages too.
  for (const key of ["xk_global_release_pedal_on_start", "xk_global_auto_pause", "xk_global_debug_mode"]) delete result[key];
  return result;
}

export function readGlobalPlayback(config: Record<string, unknown>) {
  const defaults = config.xk_default_settings && typeof config.xk_default_settings === "object"
    ? config.xk_default_settings as Record<string, unknown> : {};
  function value(key: string, fallback: boolean) {
    for (const raw of [config[`xk_global_${key}`], defaults[key], config[key]]) {
      if (typeof raw === "boolean") return raw;
    }
    return fallback;
  }
  return {
    releasePedalOnStart: value("release_pedal_on_start", false),
    pauseAtEnd: value("auto_pause", true),
    debugOutput: value("debug_mode", false),
  };
}
