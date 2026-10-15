import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { FileHeader } from "./FileHeader";
import { setTranslationLanguage } from "../lib/i18n";
const engine = vi.hoisted(() => ({
  fileName: "告白气球.mid",
  selectedTracksInfo: [[0, "Auto-Detect"]],
  sheetSource: null,
  isPreparing: false,
  isGeneratingPedal: false,
  clearSong: vi.fn(),
}));
vi.mock("../state/PlaybackEngineContext", () => ({
  usePlaybackEngine: () => engine,
}));
beforeEach(() => {
  vi.clearAllMocks();
  engine.isPreparing = false;
  setTranslationLanguage("zh-CN");
});
describe("current song header", () => {
  it("shows the song and track count without the obsolete save and file import buttons", () => {
    render(<FileHeader />);
    expect(screen.getByText("告白气球.mid")).toBeTruthy();
    expect(screen.queryByLabelText("保存演奏")).toBeNull();
    expect(screen.queryByLabelText("打开 MIDI")).toBeNull();
  });
  it("clears the source through the playback engine", () => {
    render(<FileHeader />);
    fireEvent.click(screen.getByLabelText("清除曲目"));
    expect(engine.clearSong).toHaveBeenCalledOnce();
  });
  it("does not allow clearing a song during preparation", () => {
    engine.isPreparing = true;
    render(<FileHeader />);
    expect(screen.getByLabelText("清除曲目")).toBeDisabled();
  });
});
