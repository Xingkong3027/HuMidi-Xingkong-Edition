import { invoke } from "@tauri-apps/api/core";
import { DEFAULT_CONFIG, type PlaybackConfig } from "../pages/playback/types";
import {
  toBackendConfig,
  type SelectedTrackInfo,
  type TimelineData,
} from "./tauri";

export interface PlaylistItem {
  id: string;
  name: string;
  source_type: "midi" | "sheet";
  source_label: string;
  duration: number;
  modified_at?: string;
  midi_available: boolean;
  sheet_available: boolean;
  cache_available: boolean;
  cache_rebuild_required?: boolean;
  humanization_active?: boolean;
  random_effect_active?: boolean;
  humanization_mode: string;
  random_seed_mode: string;
}
export interface PlaylistSong {
  song_version: number;
  source: {
    type: "midi" | "sheet";
    original_path?: string;
    original_filename?: string;
    local_midi_filename?: string;
    sheet_text?: string;
    format_name?: string;
    bpm?: number;
    humanize?: boolean;
  };
  playback_settings: Record<string, unknown>;
  selected_tracks: { index: number; role: string }[];
  legacy_cache_only?: boolean;
}
/** Old xk.1 edits could lose the source name; never present a storage UUID as a MIDI name. */
export function playlistSourceLabel(
  item: Pick<PlaylistItem, "id" | "source_label" | "source_type">,
): string {
  if (item.source_type === "midi" && item.source_label === `${item.id}.mid`)
    return "MIDI 原件（原文件名未保留）";
  if (
    item.source_type === "midi" &&
    /^[0-9a-f]{32}\.midi?$/i.test(item.source_label)
  )
    return "MIDI 原件（编号文件）";
  return item.source_label;
}
export interface PlaylistDetail {
  metadata: PlaylistItem;
  song: PlaylistSong;
  midi_path: string | null;
  cache_path: string;
}
export interface ImportReport {
  imported: number;
  errors: string[];
}
export const listPlaylist = () => invoke<PlaylistItem[]>("playlist_list");
export const getPlaylistSong = (id: string) =>
  invoke<PlaylistDetail>("playlist_get", { id });
export const putPlaylistSong = (
  name: string,
  song: PlaylistSong,
  midiPath: string | null,
  duration = 0,
  id: string | null = null,
) =>
  invoke<PlaylistItem>("playlist_put", { id, name, song, midiPath, duration });
export const deletePlaylistSongs = (ids: string[]) =>
  invoke<void>("playlist_delete", { ids });
export const reorderPlaylist = (ids: string[]) =>
  invoke<void>("playlist_reorder", { ids });
export const patchPlaylistSongs = (
  ids: string[],
  patch: Record<string, unknown>,
) => invoke<void>("playlist_patch", { ids, patch });
export const exportPlaylist = (path: string, complete: boolean) =>
  invoke<number>("playlist_export", { path, complete });
export const importPlaylistLibrary = (path: string) =>
  invoke<ImportReport>("playlist_import_library", { path });
export const importPlaylist = (path: string) =>
  invoke<ImportReport>("playlist_import", { path });
export const savePlaylistMidi = (id: string, path: string) =>
  invoke<void>("playlist_save_midi", { id, path });
export function playlistCompilationKey(config: PlaybackConfig): string {
  const value = toBackendConfig(config, "") as unknown as Record<string, unknown>;
  for (const key of ["midi_file", "countdown", "release_pedal_on_start", "countdown_seconds", "auto_pause", "debug_mode"]) delete value[key];
  return JSON.stringify(value);
}
export const preparePlaylistCache = (id: string, config: PlaybackConfig) =>
  invoke<void>("playlist_prepare_cache", { id, config: toBackendConfig(config, "") });
export const cachePlaylistSong = (id: string, config: PlaybackConfig) =>
  invoke<void>("playlist_cache_current", {
    id,
    config: toBackendConfig(config, ""),
  });
export const restorePlaylistCache = (
  id: string,
  config: PlaybackConfig,
  allowLegacy = false,
) =>
  invoke<{ timeline: TimelineData; pedal_intervals: [number, number][]; confidence?: number[]; confidence_fps?: number; curve_on?: PlaybackConfig["pedal_curve_on"]; curve_off?: PlaybackConfig["pedal_curve_off"] }>(
    "playlist_restore_cache",
    { id, config: toBackendConfig(config, ""), allowLegacy },
  );

/** Python archives use percent tempo; Rust archives use ratios. Explicit unit
 * markers make migration idempotent. Legacy schema fields identify Python data. */
export function songConfig(settings: Record<string, unknown>): PlaybackConfig {
  const patch: Record<string, unknown> = {};
  for (const key of Object.keys(DEFAULT_CONFIG))
    if (
      key in settings &&
      (Array.isArray((DEFAULT_CONFIG as unknown as Record<string, unknown>)[key])
        ? Array.isArray(settings[key])
        : typeof settings[key] ===
          typeof (DEFAULT_CONFIG as unknown as Record<string, unknown>)[key] ||
          key === "random_seed")
    )
      patch[key] = settings[key];
  for (const key of ["tempo", "articulation", "drift_decay_factor"])
    if (typeof settings[key] === "number")
      patch[key] = (settings[key] as number) *
        (key === "tempo" && (settings.tempo_unit === "percent" ||
          (settings.tempo_unit == null && "humanization_seed" in settings &&
            !("random_seed" in settings) && !("humanization_on" in settings))) ? 1 : 100);
  patch.pedal_ai_mode = ["auto", "custom"].includes(String(settings.pedal_ai_mode))
    ? settings.pedal_ai_mode
    : ((Array.isArray(settings.pedal_curve_on) && settings.pedal_curve_on.length > 0) || (Array.isArray(settings.pedal_curve_off) && settings.pedal_curve_off.length > 0)) ? "custom" : "auto";
  const mode = settings.humanization_mode;
  patch.humanization_mode = ["disabled", "global", "individual"].includes(
    String(mode),
  )
    ? mode
    : settings.humanization_on === false
      ? "disabled"
      : "individual";
  patch.humanization_on = patch.humanization_mode !== "disabled";
  patch.humanization_seed_mode =
    settings.humanization_seed_mode ??
    (settings.random_seed != null || settings.humanization_seed != null
      ? "fixed_custom"
      : "dynamic");
  patch.random_seed =
    settings.random_seed ?? settings.humanization_seed ?? null;
  return { ...DEFAULT_CONFIG, ...patch } as PlaybackConfig;
}
export function songSettings(config: PlaybackConfig): Record<string, unknown> {
  return {
    ...config,
    tempo: config.tempo / 100,
    tempo_unit: "ratio",
    articulation: config.articulation / 100,
    drift_decay_factor: config.drift_decay_factor / 100,
    midi_file: "",
  };
}
export function makeMidiSong(
  path: string,
  config: PlaybackConfig,
  tracks: SelectedTrackInfo[],
): PlaylistSong {
  return {
    song_version: 3,
    source: {
      type: "midi",
      original_path: path,
      original_filename: path.split(/[\\/]/).pop() || "MIDI.mid",
    },
    playback_settings: songSettings(config),
    selected_tracks: tracks.map(([index, role]) => ({ index, role })),
  };
}
export function makeSheetSong(
  text: string,
  bpm: number,
  config: PlaybackConfig,
): PlaylistSong {
  return {
    song_version: 3,
    source: {
      type: "sheet",
      sheet_text: text,
      bpm,
      format_name: "Virtual Piano",
      humanize: config.humanization_on,
    },
    playback_settings: songSettings(config),
    selected_tracks: [],
  };
}
export type PlaylistMode =
  "single" | "repeat_one" | "sequential" | "repeat_all" | "shuffle";
export function nextSongId(
  items: Pick<PlaylistItem, "id">[],
  current: string | null,
  mode: PlaylistMode,
  direction = 1,
  random = Math.random,
): string | null {
  if (!items.length) return null;
  const i = items.findIndex((x) => x.id === current);
  if (i < 0) return items[0].id;
  if (mode === "single") return null;
  if (mode === "repeat_one") return current;
  if (mode === "shuffle") {
    const pool = items.filter((x) => x.id !== current);
    return pool.length
      ? pool[Math.min(pool.length - 1, Math.floor(random() * pool.length))].id
      : current;
  }
  const next = i + direction;
  return mode === "repeat_all"
    ? items[(next + items.length) % items.length].id
    : (items[next]?.id ?? null);
}
