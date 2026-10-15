import { t, translateNode } from "../../lib/i18n";
import { useEffect, useState } from "react";
import { Card } from "../../components/Card";
import {
  ArrowClockwiseIcon,
  ArrowCounterClockwiseIcon,
  PencilSimpleIcon,
} from "@phosphor-icons/react";
import { Select } from "../../components/Field";
import { Button } from "../../components/Button";
import { ThresholdEditorDialog } from "../../dialogs/ThresholdEditorDialog";
import type { PedalConfidence } from "../../lib/pedalPreview";
import type { ThresholdCurves } from "../../lib/thresholdCurve";
import { ThresholdChart } from "./ThresholdChart";
import { ThresholdLegend } from "./ThresholdLegend";

export interface PedalAiStats {
  avgDur: number;
  minDur: number;
  maxDur: number;
  pressesPerMin: number;
}

interface PedalAiCardProps {
  hasThresholds: boolean;
  generateEnabled: boolean;
  curves: ThresholdCurves;
  stats: PedalAiStats | null;
  confidence?: PedalConfidence | null;
  mode?: "auto" | "custom";
  pedalIntervals?: readonly (readonly [number, number])[];
  onModeChange?: (mode: "auto" | "custom") => void;
  onGenerate: () => void;
  onCurvesChange: (curves: ThresholdCurves) => void;
  onReset: () => void;
}

const CHATTER_MAX_PRESSES_PER_MIN = 45;
const CHATTER_MIN_AVG_HOLD = 0.25;
const CHATTER_MIN_HOLD = 0.08;
const SPARSE_MIN_PRESSES_PER_MIN = 3;
const SPARSE_MAX_HOLD = 12;
const SPARSE_MAX_HOLD_RATIO = 8;

function diagnose(stats: PedalAiStats): string | null {
  const isChattering =
    stats.pressesPerMin > CHATTER_MAX_PRESSES_PER_MIN ||
    stats.avgDur < CHATTER_MIN_AVG_HOLD ||
    stats.minDur < CHATTER_MIN_HOLD;
  if (isChattering) return "⚠ 踏板切换较频繁";
  const isSparse =
    stats.pressesPerMin < SPARSE_MIN_PRESSES_PER_MIN ||
    stats.maxDur > SPARSE_MAX_HOLD ||
    (stats.avgDur > 0 && stats.maxDur / stats.avgDur > SPARSE_MAX_HOLD_RATIO);
  return isSparse ? "⚠ 踏板持续较长或次数较少" : null;
}

export function PedalAiCard({
  hasThresholds,
  generateEnabled,
  curves,
  stats,
  confidence = null,
  mode = "custom",
  pedalIntervals,
  onModeChange,
  onGenerate,
  onCurvesChange,
  onReset,
}: PedalAiCardProps) {
  const warning = stats ? diagnose(stats) : null;
  const [editorOpen, setEditorOpen] = useState(false);

  useEffect(() => {
    if (!confidence) setEditorOpen(false);
  }, [confidence]);

  return (
    <>
      <Card
        title={t("PedalAI 踏板")}
        titleButtons={
          hasThresholds && (
            <>
              {translateNode(
                warning && (
                  <span className="pedal-ai-card__warning">
                    {translateNode(warning)}
                  </span>
                ),
              )}
              {translateNode(
                confidence && (
                  <Button
                    variant="icon"
                    subtle
                    onClick={() => { onModeChange?.("custom"); setEditorOpen(true); }}
                    title={t("编辑阈值曲线")}
                  >
                    <PencilSimpleIcon weight="duotone" />
                  </Button>
                ),
              )}
              <Button
                variant="icon"
                subtle
                danger
                onClick={onReset}
                title={t("重置")}
              >
                <ArrowCounterClockwiseIcon weight="duotone" />
              </Button>
            </>
          )
        }
        className="pedal-ai-card"
      >
        <div className="control-row">
          <label htmlFor="pedal-ai-mode">{t("生成方式")}</label>
          <Select id="pedal-ai-mode" value={mode} onChange={(e) => onModeChange?.(e.target.value as "auto" | "custom")}>
            <option value="auto">{t("自动峰值")}</option>
            <option value="custom">{t("自定义阈值")}</option>
          </Select>
        </div>
        <p className="page-placeholder__hint">{t(mode === "auto" ? "自动分析 AI 置信度峰值；图中阴影表示实际踏板区间。" : "按下和抬起阈值决定踏板区间，可编辑曲线细调。")}</p>
        <p className="page-placeholder__hint">{t("相同音符与计算模式会复用 AI 预测；切换生成方式或修改阈值无需重新分析。")}</p>
        {translateNode(
          !hasThresholds ? (
            <div className="pedal-ai-card__pre">
              <span className="pedal-ai-card__hint">
                {t(
                  "按下和抬起阈值决定模型在多大置信度下触发踏板，可按乐曲细调。",
                )}
              </span>
              <Button
                variant="accent"
                disabled={!generateEnabled}
                onClick={onGenerate}
              >
                {t("生成踏板事件")}
              </Button>
            </div>
          ) : (
            <div className="pedal-ai-card__post">
              <div className="pedal-ai-card__controls">
                <div className="pedal-ai-card__side">
                  {translateNode(
                    stats && (
                      <div className="pedal-ai-card__stats">
                        <span>
                          {t("平均持踏：")}
                          {translateNode(stats.avgDur.toFixed(2))}
                          {t("s")}
                        </span>
                        <span>
                          {t("最短持踏：")}
                          {translateNode(stats.minDur.toFixed(2))}
                          {t("s")}
                        </span>
                        <span>
                          {t("最长持踏：")}
                          {translateNode(stats.maxDur.toFixed(2))}
                          {t("s")}
                        </span>
                        <span>
                          {t("每分钟次数：")}
                          {translateNode(stats.pressesPerMin.toFixed(1))}
                        </span>
                      </div>
                    ),
                  )}
                  <Button className="pedal-ai-card__regen" onClick={onGenerate}>
                    <ArrowClockwiseIcon weight="duotone" />
                    {t("重新生成")}
                  </Button>
                </div>
              </div>
              {translateNode(
                confidence && (
                  <>
                    <ThresholdChart confidence={confidence} curves={curves} pedalIntervals={mode === "auto" ? pedalIntervals : undefined} showThresholds={mode === "custom"} />
                    {mode === "custom" && <ThresholdLegend />}
                  </>
                ),
              )}
            </div>
          ),
        )}
      </Card>
      {translateNode(
        editorOpen && confidence && (
          <ThresholdEditorDialog
            confidence={confidence}
            curves={curves}
            onCurvesChange={onCurvesChange}
            onClose={() => setEditorOpen(false)}
          />
        ),
      )}
    </>
  );
}
