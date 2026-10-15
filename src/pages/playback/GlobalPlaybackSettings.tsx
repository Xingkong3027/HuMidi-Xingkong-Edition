import { t } from "../../lib/i18n";
import { Card } from "../../components/Card";
import { ToggleSwitch } from "../../components/ToggleSwitch";
import { useAppSettings } from "../../state/AppSettingsContext";

export function GlobalPlaybackSettings() {
  const settings = useAppSettings();
  return (
    <div className="playback-globals">
      <p className="page-placeholder__hint">{t("自动保存，适用于所有曲目。修改后于下次开始演奏生效；当前会话和暂停后继续保持原设置。无需重新导入 MIDI。")}</p>
      <Card title={t("演奏开始")}>
        <ToggleSwitch checked={settings.releasePedalOnStart} onChange={settings.setReleasePedalOnStart} label={t("开始时释放空格（踏板）")} />
        <p className="page-placeholder__hint">{t("开始输出前释放一次踏板，不影响歌曲后续踏板事件。")}</p>
      </Card>
      <Card title={t("窗口焦点")}>
        <ToggleSwitch checked={settings.autoFocusRoblox} onChange={settings.setAutoFocusRoblox} label={t("播放时自动切换到 Roblox 窗口")} />
        <p className="page-placeholder__hint">{t("默认关闭。开始演奏或手动继续时，在倒计时后尝试切换一次；找不到游戏窗口或切换失败则暂停并提示。演奏中不会反复抢回焦点。")}</p>
        <ToggleSwitch checked={settings.pauseOnAppFocus} onChange={settings.setPauseOnAppFocus} label={t("本窗口获得焦点时暂停演奏")} />
        <p className="page-placeholder__hint">{t("默认关闭。开启后，开始演奏会先完成自动切换，再检查本窗口是否有焦点；演奏中主动切回本窗口仍会暂停。关闭后进度继续，本窗口不接收演奏按键。")}</p>
      </Card>
      <Card title={t("演奏结束")}>
        <ToggleSwitch checked={settings.pauseAtEnd} onChange={settings.setPauseAtEnd} label={t("单曲试听结束后停留在曲尾")} />
        <p className="page-placeholder__hint">{t("开启后单曲试听在曲尾暂停，可拖回某段继续；直接播放会从头开始。歌单播放仍按播放模式继续，不会逐曲暂停。")}</p>
      </Card>
      <Card title={t("诊断")}>
        <ToggleSwitch checked={settings.debugOutput} onChange={settings.setDebugOutput} label={t("调试输出")} />
        <p className="page-placeholder__hint">{t("在调试页记录演奏会话使用的全局设置，不改变音符、踏板或演奏时序。")}</p>
      </Card>
    </div>
  );
}
