import { t as tr, translateNode } from "../lib/i18n";
import { useState } from "react";
import { Modal } from "../components/Modal";
import { Button } from "../components/Button";
import { Checkbox, Select } from "../components/Field";

export type HandRole = "Auto-Detect" | "Left Hand" | "Right Hand";

export interface TrackRow {
  index: number;
  name: string;
  instrument: string;
  noteCount: number;
  channel: number;
}

interface TrackSelectionRowState {
  included: boolean;
  role: HandRole;
}

interface TrackSelectionDialogProps {
  tracks: TrackRow[];
  onCancel: () => void;
  onConfirm: (selection: { index: number; role: HandRole }[]) => void;
  initialSelection?: { index: number; role: HandRole }[];
  title?: string;
}

export function TrackSelectionDialog({
  tracks,
  onCancel,
  onConfirm,
  initialSelection,
  title,
}: TrackSelectionDialogProps) {
  const [rows, setRows] = useState<Record<number, TrackSelectionRowState>>(() =>
    Object.fromEntries(
      tracks.map((t) => [
        t.index,
        {
          included: initialSelection
            ? initialSelection.some((s) => s.index === t.index)
            : t.channel !== 9,
          role:
            initialSelection?.find((s) => s.index === t.index)?.role ??
            ("Auto-Detect" as HandRole),
        },
      ]),
    ),
  );

  function updateRow(index: number, patch: Partial<TrackSelectionRowState>) {
    setRows((r) => ({ ...r, [index]: { ...r[index], ...patch } }));
  }

  return (
    <Modal
      title={title ?? tr("Select Tracks")}
      onClose={onCancel}
      width={720}
      height={400}
      footer={
        <>
          <Button onClick={onCancel}>{tr("Cancel")}</Button>
          <Button
            variant="accent"
            disabled={!Object.values(rows).some((row) => row.included)}
            onClick={() =>
              onConfirm(
                tracks
                  .filter((t) => rows[t.index].included)
                  .map((t) => ({ index: t.index, role: rows[t.index].role })),
              )
            }
          >
            {tr("OK")}
          </Button>
        </>
      }
    >
      <p className="track-selection__info">
        {tr(
          "Choose which tracks to play and override hand assignment where needed. Drum tracks are excluded by default.",
        )}
      </p>
      <table className="track-selection__table">
        <thead>
          <tr>
            <th>{tr("Play")}</th>
            <th>{tr("Track Name")}</th>
            <th>{tr("Instrument")}</th>
            <th>{tr("Notes")}</th>
            <th>{tr("Hand Assignment")}</th>
          </tr>
        </thead>
        <tbody>
          {translateNode(
            tracks.map((t) => (
              <tr key={t.index}>
                <td>
                  <Checkbox
                    checked={rows[t.index].included}
                    onChange={(e) =>
                      updateRow(t.index, { included: e.target.checked })
                    }
                  />
                </td>
                <td>{t.name}</td>
                <td>{translateNode(t.instrument)}</td>
                <td>{translateNode(t.noteCount)}</td>
                <td>
                  <Select
                    value={rows[t.index].role}
                    onChange={(e) =>
                      updateRow(t.index, { role: e.target.value as HandRole })
                    }
                  >
                    <option value="Auto-Detect">{tr("Auto-Detect")}</option>
                    <option value="Left Hand">{tr("Left Hand")}</option>
                    <option value="Right Hand">{tr("Right Hand")}</option>
                  </Select>
                </td>
              </tr>
            )),
          )}
        </tbody>
      </table>
    </Modal>
  );
}
