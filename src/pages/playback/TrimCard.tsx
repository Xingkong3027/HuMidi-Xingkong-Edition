import { t, translateNode } from "../../lib/i18n";
import { Card } from "../../components/Card";
import { ToggleSwitch } from "../../components/ToggleSwitch";
import { NumberInput } from "../../components/Field";
import type { PlaybackConfig } from "./types";

export function TrimCard({
  config,
  onChange,
}: {
  config: PlaybackConfig;
  onChange: (patch: Partial<PlaybackConfig>) => void;
}) {
  const manual = config.trim_enabled && !config.trim_auto;
  const invalid =
    manual &&
    config.trim_end_seconds > 0 &&
    config.trim_end_seconds <= config.trim_start_seconds;
  return (
    <Card title={t("曲目裁剪")} className="trim-card">
      <div className="control-row">
        <ToggleSwitch
          checked={config.trim_enabled}
          onChange={(v) => onChange({ trim_enabled: v })}
          label={t("启用裁剪")}
        />
      </div>
      <div className="control-row">
        <ToggleSwitch
          disabled={!config.trim_enabled}
          checked={config.trim_auto}
          onChange={(v) => onChange({ trim_auto: v })}
          label={t("自动移除首尾空白")}
        />
      </div>
      <div className="trim-card__range">
        <label>
          {t("开始（秒）")}
          <NumberInput
            aria-label={t("裁剪开始秒数")}
            disabled={!manual}
            min={0}
            step={0.1}
            value={config.trim_start_seconds}
            onChange={(e) =>
              onChange({
                trim_start_seconds: Math.max(0, Number(e.target.value)),
              })
            }
          />
        </label>
        <span aria-hidden="true">{t("→")}</span>
        <label>
          {t("结束（秒）")}
          <NumberInput
            aria-label={t("裁剪结束秒数")}
            disabled={!manual}
            min={0}
            step={0.1}
            value={config.trim_end_seconds}
            onChange={(e) =>
              onChange({
                trim_end_seconds: Math.max(0, Number(e.target.value)),
              })
            }
          />
        </label>
      </div>
      <span
        className={invalid ? "trim-card__error" : "page-placeholder__hint"}
        role={invalid ? "alert" : undefined}
      >
        {translateNode(
          invalid
            ? "结束时间必须大于开始时间。"
            : "按当前速度计算时间。结束设为 0 表示曲尾；自动模式按每首歌所选音轨独立计算。",
        )}
      </span>
    </Card>
  );
}
