import { t, translateNode } from "../../lib/i18n";
import { Card } from "../../components/Card";
import { Select, NumberInput } from "../../components/Field";
import { Button } from "../../components/Button";
import { newRandomSeed } from "./humanization";
import type { PlaybackConfig } from "./types";

export function HumanizationPolicyCard({
  config,
  onChange,
}: {
  config: PlaybackConfig;
  onChange: (patch: Partial<PlaybackConfig>) => void;
}) {
  const enabled =
    config.humanization_mode !== "disabled" && config.humanization_on;
  return (
    <Card title={t("模拟人演奏")} className="humanization-policy">
      <div className="control-row">
        <label className="control-row__label" htmlFor="humanization-mode">
          {t("配置来源")}
        </label>
        <Select
          id="humanization-mode"
          value={config.humanization_mode}
          onChange={(e) =>
            onChange({
              humanization_mode: e.target
                .value as PlaybackConfig["humanization_mode"],
            })
          }
        >
          <option value="disabled">{t("禁用")}</option>
          <option value="global">{t("使用全局配置")}</option>
          <option value="individual">{t("单独配置当前曲目")}</option>
        </Select>
      </div>
      <div className="control-row">
        <label className="control-row__label" htmlFor="humanization-random">
          {t("演奏随机性")}
        </label>
        <Select
          id="humanization-random"
          disabled={!enabled}
          value={config.humanization_seed_mode}
          onChange={(e) =>
            onChange({
              humanization_seed_mode: e.target
                .value as PlaybackConfig["humanization_seed_mode"],
            })
          }
        >
          <option value="dynamic">{t("动态 · 每次重新演奏")}</option>
          <option value="fixed_random">{t("固定 · 自动生成种子")}</option>
          <option value="fixed_custom">{t("固定 · 自定义种子")}</option>
        </Select>
      </div>
      <div className="control-row">
        <label className="control-row__label" htmlFor="humanization-seed">
          {t("随机种子")}
        </label>
        <NumberInput
          id="humanization-seed"
          min={0}
          max={Number.MAX_SAFE_INTEGER}
          step={1}
          disabled={
            !enabled || config.humanization_seed_mode !== "fixed_custom"
          }
          value={config.random_seed ?? ""}
          placeholder={t("动态")}
          onChange={(e) =>
            onChange({
              random_seed: Math.min(
                Number.MAX_SAFE_INTEGER,
                Math.max(0, Math.floor(Number(e.target.value))),
              ),
            })
          }
        />
        {translateNode(
          enabled && config.humanization_seed_mode === "fixed_random" && (
            <Button onClick={() => onChange({ random_seed: newRandomSeed() })}>
              {t("换一个")}
            </Button>
          ),
        )}
      </div>
      <span className="page-placeholder__hint">
        {translateNode(
          config.humanization_mode === "global"
            ? "详细参数来自「设置 → 演奏预设」，下次编译时生效。"
            : enabled
              ? "固定种子让相同曲目与设置产生可重复的演奏。修改演奏参数会更新自动种子。"
              : "保留详细参数，关闭所有模拟人演奏效果。",
        )}
      </span>
    </Card>
  );
}
