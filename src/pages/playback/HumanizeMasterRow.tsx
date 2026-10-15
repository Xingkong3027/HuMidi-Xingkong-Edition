import { t } from "../../lib/i18n";
import { Card } from "../../components/Card";
import { ArrowCounterClockwiseIcon } from "@phosphor-icons/react";
import { ToggleSwitch } from "../../components/ToggleSwitch";
import { Button } from "../../components/Button";
import { Label } from "../../components/Label";

interface HumanizeMasterRowProps {
  humanizeAll: boolean;
  simulateHands: boolean;
  chordRoll: boolean;
  onHumanizeAllChange: (v: boolean) => void;
  onSimulateHandsChange: (v: boolean) => void;
  onChordRollChange: (v: boolean) => void;
  onReset: () => void;
}

export function HumanizeMasterRow({
  humanizeAll,
  simulateHands,
  chordRoll,
  onHumanizeAllChange,
  onSimulateHandsChange,
  onChordRollChange,
  onReset,
}: HumanizeMasterRowProps) {
  return (
    <Card
      title={t("演奏细节")}
      titleButtons={
        <Button
          variant="icon"
          subtle
          danger
          onClick={onReset}
          title={t("重置")}
        >
          <ArrowCounterClockwiseIcon weight="duotone" />
        </Button>
      }
    >
      <div className="check-pair">
        <ToggleSwitch
          checked={humanizeAll}
          onChange={onHumanizeAllChange}
          label={t("启用所有细节")}
        />
        <Label className="check-pair__desc">
          {t("统一切换下面所有模拟选项")}
        </Label>
      </div>
      <div className="check-pair">
        <ToggleSwitch
          checked={simulateHands}
          onChange={onSimulateHandsChange}
          label={t("模拟双手")}
        />
        <Label className="check-pair__desc">
          {t("分别处理双手的细微时序")}
        </Label>
      </div>
      <div className="check-pair">
        <ToggleSwitch
          checked={chordRoll}
          onChange={onChordRollChange}
          label={t("和弦琶音")}
        />
        <Label className="check-pair__desc">
          {t("和弦各音依次轻微错开，模拟手指落键")}
        </Label>
      </div>
    </Card>
  );
}
