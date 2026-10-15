import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TrackSelectionDialog } from "./TrackSelectionDialog";
const tracks = [
  { index: 0, name: "Piano", instrument: "Piano", noteCount: 12, channel: 0 },
  { index: 1, name: "Drums", instrument: "Drums", noteCount: 6, channel: 9 },
];
describe("track selection", () => {
  it("restores the song's selection and hand assignment", () => {
    const confirm = vi.fn();
    render(
      <TrackSelectionDialog
        tracks={tracks}
        initialSelection={[{ index: 0, role: "Left Hand" }]}
        onCancel={() => {}}
        onConfirm={confirm}
      />,
    );
    expect(
      (screen.getAllByRole("combobox")[0] as HTMLSelectElement).value,
    ).toBe("Left Hand");
    fireEvent.click(screen.getByText(/^(OK|确定)$/));
    expect(confirm).toHaveBeenCalledWith([{ index: 0, role: "Left Hand" }]);
  });
  it("does not accept an empty selection", () => {
    render(
      <TrackSelectionDialog
        tracks={tracks}
        initialSelection={[]}
        onCancel={() => {}}
        onConfirm={() => {}}
      />,
    );
    expect(screen.getByText(/^(OK|确定)$/)).toBeDisabled();
  });
});
