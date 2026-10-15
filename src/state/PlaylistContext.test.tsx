import {
  act,
  renderHook,
  waitFor,
  fireEvent,
  screen,
} from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";
import { DEFAULT_CONFIG } from "../pages/playback/types";
import { setTranslationLanguage } from "../lib/i18n";
const mocks = vi.hoisted(() => ({
  handlers: new Map<string, () => void>(),
  list: vi.fn(),
  get: vi.fn(),
  prepare: vi.fn(),
  start: vi.fn(),
  stop: vi.fn(),
  clear: vi.fn(),
  put: vi.fn(),
  cache: vi.fn(),
  precache: vi.fn(),
  hit: vi.fn(() => false),
  begin: vi.fn(),
  end: vi.fn(),
  open: vi.fn(),
  parse: vi.fn(),
  importPlaylist: vi.fn(),
}));
vi.mock("../lib/appDialogs", () => ({
  open: mocks.open,
  save: vi.fn(),
  ask: vi.fn(),
}));
vi.mock("../lib/midiRepair", () => ({ parseMidiWithRepair: mocks.parse }));
vi.mock("./PlaybackEngineContext", () => ({
  usePlaybackEngine: () => ({
    preparePlaylistSong: mocks.prepare,
    preparedCacheHit: mocks.hit,
    startPrepared: mocks.start,
    stop: mocks.stop,
    clock: { duration: () => 2 },
    clearSong: mocks.clear,
    play: vi.fn(),
    midiFilePath: "/library/midi/a.mid",
    selectedTracksInfo: [[0, "Auto-Detect"]],
    totalDuration: 2,
  }),
}));
vi.mock("./PlaybackConfigContext", () => ({
  usePlaybackConfig: () => ({ config: DEFAULT_CONFIG, defaultConfig: DEFAULT_CONFIG, beginEdit: mocks.begin, endEdit: mocks.end }),
}));
vi.mock("./LogContext", () => ({ useLog: () => ({ appendLog: vi.fn() }) }));
vi.mock("../lib/tauri", async () => ({
  ...(await vi.importActual("../lib/tauri")),
  isTauri: () => true,
  onEvent: (name: string, fn: () => void) => {
    mocks.handlers.set(name, fn);
    return Promise.resolve(() => {});
  },
}));
vi.mock("./usePersistedState", async () => {
  const { useState } = await import("react");
  return {
    usePersistedState: (_key: string, value: unknown) => useState(value),
  };
});
vi.mock("../lib/playlist", async () => {
  const actual = await vi.importActual("../lib/playlist");
  return {
    ...actual,
    putPlaylistSong: mocks.put,
    cachePlaylistSong: mocks.cache,
    preparePlaylistCache: mocks.precache,
    listPlaylist: mocks.list,
    getPlaylistSong: mocks.get,
    importPlaylist: mocks.importPlaylist,
  };
});
import { PlaylistProvider, usePlaylist } from "./PlaylistContext";
const items = [
  { id: "a", name: "A" },
  { id: "b", name: "B" },
];
const wrapper = ({ children }: { children: ReactNode }) => (
  <PlaylistProvider>{children}</PlaylistProvider>
);
beforeEach(() => {
  setTranslationLanguage("zh-CN");
  vi.clearAllMocks();
  mocks.handlers.clear();
  mocks.list.mockResolvedValue(items);
  mocks.get.mockImplementation(async (id: string) => ({
    metadata: { id, name: id },
    midi_path: "/copied.mid",
    song: {
      source: {
        type: "midi",
        original_filename: "告白气球.mid",
        original_path: "/原件/告白气球.mid",
      },
      playback_settings: { tempo: 1, humanization_seed_mode: "dynamic" },
      selected_tracks: [],
    },
  }));
  mocks.prepare.mockResolvedValue(DEFAULT_CONFIG);
  mocks.put.mockResolvedValue({ id: "a", name: "a" });
  mocks.cache.mockResolvedValue(undefined);
  mocks.precache.mockResolvedValue(undefined);
  mocks.hit.mockReturnValue(false);
  mocks.parse.mockResolvedValue({
    clip: false,
    parsed: {
      initial_bpm: 120,
      tracks: [
        {
          index: 0,
          name: "Piano",
          instrument_name: "Piano",
          note_count: 12,
          is_drum: false,
        },
      ],
    },
  });
  mocks.start.mockResolvedValue(undefined);
  mocks.importPlaylist.mockResolvedValue({ imported: 1, errors: [] });
  mocks.stop.mockResolvedValue(undefined);
});
it("imports old JSON files through the normal file picker and displays the result", async () => {
  const { result } = renderHook(usePlaylist, { wrapper });
  mocks.open.mockResolvedValueOnce("C:/旧版/backup.json");
  await act(async () => result.current.importPackage());
  expect(mocks.open.mock.calls[0][0].filters[0].extensions).toContain("json");
  expect(mocks.open.mock.calls[0][0].directory).toBe(false);
  expect(mocks.importPlaylist).toHaveBeenCalledWith("C:/旧版/backup.json");
  expect(result.current.report).toEqual({ imported: 1, errors: [] });
});
describe("playlist playback ownership", () => {
  it("advances after natural completion and never after manual stop", async () => {
    const { result } = renderHook(usePlaylist, { wrapper });
    await waitFor(() => expect(result.current.items).toHaveLength(2));
    await act(async () => result.current.play("a"));
    await act(async () => mocks.handlers.get("natural_finished")?.());
    await waitFor(() => expect(result.current.currentId).toBe("b"));
    await act(async () => result.current.stop());
    const n = mocks.start.mock.calls.length;
    await act(async () => mocks.handlers.get("natural_finished")?.());
    expect(mocks.start).toHaveBeenCalledTimes(n);
    expect(result.current.active).toBe(false);
  });
  it("does not lose natural completion while start is still awaiting refresh", async () => {
    let release!: () => void;
    mocks.start.mockImplementationOnce(
      () =>
        new Promise<void>((resolve) => {
          release = resolve;
        }),
    );
    const { result } = renderHook(usePlaylist, { wrapper });
    await waitFor(() => expect(result.current.items).toHaveLength(2));
    let playing!: Promise<void>;
    act(() => {
      playing = result.current.play("a");
    });
    await waitFor(() => expect(mocks.start).toHaveBeenCalledOnce());
    act(() => mocks.handlers.get("natural_finished")?.());
    await act(async () => {
      release();
      await playing;
    });
    await waitFor(() => expect(result.current.currentId).toBe("b"));
  });
  it("cancels a prepared song if the source is replaced, and reports preparation failures", async () => {
    let release!: () => void;
    mocks.prepare.mockImplementationOnce(
      () =>
        new Promise<typeof DEFAULT_CONFIG>((resolve) => {
          release = () => resolve(DEFAULT_CONFIG);
        }),
    );
    const { result } = renderHook(usePlaylist, { wrapper });
    await waitFor(() => expect(result.current.items).toHaveLength(2));
    let playing!: Promise<void>;
    act(() => {
      playing = result.current.play("a");
    });
    await waitFor(() => expect(mocks.prepare).toHaveBeenCalledOnce());
    act(() => window.dispatchEvent(new Event("xingkong-source-replaced")));
    await act(async () => {
      release();
      await playing;
    });
    expect(mocks.start).not.toHaveBeenCalled();
    mocks.prepare.mockRejectedValueOnce(new Error("broken source"));
    await act(async () => result.current.play("b"));
    expect(result.current.error).toContain("broken source");
    expect(result.current.busy).toBe(false);
    expect(result.current.active).toBe(false);
  });
});

describe("song editor ownership", () => {
  it("single MIDI import asks for tracks and remains a draft until explicitly added", async () => {
    mocks.open.mockResolvedValue(["/songs/中文曲名.mid"]);
    const { result } = renderHook(usePlaylist, { wrapper });
    let importing!: Promise<void>;
    act(() => {
      importing = result.current.batchImport();
    });
    await waitFor(() =>
      expect(
        screen.getByText("Piano", { selector: "td:nth-child(2)" }),
      ).toBeTruthy(),
    );
    fireEvent.click(screen.getByText(/^(OK|确定)$/));
    await act(async () => importing);
    expect(mocks.put).not.toHaveBeenCalled();
    expect(result.current.pendingCount).toBe(1);
    await act(async () => {
      await result.current.addCurrent();
    });
    expect(mocks.put).toHaveBeenLastCalledWith(
      "中文曲名",
      expect.objectContaining({
        source: expect.objectContaining({ original_filename: "中文曲名.mid" }),
      }),
      "/songs/中文曲名.mid",
      2,
      null,
    );
  });
  it("multi MIDI import offers automatic tracks and saves each song only after settings", async () => {
    mocks.open.mockResolvedValue(["/songs/一.mid", "/songs/二.mid"]);
    const { result } = renderHook(usePlaylist, { wrapper });
    let importing!: Promise<void>;
    act(() => {
      importing = result.current.batchImport();
    });
    await waitFor(() => expect(screen.getByText("自动选择音轨")).toBeTruthy());
    fireEvent.click(screen.getByText("自动选择音轨"));
    await act(async () => importing);
    expect(mocks.put).not.toHaveBeenCalled();
    expect(result.current.pendingCount).toBe(2);
    await act(async () => {
      await result.current.addCurrent();
    });
    expect(mocks.put).toHaveBeenCalledTimes(2);
    expect(mocks.put.mock.calls.map((call) => call[0])).toEqual(["一", "二"]);
    expect(
      mocks.put.mock.calls.every(
        (call) => call[1].playback_settings.humanization_mode === "individual",
      ),
    ).toBe(true);
  });
  it("automatic import falls back to manual tracks if only drums are found", async () => {
    mocks.open.mockResolvedValue(["/songs/一.mid", "/songs/鼓.mid"]);
    mocks.parse
      .mockResolvedValueOnce({
        clip: false,
        parsed: {
          tracks: [
            {
              index: 0,
              name: "Piano",
              instrument_name: "Piano",
              note_count: 12,
              is_drum: false,
            },
          ],
        },
      })
      .mockResolvedValueOnce({
        clip: false,
        parsed: {
          tracks: [
            {
              index: 0,
              name: "Drums",
              instrument_name: "Drums",
              note_count: 10,
              is_drum: true,
            },
          ],
        },
      });
    const { result } = renderHook(usePlaylist, { wrapper });
    let importing!: Promise<void>;
    act(() => {
      importing = result.current.batchImport();
    });
    await waitFor(() => expect(screen.getByText("自动选择音轨")).toBeTruthy());
    fireEvent.click(screen.getByText("自动选择音轨"));
    await waitFor(() => expect(screen.getByRole("checkbox")).toBeTruthy());
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByText(/^(OK|确定)$/));
    await act(async () => importing);
    expect(result.current.pendingCount).toBe(2);
    expect(mocks.put).not.toHaveBeenCalled();
  });
  it("a partially failed batch save retries only the unsaved song", async () => {
    const parsed = { tracks: [{ index: 0, name: "Piano", instrument_name: "Piano", note_count: 12, is_drum: false }] };
    mocks.parse.mockResolvedValueOnce({ clip: false, parsed }).mockResolvedValueOnce({ clip: true, parsed });
    mocks.open.mockResolvedValue(["/songs/一.mid", "/songs/二.mid"]);
    const { result } = renderHook(usePlaylist, { wrapper });
    let importing!: Promise<void>;
    act(() => {
      importing = result.current.batchImport();
    });
    await waitFor(() => expect(screen.getByText("自动选择音轨")).toBeTruthy());
    fireEvent.click(screen.getByText("自动选择音轨"));
    await act(async () => importing);
    mocks.put
      .mockResolvedValueOnce({ id: "first", name: "一" })
      .mockRejectedValueOnce(new Error("disk full"));
    await act(async () => {
      expect(await result.current.addCurrent()).toBe(false);
    });
    expect(result.current.loadedId).toBeNull();
    expect(result.current.pendingCount).toBe(1);
    expect(mocks.prepare).toHaveBeenLastCalledWith(expect.anything(), expect.objectContaining({ midi_clip_invalid_data: true }), false, false);
    await act(async () => {
      expect(await result.current.addCurrent()).toBe(true);
    });
    expect(mocks.put.mock.calls.map((call) => call[0])).toEqual([
      "一",
      "二",
      "二",
    ]);
  });
  it("cancelling the multi import choice leaves the library untouched", async () => {
    mocks.open.mockResolvedValue(["/songs/一.mid", "/songs/二.mid"]);
    const { result } = renderHook(usePlaylist, { wrapper });
    let importing!: Promise<void>;
    act(() => {
      importing = result.current.batchImport();
    });
    await waitFor(() =>
      expect(screen.getByText(/^(取消|Cancel)$/)).toBeTruthy(),
    );
    fireEvent.click(screen.getByText(/^(取消|Cancel)$/));
    await act(async () => importing);
    expect(mocks.put).not.toHaveBeenCalled();
    expect(result.current.pendingCount).toBe(0);
  });
  it("opens editing without compiling notes or pedal and preserves identity on save", async () => {
    const { result } = renderHook(usePlaylist, { wrapper });
    await act(async () => result.current.edit("a"));
    expect(mocks.prepare).toHaveBeenLastCalledWith(
      expect.anything(),
      expect.anything(),
      true,
      false,
    );
    expect(result.current.loadedId).toBe("a");
    await act(async () => {
      expect(await result.current.addCurrent()).toBe(true);
    });
    expect(mocks.put).toHaveBeenLastCalledWith(
      "a",
      expect.objectContaining({
        source: expect.objectContaining({
          original_filename: "告白气球.mid",
          original_path: "/原件/告白气球.mid",
        }),
      }),
      null,
      2,
      "a",
    );
    expect(result.current.editingId).toBeNull();
    expect(result.current.loadedId).toBeNull();
  });
  it("a loaded song never creates another item when settings are saved", async () => {
    const { result } = renderHook(usePlaylist, { wrapper });
    await act(async () => result.current.edit("b"));
    mocks.put.mockClear();
    await act(async () => {
      await result.current.addCurrent();
    });
    expect(mocks.put).toHaveBeenCalledOnce();
    expect(mocks.put.mock.calls[0][4]).toBe("b");
  });
  it("failed saving keeps the song editor open and exposes the error", async () => {
    const { result } = renderHook(usePlaylist, { wrapper });
    await act(async () => result.current.edit("a"));
    mocks.put.mockRejectedValueOnce(new Error("disk full"));
    await act(async () => {
      expect(await result.current.addCurrent()).toBe(false);
    });
    expect(result.current.editingId).toBe("a");
    expect(result.current.error).toContain("disk full");
  });
});

describe("cache and playback separation", () => {
  it("playing does not enter the editor or mark a song for saving", async () => {
    const { result } = renderHook(usePlaylist, { wrapper });
    await act(async () => result.current.play("a"));
    expect(result.current.loadedId).toBeNull();
    expect(result.current.editingId).toBeNull();
    expect(mocks.begin).not.toHaveBeenCalled();
    expect(mocks.prepare).toHaveBeenCalledWith(expect.anything(), expect.anything(), true, true, false, expect.any(Function));
  });
  it("cache hits start without rewriting the song or its cache", async () => {
    mocks.hit.mockReturnValue(true);
    const { result } = renderHook(usePlaylist, { wrapper });
    await act(async () => result.current.play("a"));
    expect(mocks.start).toHaveBeenCalledOnce();
    expect(mocks.put).not.toHaveBeenCalled();
    expect(mocks.cache).not.toHaveBeenCalled();
  });
});

it("prioritizes a requested song over other queued background jobs", async () => {
  mocks.list.mockResolvedValue(["a","b","c"].map(id => ({id,name:id,midi_available:true,cache_available:false})));
  let release!: () => void;
  mocks.precache.mockImplementationOnce(() => new Promise<void>(resolve => { release = resolve; }));
  const { result } = renderHook(usePlaylist, { wrapper });
  await waitFor(() => expect(mocks.precache).toHaveBeenCalledTimes(1));
  let playing!: Promise<void>;
  act(() => { playing = result.current.play("c"); });
  await act(async () => { release(); await playing; });
  await waitFor(() => expect(mocks.precache).toHaveBeenCalledTimes(3));
  expect(mocks.precache.mock.calls.map(call => call[0])).toEqual(["a","c","b"]);
  expect(result.current.currentId).toBe("c");
});

it("preloads outdated caches and leaves valid caches and cache-only songs alone", async () => {
  mocks.list.mockResolvedValue([
    {id:"a",name:"old source cache",midi_available:true,cache_available:true,cache_rebuild_required:true},
    {id:"b",name:"valid cache",midi_available:true,cache_available:true,cache_rebuild_required:false},
    {id:"c",name:"cache only",midi_available:false,cache_available:true,cache_rebuild_required:false},
  ]);
  renderHook(usePlaylist, { wrapper });
  await waitFor(() => expect(mocks.precache).toHaveBeenCalledOnce());
  expect(mocks.precache.mock.calls[0][0]).toBe("a");
});

it("keeps background status through refresh and the next job, and clears it only when the queue drains", async () => {
  let finishFirst!: () => void, finishSecond!: () => void, finishRefresh!: (value: typeof items) => void;
  const oldItems = items.map(i => ({...i,midi_available:true,cache_available:false}));
  mocks.list.mockResolvedValue(oldItems);
  mocks.precache.mockImplementationOnce(() => new Promise<void>(resolve => {finishFirst=resolve;}));
  mocks.precache.mockImplementationOnce(() => new Promise<void>(resolve => {finishSecond=resolve;}));
  const observed: string[] = [];
  const {result} = renderHook(() => { const value=usePlaylist(); observed.push(value.backgroundProgress); return value; },{wrapper});
  await waitFor(() => expect(result.current.backgroundProgress).toContain("A"));
  const firstStatus = observed.length - 1;
  mocks.list.mockImplementationOnce(() => new Promise<typeof items>(resolve => {finishRefresh=resolve;}));
  await act(async () => {finishFirst();});
  expect(result.current.backgroundProgress).toContain("A");
  expect(mocks.precache).toHaveBeenCalledOnce();
  await act(async () => {finishRefresh(oldItems);});
  await waitFor(() => expect(result.current.backgroundProgress).toContain("B"));
  expect(observed.slice(firstStatus).every(Boolean)).toBe(true);
  await act(async () => {finishSecond();});
  await waitFor(() => expect(result.current.backgroundProgress).toBe(""));
  expect(mocks.precache).toHaveBeenCalledTimes(2);
});

it("continues after a failed cache job and releases background state after the last job", async () => {
  let failFirst!: (error: Error) => void, finishSecond!: () => void;
  mocks.list.mockResolvedValue(items.map(i => ({...i,midi_available:true,cache_available:false})));
  mocks.precache.mockImplementationOnce(() => new Promise<void>((_,reject) => {failFirst=reject;}));
  mocks.precache.mockImplementationOnce(() => new Promise<void>(resolve => {finishSecond=resolve;}));
  const {result} = renderHook(usePlaylist,{wrapper});
  await waitFor(() => expect(result.current.backgroundProgress).toContain("A"));
  await act(async () => {failFirst(new Error("broken MIDI"));});
  await waitFor(() => expect(result.current.backgroundProgress).toContain("B"));
  await act(async () => {finishSecond();});
  await waitFor(() => expect(result.current.backgroundProgress).toBe(""));
});
