import { t } from "../../lib/i18n";
import { useEffect } from "react";
import { Card } from "../../components/Card";
import { Button } from "../../components/Button";
import { ToggleSwitch } from "../../components/ToggleSwitch";
import { HumRow } from "../playback/HumRow";
import { usePersistedPatch } from "../../state/usePersistedState";
import { usePlaybackConfig } from "../../state/PlaybackConfigContext";
import { DEFAULT_CONFIG, type PlaybackConfig } from "../playback/types";
import {
  extractHumanization,
  getGlobalHumanization,
  newRandomSeed,
  setGlobalHumanization,
  type HumanizationPreset,
} from "../playback/humanization";

export function GlobalHumanizationSettings() {
  const { config, setConfig } = usePlaybackConfig();
  const [preset, setPreset] = usePersistedPatch<HumanizationPreset>(
    "global humanization",
    getGlobalHumanization(),
    {
      fromConfig: (saved) => {
        if (!saved.global_humanization) return undefined;
        setGlobalHumanization(saved.global_humanization);
        return getGlobalHumanization();
      },
      toPatch: (value) => ({ global_humanization: value }),
    },
  );
  useEffect(() => {
    setGlobalHumanization(preset);
  }, [preset]);
  function update(patch: Partial<PlaybackConfig>) {
    const next = {
      ...preset,
      ...extractHumanization({ ...DEFAULT_CONFIG, ...preset, ...patch }),
    };
    setGlobalHumanization(next);
    setPreset(next);
    setConfig((current) =>
      current.humanization_mode === "global"
        ? {
            ...current,
            ...next,
            random_seed:
              current.humanization_seed_mode === "fixed_random"
                ? newRandomSeed()
                : current.random_seed,
          }
        : current,
    );
  }
  return (
    <div className="settings-tab__display">
      <Card
        title={t("全局模拟人演奏预设")}
        footer={
          <div className="global-preset__actions">
            <Button onClick={() => update(extractHumanization(config))}>
              {t("使用当前曲目参数")}
            </Button>
            <Button onClick={() => update(extractHumanization(DEFAULT_CONFIG))}>
              {t("恢复默认")}
            </Button>
          </div>
        }
      >
        <p className="page-placeholder__hint">
          {t(
            "所有选择「使用全局配置」的曲目会在下次编译时应用本页参数。曲目自身的速度、裁剪和踏板设置保持独立。",
          )}
        </p>
        <div className="control-row">
          <ToggleSwitch
            checked={preset.simulate_hands}
            onChange={(v) => update({ simulate_hands: v })}
            label={t("模拟双手")}
          />
        </div>
        <div className="control-row">
          <ToggleSwitch
            checked={preset.enable_chord_roll}
            onChange={(v) => update({ enable_chord_roll: v })}
            label={t("和弦琶音")}
          />
        </div>
        <HumRow
          name="起音变化"
          desc={t("模拟轻微提前或延后触键")}
          checked={preset.vary_timing}
          onCheckedChange={(v) => update({ vary_timing: v })}
          min={0}
          max={0.1}
          value={preset.timing_variance}
          suffix=" 秒"
          decimals={3}
          onValueChange={(v) => update({ timing_variance: v })}
        />
        <HumRow
          name="持音变化"
          desc={t("控制音符持续时间")}
          checked={preset.vary_articulation}
          onCheckedChange={(v) => update({ vary_articulation: v })}
          min={50}
          max={100}
          value={preset.articulation}
          suffix="%"
          decimals={1}
          onValueChange={(v) => update({ articulation: v })}
        />
        <HumRow
          name="速度起伏"
          desc={t("随乐句自然加快或放慢")}
          checked={preset.enable_tempo_sway}
          onCheckedChange={(v) => update({ enable_tempo_sway: v })}
          min={0}
          max={0.1}
          value={preset.tempo_sway_intensity}
          suffix=" 秒"
          decimals={3}
          onValueChange={(v) => update({ tempo_sway_intensity: v })}
        />
        <div className="control-row">
          <ToggleSwitch
            checked={preset.invert_tempo_sway}
            disabled={!preset.enable_tempo_sway}
            onChange={(v) => update({ invert_tempo_sway: v })}
            label={t("反向起伏")}
          />
        </div>
        <HumRow
          name="双手偏移"
          desc={t("双手时序的偏移与校正")}
          checked={preset.enable_drift_correction}
          onCheckedChange={(v) => update({ enable_drift_correction: v })}
          min={0}
          max={100}
          value={preset.drift_decay_factor}
          suffix="%"
          decimals={1}
          onValueChange={(v) => update({ drift_decay_factor: v })}
        />
        <HumRow
          name="失误概率"
          desc={t("偶尔漏弹或误触邻近音符")}
          checked={preset.enable_mistakes}
          onCheckedChange={(v) => update({ enable_mistakes: v })}
          min={0}
          max={10}
          value={preset.mistake_chance}
          suffix="%"
          decimals={1}
          onValueChange={(v) => update({ mistake_chance: v })}
        />
      </Card>
    </div>
  );
}
