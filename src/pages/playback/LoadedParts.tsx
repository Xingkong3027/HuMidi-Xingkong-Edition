import { t, translateNode } from "../../lib/i18n";
import { ListIcon, NotePencilIcon, SmileyMehIcon } from "@phosphor-icons/react";
import { PartCard } from "./PartCard";
import { Button } from "../../components/Button";
import { Label } from "../../components/Label";

export interface TrackPart {
  name: string;
  meta: string;
}

interface LoadedPartsProps {
  parts: TrackPart[];
  pedalCount: number;
  onEditSelection: () => void;
  editEnabled: boolean;
}

export function LoadedParts({
  parts,
  pedalCount,
  onEditSelection,
  editEnabled,
}: LoadedPartsProps) {
  return (
    <aside className="side-panel">
      <div className="side-panel__handle">
        <ListIcon weight="duotone" />
      </div>
      <div className="side-panel__content">
        <div className="side-panel__head">
          <Label className="card__title">{t("LOADED PARTS")}</Label>
          <Button
            variant="icon"
            subtle
            disabled={!editEnabled}
            onClick={onEditSelection}
            title={t("修改音轨选择")}
          >
            <NotePencilIcon weight="duotone" />
          </Button>
        </div>
        <div className="loaded-parts">
          <div className="loaded-parts__pedal">
            <PartCard title={t("踏板")} meta={`${pedalCount} 个事件`} />
          </div>
          <div className="loaded-parts__cards">
            {translateNode(
              parts.length === 0 ? (
                <div className="loaded-parts__empty">
                  <SmileyMehIcon weight="duotone" />
                  <Label className="loaded-parts__placeholder">
                    {t("尚未载入曲目。")}
                  </Label>
                </div>
              ) : (
                parts.map((p, i) => (
                  <PartCard key={i} title={p.name} meta={p.meta} />
                ))
              ),
            )}
          </div>
        </div>
      </div>
    </aside>
  );
}
