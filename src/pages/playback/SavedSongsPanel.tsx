import { t, translateNode } from "../../lib/i18n";
import { ArrowsClockwiseIcon, LayoutIcon } from "@phosphor-icons/react";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { Label } from "../../components/Label";

export interface SavedSong {
  filepath: string;
  saveName: string;
  songName: string;
  timeStr: string;
}

interface SavedSongsPanelProps {
  saves: SavedSong[];
  onRefresh: () => void;
  onOpenAll: () => void;
  onSaveClick: (save: SavedSong) => void;
}

export function SavedSongsPanel({
  saves,
  onRefresh,
  onOpenAll,
  onSaveClick,
}: SavedSongsPanelProps) {
  return (
    <Card
      title={t("演奏存档")}
      className="saved-songs-card"
      titleButtons={
        <>
          <Button variant="icon" subtle onClick={onRefresh} title={t("刷新")}>
            <ArrowsClockwiseIcon weight="duotone" />
          </Button>
          <Button
            variant="icon"
            subtle
            onClick={onOpenAll}
            title={t("全部存档")}
          >
            <LayoutIcon weight="duotone" />
          </Button>
        </>
      }
    >
      <div className="saved-songs__list">
        {translateNode(
          saves.length === 0 ? (
            <Label className="saved-songs__placeholder">
              {t("尚无演奏存档。")}
            </Label>
          ) : (
            saves.map((s) => (
              <div
                key={s.filepath}
                className="save-card"
                onClick={() => onSaveClick(s)}
              >
                <Label className="part-card__title">
                  {translateNode(s.saveName)}
                </Label>
                <Label className="part-card__meta">
                  {translateNode(s.songName)}
                </Label>
                {translateNode(
                  s.timeStr && (
                    <span className="save-card__time">
                      <Label>{translateNode(s.timeStr)}</Label>
                    </span>
                  ),
                )}
              </div>
            ))
          ),
        )}
      </div>
    </Card>
  );
}
