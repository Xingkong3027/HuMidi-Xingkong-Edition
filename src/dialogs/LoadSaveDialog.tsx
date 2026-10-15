import { ask, promptText } from "../lib/appDialogs";
import { t, translateNode } from "../lib/i18n";
import { useMemo, useState } from "react";
import { Modal } from "../components/Modal";
import { Button } from "../components/Button";
import { Label } from "../components/Label";

export interface SaveEntry {
  filepath: string;
  sourceMidiName: string;
  saveName: string;
  createdAt: string;
  tempo: number;
  pedalStyle: string;
  use88Key: boolean;
  humanization: string[];
}

interface LoadSaveDialogProps {
  saves: SaveEntry[];
  initialSelected?: string | null;
  onCancel: () => void;
  onLoad: (save: SaveEntry) => void;
  onRename: (filepath: string, newName: string) => void;
  onDelete: (filepath: string) => void;
}

export function LoadSaveDialog({
  saves,
  initialSelected = null,
  onCancel,
  onLoad,
  onRename,
  onDelete,
}: LoadSaveDialogProps) {
  const [selected, setSelected] = useState<string | null>(initialSelected);

  const groups = useMemo(() => {
    const map = new Map<string, SaveEntry[]>();
    for (const s of saves) {
      const list = map.get(s.sourceMidiName) ?? [];
      list.push(s);
      map.set(s.sourceMidiName, list);
    }
    return Array.from(map.entries());
  }, [saves]);

  const selectedSave = saves.find((s) => s.filepath === selected) ?? null;

  return (
    <Modal
      title={t("Load Save")}
      onClose={onCancel}
      width={820}
      height={520}
      footer={
        <>
          <Button
            disabled={!selectedSave}
            onClick={async () => {
              if (!selectedSave) return;
              const name = await promptText(t("输入新的名称"), selectedSave.saveName);
              if (name !== null && name.trim()) onRename(selectedSave.filepath, name.trim());
            }}
          >
            {t("Rename")}
          </Button>
          <Button
            disabled={!selectedSave}
            onClick={async () => {
              if (selectedSave && await ask(`${t("删除演奏存档")} “${selectedSave.saveName}”？`, { title:t("删除存档"), okLabel:t("删除") })) onDelete(selectedSave.filepath);
            }}
          >
            {t("Delete")}
          </Button>
          <Button onClick={onCancel}>{t("Cancel")}</Button>
          <Button
            variant="accent"
            disabled={!selectedSave}
            onClick={() => selectedSave && onLoad(selectedSave)}
          >
            {t("Load")}
          </Button>
        </>
      }
    >
      <div className="load-save-dialog">
        <div className="load-save-dialog__tree">
          {translateNode(
            groups.length === 0 && (
              <span className="load-save-dialog__empty">
                {t("No saves found.")}
              </span>
            ),
          )}
          {translateNode(
            groups.map(([midiName, entries]) => (
              <div key={midiName} className="load-save-dialog__group">
                <Label className="load-save-dialog__group-label">
                  {translateNode(midiName)}
                </Label>
                {translateNode(
                  entries.map((s) => (
                    <Button
                      key={s.filepath}
                      variant="item"
                      active={selected === s.filepath}
                      onClick={() => setSelected(s.filepath)}
                    >
                      <Label>{translateNode(s.saveName)}</Label>
                    </Button>
                  )),
                )}
              </div>
            )),
          )}
        </div>
        <div className="load-save-dialog__details">
          {translateNode(
            selectedSave ? (
              <>
                <div className="load-save-dialog__details-title">
                  {translateNode(selectedSave.sourceMidiName)}
                </div>
                <div className="load-save-dialog__details-meta">
                  {translateNode(selectedSave.createdAt)}
                </div>
                <div className="load-save-dialog__details-grid">
                  <span>{t("Tempo")}</span>
                  <span>
                    {translateNode(selectedSave.tempo)}
                    {t("%")}
                  </span>
                  <span>{t("Pedal Style")}</span>
                  <span>{translateNode(selectedSave.pedalStyle)}</span>
                  <span>{t("88-Key")}</span>
                  <span>
                    {translateNode(selectedSave.use88Key ? "Yes" : "No")}
                  </span>
                </div>
                <div className="load-save-dialog__details-subhead">
                  {t("Humanization")}
                </div>
                {translateNode(
                  selectedSave.humanization.length === 0 ? (
                    <span className="load-save-dialog__placeholder">
                      {t("None selected")}
                    </span>
                  ) : (
                    <ul className="load-save-dialog__hum-list">
                      {translateNode(
                        selectedSave.humanization.map((h) => (
                          <li key={h}>{translateNode(h)}</li>
                        )),
                      )}
                    </ul>
                  ),
                )}
              </>
            ) : (
              <span className="load-save-dialog__placeholder">
                {t("Select a save to see its details.")}
              </span>
            ),
          )}
        </div>
      </div>
    </Modal>
  );
}
