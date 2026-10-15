import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PlaybackConfigProvider } from "../../state/PlaybackConfigContext";
import { PlaybackTab } from "./PlaybackTab";
import { setTranslationLanguage } from "../../lib/i18n";
const state = vi.hoisted(() => ({
  loadedId: null as string | null,
  settingsDirty: false,
  pendingCount: 0,
  busy: false,
}));
const engine = vi.hoisted(() => ({
  parts: [],
  tracks: [{ index: 0 }],
  selectedTracksInfo: [[0, "Auto-Detect"]],
  sheetSource: null,
  midiFilePath: "test.mid",
  pedalIntervals: [],
  originalBpm: 120,
  hasCompiledPedal: false,
  hasCompiledNotes: false,
  isGeneratingPedal: false,
  isPreparing: false,
  aiStats: null,
  aiCurves: null,
  pedalConfidence: null,
  configDirty: false,
  defaultAiCurves: null,
  generatePedal: vi.fn(),
  applyConfigChanges: vi.fn(),
  discardConfigChanges: vi.fn(),
}));
vi.mock("../../state/PlaybackEngineContext", () => ({
  usePlaybackEngine: () => engine,
}));
vi.mock("../../state/PlaylistContext", () => ({ usePlaylist: () => state }));
const save = vi.fn();
const cancel = vi.fn();
const tracks = vi.fn();
function tree() {
  return (
    <PlaybackConfigProvider>
      <PlaybackTab
        onEditTrackSelection={tracks}
        onSaveChanges={save}
        onCancelChanges={cancel}
      />
    </PlaybackConfigProvider>
  );
}
beforeEach(() => {
  vi.clearAllMocks();
  state.loadedId = null;
  state.settingsDirty = false;
  state.pendingCount = 0;
  setTranslationLanguage("zh-CN");
  localStorage.clear();
});
describe("song editor", () => {
  it("opens settings directly and hides the old information and saved performances pages", () => {
    state.pendingCount = 1;
    render(tree());
    expect(screen.getByText("踏板风格")).toBeTruthy();
    expect(screen.queryByText("曲目信息")).toBeNull();
    expect(document.querySelector(".saved-songs-card")).toBeNull();
    expect(screen.getByText("修改音轨选择")).toBeTruthy();
  });
  it("offers independent humanization settings for the current song", () => {
    render(tree());
    fireEvent.click(screen.getByText("模拟人演奏"));
    expect(screen.getByText("单独配置当前曲目")).toBeTruthy();
  });
  it("applies an existing song through save-and-return without generating pedal or renaming", () => {
    state.loadedId = "a";
    state.settingsDirty = true;
    render(tree());
    fireEvent.click(screen.getByText("应用修改"));
    expect(save).toHaveBeenCalledOnce();
    expect(engine.applyConfigChanges).not.toHaveBeenCalled();
    expect(document.querySelector(".modal")).toBeNull();
  });
  it("cancel returns through the song editor cancel action", () => {
    state.loadedId = "a";
    state.settingsDirty = true;
    render(tree());
    fireEvent.click(screen.getByText("放弃修改"));
    expect(cancel).toHaveBeenCalledOnce();
  });
  it("lets users revisit track selection", () => {
    state.pendingCount = 1;
    render(tree());
    fireEvent.click(screen.getByText("修改音轨选择"));
    expect(tracks).toHaveBeenCalledOnce();
  });
});

it("import drafts use their settings directly without dead apply or discard buttons", () => {
  state.pendingCount = 1; state.settingsDirty = true;
  render(tree());
  expect(screen.getByText("正在设置导入草稿，加入歌单后保存。")).toBeTruthy();
  expect(document.querySelector(".apply-toast--visible")).toBeNull();
});
