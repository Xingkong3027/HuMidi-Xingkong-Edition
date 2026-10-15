import { beforeEach, expect, it, vi } from "vitest";
const mocks = vi.hoisted(() => ({ ask: vi.fn(), parse: vi.fn() }));
vi.mock("./appDialogs", () => ({ ask: mocks.ask }));
vi.mock("./tauri", () => ({ parseMidiStructure: mocks.parse }));
import { parseMidiWithRepair } from "./midiRepair";
beforeEach(() => vi.resetAllMocks());
it("valid and harmlessly padded MIDI bypass the repair dialog", async () => {
  mocks.parse.mockResolvedValue({ tracks: [] });
  expect((await parseMidiWithRepair("valid.mid")).clip).toBe(false);
  expect(mocks.ask).not.toHaveBeenCalled();
});
it("only authorized invalid channel data is reparsed with clipping", async () => {
  mocks.parse.mockRejectedValueOnce(new Error("MIDI_INVALID_DATA_BYTE"));
  mocks.parse.mockResolvedValueOnce({ tracks: [] });
  mocks.ask.mockResolvedValue(true);
  expect((await parseMidiWithRepair("bad.mid")).clip).toBe(true);
  expect(mocks.ask).toHaveBeenCalledOnce();
  expect(mocks.parse).toHaveBeenLastCalledWith("bad.mid", true);
});
it("cancelled repair does not parse clipped bytes", async () => {
  mocks.parse.mockRejectedValue(new Error("MIDI_INVALID_DATA_BYTE"));
  mocks.ask.mockResolvedValue(false);
  await expect(parseMidiWithRepair("bad.mid")).rejects.toThrow("已取消 MIDI 导入");
  expect(mocks.parse).toHaveBeenCalledOnce();
});
it("a truncated track is an error instead of a repair invitation", async () => {
  mocks.parse.mockRejectedValue(new Error("Truncated MIDI track."));
  await expect(parseMidiWithRepair("broken.mid")).rejects.toThrow("Truncated MIDI track");
  expect(mocks.ask).not.toHaveBeenCalled();
});
it("previously authorized songs still try valid bytes before repair", async () => {
  mocks.parse.mockResolvedValue({ tracks: [] });
  expect((await parseMidiWithRepair("valid.mid", true)).clip).toBe(false);
  expect(mocks.parse).toHaveBeenCalledOnce();
  expect(mocks.parse).toHaveBeenCalledWith("valid.mid");
  expect(mocks.ask).not.toHaveBeenCalled();
});
it("stored consent retries only invalid data without repeating the question", async () => {
  mocks.parse.mockRejectedValueOnce(new Error("MIDI_INVALID_DATA_BYTE"));
  mocks.parse.mockResolvedValueOnce({ tracks: [] });
  expect((await parseMidiWithRepair("authorized.mid", true)).clip).toBe(true);
  expect(mocks.parse).toHaveBeenLastCalledWith("authorized.mid", true);
  expect(mocks.ask).not.toHaveBeenCalled();
});
it("stored consent never repairs missing structure", async () => {
  mocks.parse.mockRejectedValue(new Error("Truncated MIDI track."));
  await expect(parseMidiWithRepair("broken.mid", true)).rejects.toThrow("Truncated MIDI track");
  expect(mocks.parse).toHaveBeenCalledOnce();
  expect(mocks.ask).not.toHaveBeenCalled();
});
