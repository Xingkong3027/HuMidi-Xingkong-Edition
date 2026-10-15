import { t } from "../lib/i18n";
import { MusicNoteIcon, XSquareIcon } from "@phosphor-icons/react";
import { Button } from "./Button";
import { usePlaybackEngine } from "../state/PlaybackEngineContext";
import { Label } from "./Label";
export function FileHeader() {
  const engine = usePlaybackEngine();
  return (
    <div className="file-header">
      <div className="file-header__tile">
        <MusicNoteIcon weight="duotone" />
      </div>
      <div className="file-header__info">
        <Label className="file-header__name" slide>
          {engine.fileName || t("尚未载入曲目")}
        </Label>
        {engine.fileName && (
          <Label className="file-header__meta">
            {engine.sheetSource
              ? t("文本曲谱")
              : `${engine.selectedTracksInfo.length} ${t("条音轨")}`}
          </Label>
        )}
      </div>
      <Button
        variant="icon"
        subtle
        size="md"
        disabled={engine.isPreparing || engine.isGeneratingPedal}
        onClick={() => void engine.clearSong()}
        aria-label={t("清除曲目")}
      >
        <XSquareIcon weight="duotone" />
      </Button>
    </div>
  );
}
