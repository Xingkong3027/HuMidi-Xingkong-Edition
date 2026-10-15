import { t, translateNode } from "../../lib/i18n";
import { Card } from "../../components/Card";
import { ArrowCounterClockwiseIcon } from "@phosphor-icons/react";
import { ToggleSwitch } from "../../components/ToggleSwitch";
import { PEDAL_MAPPING, type PlaybackConfig } from "./types";
import { Button } from "../../components/Button";
import { NumberInput, Select } from "../../components/Field";
import { Label } from "../../components/Label";

const PEDAL_LABELS = Object.keys(PEDAL_MAPPING);

interface PerformanceCardProps {
  config: PlaybackConfig;
  onChange: (patch: Partial<PlaybackConfig>) => void;
  onReset: () => void;
  midiPedalAvailable: boolean;
}

export function PerformanceCard({
  config,
  onChange,
  onReset,
  midiPedalAvailable,
}: PerformanceCardProps) {
  return (
    <Card
      title={t("演奏参数")}
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
      className="performance-card"
    >
      <div className="control-row">
        <div className="control-row__label">
          <Label>{t("踏板风格")}</Label>
        </div>
        <Select
          value={config.pedal_style}
          onChange={(e) => onChange({ pedal_style: e.target.value })}
        >
          {translateNode(
            PEDAL_LABELS.map((l) => (
              <option key={l} value={PEDAL_MAPPING[l]}>
                {translateNode(
                  {
                    None: "不使用",
                    PedalAI: "PedalAI 智能",
                    Adaptive: "自适应",
                    Rhythmic: "节奏型",
                    Harmonic: "和声型",
                  }[l] ?? l,
                )}
              </option>
            )),
          )}
        </Select>
      </div>
      <span className="performance-card__pedal-note">
        {t("推荐 PedalAI 或自适应，结合曲目风格生成踏板。")}
      </span>
      <div className="control-row">
        <ToggleSwitch
          checked={config.pedal_before_humanize}
          onChange={(v) => onChange({ pedal_before_humanize: v })}
          label={t("先生成踏板，再应用模拟人演奏")}
        />
      </div>

      <div className="control-row">
        <div className="control-row__label">
          <Label>{t("移调")}</Label>
        </div>
        <NumberInput
          min={-24}
          max={24}
          value={config.transpose}
          onChange={(e) => onChange({ transpose: Number(e.target.value) })}
        />
        <span className="control-row__suffix">{t("半音")}</span>
      </div>

      {translateNode(
        midiPedalAvailable && (
          <div className="control-row">
            <ToggleSwitch
              checked={config.use_midi_pedal}
              onChange={(v) => onChange({ use_midi_pedal: v })}
              label={t("使用 MIDI 原始踏板")}
            />
          </div>
        ),
      )}
    </Card>
  );
}
