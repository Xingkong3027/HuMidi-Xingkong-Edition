import { translateNode } from "../lib/i18n";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { open as openDialog, message as showMessage } from "../lib/appDialogs";
import { parseMidiWithRepair } from "../lib/midiRepair";
import {
  restorePlaylistCache,
  playlistCompilationKey,
  songConfig,
  type PlaylistDetail,
} from "../lib/playlist";
import {
  resolvePlaybackConfig,
  usesDynamicRandomness,
} from "../pages/playback/humanization";
import { usePlaybackConfig } from "./PlaybackConfigContext";
import { useLog } from "./LogContext";
import {
  isTauri,
  onEvent,
  compileNotes as invokeCompileNotes,
  compileNotesFromSheet as invokeCompileNotesFromSheet,
  compilePedal as invokeCompilePedal,
  startPlayback as invokeStartPlayback,
  togglePause as invokeTogglePause,
  stopPlayback as invokeStopPlayback,
  seekPlayback as invokeSeekPlayback,
  clearLoadedSong as invokeClearLoadedSong,
  savePlayback as invokeSavePlayback,
  resumeFromSave as invokeResumeFromSave,
  getSaveDir,
  getMidiDir,
  blockedInputMessage,
  type TrackSummary,
  type SelectedTrackInfo,
  type PedalData,
  type BackendNote,
  type TempoEvent,
  type TimeSignatureEvent,
  type MeasureBoundary,
} from "../lib/tauri";
import { defaultSaveName } from "../lib/saveName";
import {
  activePitchesAt,
  buildNoteTimeline,
  pedalActiveAt,
} from "../lib/noteTimeline";
import type { HandRole } from "../dialogs/TrackSelectionDialog";
import type { TrackPart } from "../pages/playback/LoadedParts";
import type { PedalAiStats } from "../pages/playback/PedalAiCard";
import { PlaybackClock } from "./playbackClock";
import { LiveKeys } from "./liveKeys";
import {
  PREVIEW_CONFIDENCE,
  PREVIEW_CURVES,
  PREVIEW_SONG,
} from "./previewSong";
import type { PedalConfidence } from "../lib/pedalPreview";
import { hasCurves, type ThresholdCurves } from "../lib/thresholdCurve";
import { DEFAULT_CONFIG, type PlaybackConfig } from "../pages/playback/types";
import {
  NOTES_CONFIG_KEYS,
  PEDAL_CONFIG_KEYS,
  configDiffers,
  pickConfig,
} from "../pages/playback/compileConfig";

interface PlaybackEngineValue {
  fileName: string;
  selectedTracksInfo: SelectedTrackInfo[];
  sheetSource: { text: string; bpm: number } | null;
  countdownRemaining: number;
  isPreparing: boolean;
  autoTrackSelection: boolean;
  preparePlaylistSong: (
    detail: PlaylistDetail,
    settings: PlaybackConfig,
    useCache?: boolean,
    compile?: boolean,
    editSettings?: boolean,
    onPhase?: (phase: string) => void,
  ) => Promise<PlaybackConfig>;
  preparedCacheHit: () => boolean;
  startPrepared: (settings?: PlaybackConfig) => Promise<void>;
  midiFilePath: string;
  tracks: TrackSummary[];
  parts: TrackPart[];
  originalBpm: number;
  totalDuration: number;
  finalNotes: BackendNote[];
  playedNotes: BackendNote[];
  visualizerUse88: boolean;
  tempoEvents: TempoEvent[];
  timeSignatures: TimeSignatureEvent[];
  measureBoundaries: MeasureBoundary[];
  hasCompiledNotes: boolean;
  hasCompiledPedal: boolean;
  isGeneratingPedal: boolean;
  pedalIntervals: [number, number][];
  aiCurves: ThresholdCurves | null;
  pedalConfidence: PedalConfidence | null;
  configDirty: boolean;
  defaultAiCurves: ThresholdCurves | null;
  aiStats: PedalAiStats | null;
  isPlaying: boolean;
  isPaused: boolean;
  clock: PlaybackClock;
  liveKeys: LiveKeys;
  saveDirConfigured: boolean;

  openFileBrowser: () => Promise<void>;
  loadFile: (path: string, name: string) => Promise<void>;
  applyConfigChanges: () => Promise<void>;
  discardConfigChanges: () => void;
  confirmTrackSelection: (
    selection: { index: number; role: HandRole }[],
  ) => Promise<void>;
  generatePedal: () => Promise<void>;
  play: () => Promise<void>;
  togglePause: () => Promise<void>;
  stop: () => Promise<void>;
  seek: (time: number) => Promise<void>;
  isSaving: boolean;
  saveCount: number;
  save: (name?: string) => Promise<SaveResult>;
  resumeSave: (filepath: string, label: string) => Promise<void>;
  playTranslatedSheet: (
    sheetText: string,
    bpm: number,
    humanize?: boolean,
  ) => Promise<void>;
  clearSong: () => Promise<void>;
  blockedInput: string | null;
  dismissBlockedInput: () => void;
  legacyThresholdNotice: boolean;
  dismissLegacyThresholdNotice: () => void;
}

export type SaveResult = { path: string } | { error: string };

const NO_AI_CURVES = {
  pedal_curve_on: DEFAULT_CONFIG.pedal_curve_on,
  pedal_curve_off: DEFAULT_CONFIG.pedal_curve_off,
};

const PlaybackEngineContext = createContext<PlaybackEngineValue | null>(null);

function formatSnapshotDuration(totalDur: number): string {
  const minutes = Math.floor(totalDur / 60);
  const seconds = Math.floor(totalDur % 60);
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

function statsFromIntervals(
  intervals: [number, number][],
  totalDuration: number,
): PedalAiStats | null {
  if (intervals.length === 0) return null;
  const durations = intervals.map(([s, e]) => e - s);
  const avgDur = durations.reduce((a, b) => a + b, 0) / durations.length;
  return {
    avgDur,
    minDur: Math.min(...durations),
    maxDur: Math.max(...durations),
    pressesPerMin:
      totalDuration > 0 ? (intervals.length / totalDuration) * 60 : 0,
  };
}

export function PlaybackEngineProvider({ children }: { children: ReactNode }) {
  const { config, updateConfig, setConfig } = usePlaybackConfig();
  const { appendLog, updateSnapshot, clearSnapshot } = useLog();

  const [sheetSource, setSheetSource] = useState<{
    text: string;
    bpm: number;
  } | null>(null);
  const sheetSourceRef = useRef(sheetSource);
  sheetSourceRef.current = sheetSource;
  const [countdownRemaining, setCountdownRemaining] = useState(0);
  const [isPreparing, setIsPreparing] = useState(false);
  const [autoTrackSelection, setAutoTrackSelection] = useState(true);
  const sourceIsEditableRef = useRef(false);
  const restoredCacheRef = useRef(false);
  const preparedIdentityRef = useRef<string | null>(null);
  const compileConfigUsedRef = useRef<PlaybackConfig | null>(null);
  const preparedConfigRef = useRef<PlaybackConfig | null>(null);
  const [fileName, setFileName] = useState("");
  const [midiFilePath, setMidiFilePath] = useState("");
  const preparedMidiPathRef = useRef("");
  const [tracks, setTracks] = useState<TrackSummary[]>([]);
  const [parts, setParts] = useState<TrackPart[]>([]);
  const [selectedTracksInfo, setSelectedTracksInfo] = useState<
    SelectedTrackInfo[]
  >([]);
  const [originalBpm, setOriginalBpm] = useState(0);
  const [totalDuration, setTotalDuration] = useState(0);
  const [finalNotes, setFinalNotes] = useState<BackendNote[]>([]);
  const [playedNotes, setPlayedNotes] = useState<BackendNote[]>([]);
  const [tempoEvents, setTempoEvents] = useState<TempoEvent[]>([]);
  const [timeSignatures, setTimeSignatures] = useState<TimeSignatureEvent[]>(
    [],
  );
  const [measureBoundaries, setMeasureBoundaries] = useState<MeasureBoundary[]>(
    [],
  );
  const [hasCompiledNotes, setHasCompiledNotes] = useState(false);
  const [hasCompiledPedal, setHasCompiledPedal] = useState(false);
  const [isGeneratingPedal, setIsGeneratingPedal] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [blockedInput, setBlockedInput] = useState<string | null>(null);
  const [legacyThresholdNotice, setLegacyThresholdNotice] = useState(false);
  const [saveCount, setSaveCount] = useState(0);
  const [pedalIntervals, setPedalIntervals] = useState<[number, number][]>([]);
  const [aiCurves, setAiCurves] = useState<ThresholdCurves | null>(null);
  const [pedalConfidence, setPedalConfidence] =
    useState<PedalConfidence | null>(null);
  const [compiledNotesConfig, setCompiledNotesConfig] =
    useState<Partial<PlaybackConfig> | null>(null);
  const [compiledPedalConfig, setCompiledPedalConfig] =
    useState<Partial<PlaybackConfig> | null>(null);
  const [defaultAiCurves, setDefaultAiCurves] =
    useState<ThresholdCurves | null>(null);
  const defaultAiCurvesRef = useRef(defaultAiCurves);
  defaultAiCurvesRef.current = defaultAiCurves;
  const [isPlaying, setIsPlaying] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [clock] = useState(() => new PlaybackClock({ selfTimed: !isTauri() }));
  const [liveKeys] = useState(() => new LiveKeys());
  const [saveDirConfigured, setSaveDirConfigured] = useState(false);
  const running = isPlaying && !isPaused;

  const configRef = useRef(config);
  configRef.current = config;
  const updateConfigRef = useRef(updateConfig);
  updateConfigRef.current = updateConfig;
  const isPlayingRef = useRef(isPlaying);
  isPlayingRef.current = isPlaying;
  const isGeneratingPedalRef = useRef(false);
  const atEndRef = useRef(false);
  const isSavingRef = useRef(false);
  const songVersionRef = useRef(0);
  const playRef = useRef(play);
  playRef.current = play;
  const stopRef = useRef(stop);
  stopRef.current = stop;
  const togglePauseRef = useRef(togglePause);
  togglePauseRef.current = togglePause;
  const saveRef = useRef(save);
  saveRef.current = save;

  useEffect(() => {
    const invalidate = () => { preparedIdentityRef.current = null; };
    window.addEventListener("xingkong-source-replaced", invalidate);
    return () => window.removeEventListener("xingkong-source-replaced", invalidate);
  }, []);

  useEffect(() => {
    if (!isTauri()) return;
    getSaveDir()
      .then((dir) => setSaveDirConfigured(!!dir))
      .catch(() => {});
  }, []);

  useEffect(() => {
    clock.setRunning(running);
  }, [clock, running]);

  useEffect(() => {
    clock.setDuration(totalDuration);
  }, [clock, totalDuration]);

  const previewTimeline = useMemo(
    () => buildNoteTimeline(playedNotes),
    [playedNotes],
  );

  useEffect(() => {
    if (isTauri()) return;
    if (!running) {
      liveKeys.clear();
      return;
    }
    const simulateKeys = () => {
      const time = clock.time();
      liveKeys.setPitches(activePitchesAt(previewTimeline, time));
      liveKeys.setPedal(pedalActiveAt(pedalIntervals, time));
    };
    simulateKeys();
    return clock.subscribe(simulateKeys);
  }, [clock, liveKeys, running, previewTimeline, pedalIntervals]);

  useEffect(() => {
    if (!isTauri()) return;
    const unlisten: Promise<() => void>[] = [
      onEvent("status_updated", (msg) => appendLog(msg)),
      onEvent("progress_updated", (t) => clock.report(t)),
      onEvent("countdown_updated", setCountdownRemaining),
      onEvent("playback_finished", () => {
        setCountdownRemaining(0);
        atEndRef.current = false;
        setIsPlaying(false);
        setIsPaused(false);
        appendLog("Playback finished");
      }),
      onEvent("visualizer_updated", (pitches) => liveKeys.setPitches(pitches)),
      onEvent("pedal_updated", (active) => liveKeys.setPedal(active)),
      onEvent("auto_paused", () => {
        atEndRef.current = true;
        setIsPaused(true);
      }),
      onEvent("focus_paused", () => {
        atEndRef.current = false;
        setIsPaused(true);
      }),
      onEvent("window_activation_failed", (message) => {
        void showMessage(message, "自动切换窗口未完成");
      }),
      onEvent("error_occurred", (msg) => appendLog(`Error: ${msg}`)),
      onEvent("playback_started", () => {
        atEndRef.current = false;
        setIsPlaying(true);
      }),
      onEvent("hotkey_toggle_requested", () => {
        if (
          window.dispatchEvent(
            new Event("xingkong-play-request", { cancelable: true }),
          )
        )
          void (isPlayingRef.current
            ? togglePauseRef.current()
            : playRef.current());
      }),
      onEvent("hotkey_save_requested", () => {
        const request = new Event("xingkong-save-request", {
          cancelable: true,
        });
        window.dispatchEvent(request);
        if (!request.defaultPrevented) void saveRef.current();
      }),
    ];
    return () => {
      unlisten.forEach((p) => p.then((fn) => fn()));
    };
  }, [appendLog, clock, liveKeys]);

  const loadFile = useCallback(
    async (path: string, name: string) => {
      window.dispatchEvent(new Event("xingkong-source-replaced"));
      if (isPlayingRef.current) await stopRef.current();
      setSheetSource(null);
      sheetSourceRef.current = null;
      preparedConfigRef.current = null;
      sourceIsEditableRef.current = true;
      setAutoTrackSelection(true);
      const version = ++songVersionRef.current;
      setMidiFilePath(path);
      setFileName(name);
      setHasCompiledNotes(false);
      setHasCompiledPedal(false);
      setPedalIntervals([]);
      setAiCurves(null);
      setPedalConfidence(null);
      setCompiledNotesConfig(null);
      setCompiledPedalConfig(null);
      setDefaultAiCurves(null);
      updateConfigRef.current(NO_AI_CURVES);
      setParts([]);
      setSelectedTracksInfo([]);
      setFinalNotes([]);
      setPlayedNotes([]);
      setTempoEvents([]);
      setTimeSignatures([]);
      setMeasureBoundaries([]);
      setOriginalBpm(0);
      appendLog(`Loading ${name}`);
      clearSnapshot();
      updateSnapshot({ file: name, source: "MIDI file" });
      if (!isTauri()) {
        setTracks([
          {
            index: 0,
            name: "Piano Right",
            note_count: 214,
            instrument_name: "Acoustic Grand Piano",
            is_drum: false,
          },
          {
            index: 1,
            name: "Piano Left",
            note_count: 128,
            instrument_name: "Acoustic Grand Piano",
            is_drum: false,
          },
          {
            index: 2,
            name: "Click Track",
            note_count: 96,
            instrument_name: "Drum Kit",
            is_drum: true,
          },
        ]);
        setOriginalBpm(120);
        appendLog(
          "Parsed 3 track(s) successful (preview mode, not a real MIDI parse)",
        );
        return;
      }
      try {
        // Loading a new source must not inherit another song's repair consent.
        const result = await parseMidiWithRepair(path, false);
        const parsed = result.parsed;
        updateConfigRef.current({ midi_clip_invalid_data: result.clip });
        if (version !== songVersionRef.current) return;
        setTracks(parsed.tracks);
        setOriginalBpm(parsed.initial_bpm);
        updateSnapshot({ tempo: `${Math.round(parsed.initial_bpm)} BPM` });
        appendLog(`Parsed ${parsed.tracks.length} track(s) successful`);
      } catch (e) {
        if (version !== songVersionRef.current) return;
        appendLog(`Failed to parse MIDI: ${String(e)}`);
      }
    },
    [appendLog],
  );

  async function openFileBrowser() {
    if (!isTauri()) {
      appendLog("File dialog unavailable outside the desktop app");
      return;
    }
    const midiDir = await getMidiDir().catch(() => "");
    const selected = await openDialog({
      multiple: false,
      filters: [{ name: "MIDI", extensions: ["mid", "midi"] }],
      defaultPath: midiDir || undefined,
    });
    if (typeof selected === "string") {
      await loadFile(selected, selected.split(/[\\/]/).pop() ?? selected);
    }
  }

  async function confirmTrackSelection(
    selection: { index: number; role: HandRole }[],
  ) {
    const info: SelectedTrackInfo[] = selection.map((s) => [s.index, s.role]);
    setSelectedTracksInfo(info);
    setParts(
      selection.map(({ index, role }) => {
        const t = tracks.find((tr) => tr.index === index)!;
        const roleLabel =
          role === "Auto-Detect"
            ? "Auto"
            : role === "Left Hand"
              ? "Left"
              : "Right";
        return { name: t.name, meta: `♩ ${t.note_count} · ${roleLabel}` };
      }),
    );
    setIsPreparing(true);
    try {
      await compileNotesNow(info);
    } finally {
      setIsPreparing(false);
    }
  }

  async function compileNotesNow(info: SelectedTrackInfo[]): Promise<boolean> {
    preparedIdentityRef.current = null;
    const version = songVersionRef.current;
    const configUsed = resolvePlaybackConfig(configRef.current);
    if (!isTauri()) {
      setTotalDuration(PREVIEW_SONG.totalDuration);
      setFinalNotes(PREVIEW_SONG.notes);
      setPlayedNotes(PREVIEW_SONG.notes);
      setTempoEvents(PREVIEW_SONG.tempoEvents);
      setTimeSignatures([]);
      setMeasureBoundaries(PREVIEW_SONG.measureBoundaries);
      setHasCompiledNotes(true);
      setHasCompiledPedal(false);
      compileConfigUsedRef.current = configUsed;
      setCompiledNotesConfig(pickConfig(configUsed, NOTES_CONFIG_KEYS));
      setCompiledPedalConfig(null);
      setDefaultAiCurves(null);
      updateConfig(NO_AI_CURVES);
      appendLog("Notes compiled successful (preview mode)");
      return true;
    }
    try {
      const timeline = sheetSourceRef.current
        ? await invokeCompileNotesFromSheet(
            configUsed,
            sheetSourceRef.current.text,
            sheetSourceRef.current.bpm,
          )
        : await invokeCompileNotes(configUsed, midiFilePath, info);
      if (version !== songVersionRef.current) return false;
      setTotalDuration(timeline.total_dur);
      setFinalNotes(timeline.final_notes);
      setPlayedNotes(timeline.played_notes);
      setTempoEvents(timeline.tempo_events);
      setTimeSignatures(timeline.time_signatures);
      setMeasureBoundaries(timeline.measure_boundaries);
      setHasCompiledNotes(true);
      setHasCompiledPedal(false);
      updateSnapshot({
        tracks: info.length,
        notes: timeline.final_notes.length,
        duration: formatSnapshotDuration(timeline.total_dur),
      });
      compileConfigUsedRef.current = configUsed;
      setCompiledNotesConfig(pickConfig(configUsed, NOTES_CONFIG_KEYS));
      setCompiledPedalConfig(null);
      setDefaultAiCurves(null);
      updateConfig(NO_AI_CURVES);
      appendLog("Notes compiled successful");
      return true;
    } catch (e) {
      if (version !== songVersionRef.current) return false;
      appendLog(`Failed to compile notes: ${String(e)}`);
      const blocked = blockedInputMessage(e);
      if (blocked !== null) {
        setBlockedInput(blocked);
        await clearSong();
      }
      return false;
    }
  }

  function captureDefaultCurves(curves: ThresholdCurves) {
    if (defaultAiCurvesRef.current === null) {
      setDefaultAiCurves(curves);
    }
  }

  async function generatePedal() {
    if (
      ((!hasCompiledNotes &&
        (selectedTracksInfo.length > 0 || !!sheetSourceRef.current)) ||
        notesDirty) &&
      sourceIsEditableRef.current
    ) {
      restoredCacheRef.current = false;
      if (!(await compileNotesNow(selectedTracksInfo))) return;
    }
    await compilePedalNow();
  }

  const notesDirty =
    hasCompiledNotes &&
    configDiffers(
      resolvePlaybackConfig(config),
      compiledNotesConfig,
      NOTES_CONFIG_KEYS,
    );
  const pedalDirty =
    hasCompiledPedal &&
    configDiffers(config, compiledPedalConfig, PEDAL_CONFIG_KEYS);
  const configDirty = notesDirty || pedalDirty;

  async function applyConfigChanges() {
    if (isPlayingRef.current) await stop();
    if (!sourceIsEditableRef.current) {
      appendLog("此存档只有编译结果，无法修改原始演奏参数");
      return;
    }
    if (notesDirty) {
      restoredCacheRef.current = false;
      const compiled = await compileNotesNow(selectedTracksInfo);
      if (compiled)
        await compilePedalNow({ ...configRef.current, ...NO_AI_CURVES });
    } else if (pedalDirty) {
      await compilePedalNow();
    }
  }

  function discardConfigChanges() {
    updateConfig({ ...compiledNotesConfig, ...compiledPedalConfig });
  }

  async function compilePedalNow(
    configOverride?: PlaybackConfig,
  ): Promise<PedalData | null> {
    preparedIdentityRef.current = null;
    if (!isTauri()) {
      const previewCurves = { on: PREVIEW_CURVES.on, off: PREVIEW_CURVES.off };
      const previewCurveConfig = {
        pedal_curve_on: previewCurves.on,
        pedal_curve_off: previewCurves.off,
      };
      setPedalIntervals(PREVIEW_SONG.pedalIntervals);
      setAiCurves(previewCurves);
      setPedalConfidence(PREVIEW_CONFIDENCE);
      setCompiledPedalConfig({
        ...pickConfig(configOverride ?? configRef.current, PEDAL_CONFIG_KEYS),
        ...previewCurveConfig,
      });
      captureDefaultCurves(previewCurves);
      updateConfig(previewCurveConfig);
      setHasCompiledPedal(true);
      appendLog("Pedal compiled successful (preview mode)");
      return null;
    }
    if (isGeneratingPedalRef.current) return null;
    isGeneratingPedalRef.current = true;
    setIsGeneratingPedal(true);
    try {
      const configUsed = {
        ...(compileConfigUsedRef.current ?? configRef.current),
        ...pickConfig(configRef.current, PEDAL_CONFIG_KEYS),
        ...(configOverride ?? {}),
      };
      const data = await invokeCompilePedal(configUsed, midiFilePath);
      const curves: ThresholdCurves = {
        on: data.curve_on,
        off: data.curve_off,
      };
      const hasAiCurves = hasCurves(curves);
      const curveConfig = hasAiCurves
        ? { pedal_curve_on: curves.on, pedal_curve_off: curves.off }
        : NO_AI_CURVES;
      setPedalIntervals(data.pedal_intervals);
      setAiCurves(hasAiCurves ? curves : null);
      setPedalConfidence(
        data.confidence.length > 0
          ? { values: data.confidence, fps: data.confidence_fps }
          : null,
      );
      if (hasAiCurves) captureDefaultCurves(curves);
      setHasCompiledPedal(true);
      setCompiledPedalConfig({
        ...pickConfig(configUsed, PEDAL_CONFIG_KEYS),
        ...curveConfig,
      });
      if (!hasAiCurves) setDefaultAiCurves(null);
      configRef.current = { ...configRef.current, ...curveConfig };
      updateConfig(curveConfig);
      updateSnapshot({ pedal: `${data.pedal_intervals.length} presses` });
      appendLog("Pedal compiled successful");
      return data;
    } catch (e) {
      appendLog(`Failed to compile pedal: ${String(e)}`);
      return null;
    } finally {
      isGeneratingPedalRef.current = false;
      setIsGeneratingPedal(false);
    }
  }

  async function play() {
    if (isGeneratingPedalRef.current || isPreparing) return;
    setIsPaused(false);
    if (!isTauri()) {
      setIsPlaying((p) => !p);
      return;
    }
    setIsPreparing(true);
    try {
      const effective = resolvePlaybackConfig(configRef.current);
      const randomPerformance =
        effective.humanization_on &&
        [
          effective.vary_timing,
          effective.vary_articulation,
          effective.enable_chord_roll,
          effective.enable_drift_correction,
          effective.enable_tempo_sway,
          effective.enable_mistakes,
        ].some(Boolean);
      let needsPedal = !hasCompiledPedal;
      if (
        sourceIsEditableRef.current &&
        (!hasCompiledNotes ||
          configDirty ||
          (effective.random_seed === null && randomPerformance))
      ) {
        if (!(await compileNotesNow(selectedTracksInfo))) return;
        needsPedal = true;
      }
      if (needsPedal && !(await compilePedalNow())) return;
      await invokeStartPlayback(configRef.current, midiFilePath);
    } catch (e) {
      appendLog(`Failed to start playback: ${String(e)}`);
      const blocked = blockedInputMessage(e);
      if (blocked !== null) setBlockedInput(blocked);
    } finally {
      setIsPreparing(false);
    }
  }

  async function togglePause() {
    if (!isTauri()) {
      setIsPlaying((p) => !p);
      return;
    }
    if (atEndRef.current) {
      atEndRef.current = false;
      clock.jump(0);
      await invokeSeekPlayback(0);
    }
    setIsPaused((p) => !p);
    await invokeTogglePause();
  }

  async function stop() {
    songVersionRef.current += 1;
    setCountdownRemaining(0);
    setIsPlaying(false);
    setIsPaused(false);
    isPlayingRef.current = false;
    if (!isTauri()) {
      setIsPlaying(false);
      clock.jump(0);
      return;
    }
    atEndRef.current = false;
    await invokeStopPlayback();
    clock.jump(0);
  }

  async function seek(time: number) {
    if (!isTauri()) {
      clock.jump(time);
      return;
    }
    atEndRef.current = false;
    if (isPlayingRef.current) clock.jump(time);
    await invokeSeekPlayback(time);
  }

  async function save(name?: string): Promise<SaveResult> {
    if (!isTauri()) {
      appendLog("Save unavailable outside the desktop app");
      return { error: "Save unavailable outside the desktop app" };
    }
    if (isSavingRef.current) return { error: "A save is already in progress." };
    if (isGeneratingPedalRef.current)
      return { error: "Pedal is still generating." };
    isSavingRef.current = true;
    setIsSaving(true);
    try {
      let saveConfig = configRef.current;
      if (!hasCompiledPedal) {
        const data = await compilePedalNow();
        if (data && data.curve_on.length > 0 && data.curve_off.length > 0) {
          saveConfig = {
            ...saveConfig,
            pedal_curve_on: data.curve_on,
            pedal_curve_off: data.curve_off,
          };
        }
      }
      const path = await invokeSavePlayback(
        saveConfig,
        midiFilePath,
        selectedTracksInfo,
        fileName,
        name ?? defaultSaveName(fileName),
      );
      appendLog(`Saved to ${path}`);
      setSaveCount((c) => c + 1);
      return { path };
    } catch (e) {
      appendLog(`Failed to save: ${String(e)}`);
      return { error: String(e) };
    } finally {
      isSavingRef.current = false;
      setIsSaving(false);
    }
  }

  async function resumeSave(filepath: string, label: string) {
    window.dispatchEvent(new Event("xingkong-source-replaced"));
    if (!isTauri()) {
      appendLog("Resume unavailable outside the desktop app");
      return;
    }
    if (isPlayingRef.current) await stop();
    try {
      const result = await invokeResumeFromSave(filepath);
      setFinalNotes(result.final_notes);
      setPlayedNotes(result.played_notes);
      setTotalDuration(result.total_dur);
      setTempoEvents(result.tempo_events);
      setTimeSignatures(result.time_signatures);
      setMeasureBoundaries(result.measure_boundaries);
      sourceIsEditableRef.current = false;
      setHasCompiledNotes(true);
      setHasCompiledPedal(true);
      setPedalIntervals(result.pedal_intervals ?? []);
      if (result.playback_settings) {
        const restored = {
          ...songConfig(result.playback_settings),
          pedal_curve_on: result.pedal_curve_on,
          pedal_curve_off: result.pedal_curve_off,
        };
        setConfig(restored);
        configRef.current = restored;
      }
      setAiCurves(null);
      setPedalConfidence(null);
      setCompiledNotesConfig(null);
      setCompiledPedalConfig(null);
      setDefaultAiCurves(null);
      updateConfig({
        pedal_curve_on: result.pedal_curve_on,
        pedal_curve_off: result.pedal_curve_off,
      });
      setLegacyThresholdNotice(result.legacy_pedal_thresholds);
      setFileName(label);
      setMidiFilePath("");
      setSheetSource(null);
      sheetSourceRef.current = null;
      sourceIsEditableRef.current = false;
      setParts([]);
      setSelectedTracksInfo([]);
      clearSnapshot();
      updateSnapshot({
        file: label,
        source: "Save file",
        tracks: result.track_count,
        pedal: `${result.pedal_count} presses`,
      });
      appendLog(`Resumed save: ${label}`);
    } catch (e) {
      appendLog(`Failed to resume save: ${String(e)}`);
      const blocked = blockedInputMessage(e);
      if (blocked !== null) setBlockedInput(blocked);
    }
  }

  async function playTranslatedSheet(
    sheetText: string,
    bpm: number,
    humanize?: boolean,
  ) {
    const sheetConfig =
      humanize === undefined
        ? configRef.current
        : {
            ...configRef.current,
            humanization_on: humanize,
            humanization_mode: humanize
              ? ("individual" as const)
              : ("disabled" as const),
          };
    configRef.current = sheetConfig;
    setConfig(sheetConfig);
    window.dispatchEvent(new Event("xingkong-source-replaced"));
    if (isPlayingRef.current) await stop();
    songVersionRef.current += 1;
    sourceIsEditableRef.current = true;
    setSheetSource({ text: sheetText, bpm });
    sheetSourceRef.current = { text: sheetText, bpm };
    if (!isTauri()) {
      appendLog("Sheet playback unavailable outside the desktop app");
      return;
    }
    try {
      const timeline = await invokeCompileNotesFromSheet(
        resolvePlaybackConfig(configRef.current),
        sheetText,
        bpm,
      );
      setFinalNotes(timeline.final_notes);
      setPlayedNotes(timeline.played_notes);
      setTotalDuration(timeline.total_dur);
      setTempoEvents(timeline.tempo_events);
      setTimeSignatures(timeline.time_signatures);
      setMeasureBoundaries(timeline.measure_boundaries);
      setHasCompiledNotes(true);
      setHasCompiledPedal(false);
      setCompiledNotesConfig(null);
      setCompiledPedalConfig(null);
      setAiCurves(null);
      setDefaultAiCurves(null);
      updateConfig(NO_AI_CURVES);
      compileConfigUsedRef.current = resolvePlaybackConfig(configRef.current);
      setCompiledNotesConfig(
        pickConfig(compileConfigUsedRef.current, NOTES_CONFIG_KEYS),
      );
      setFileName("Translated sheet");
      setMidiFilePath("");
      setParts([]);
      setSelectedTracksInfo([]);
      clearSnapshot();
      updateSnapshot({
        file: "(pasted sheet)",
        source: "Virtual Piano import",
        tempo: `${bpm} BPM`,
      });
      appendLog(
        `Sheet compiled successful: ${timeline.final_notes.length} note(s)`,
      );
      await compilePedalNow({ ...configRef.current, ...NO_AI_CURVES });
      setIsPaused(false);
      await invokeStartPlayback(configRef.current, "");
    } catch (e) {
      appendLog(`Failed to play translated sheet: ${String(e)}`);
    }
  }

  async function clearSong() {
    preparedIdentityRef.current = null;
    if (isGeneratingPedalRef.current) {
      appendLog("Cannot clear the song while the pedal is generating");
      return;
    }
    window.dispatchEvent(new Event("xingkong-source-replaced"));
    if (isPlayingRef.current) await stop();
    if (isTauri()) {
      try {
        await invokeClearLoadedSong();
      } catch (e) {
        appendLog(`Failed to clear the song: ${String(e)}`);
        return;
      }
    }
    songVersionRef.current += 1;
    sourceIsEditableRef.current = false;
    setFileName("");
    setSheetSource(null);
    sheetSourceRef.current = null;
    setCountdownRemaining(0);
    preparedConfigRef.current = null;
    setMidiFilePath("");
    setTracks([]);
    setParts([]);
    setSelectedTracksInfo([]);
    setOriginalBpm(0);
    setTotalDuration(0);
    setFinalNotes([]);
    setPlayedNotes([]);
    setTempoEvents([]);
    setTimeSignatures([]);
    setMeasureBoundaries([]);
    setHasCompiledNotes(false);
    setHasCompiledPedal(false);
    setPedalIntervals([]);
    setAiCurves(null);
    setPedalConfidence(null);
    setCompiledNotesConfig(null);
    setCompiledPedalConfig(null);
    setDefaultAiCurves(null);
    updateConfig(NO_AI_CURVES);
    clock.jump(0);
    liveKeys.clear();
    clearSnapshot();
    appendLog("Cleared the loaded song");
  }

  function acceptTimeline(timeline: {
    final_notes: BackendNote[];
    played_notes: BackendNote[];
    total_dur: number;
    tempo_events: TempoEvent[];
    time_signatures: TimeSignatureEvent[];
    measure_boundaries: MeasureBoundary[];
  }) {
    setFinalNotes(timeline.final_notes);
    setPlayedNotes(timeline.played_notes);
    setTotalDuration(timeline.total_dur);
    clock.setDuration(timeline.total_dur);
    setTempoEvents(timeline.tempo_events);
    setTimeSignatures(timeline.time_signatures);
    setMeasureBoundaries(timeline.measure_boundaries);
    setHasCompiledNotes(true);
    clock.jump(0);
    liveKeys.clear();
  }

  async function preparePlaylistSong(
    detail: PlaylistDetail,
    settings: PlaybackConfig,
    useCache = true,
    compile = true,
    editSettings = true,
    onPhase: (phase: string) => void = () => {},
  ): Promise<PlaybackConfig> {
    if (!isTauri()) throw new Error("请在桌面程序中打开歌单");
    setIsPreparing(true);
    setAutoTrackSelection(false);
    const sourceIdentity = JSON.stringify([detail.metadata.id, detail.metadata.modified_at, detail.song.source, detail.song.selected_tracks, detail.midi_path]);
    const identity = sourceIdentity + ":" + playlistCompilationKey(settings);
    const reusable = compile && useCache && !usesDynamicRandomness(settings) && preparedIdentityRef.current === identity;
    const version = ++songVersionRef.current;
    try {
      await invokeStopPlayback();
      if (version !== songVersionRef.current) throw new Error("加载已取消");
      setIsPlaying(false); setIsPaused(false); setCountdownRemaining(0);
      if (reusable) {
        restoredCacheRef.current = true;
        preparedConfigRef.current = settings;
        return settings;
      }
      preparedIdentityRef.current = null;
      sourceIsEditableRef.current = !!detail.midi_path || detail.song.source.type === "sheet";
      restoredCacheRef.current = false;
      setHasCompiledNotes(false); setHasCompiledPedal(false);
      setPedalConfidence(null); setAiCurves(null); setDefaultAiCurves(null);
      let used = { ...settings };
      const path = detail.midi_path ?? "";
      preparedMidiPathRef.current = path;
      const sheet = detail.song.source.type === "sheet";
      const text = detail.song.source.sheet_text ?? "";
      const bpm = detail.song.source.bpm ?? 120;
      setFileName(detail.metadata.name); setMidiFilePath(path);
      setSheetSource(sheet ? { text, bpm } : null);
      sheetSourceRef.current = sheet ? { text, bpm } : null;
      setTracks([]); setParts([]);
      let info: SelectedTrackInfo[] = detail.song.selected_tracks.map((t) => [t.index, t.role]);
      let cached = false;
      if (useCache && (!usesDynamicRandomness(used) || (!path && !sheet))) {
        onPhase("正在读取演奏缓存…");
        try {
          const result = await restorePlaylistCache(detail.metadata.id, used, !path && !sheet);
          if (version !== songVersionRef.current) throw new Error("加载已取消");
          acceptTimeline(result.timeline); setPedalIntervals(result.pedal_intervals);
          const curves = { on: result.curve_on ?? used.pedal_curve_on, off: result.curve_off ?? used.pedal_curve_off };
          if (hasCurves(curves)) { setAiCurves(curves); setDefaultAiCurves(curves); }
          if (result.confidence?.length) setPedalConfidence({ values: result.confidence, fps: result.confidence_fps ?? 50 });
          setHasCompiledPedal(true); cached = true; restoredCacheRef.current = true;
        } catch (e) {
          if (version !== songVersionRef.current || (!path && !sheet)) throw e;
          appendLog(`缓存需更新：${String(e)}`);
        }
      }
      // Playback with a valid cache does not need to parse MIDI for editor track labels.
      if ((!cached || !compile) && !sheet && path) {
        onPhase("正在解析 MIDI…");
        const result = await parseMidiWithRepair(path, used.midi_clip_invalid_data);
        if (version !== songVersionRef.current) throw new Error("加载已取消");
        used = { ...used, midi_clip_invalid_data: result.clip };
        if (!info.length) info = result.parsed.tracks.filter((t) => !t.is_drum && t.note_count > 0).map((t) => [t.index, "Auto-Detect"]);
        if (!info.length) throw new Error("没有可演奏的非鼓音轨");
        setTracks(result.parsed.tracks); setOriginalBpm(result.parsed.initial_bpm);
        setParts(info.map(([index, role]) => ({ name: result.parsed.tracks.find((t) => t.index === index)?.name ?? `音轨 ${index}`, meta: role })));
      } else if (sheet) setOriginalBpm(bpm);
      else if (!cached && !path) throw new Error("MIDI 源文件缺失，请重新关联文件");
      setSelectedTracksInfo(info);
      if (!compile && cached) {
        compileConfigUsedRef.current = resolvePlaybackConfig(used);
        setCompiledNotesConfig(pickConfig(compileConfigUsedRef.current, NOTES_CONFIG_KEYS));
        setCompiledPedalConfig(pickConfig(used, PEDAL_CONFIG_KEYS)); preparedConfigRef.current = used;
        if (editSettings) { configRef.current = used; setConfig(used); }
        return used;
      }
      if (!compile) {
        setCompiledNotesConfig(null); setCompiledPedalConfig(null);
        setTotalDuration(detail.metadata.duration); setFinalNotes([]); setPlayedNotes([]);
        setTempoEvents([]); setTimeSignatures([]); setMeasureBoundaries([]); setPedalIntervals([]);
        preparedConfigRef.current = null; compileConfigUsedRef.current = null;
        if (editSettings) { configRef.current = used; setConfig(used); }
        clock.jump(0); liveKeys.clear(); return used;
      }
      if (!cached) {
        onPhase("正在生成演奏音符…");
        const timeline = sheet ? await invokeCompileNotesFromSheet(used, text, bpm) : await invokeCompileNotes(used, path, info);
        if (version !== songVersionRef.current) throw new Error("加载已取消");
        acceptTimeline(timeline);
        onPhase(used.pedal_style === "ai" && !used.use_midi_pedal ? "正在计算 AI 踏板…" : "正在生成踏板事件…");
        const pedal = await invokeCompilePedal(used, path);
        if (version !== songVersionRef.current) throw new Error("加载已取消");
        if (pedal.curve_on.length && pedal.curve_off.length) used = { ...used, pedal_curve_on: pedal.curve_on, pedal_curve_off: pedal.curve_off };
        setPedalIntervals(pedal.pedal_intervals); setHasCompiledPedal(true);
        const curves = { on: pedal.curve_on, off: pedal.curve_off };
        setAiCurves(hasCurves(curves) ? curves : null); setDefaultAiCurves(hasCurves(curves) ? curves : null);
        setPedalConfidence(pedal.confidence.length ? { values: pedal.confidence, fps: pedal.confidence_fps } : null);
      }
      compileConfigUsedRef.current = resolvePlaybackConfig(used);
      setCompiledNotesConfig(pickConfig(compileConfigUsedRef.current, NOTES_CONFIG_KEYS));
      setCompiledPedalConfig(pickConfig(used, PEDAL_CONFIG_KEYS)); preparedConfigRef.current = used;
      preparedIdentityRef.current = usesDynamicRandomness(used) ? null : sourceIdentity + ":" + playlistCompilationKey(used);
      if (editSettings) { configRef.current = used; setConfig(used); }
      updateSnapshot({ file: detail.metadata.name, source: sheet ? "歌单 · 文本曲谱" : "歌单 · MIDI" });
      return used;
    } finally { setIsPreparing(false); }
  }
  async function startPrepared(settings?: PlaybackConfig) {
    const used = settings ?? preparedConfigRef.current ?? configRef.current;
    setIsPaused(false);
    await invokeStartPlayback(used, preparedMidiPathRef.current);
  }

  const aiStats = useMemo(
    () => statsFromIntervals(pedalIntervals, totalDuration),
    [pedalIntervals, totalDuration],
  );

  const value: PlaybackEngineValue = {
    selectedTracksInfo,
    sheetSource,
    countdownRemaining,
    isPreparing,
    autoTrackSelection,
    preparePlaylistSong,
    startPrepared,
    preparedCacheHit: () => restoredCacheRef.current,
    fileName,
    midiFilePath,
    tracks,
    parts,
    originalBpm,
    totalDuration,
    finalNotes,
    playedNotes,
    visualizerUse88: compiledNotesConfig?.use_88_key_layout ?? config.use_88_key_layout,
    tempoEvents,
    timeSignatures,
    measureBoundaries,
    hasCompiledNotes,
    hasCompiledPedal,
    isGeneratingPedal,
    isSaving,
    saveCount,
    pedalIntervals,
    aiCurves,
    pedalConfidence,
    configDirty,
    defaultAiCurves,
    aiStats,
    isPlaying,
    isPaused,
    clock,
    liveKeys,
    saveDirConfigured,
    openFileBrowser,
    loadFile,
    applyConfigChanges,
    discardConfigChanges,
    confirmTrackSelection,
    generatePedal,
    play,
    togglePause,
    stop,
    seek,
    save,
    resumeSave,
    playTranslatedSheet,
    clearSong,
    blockedInput,
    dismissBlockedInput: () => setBlockedInput(null),
    legacyThresholdNotice,
    dismissLegacyThresholdNotice: () => setLegacyThresholdNotice(false),
  };

  return (
    <PlaybackEngineContext.Provider value={value}>
      {translateNode(children)}
    </PlaybackEngineContext.Provider>
  );
}

export function usePlaybackEngine() {
  const ctx = useContext(PlaybackEngineContext);
  if (!ctx)
    throw new Error(
      "usePlaybackEngine must be used within PlaybackEngineProvider",
    );
  return ctx;
}
