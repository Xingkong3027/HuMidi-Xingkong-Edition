import { act, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { StatusIndicator } from "./StatusIndicator";
afterEach(() => vi.unstubAllGlobals());
describe("loading status animation", () => {
  it("rotates while preparing and shows the dashed loading glyph", () => {
    const frames: FrameRequestCallback[] = [];
    vi.stubGlobal("requestAnimationFrame", (fn: FrameRequestCallback) => {
      frames.push(fn);
      return frames.length;
    });
    vi.stubGlobal("cancelAnimationFrame", vi.fn());
    const { container, rerender } = render(
      <StatusIndicator status="unloaded" />,
    );
    rerender(<StatusIndicator status="loading" label="正在准备演奏…" />);
    const rotor = container.querySelector(
      ".status-indicator__spinner",
    ) as HTMLElement;
    act(() => frames.shift()!(10));
    const before = rotor.style.transform;
    act(() => frames.shift()!(40));
    expect(rotor.style.transform).not.toBe(before);
    expect(
      container.querySelector(".status-indicator")?.getAttribute("data-status"),
    ).toBe("loading");
  });
});
