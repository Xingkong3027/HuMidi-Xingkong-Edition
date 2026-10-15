import { fireEvent, render, screen, cleanup } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { setTranslationLanguage } from "../../lib/i18n";
import type { PlaylistItem } from "../../lib/playlist";
import { DEFAULT_CONFIG } from "../playback/types";
const mocks = vi.hoisted(() => ({ setSelected: vi.fn(), busy: false, nativeDialog: false }));
const items: PlaylistItem[] = ["Alpha", "Beta", "Gamma"].map((name, i) => ({
  id: String(i), name, source_type: "midi", source_label: `${name}.mid`, duration: 10,
  midi_available: true, sheet_available: false, cache_available: true,
  humanization_mode: "disabled", random_seed_mode: "fixed_custom",
}));
vi.mock("../../state/PlaylistContext", () => ({ usePlaylist: () => ({
  items, selected: [], busy: mocks.busy, backgroundProgress: "", progress: "",
  mode: "single", setSelected: mocks.setSelected,
}) }));
vi.mock("../../state/PlaybackConfigContext", () => ({ usePlaybackConfig: () => ({ config: DEFAULT_CONFIG }) }));
vi.mock("../../lib/appDialogs", () => ({ isNativeFileDialogOpen: () => mocks.nativeDialog }));
import { PlaylistTab } from "./PlaylistTab";
const show = () => render(<PlaylistTab onEditPlayback={() => {}} onImportMidi={() => {}} />);
const key = (target: Document | Element = document, options = {}) =>
  fireEvent.keyDown(target, { key: "a", ctrlKey: true, ...options });

describe("playlist select-all keyboard shortcut", () => {
  beforeEach(() => { mocks.setSelected.mockClear(); mocks.busy = false; mocks.nativeDialog = false; setTranslationLanguage("zh-CN"); });
  afterEach(cleanup);
  it("selects every song from the page and cancels browser text selection", () => {
    show();
    expect(key()).toBe(false);
    expect(mocks.setSelected).toHaveBeenCalledWith(["0", "1", "2"]);
  });
  it("matches the button's whole-library scope while search hides songs", () => {
    show();
    fireEvent.change(screen.getByPlaceholderText("搜索曲目或来源…"), { target: { value: "Alpha" } });
    expect(screen.getAllByRole("option").filter(e => e.classList.contains("playlist-row"))).toHaveLength(1);
    key(screen.getByText("Alpha"));
    expect(mocks.setSelected).toHaveBeenLastCalledWith(["0", "1", "2"]);
    fireEvent.click(screen.getByRole("button", { name: /^全选$/ }));
    expect(mocks.setSelected).toHaveBeenLastCalledWith(["0", "1", "2"]);
  });
  it("leaves search input text selection to the browser", () => {
    show();
    expect(key(screen.getByPlaceholderText("搜索曲目或来源…"))).toBe(true);
    expect(mocks.setSelected).not.toHaveBeenCalled();
  });
  it("preserves textarea and nested editable content selection", () => {
    show();
    const host = document.createElement("div"); host.contentEditable = "true"; host.setAttribute("contenteditable", "true");
    const child = host.appendChild(document.createElement("span")); document.body.appendChild(host);
    const textarea = document.body.appendChild(document.createElement("textarea"));
    expect(key(child)).toBe(true); expect(key(textarea)).toBe(true);
    expect(mocks.setSelected).not.toHaveBeenCalled(); host.remove(); textarea.remove();
  });
  it("does not change songs when a modal or native chooser is open", () => {
    show(); fireEvent.click(screen.getByRole("button", { name: /^导入歌单$/ }));
    expect(key()).toBe(true); expect(mocks.setSelected).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: /^取消$/ }));
    mocks.nativeDialog = true;
    expect(key()).toBe(true); expect(mocks.setSelected).not.toHaveBeenCalled();
  });
  it("does not select while busy or hijack other key combinations", () => {
    mocks.busy = true; const view = show(); key(); expect(mocks.setSelected).not.toHaveBeenCalled();
    mocks.busy = false; view.rerender(<PlaylistTab onEditPlayback={() => {}} onImportMidi={() => {}} />);
    for (const options of [{ altKey: true }, { shiftKey: true }, { ctrlKey: false }, { isComposing: true }]) expect(key(document, options)).toBe(true);
    expect(mocks.setSelected).not.toHaveBeenCalled();
  });
  it("supports the platform command modifier and removes its listener on leaving the page", () => {
    const view = show(); key(document, { ctrlKey: false, metaKey: true, key: "A" });
    expect(mocks.setSelected).toHaveBeenCalledWith(["0", "1", "2"]);
    mocks.setSelected.mockClear(); view.unmount(); expect(key()).toBe(true);
    expect(mocks.setSelected).not.toHaveBeenCalled();
  });
});
