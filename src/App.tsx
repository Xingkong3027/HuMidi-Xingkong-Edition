import { isNativeFileDialogOpen } from "./lib/appDialogs";
import { AppDialogHost } from "./components/AppDialogHost";
import { t, translateNode } from "./lib/i18n";
import { useEffect, useRef, useState } from "react";
import { ThemeProvider } from "./theme/ThemeProvider";
import {
  AppSettingsProvider,
  useAppSettings,
} from "./state/AppSettingsContext";
import { PlaybackConfigProvider } from "./state/PlaybackConfigContext";
import { LogProvider, useLog } from "./state/LogContext";
import {
  PlaybackEngineProvider,
  usePlaybackEngine,
} from "./state/PlaybackEngineContext";
import { LanguageProvider, useLanguage } from "./state/LanguageContext";
import { PlaylistProvider, usePlaylist } from "./state/PlaylistContext";
import { PlaylistTab, PlaylistMini } from "./pages/playlist/PlaylistTab";
import { Button } from "./components/Button";
import { MessageModal } from "./components/MessageModal";
import { isTauri, onEvent } from "./lib/tauri";
import { Sidebar } from "./components/Sidebar";
import { TransportBar } from "./components/TransportBar";
import { FileHeader } from "./components/FileHeader";
import {
  TrackSelectionDialog,
  type HandRole,
} from "./dialogs/TrackSelectionDialog";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import { PlaybackTab } from "./pages/playback/PlaybackTab";
import { VisualizerTab } from "./pages/visualizer/VisualizerTab";
import { SettingsTab } from "./pages/settings/SettingsTab";
import { TranslatorTab } from "./pages/translator/TranslatorTab";
import { DebugTab } from "./pages/debug/DebugTab";
import { LicenseTab } from "./pages/license/LicenseTab";
import { UpdateCheckPrompt } from "./dialogs/UpdateCheckPrompt";
import { UpdateAvailableModal } from "./dialogs/UpdateAvailableModal";
import { BlockedInputDialog } from "./dialogs/BlockedInputDialog";
import { LegacyThresholdsDialog } from "./dialogs/LegacyThresholdsDialog";
import { useKeyForwarding } from "./lib/useKeyForwarding";
import { useCollapsedWindowSize } from "./lib/useCollapsedWindowSize";
import { PAGE_IDS, type PageId } from "./pages/pageIds";
import { usePersistedState } from "./state/usePersistedState";
import { parseBoolean, parseOneOf } from "./state/persistedParsers";
import "./App.css";

const PAGE_TITLES: Record<PageId, string> = {
  playback: "Playback",
  playlist: "Playlist",
  visualizer: "Visualizer",
  translator: "Translator",
  settings: "Settings",
  debug: "Debug",
  license: "About / License",
};

function AppShell() {
  const { resolved: language } = useLanguage();
  const [activePage, setActivePage] = usePersistedState<PageId>(
    "ui_active_page",
    "playback",
    {
      parse: parseOneOf(PAGE_IDS),
    },
  );
  const [isCollapsed, setIsCollapsed] = usePersistedState(
    "ui_collapsed",
    false,
    { parse: parseBoolean },
  );
  const [trackSelectionOpen, setTrackSelectionOpen] = useState(false);
  const [editorSubTab, setEditorSubTab] = usePersistedState("ui_editor_subtab", 0, {
    parse: parseOneOf([0, 1, 2]),
  });
  const windowRef = useRef<HTMLDivElement>(null);
  const { appendLog } = useLog();
  useCollapsedWindowSize(isCollapsed, windowRef, appendLog);
  const {
    opacity,
    showStatusText,
    showTimeline,
    showPiano,
    switchToVisualizerOnPlay,
    showUpdatePrompt,
    resolveUpdatePrompt,
    updateAvailable,
    dismissUpdateAvailable,
  } = useAppSettings();
  useKeyForwarding();
  const engine = usePlaybackEngine();
  const playlist = usePlaylist();

  const actionsRef = useRef({
    playPause: () => {},
    stop: () => {},
    next: () => {},
    previous: () => {},
    save: () => {},
  });
  actionsRef.current = {
    playPause: () => {
      if (isNativeFileDialogOpen() || document.querySelector('[role="dialog"]')) return;
      if (playlist.busy || engine.isPreparing) return;
      if (engine.countdownRemaining > 0) {
        void playlist.stop();
        return;
      }
      if (engine.isPlaying) {
        const selectedId = playlist.selected[0];
        if (engine.isPaused && selectedId && selectedId !== playlist.currentId &&
            (playlist.active || activePage === "playlist" || isCollapsed)) void playlist.play(selectedId);
        else void engine.togglePause();
        return;
      }
      if (
        activePage === "playlist" ||
        (playlist.active && activePage !== "playback") ||
        (isCollapsed && playlist.selected.length > 0)
      )
        void playlist.play();
      else if (activePage === "translator")
        window.dispatchEvent(new Event("xingkong-sheet-play"));
      else if (playlist.loadedId || playlist.pendingCount > 0) void playlist.preview();
      else if (playlist.items.length > 0) void playlist.play();
    },
    stop: () => {
      void playlist.stop();
    },
    next: () => {
      if (isNativeFileDialogOpen() || document.querySelector('[role="dialog"]')) return;
      void playlist.next(1);
    },
    previous: () => {
      if (isNativeFileDialogOpen() || document.querySelector('[role="dialog"]')) return;
      void playlist.next(-1);
    },
    save: () => {
      if (isNativeFileDialogOpen() || document.querySelector('[role="dialog"]')) return;
      if (
        !playlist.busy &&
        !engine.isPreparing &&
        !engine.isGeneratingPedal &&
        (playlist.loadedId || playlist.pendingCount > 0 || (engine.sheetSource && !playlist.active)) &&
        (engine.selectedTracksInfo.length > 0 || engine.sheetSource)
      )
        void playlist.addCurrent().then((saved) => {
          if (saved) setActivePage("playlist");
        });
    },
  };
  useEffect(() => {
    const play = (event: Event) => {
      event.preventDefault();
      actionsRef.current.playPause();
    };
    window.addEventListener("xingkong-play-request", play);
    const save = (event: Event) => {
      event.preventDefault();
      actionsRef.current.save();
    };
    window.addEventListener("xingkong-save-request", save);
    const listeners = isTauri()
      ? [
          onEvent("hotkey_stop_requested", () => actionsRef.current.stop()),
          onEvent("hotkey_next_requested", () => actionsRef.current.next()),
          onEvent("hotkey_previous_requested", () =>
            actionsRef.current.previous(),
          ),
        ]
      : [];
    return () => {
      window.removeEventListener("xingkong-play-request", play);
      window.removeEventListener("xingkong-save-request", save);
      listeners.forEach((p) => {
        void p.then((unlisten) => unlisten());
      });
    };
  }, []);

  useEffect(() => {
    function handleKeydown(e: KeyboardEvent) {
      if (e.defaultPrevented) return;
      if (e.ctrlKey && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setIsCollapsed((c) => !c);
      }
    }
    window.addEventListener("keydown", handleKeydown);
    return () => window.removeEventListener("keydown", handleKeydown);
  }, []);

  const playbackRunning = engine.isPlaying && !engine.isPaused;
  const visualizerAvailableRef = useRef(showTimeline || showPiano);
  visualizerAvailableRef.current = showTimeline || showPiano;
  const switchOnPlayRef = useRef(switchToVisualizerOnPlay);
  switchOnPlayRef.current = switchToVisualizerOnPlay;
  const wasRunningRef = useRef(false);

  useEffect(() => {
    if (
      playbackRunning &&
      !wasRunningRef.current &&
      switchOnPlayRef.current &&
      visualizerAvailableRef.current
    ) {
      setActivePage("visualizer");
    }
    wasRunningRef.current = playbackRunning;
  }, [playbackRunning, setActivePage]);

  useEffect(() => {
    if (engine.tracks.length > 0 && engine.autoTrackSelection)
      setTrackSelectionOpen(true);
  }, [engine.tracks]);

  async function confirmTrackSelection(
    selection: { index: number; role: HandRole }[],
  ) {
    setTrackSelectionOpen(false);
    await engine.confirmTrackSelection(selection);
  }

  async function saveSong() {
    if (await playlist.addCurrent()) setActivePage("playlist");
  }
  function cancelChanges() {
    playlist.cancelEdit();
    setActivePage("playlist");
  }
  const sourceReady =
    engine.selectedTracksInfo.length > 0 || !!engine.sheetSource;
  const waiting =
    playlist.busy ||
    engine.isPreparing ||
    engine.isGeneratingPedal ||
    engine.countdownRemaining > 0;
  const status = waiting
    ? "loading"
    : !engine.fileName
      ? "unloaded"
      : engine.hasCompiledPedal
        ? "ready"
        : "loaded";
  const statusLabel = waiting
    ? playlist.progress ||
      (engine.countdownRemaining > 0 ? t("等待倒计时…") : t("正在准备演奏…"))
    : {
        unloaded: t("尚未载入曲目"),
        loaded: t("已载入"),
        loading: t("正在准备演奏…"),
        ready: t("准备就绪"),
      }[status];

  return (
    <div
      data-language={language}
      ref={windowRef}
      className={`app-window${isCollapsed ? " app-window--collapsed" : ""}`}
      style={{ opacity: opacity / 100 }}
    >
      {translateNode(
        !isCollapsed && (
          <div className="app-body">
            <Sidebar
              activePage={activePage}
              onNavigate={setActivePage}
              visualizerDisabled={!showTimeline && !showPiano}
            />
            <div className="app-page-area">
              <FileHeader />
              {translateNode(
                activePage === "playback" && editorSubTab !== 2 && (
                  <div className="song-actions">
                    <span>
                      {playlist.pendingCount > 1
                        ? t(
                            `待加入 ${playlist.pendingCount} 首 · 此处设置应用于这一批，加入后每首独立保存`,
                          )
                        : playlist.loadedId
                          ? t("正在修改歌单曲目 · 设置仅保存到此曲目")
                          : playlist.pendingCount > 0 ? t("导入草稿 · 参数将在加入歌单时保存")
                          : t("新曲目默认值 · 新导入 MIDI 使用这些参数")}
                    </span>
                    {(playlist.loadedId || playlist.pendingCount > 0) && (
                      <Button disabled={waiting} onClick={cancelChanges}>
                        {t(playlist.pendingCount > 0 ? "放弃导入" : "放弃修改")}
                      </Button>
                    )}
                    {playlist.loadedId ? (
                      <Button
                        variant="accent"
                        disabled={!sourceReady || waiting}
                        onClick={() => void saveSong()}
                      >
                        {t("保存修改并返回歌单")}
                      </Button>
                    ) : playlist.pendingCount > 0 ? (
                      <Button
                        variant="accent"
                        disabled={!sourceReady || waiting}
                        onClick={() => void saveSong()}
                      >
                        {t(
                          playlist.pendingCount > 1
                            ? "全部加入歌单"
                            : "加入歌单",
                        )}
                      </Button>
                    ) : null}
                    <Button
                      disabled={waiting}
                      onClick={() => void playlist.batchImport()}
                    >
                      {t("导入 MIDI")}
                    </Button>
                  </div>
                ),
              )}
              <div className="app-page-content">
                {translateNode(
                  activePage === "playback" ? (
                    <PlaybackTab
                        activeTab={editorSubTab}
                        onTabChange={setEditorSubTab}
                      onEditTrackSelection={() => setTrackSelectionOpen(true)}
                      onSaveChanges={saveSong}
                      onCancelChanges={cancelChanges}
                    />
                  ) : activePage === "playlist" ? (
                    <PlaylistTab
                      onEditPlayback={() => setActivePage("playback")}
                      onImportMidi={() => {
                        setActivePage("playback");
                        void playlist.batchImport();
                      }}
                    />
                  ) : activePage === "visualizer" ? (
                    <VisualizerTab />
                  ) : activePage === "settings" ? (
                    <SettingsTab />
                  ) : activePage === "translator" ? (
                    <TranslatorTab />
                  ) : activePage === "debug" ? (
                    <DebugTab />
                  ) : activePage === "license" ? (
                    <LicenseTab />
                  ) : (
                    <PlaceholderPage title={PAGE_TITLES[activePage]} />
                  ),
                )}
              </div>
            </div>
          </div>
        ),
      )}

      {translateNode(isCollapsed && <FileHeader />)}
      {translateNode(
        isCollapsed && playlist.items.length > 0 && <PlaylistMini />,
      )}

      <TransportBar
        isPlaying={engine.isPlaying && !engine.isPaused}
        clock={engine.clock}
        totalTime={engine.totalDuration}
        isCollapsed={isCollapsed}
        status={status}
        statusLabel={statusLabel}
        showStatusText={showStatusText}
        playEnabled={
          !playlist.busy &&
          !engine.isPreparing &&
          (sourceReady ||
            engine.hasCompiledNotes ||
            (playlist.items.length > 0) ||
            activePage === "translator")
        }
        onScrub={(time) => void engine.seek(time)}
        onPlayPause={() => actionsRef.current.playPause()}
        onStop={() => actionsRef.current.stop()}
        onPrevious={
          playlist.items.length
            ? () => actionsRef.current.previous()
            : undefined
        }
        onNext={
          playlist.items.length ? () => actionsRef.current.next() : undefined
        }
        countdownRemaining={engine.countdownRemaining}
        sourceLabel={
          engine.fileName
            ? `${engine.fileName} · ${playlist.active ? "歌单" : engine.sheetSource ? "文本曲谱" : engine.midiFilePath ? "MIDI" : "演奏存档"}`
            : undefined
        }
        onSeekStart={() => void engine.seek(0)}
        onSeekEnd={() => void engine.seek(engine.totalDuration)}
        onToggleCollapsed={() => setIsCollapsed((c) => !c)}
      />
      {translateNode(
        playlist.error && (
          <MessageModal
            title={t("歌单操作未完成")}
            width={520}
            height={260}
            body={playlist.error}
            onClose={playlist.dismissError}
            buttons={[
              {
                label: "关闭",
                variant: "accent",
                onClick: playlist.dismissError,
              },
            ]}
          />
        ),
      )}
      {translateNode(
        playlist.report && (
          <MessageModal
            title={t("操作结果")}
            width={620}
            height={350}
            body={`已处理 ${playlist.report.imported} 首曲目。${playlist.report.errors.length ? "\n\n" + playlist.report.errors.join("\n") : ""}`}
            onClose={playlist.clearReport}
            buttons={[
              {
                label: "完成",
                variant: "accent",
                onClick: playlist.clearReport,
              },
            ]}
          />
        ),
      )}

      {translateNode(
        trackSelectionOpen && (
          <TrackSelectionDialog
            initialSelection={
              engine.selectedTracksInfo.length
                ? engine.selectedTracksInfo.map(([index, role]) => ({
                    index,
                    role: role as HandRole,
                  }))
                : undefined
            }
            tracks={engine.tracks.map((t) => ({
              index: t.index,
              name: t.name,
              instrument: t.instrument_name,
              noteCount: t.note_count,
              channel: t.is_drum ? 9 : 0,
            }))}
            onCancel={() => setTrackSelectionOpen(false)}
            onConfirm={confirmTrackSelection}
          />
        ),
      )}

      {translateNode(
        engine.blockedInput !== null && (
          <BlockedInputDialog
            message={engine.blockedInput}
            onDismiss={engine.dismissBlockedInput}
          />
        ),
      )}
      {translateNode(
        engine.legacyThresholdNotice && (
          <LegacyThresholdsDialog
            onDismiss={engine.dismissLegacyThresholdNotice}
          />
        ),
      )}
      {translateNode(
        showUpdatePrompt && (
          <UpdateCheckPrompt onChoice={resolveUpdatePrompt} />
        ),
      )}
      {translateNode(
        updateAvailable && (
          <UpdateAvailableModal
            currentVersion={updateAvailable.currentVersion}
            latestVersion={updateAvailable.tag}
            releasesUrl={updateAvailable.url}
            onDismiss={dismissUpdateAvailable}
          />
        ),
      )}
    </div>
  );
}

function App() {
  return (
    <LanguageProvider>
      <ThemeProvider>
        <LogProvider>
          <AppSettingsProvider>
            <PlaybackConfigProvider>
              <PlaybackEngineProvider>
                <PlaylistProvider>
                  <AppShell />
                  <AppDialogHost />
                </PlaylistProvider>
              </PlaybackEngineProvider>
            </PlaybackConfigProvider>
          </AppSettingsProvider>
        </LogProvider>
      </ThemeProvider>
    </LanguageProvider>
  );
}

export default App;
