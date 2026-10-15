import { translateNode } from "../lib/i18n";
import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { open, save, ask } from "../lib/appDialogs";
import {
  TrackSelectionDialog,
  type TrackRow,
  type HandRole,
} from "../dialogs/TrackSelectionDialog";
import { usePlaybackEngine } from "./PlaybackEngineContext";
import { usePlaybackConfig } from "./PlaybackConfigContext";
import { useLog } from "./LogContext";
import { isTauri, onEvent, type SelectedTrackInfo } from "../lib/tauri";
import {
  listPlaylist,
  getPlaylistSong,
  putPlaylistSong,
  deletePlaylistSongs,
  reorderPlaylist,
  patchPlaylistSongs,
  importPlaylistLibrary,
  importPlaylist,
  exportPlaylist,
  savePlaylistMidi,
  cachePlaylistSong,
  preparePlaylistCache,
  playlistCompilationKey,
  songConfig,
  songSettings,
  makeMidiSong,
  makeSheetSong,
  type PlaylistDetail,
  nextSongId,
  type PlaylistItem,
  type PlaylistMode,
  type ImportReport,
} from "../lib/playlist";
import { parseMidiWithRepair } from "../lib/midiRepair";
import {
  validSeed,
  extractHumanization,
  resolvePlaybackConfig,
  newRandomSeed,
  usesDynamicRandomness,
} from "../pages/playback/humanization";
import { usePersistedState } from "./usePersistedState";
import { parseOneOf } from "./persistedParsers";
import { type PlaybackConfig } from "../pages/playback/types";
import { Modal } from "../components/Modal";
import { Button } from "../components/Button";
import { t } from "../lib/i18n";

interface PlaylistValue {
  items: PlaylistItem[];
  selected: string[];
  setSelected: (ids: string[]) => void;
  currentId: string | null;
  editingId: string | null;
  loadedId: string | null;
  pendingCount: number;
  settingsDirty: boolean;
  busy: boolean;
  progress: string;
  backgroundProgress: string;
  error: string | null;
  dismissError: () => void;
  mode: PlaylistMode;
  setMode: (mode: PlaylistMode) => void;
  active: boolean;
  refresh: () => Promise<void>;
  play: (id?: string) => Promise<void>;
  preview: () => Promise<void>;
  stop: () => Promise<void>;
  next: (direction?: number) => Promise<void>;
  addCurrent: (name?: string) => Promise<boolean>;
  addSheet: (
    name: string,
    text: string,
    bpm: number,
    humanize: boolean,
  ) => Promise<void>;
  batchImport: (manual?: boolean) => Promise<void>;
  importPackage: () => Promise<void>;
  importOldLibrary: () => Promise<void>;
  exportPackage: (complete: boolean) => Promise<void>;
  remove: (ids: string[]) => Promise<void>;
  reorder: (ids: string[]) => Promise<void>;
  edit: (id: string) => Promise<void>;
  cancelEdit: () => void;
  rename: (id: string, name: string) => Promise<void>;
  batchPatch: (patch: Partial<PlaybackConfig>) => Promise<void>;
  saveMidi: (ids: string[]) => Promise<void>;
  report: ImportReport | null;
  clearReport: () => void;
}
const Context = createContext<PlaylistValue | null>(null);
export function PlaylistProvider({ children }: { children: ReactNode }) {
  const engine = usePlaybackEngine();
  const { config, defaultConfig, beginEdit, endEdit } = usePlaybackConfig();
  const { appendLog } = useLog();
  const [items, setItems] = useState<PlaylistItem[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [loadedId, setLoadedId] = useState<string | null>(null);
  const loadedDetail = useRef<PlaylistDetail | null>(null);
  const [pending, setPending] = useState<PlaylistDetail[]>([]);
  const [baseline, setBaseline] = useState<PlaybackConfig | null>(null);
  const [importChoiceCount, setImportChoiceCount] = useState(0);
  const importAnswer = useRef<((choice: boolean | null) => void) | null>(null);
  function finishImportChoice(choice: boolean | null) {
    importAnswer.current?.(choice);
    importAnswer.current = null;
    setImportChoiceCount(0);
  }
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState("");
  const [backgroundProgress, setBackgroundProgress] = useState("");
  const cacheQueue = useRef(false);
  const cacheTasks = useRef(new Map<string, () => Promise<void>>());
  const cacheJobs = useRef(new Map<string, Promise<void>>());
  const cacheAttempts = useRef(new Set<string>());
  const alive = useRef(true);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  async function runCacheQueue() {
    if (cacheQueue.current) return;
    cacheQueue.current = true;
    try {
      while (cacheTasks.current.size) {
        const [id, task] = cacheTasks.current.entries().next().value!;
        cacheTasks.current.delete(id);
        await task();
      }
    } finally {
      cacheQueue.current = false;
      if (alive.current) setBackgroundProgress("");
    }
  }
  function queueCache(id: string, settings: PlaybackConfig, name: string, force = false) {
    if (usesDynamicRandomness(settings)) return;
    const key = id + ":" + playlistCompilationKey(settings);
    if (cacheJobs.current.has(id)) {
      if (force) void cacheJobs.current.get(id)!.then(() => queueCache(id, settings, name, true));
      return;
    }
    if (!force && cacheAttempts.current.has(key)) return;
    cacheAttempts.current.add(key);
    let finish!: () => void;
    const job = new Promise<void>((resolve) => { finish = resolve; });
    cacheJobs.current.set(id, job);
    cacheTasks.current.set(id, async () => {
      try {
        if (!alive.current) return;
        setBackgroundProgress(`${t("正在后台准备")}：${name}`);
        await preparePlaylistCache(id, settings);
      } catch (e) { appendLog(`后台缓存：${name} · ${String(e)}`); }
      finally {
        cacheJobs.current.delete(id);
        try {
          if (alive.current) await refresh();
        } finally { finish(); }
      }
    });
    void runCacheQueue();
  }
  useEffect(() => {
    if (!isTauri()) return;
    for (const item of items.filter((i) => (!i.cache_available || i.cache_rebuild_required) && (i.midi_available || i.sheet_available))) {
      void getPlaylistSong(item.id).then((detail) => queueCache(item.id, songConfig(detail.song.playback_settings), item.name)).catch((e) => appendLog(`后台读取：${String(e)}`));
    }
  }, [items]);
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState(false);
  const activeRef = useRef(false);
  const ticketRef = useRef(0);
  const busyRef = useRef(false);
  const [manualTracks, setManualTracks] = useState<TrackRow[] | null>(null);
  const trackAnswer = useRef<
    ((selection: SelectedTrackInfo[] | null) => void) | null
  >(null);
  function chooseTracks(rows: TrackRow[]): Promise<SelectedTrackInfo[] | null> {
    setManualTracks(rows);
    return new Promise((resolve) => {
      trackAnswer.current = resolve;
    });
  }
  function finishTracks(selection: { index: number; role: HandRole }[] | null) {
    trackAnswer.current?.(selection?.map((t) => [t.index, t.role]) ?? null);
    trackAnswer.current = null;
    setManualTracks(null);
  }
  const [report, setReport] = useState<ImportReport | null>(null);
  const [mode, setMode] = usePersistedState<PlaylistMode>(
    "xk_playlist_mode",
    "sequential",
    {
      parse: parseOneOf([
        "single",
        "repeat_one",
        "sequential",
        "repeat_all",
        "shuffle",
      ] as const),
    },
  );
  const pendingNatural = useRef(false);
  const currentRef = useRef(currentId);
  currentRef.current = currentId;
  const actionRef = useRef<() => void>(() => {});
  actionRef.current = () => {
    if (!activeRef.current) return;
    if (busyRef.current) {
      pendingNatural.current = true;
      return;
    }
    const nextId = nextSongId(items, currentRef.current, mode);
    if (nextId) void play(nextId);
    else {
      activeRef.current = false;
      setActive(false);
    }
  };
  useEffect(() => {
    if (!isTauri()) return;
    void refresh();
    const listening = onEvent("natural_finished", () => actionRef.current());
    return () => {
      void listening.then((fn) => fn());
    };
  }, []);
  useEffect(() => {
    const replace = () => {
      ticketRef.current++;
      activeRef.current = false;
      pendingNatural.current = false;
      setActive(false);
      setEditingId(null);
      setLoadedId(null);
      loadedDetail.current = null;
      setPending([]);
      setBaseline(null);
      endEdit();
    };
    window.addEventListener("xingkong-source-replaced", replace);
    return () =>
      window.removeEventListener("xingkong-source-replaced", replace);
  }, []);
  function fail(e: unknown) {
    setError(String(e));
    appendLog(`歌单：${String(e)}`);
  }
  async function refresh() {
    if (!isTauri()) return;
    try {
      const next = await listPlaylist();
      setItems(next);
      setSelected((ids) => ids.filter((id) => next.some((i) => i.id === id)));
    } catch (e) {
      fail(e);
    }
  }
  async function withBusy(work: () => Promise<void>) {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setError(null);
    try {
      await work();
      return true;
    } catch (e) {
      fail(e);
      return false;
    } finally {
      busyRef.current = false;
      setBusy(false);
      setProgress("");
      if (pendingNatural.current) {
        pendingNatural.current = false;
        queueMicrotask(() => actionRef.current());
      }
    }
  }
  async function play(requested?: string) {
    const id = requested ?? selected[0] ?? currentId ?? items[0]?.id;
    if (!id) return;
    if (pending.length || (loadedId && baseline && JSON.stringify(songSettings(config)) !== JSON.stringify(songSettings(baseline)))) {
      fail("请先保存或放弃当前导入／修改，再播放歌单曲目"); return;
    }
    const success = await withBusy(async () => {
      const ticket = ++ticketRef.current;
      activeRef.current = false; setActive(false);
      setProgress("正在准备歌曲…");
      const queued = cacheJobs.current.get(id);
      if (queued) {
        const task = cacheTasks.current.get(id);
        if (task) {
          cacheTasks.current.delete(id);
          cacheTasks.current = new Map([[id, task], ...cacheTasks.current.entries()]);
        }
        setProgress("正在完成此曲目的后台缓存…"); await queued;
      }
      if (ticket !== ticketRef.current) return;
      const detail = await getPlaylistSong(id);
      let settings = { ...songConfig(detail.song.playback_settings) };
      if (settings.humanization_seed_mode === "fixed_random" && !validSeed(settings.random_seed)) settings = { ...settings, random_seed: newRandomSeed() };
      const basis = JSON.stringify(extractHumanization(resolvePlaybackConfig(settings)));
      if (settings.humanization_mode === "global" && settings.humanization_seed_mode === "fixed_random" && detail.song.playback_settings.xk_humanization_basis !== basis) settings = { ...settings, random_seed: newRandomSeed() };
      endEdit(); setLoadedId(null); loadedDetail.current = null; setEditingId(null); setBaseline(null);
      const used = await engine.preparePlaylistSong(detail, settings, true, true, false, setProgress);
      if (ticket !== ticketRef.current) return;
      const cacheHit = engine.preparedCacheHit();
      if (!cacheHit && (detail.midi_path || detail.song.source.type === "sheet")) {
        const song = { ...detail.song, playback_settings: { ...songSettings(used), xk_humanization_basis: basis } };
        await putPlaylistSong(detail.metadata.name, song, null, engine.clock.duration(), id);
        if (!usesDynamicRandomness(used)) await cachePlaylistSong(id, used).catch((e) => appendLog(`缓存未保存：${String(e)}`));
      }
      if (ticket !== ticketRef.current) return;
      currentRef.current = id; setCurrentId(id); setSelected([id]);
      activeRef.current = true; setActive(true); setProgress("");
      await engine.startPrepared(used, true);
      if (!cacheHit) await refresh();
    });
    if (!success) { activeRef.current = false; setActive(false); }
  }
  async function stop() {
    pendingNatural.current = false;
    ticketRef.current++;
    activeRef.current = false;
    setActive(false);
    await engine.stop();
  }
  async function next(direction = 1) {
    const id = nextSongId(
      items,
      currentId ?? selected[0] ?? null,
      mode === "shuffle" ? "shuffle" : "repeat_all",
      direction,
    );
    if (id) await play(id);
  }
  async function addCurrent(name?: string): Promise<boolean> {
    const success = await withBusy(async () => {
      await stop();
      if (
        (!engine.midiFilePath && !engine.sheetSource) ||
        (engine.midiFilePath && !engine.selectedTracksInfo.length)
      )
        throw new Error("请先加载 MIDI 或文本曲谱");
      const existing = loadedDetail.current;
      const drafts = existing ? [existing] : pending.length ? pending : [null];
      const saved: string[] = [];
      try {
        for (const [index, draft] of drafts.entries()) {
          const used = {
            ...config,
            midi_clip_invalid_data:
              draft && drafts.length > 1
                ? Boolean(draft.song.playback_settings.midi_clip_invalid_data)
                : config.midi_clip_invalid_data,
          };
          if (
            drafts.length > 1 &&
            used.humanization_seed_mode === "fixed_random"
          )
            used.random_seed = newRandomSeed();
          const sourceSong =
            draft?.song ??
            (engine.sheetSource
              ? makeSheetSong(
                  engine.sheetSource.text,
                  engine.sheetSource.bpm,
                  used,
                )
              : makeMidiSong(
                  engine.midiFilePath,
                  used,
                  engine.selectedTracksInfo,
                ));
          const song = {
            ...sourceSong,
            playback_settings: { ...songSettings(used), xk_humanization_basis: JSON.stringify(extractHumanization(resolvePlaybackConfig(used))) },
            selected_tracks:
              index === 0
                ? engine.selectedTracksInfo.map(([index, role]) => ({
                    index,
                    role,
                  }))
                : sourceSong.selected_tracks,
          };
          const result = await putPlaylistSong(
            existing?.metadata.name ??
              (drafts.length === 1 && name
                ? name
                : (draft?.metadata.name ??
                  engine.fileName.replace(/\.midi?$/i, ""))),
            song,
            existing
              ? null
              : (draft?.midi_path ?? (engine.midiFilePath || null)),
            existing?.metadata.duration ??
              (drafts.length === 1 ? engine.totalDuration : 0),
            existing?.metadata.id ?? null,
          );
          saved.push(result.id);
          queueCache(result.id, used, result.name, true);

        }
      } catch (error) {
        if (!existing && saved.length) {
          const remaining = drafts
            .slice(saved.length)
            .filter((d): d is PlaylistDetail => d !== null);
          setPending(remaining);
          setLoadedId(null);
          loadedDetail.current = null;
          if (remaining.length)
            await engine.preparePlaylistSong(
              remaining[0],
              {
                ...config,
                midi_clip_invalid_data: Boolean(
                  remaining[0].song.playback_settings.midi_clip_invalid_data,
                ),
              },
              false,
              false,
            );
          setSelected(saved);
          await refresh();
        }
        throw error;
      }
      setLoadedId(null); loadedDetail.current = null;
      setEditingId(null); setPending([]); setBaseline(null);
      await engine.clearSong(); endEdit();
      setSelected(saved);
      await refresh();
    });
    return success === true;
  }
  async function addSheet(
    name: string,
    text: string,
    bpm: number,
    humanize: boolean,
  ) {
    await withBusy(async () => {
      const used = {
        ...config,
        humanization_on: humanize,
        humanization_mode: humanize
          ? ("individual" as const)
          : ("disabled" as const),
      };
      const result = await putPlaylistSong(
        name,
        makeSheetSong(text, bpm, used),
        null,
        0,
      );
      queueCache(result.id, used, name, true);
      setSelected([result.id]);
      await refresh();
    });
  }
  async function batchImport(manual = false) {
    await withBusy(async () => {
      const files = await open({
        multiple: true,
        filters: [{ name: "MIDI", extensions: ["mid", "midi"] }],
      });
      if (!files) return;
      const paths = Array.isArray(files) ? files : [files];
      if (paths.length > 1 && !manual) {
        const choice = await new Promise<boolean | null>((resolve) => {
          importAnswer.current = resolve;
          setImportChoiceCount(paths.length);
        });
        if (choice === null) return;
        manual = choice;
      }
      await stop();
      const errors: string[] = [];
      const drafts: PlaylistDetail[] = [];
      for (let i = 0; i < paths.length; i++) {
        const path = paths[i];
        setProgress(
          `导入 ${i + 1}/${paths.length} · ${path.split(/[\\/]/).pop()}`,
        );
        try {
          const result = await parseMidiWithRepair(path, false);
          let tracks: SelectedTrackInfo[] = result.parsed.tracks
            .filter((t) => !t.is_drum && t.note_count > 0)
            .map((t) => [t.index, "Auto-Detect"]);
          if (manual || paths.length === 1 || !tracks.length) {
            const chosen = await chooseTracks(
              result.parsed.tracks
                .filter((t) => t.note_count > 0)
                .map((t) => ({
                  index: t.index,
                  name: t.name,
                  instrument: t.instrument_name,
                  noteCount: t.note_count,
                  channel: t.is_drum ? 9 : 0,
                })),
            );
            if (chosen === null) throw new Error("已跳过此首 MIDI");
            tracks = chosen;
          }
          if (!tracks.length) throw new Error("没有选择可演奏音轨");
          let settings = {
            ...defaultConfig,
            pedal_curve_on: [], pedal_curve_off: [],
            midi_clip_invalid_data: result.clip,
          };
          if (settings.humanization_seed_mode === "fixed_random")
            settings = { ...settings, random_seed: newRandomSeed() };
          const name =
            path
              .split(/[\\/]/)
              .pop()
              ?.replace(/\.midi?$/i, "") || "MIDI";
          drafts.push({
            metadata: {
              id: "",
              name,
              source_type: "midi",
              source_label: path.split(/[\\/]/).pop() ?? name,
              duration: 0,
              midi_available: true,
              sheet_available: false,
              cache_available: false,
              humanization_mode: settings.humanization_mode,
              random_seed_mode: settings.humanization_seed_mode,
            },
            song: makeMidiSong(path, settings, tracks),
            midi_path: path,
            cache_path: "",
          });
        } catch (e) {
          errors.push(`${path.split(/[\\/]/).pop()}：${String(e)}`);
        }
      }
      if (drafts.length) {
        beginEdit(songConfig(drafts[0].song.playback_settings), "import");
        const used = await engine.preparePlaylistSong(
          drafts[0],
          songConfig(drafts[0].song.playback_settings),
          false,
          false,
        );
        loadedDetail.current = null;
        setLoadedId(null);
        setEditingId(null);
        setPending(drafts);
        setBaseline(used);
      }
      if (errors.length) setError(errors.join("\n"));
    });
  }
  async function importPackage() {
    await withBusy(async () => {
      const path = await open({
        directory: false,
        multiple: false,
        title: "导入新旧版歌单文件",
        filters: [{ name: "HuMidi 歌单 / 旧版索引", extensions: ["humidiplaylist", "json", "zip"] }],
      });
      if (typeof path !== "string") return;
      setProgress("正在导入歌单…");
      setReport(await importPlaylist(path));
      await refresh();
    });
  }
  async function importOldLibrary() {
    await withBusy(async () => {
      const path = await open({
        directory: true,
        multiple: false,
        title: "选择旧版数据目录或 playlist 文件夹",
      });
      if (typeof path !== "string") return;
      setProgress("正在复制旧版歌库…");
      setReport(await importPlaylistLibrary(path));
      await refresh();
    });
  }
  async function exportPackage(complete: boolean) {
    await withBusy(async () => {
      const path = await save({
        defaultPath: complete
          ? "星空歌单-完整.humidiplaylist"
          : "星空歌单.humidiplaylist",
        filters: [{ name: "HuMidi 歌单", extensions: ["humidiplaylist"] }],
      });
      if (!path) return;
      setProgress("正在导出歌单…");
      const n = await exportPlaylist(path, complete);
      setReport({ imported: n, errors: [] });
    });
  }
  async function remove(ids: string[]) {
    if (!ids.length) return;
    const yes = await ask(`从歌单删除 ${ids.length} 首歌曲？`, {
      title: "删除歌曲",
      kind: "warning",
      okLabel: "删除",
      cancelLabel: "取消",
    });
    if (!yes) return;
    await withBusy(async () => {
      if (currentId && ids.includes(currentId)) await stop();
      await deletePlaylistSongs(ids);
      if (editingId && ids.includes(editingId)) setEditingId(null);
      await refresh();
    });
  }
  async function reorder(ids: string[]) {
    await withBusy(async () => {
      await reorderPlaylist(ids);
      await refresh();
    });
  }
  async function edit(id: string) {
    await withBusy(async () => {
      await stop();
      const detail = await getPlaylistSong(id);
      if (!detail.midi_path && detail.song.source.type !== "sheet")
        throw new Error("此旧歌曲仅有缓存，无法修改原始音轨");
      beginEdit(songConfig(detail.song.playback_settings), "song");
      await engine.preparePlaylistSong(
        detail,
        songConfig(detail.song.playback_settings),
        true,
        false,
      );
      setEditingId(id);
      setLoadedId(id);
      loadedDetail.current = detail;
      setPending([]);
      setBaseline(songConfig(detail.song.playback_settings));
      setSelected([id]);
    });
  }
  async function rename(id: string, name: string) {
    await withBusy(async () => {
      const detail = await getPlaylistSong(id);
      await putPlaylistSong(
        name,
        detail.song,
        null,
        detail.metadata.duration,
        id,
      );
      await refresh();
    });
  }
  async function batchPatch(patch: Partial<PlaybackConfig>) {
    await withBusy(async () => {
      const keys = Object.keys(patch);
      if (!keys.length) return;
      const converted: Record<string, unknown> = { ...patch };
      if (patch.humanization_mode !== undefined)
        converted.humanization_on = patch.humanization_mode !== "disabled";
      for (const key of [
        "tempo",
        "articulation",
        "drift_decay_factor",
      ] as const)
        if (typeof patch[key] === "number") converted[key] = patch[key]! / 100;
      await patchPlaylistSongs(selected, converted);
      for (const id of selected) {
        const detail = await getPlaylistSong(id);
        queueCache(id, songConfig(detail.song.playback_settings), detail.metadata.name, true);
      }
      await refresh();
    });
  }
  async function saveMidi(ids: string[]) {
    await withBusy(async () => {
      const folder = await open({ directory: true, multiple: false });
      if (typeof folder !== "string") return;
      const errors: string[] = [];
      let imported = 0;
      for (const id of ids) {
        const detail = await getPlaylistSong(id);
        if (!detail.midi_path) continue;
        const filename =
          detail.song.source.original_filename?.replace(
            /[<>:"/\\|?*\x00-\x1f]/g,
            "_",
          ) || `${id}.mid`;
        try {
          await savePlaylistMidi(id, `${folder}/${id.slice(0, 8)}-${filename}`);
          imported++;
        } catch (e) {
          errors.push(String(e));
        }
      }
      setReport({ imported, errors });
    });
  }
  const value: PlaylistValue = {
    items,
    selected,
    setSelected,
    currentId,
    editingId,
    loadedId,
    pendingCount: pending.length,
    settingsDirty:
      baseline !== null &&
      JSON.stringify(songSettings(config)) !==
        JSON.stringify(songSettings(baseline)),
    busy,
    progress,
    backgroundProgress,
    error,
    dismissError: () => setError(null),
    mode,
    setMode,
    active,
    refresh,
    play,
    preview: async () => {
      activeRef.current = false;
      pendingNatural.current = false;
      setActive(false);
      await engine.play();
    },
    stop,
    next,
    addCurrent,
    addSheet,
    batchImport,
    importPackage,
    importOldLibrary,
    exportPackage,
    remove,
    reorder,
    edit,
    cancelEdit: () => {
      setEditingId(null); setLoadedId(null); loadedDetail.current = null;
      setPending([]); setBaseline(null);
      void engine.clearSong().finally(endEdit);
    },
    rename,
    batchPatch,
    saveMidi,
    report,
    clearReport: () => setReport(null),
  };
  return (
    <Context.Provider value={value}>
      {translateNode(children)}
      {importChoiceCount > 0 && (
        <Modal
          title={t("多首 MIDI 的音轨选择")}
          width={500}
          height={255}
          onClose={() => finishImportChoice(null)}
          footer={
            <Button onClick={() => finishImportChoice(null)}>
              {t("取消")}
            </Button>
          }
        >
          <p>
            {t(
              `已选择 ${importChoiceCount} 首 MIDI。导入后统一调整设置，再加入歌单。`,
            )}
          </p>
          <div className="import-choices">
            <Button variant="accent" onClick={() => finishImportChoice(false)}>
              {t("自动选择音轨")}
            </Button>
            <Button onClick={() => finishImportChoice(true)}>
              {t("逐首选择音轨")}
            </Button>
          </div>
          <p className="playlist-muted">
            {t("自动选择无法找到非鼓音轨时，会请你手动选择。")}
          </p>
        </Modal>
      )}
      {manualTracks && (
        <TrackSelectionDialog
          tracks={manualTracks}
          title={progress}
          onCancel={() => finishTracks(null)}
          onConfirm={finishTracks}
        />
      )}
    </Context.Provider>
  );
}
export function usePlaylist() {
  const value = useContext(Context);
  if (!value) throw new Error("PlaylistProvider missing");
  return value;
}
