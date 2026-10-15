import { t, translateNode } from "../../lib/i18n";
import { useMemo } from "react";
import { usePersistedState } from "../../state/usePersistedState";
import { parseOneOf } from "../../state/persistedParsers";
import { TabPage } from "../../components/TabPage";
import { Button } from "../../components/Button";
import { PerformanceCard } from "./PerformanceCard";
import { TrimCard } from "./TrimCard";
import { HumanizationPolicyCard } from "./HumanizationPolicyCard";
import { OptionsCard } from "./OptionsCard";
import { TempoCard } from "./TempoCard";
import { PedalAiCard } from "./PedalAiCard";
import { HumanizeMasterRow } from "./HumanizeMasterRow";
import { HumRow } from "./HumRow";
import { ApplyToast } from "./ApplyToast";
import { Card } from "../../components/Card";
import { usePlaybackConfig } from "../../state/PlaybackConfigContext";
import { usePlaybackEngine } from "../../state/PlaybackEngineContext";
import { usePlaylist } from "../../state/PlaylistContext";
import { Checkbox } from "../../components/Field";
const TABS = ["演奏设置", "模拟人演奏"] as const;
interface PlaybackTabProps {
  onEditTrackSelection: () => void;
  onSaveChanges: () => Promise<void>;
  onCancelChanges: () => void;
}
export function PlaybackTab({
  onEditTrackSelection,
  onSaveChanges,
  onCancelChanges,
}: PlaybackTabProps) {
  const [subTab, setSubTab] = usePersistedState("ui_editor_subtab", 0, {
    parse: parseOneOf([0, 1]),
  });
  const { config, updateConfig } = usePlaybackConfig();
  const engine = usePlaybackEngine();
  const playlist = usePlaylist();
  const editingSource = !!playlist.loadedId || playlist.pendingCount > 0;
  const humanizeAll = useMemo(
    () =>
      config.vary_timing &&
      config.vary_articulation &&
      config.simulate_hands &&
      config.enable_chord_roll &&
      config.enable_tempo_sway &&
      config.enable_drift_correction &&
      config.enable_mistakes,
    [config],
  );

  function toggleAll(v: boolean) {
    updateConfig({
      simulate_hands: v,
      enable_chord_roll: v,
      vary_timing: v,
      vary_articulation: v,
      enable_tempo_sway: v,
      enable_drift_correction: v,
      enable_mistakes: v,
    });
  }

  return (
    <div className="playback-tab">
      <div className="editor-scope-note">{t(editingSource ? playlist.loadedId ? "正在修改此曲目，保存后返回歌单。" : "正在设置导入草稿，加入歌单后保存。" : "全局默认设置 · 自动保存，仅用于之后新导入的曲目。")}</div>
      {editingSource && <div className="editor-track-row">
        <span>
          {t("音轨选择")} · {engine.selectedTracksInfo.length} {t("条音轨")}
        </span>
        <Button disabled={!engine.tracks.length} onClick={onEditTrackSelection}>
          {t("修改音轨选择")}
        </Button>
      </div>}
      <TabPage tabs={TABS} active={subTab} onChange={setSubTab}>
        {" "}
        {translateNode(
          subTab === 0 && (
            <div className="playback-tab__playback-page">
              {" "}
              <div className="playback-tab__two-col">
                {" "}
                <PerformanceCard
                  config={config}
                  onChange={updateConfig}
                  onReset={() =>
                    updateConfig({
                      transpose: 0,
                      pedal_style: "ai",
                      pedal_before_humanize: true,
                    })
                  }
                  midiPedalAvailable={editingSource && !!engine.midiFilePath}
                />{" "}
                <OptionsCard
                  config={config}
                  onChange={updateConfig}
                  onReset={() =>
                    updateConfig({
                      use_88_key_layout: false,
                      countdown: true,
                      release_pedal_on_start: false,
                      countdown_seconds: 3,
                      auto_pause: true,
                      performance_optimization: false,
                      debug_mode: false,
                    })
                  }
                />{" "}
              </div>{" "}
              <TrimCard config={config} onChange={updateConfig} />{" "}
              <TempoCard
                tempo={config.tempo}
                originalBpm={editingSource ? engine.originalBpm : 0}
                onTempoChange={(v) => updateConfig({ tempo: v })}
              />{" "}
              {(config.pedal_style === "ai" ||
                config.pedal_style === "hybrid") &&
                !config.use_midi_pedal && (
                  <PedalAiCard
                    hasThresholds={
                      editingSource && engine.hasCompiledPedal && engine.aiCurves !== null
                    }
                    confidence={editingSource ? engine.pedalConfidence : null}
                    generateEnabled={editingSource && 
                      (engine.selectedTracksInfo.length > 0 ||
                        !!engine.sheetSource) &&
                      !engine.isPreparing &&
                      !engine.isGeneratingPedal
                    }
                    curves={{
                      on: config.pedal_curve_on,
                      off: config.pedal_curve_off,
                    }}
                    mode={config.pedal_ai_mode}
                    pedalIntervals={engine.pedalIntervals}
                    onModeChange={(mode) => updateConfig({ pedal_ai_mode: mode })}
                    stats={engine.aiStats}
                    onGenerate={engine.generatePedal}
                    onCurvesChange={(curves) =>
                      updateConfig({
                        pedal_ai_mode: "custom",
                        pedal_curve_on: curves.on,
                        pedal_curve_off: curves.off,
                      })
                    }
                    onReset={() => updateConfig({ pedal_ai_mode: "auto", pedal_curve_on: [], pedal_curve_off: [] })}
                  />
                )}{" "}
            </div>
          ),
        )}{" "}
        {translateNode(
          subTab === 1 && (
            <div className="playback-tab__humanize-page">
              <HumanizationPolicyCard config={config} onChange={updateConfig} />
              <fieldset
                className="humanization-details"
                disabled={
                  config.humanization_mode !== "individual" ||
                  !config.humanization_on
                }
              >
                {" "}
                <HumanizeMasterRow
                  humanizeAll={humanizeAll}
                  simulateHands={config.simulate_hands}
                  chordRoll={config.enable_chord_roll}
                  onHumanizeAllChange={toggleAll}
                  onSimulateHandsChange={(v) =>
                    updateConfig({ simulate_hands: v })
                  }
                  onChordRollChange={(v) =>
                    updateConfig({ enable_chord_roll: v })
                  }
                  onReset={() =>
                    updateConfig({
                      simulate_hands: false,
                      enable_chord_roll: false,
                    })
                  }
                />{" "}
                <Card title={t("节奏与触键")}>
                  {" "}
                  <HumRow
                    name="起音变化"
                    desc={t("音符略早或略晚开始，模拟真人触键")}
                    checked={config.vary_timing}
                    onCheckedChange={(v) => updateConfig({ vary_timing: v })}
                    min={0}
                    max={0.1}
                    value={config.timing_variance}
                    suffix=" s"
                    decimals={3}
                    onValueChange={(v) => updateConfig({ timing_variance: v })}
                  />{" "}
                  <HumRow
                    name="持音变化"
                    desc={t("让部分音符保持稍长或稍短时间")}
                    checked={config.vary_articulation}
                    onCheckedChange={(v) =>
                      updateConfig({ vary_articulation: v })
                    }
                    min={50}
                    max={100}
                    value={config.articulation}
                    suffix="%"
                    decimals={1}
                    onValueChange={(v) => updateConfig({ articulation: v })}
                  />{" "}
                  <HumRow
                    name="速度起伏"
                    desc={t("随乐句自然加快或放慢")}
                    checked={config.enable_tempo_sway}
                    onCheckedChange={(v) =>
                      updateConfig({ enable_tempo_sway: v })
                    }
                    min={0}
                    max={0.1}
                    value={config.tempo_sway_intensity}
                    suffix=" s"
                    decimals={3}
                    onValueChange={(v) =>
                      updateConfig({ tempo_sway_intensity: v })
                    }
                  />{" "}
                  <div className="check-pair">
                    {" "}
                    <label className="check-pair__inline">
                      {" "}
                      <Checkbox
                        disabled={!config.enable_tempo_sway}
                        checked={config.invert_tempo_sway}
                        onChange={(e) =>
                          updateConfig({ invert_tempo_sway: e.target.checked })
                        }
                      />
                      {t("反向起伏")}
                    </label>{" "}
                    <span className="check-pair__desc">
                      {t("反转速度起伏的方向")}
                    </span>{" "}
                  </div>{" "}
                </Card>{" "}
                <Card title={t("双手与自然误差")}>
                  {" "}
                  <HumRow
                    name="双手偏移"
                    desc={t("为双手加入细微的节奏偏移")}
                    checked={config.enable_drift_correction}
                    onCheckedChange={(v) =>
                      updateConfig({ enable_drift_correction: v })
                    }
                    min={0}
                    max={100}
                    value={config.drift_decay_factor}
                    suffix="%"
                    decimals={1}
                    onValueChange={(v) =>
                      updateConfig({ drift_decay_factor: v })
                    }
                  />{" "}
                  <HumRow
                    name="失误概率"
                    desc={t("偶尔漏弹或误触邻近音符")}
                    checked={config.enable_mistakes}
                    onCheckedChange={(v) =>
                      updateConfig({ enable_mistakes: v })
                    }
                    min={0}
                    max={10}
                    value={config.mistake_chance}
                    suffix="%"
                    decimals={1}
                    onValueChange={(v) => updateConfig({ mistake_chance: v })}
                  />{" "}
                </Card>
              </fieldset>{" "}
            </div>
          ),
        )}
      </TabPage>

      <ApplyToast
        visible={!!playlist.loadedId && (playlist.settingsDirty || engine.configDirty)}
        onApply={() => {
          void onSaveChanges();
        }}
        onDiscard={() => {
          onCancelChanges();
        }}
        savingSong={!!playlist.loadedId}
        disabled={
          playlist.busy || engine.isPreparing || engine.isGeneratingPedal
        }
      />
    </div>
  );
}
