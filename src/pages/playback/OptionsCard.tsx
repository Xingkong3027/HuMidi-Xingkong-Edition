import { t } from "../../lib/i18n";
import { Card } from "../../components/Card";
import { ArrowCounterClockwiseIcon } from "@phosphor-icons/react";
import { ToggleSwitch } from "../../components/ToggleSwitch";
import type { PlaybackConfig } from "./types";
import { Button } from "../../components/Button";
import { SliderSpinbox } from "../../components/SliderSpinbox";

interface OptionsCardProps {
  config: PlaybackConfig;
  onChange: (patch: Partial<PlaybackConfig>) => void;
  onReset: () => void;
}

export function OptionsCard({ config, onChange, onReset }: OptionsCardProps) {
  return (
    <Card
      title={t("播放选项")}
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
      className="options-card"
    >
      <div className="control-row">
        <ToggleSwitch
          checked={config.use_88_key_layout}
          onChange={(v) => onChange({ use_88_key_layout: v })}
          label={t("88 键布局")}
        />
      </div>
      <div className="control-row">
        <ToggleSwitch
          checked={config.countdown}
          onChange={(v) => onChange({ countdown: v })}
          label={t("开始前倒计时")}
        />
      </div>
      <SliderSpinbox
        min={1}
        max={10}
        value={config.countdown_seconds}
        suffix=" 秒"
        disabled={!config.countdown}
        onChange={(v) => onChange({ countdown_seconds: Math.round(v) })}
      />
      <div className="control-row">
        <ToggleSwitch
          checked={config.performance_optimization}
          onChange={(v) => onChange({ performance_optimization: v })}
          label={t("密集 MIDI 性能优化")}
        />
      </div>
      <span className="page-placeholder__hint">
        {t("关闭时优先兼容原版演奏；开启后加快密集谱与 AI 计算，合并同一时刻重复按键，可能产生细微演奏差异。")}
      </span>
    </Card>
  );
}
