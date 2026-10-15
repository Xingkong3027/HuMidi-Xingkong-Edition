import { t, translateNode } from "../../lib/i18n";
import { useLanguage } from "../../state/LanguageContext";
import type { Language } from "../../lib/i18n";
import { GlobalHumanizationSettings } from "./GlobalHumanizationSettings";
import { ShortcutSettings } from "./ShortcutSettings";
import { useEffect, useState } from "react";
import { open as openDialog } from "../../lib/appDialogs";
import { openPath } from "@tauri-apps/plugin-opener";
import { Card } from "../../components/Card";
import { ToggleSwitch } from "../../components/ToggleSwitch";
import { SliderSpinbox } from "../../components/SliderSpinbox";
import { ThemeDialog } from "../../dialogs/ThemeDialog";
import { useTheme } from "../../theme/ThemeProvider";
import {
  MAX_VISIBLE_SAVES,
  MIN_VISIBLE_SAVES,
  useAppSettings,
} from "../../state/AppSettingsContext";
import { usePlaybackConfig } from "../../state/PlaybackConfigContext";
import { useLog } from "../../state/LogContext";
import { DEFAULT_CONFIG } from "../playback/types";
import { openUrl } from "@tauri-apps/plugin-opener";
import {
  isTauri,
  setSaveDir,
  getSaveDir,
  setMidiDir,
  getMidiDir,
  getThemesFile,
  setThemesDir,
  checkForUpdatesNow,
  getAppVersion,
  type UpdateCheckOutcome,
} from "../../lib/tauri";
import { Button } from "../../components/Button";
import { TabPage } from "../../components/TabPage";
import { Select, TextInput } from "../../components/Field";
import { Label } from "../../components/Label";
import { usePersistedState } from "../../state/usePersistedState";
import { parseOneOf } from "../../state/persistedParsers";

const NAV_ITEMS = [
  "Display",
  "Files",
  "Hotkey",
  "Performance",
  "System",
  "Privacy",
] as const;
const NAV_LABELS: Record<string, string> = {
  Display: "显示",
  Files: "文件",
  Hotkey: "快捷键",
  Performance: "演奏预设",
  System: "系统",
  Privacy: "隐私",
};

type SettingsNav = (typeof NAV_ITEMS)[number];

function DisplayPage() {
  const { language, setLanguage } = useLanguage();
  const settings = useAppSettings();
  const { themeName, setThemeName, themeNames } = useTheme();
  const [themeDialogOpen, setThemeDialogOpen] = useState(false);

  return (
    <div className="settings-tab__display">
      <Card title={t("语言")}>
        <div className="control-row">
          <Select
            value={language}
            onChange={(e) => setLanguage(e.target.value as Language)}
            aria-label={t("语言")}
          >
            <option value="auto">{t("跟随系统")}</option>
            <option value="zh-CN">简体中文</option>
            <option value="en">English</option>
          </Select>
        </div>
      </Card>
      <Card title={t("窗口")}>
        <div className="control-row">
          <div>
            <ToggleSwitch checked={settings.autoFocusRoblox} onChange={settings.setAutoFocusRoblox} label={t("播放时自动切换到 Roblox 窗口")} />
            <p className="page-placeholder__hint">{t("默认关闭。开始演奏或手动继续时，在倒计时后尝试切换一次；找不到游戏窗口或切换失败则暂停并提示。演奏中不会反复抢回焦点。")}</p>
          </div>
        </div>
        <div className="control-row">
          <div>
            <ToggleSwitch checked={settings.pauseOnAppFocus} onChange={settings.setPauseOnAppFocus} label={t("本窗口获得焦点时暂停演奏")} />
            <p className="page-placeholder__hint">{t("默认关闭。开启后，开始演奏会先完成自动切换，再检查本窗口是否有焦点；演奏中主动切回本窗口仍会暂停。关闭后进度继续，本窗口不接收演奏按键。")}</p>
          </div>
        </div>
        <div className="control-row">
          <ToggleSwitch
            checked={settings.alwaysOnTop}
            onChange={settings.setAlwaysOnTop}
            label={t("窗口置顶")}
          />
        </div>
        <div className="control-row">
          <div className="control-row__label">
            <Label>{t("窗口透明度")}</Label>
          </div>
          <SliderSpinbox
            min={20}
            max={100}
            value={settings.opacity}
            suffix="%"
            onChange={settings.setOpacity}
          />
        </div>
        <div className="control-row">
          <ToggleSwitch
            checked={settings.showStatusText}
            onChange={settings.setShowStatusText}
            label={t("显示播放状态")}
          />
        </div>
      </Card>

      <Card title={t("可视化")}>
        <div className="control-row">
          <ToggleSwitch
            checked={settings.showTimeline}
            onChange={settings.setShowTimeline}
            label={t("显示时间轴")}
          />
        </div>
        <div className="control-row">
          <ToggleSwitch
            checked={settings.visualizerHorizontal}
            onChange={settings.setVisualizerHorizontal}
            label={t("横向滚动")}
          />
        </div>
        <div className="control-row">
          <ToggleSwitch
            checked={settings.showPiano}
            onChange={settings.setShowPiano}
            label={t("显示钢琴键盘")}
          />
        </div>
        <div className="control-row">
          <ToggleSwitch
            checked={settings.showPianoPedal}
            onChange={settings.setShowPianoPedal}
            label={t("显示踏板状态")}
          />
        </div>
        <div className="control-row">
          <ToggleSwitch
            checked={settings.switchToVisualizerOnPlay}
            onChange={settings.setSwitchToVisualizerOnPlay}
            label={t("播放时切换到可视化")}
          />
        </div>
      </Card>

      <Card title={t("演奏存档")}>
        <div className="control-row">
          <div className="control-row__label">
            <Label>{t("最近存档数量")}</Label>
          </div>
          <SliderSpinbox
            min={MIN_VISIBLE_SAVES}
            max={MAX_VISIBLE_SAVES}
            value={settings.maxVisibleSaves}
            onChange={settings.setMaxVisibleSaves}
          />
        </div>
      </Card>

      <Card
        title={t("外观")}
        footer={
          <Button onClick={() => setThemeDialogOpen(true)}>
            {t("自定义…")}
          </Button>
        }
      >
        <div className="control-row">
          <div className="control-row__label">
            <Label>{t("主题")}</Label>
          </div>
          <Select
            value={themeName}
            onChange={(e) => setThemeName(e.target.value)}
          >
            {translateNode(
              themeNames.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              )),
            )}
          </Select>
        </div>
      </Card>

      {translateNode(
        themeDialogOpen && (
          <ThemeDialog onClose={() => setThemeDialogOpen(false)} />
        ),
      )}
    </div>
  );
}

function DirectoryRow({
  title,
  hint,
  path,
  onBrowse,
}: {
  title: string;
  hint: string;
  path: string;
  onBrowse: () => void;
}) {
  return (
    <Card title={title}>
      <div className="control-row">
        <TextInput
          className="settings-tab__path-input"
          readOnly
          value={path || t("未设置")}
        />
        <Button
          onClick={() => void openPath(path)}
          disabled={!isTauri() || !path}
          title={t("在文件管理器中打开")}
        >
          {t("打开")}
        </Button>
        <Button onClick={onBrowse} disabled={!isTauri()}>
          {t("浏览…")}
        </Button>
      </div>
      <span className="page-placeholder__hint">{translateNode(hint)}</span>
    </Card>
  );
}

function FilesPage() {
  const [saveDir, setSaveDirState] = useState("");
  const [midiDir, setMidiDirState] = useState("");
  const [themesFile, setThemesFile] = useState("");

  useEffect(() => {
    if (!isTauri()) return;
    getSaveDir()
      .then(setSaveDirState)
      .catch(() => {});
    getMidiDir()
      .then(setMidiDirState)
      .catch(() => {});
    getThemesFile()
      .then(setThemesFile)
      .catch(() => {});
  }, []);

  async function browseSaveDir() {
    if (!isTauri()) return;
    const selected = await openDialog({
      directory: true,
      multiple: false,
      defaultPath: saveDir || undefined,
    });
    if (typeof selected === "string") {
      await setSaveDir(selected);
      setSaveDirState(selected);
    }
  }

  async function browseMidiDir() {
    if (!isTauri()) return;
    const selected = await openDialog({
      directory: true,
      multiple: false,
      defaultPath: midiDir || undefined,
    });
    if (typeof selected === "string") {
      await setMidiDir(selected);
      setMidiDirState(selected);
    }
  }

  async function browseThemesDir() {
    if (!isTauri()) return;
    const selected = await openDialog({ directory: true, multiple: false });
    if (typeof selected === "string") {
      const newPath = await setThemesDir(selected);
      setThemesFile(newPath);
    }
  }

  return (
    <div className="settings-tab__display">
      <DirectoryRow
        title={t("演奏存档目录")}
        hint={t("「保存演奏」生成的编译存档目录。")}
        path={saveDir}
        onBrowse={browseSaveDir}
      />
      <DirectoryRow
        title={t("MIDI 默认目录")}
        hint={t("打开 MIDI 时默认显示的目录。")}
        path={midiDir}
        onBrowse={browseMidiDir}
      />
      <DirectoryRow
        title={t("主题文件")}
        hint={t("保存自定义主题的 JSON 文件。")}
        path={themesFile}
        onBrowse={browseThemesDir}
      />
    </div>
  );
}

function SystemPage() {
  const settings = useAppSettings();
  const { setConfig } = usePlaybackConfig();
  const [checking, setChecking] = useState(false);
  const [checkResult, setCheckResult] = useState<UpdateCheckOutcome | null>(
    null,
  );
  const [appVersion, setAppVersion] = useState<string | null>(null);

  useEffect(() => {
    if (!isTauri()) return;
    getAppVersion()
      .then(setAppVersion)
      .catch(() => {});
  }, []);

  async function handleCheckNow() {
    if (!isTauri()) return;
    setChecking(true);
    try {
      setCheckResult(await checkForUpdatesNow());
    } catch {
      setCheckResult({ status: "indeterminate" });
    } finally {
      setChecking(false);
    }
  }

  return (
    <div className="settings-tab__display">
      <Card title={t("更新")}>
        <Label className="settings-tab__version">{t("当前版本：")} {appVersion ?? "—"}</Label>
        <div className="control-row">
          <ToggleSwitch
            checked={settings.autoCheckUpdates}
            onChange={settings.setAutoCheckUpdates}
            label={t("自动检查 Xingkong 更新")}
          />
        </div>
        <div className="control-row">
          <Button disabled={checking} onClick={() => void handleCheckNow()}>
            {translateNode(checking ? "正在检查…" : "立即检查")}
          </Button>
          {translateNode(
            checkResult?.status === "update_available" && (
              <Button
                variant="accent"
                onClick={() => void openUrl(checkResult.url)}
              >
                {t("发现更新（")}
                {translateNode(checkResult.tag)}
                {t("）：打开发布页")}
              </Button>
            ),
          )}
          {translateNode(
            checkResult?.status === "no_update" && (
              <span>{t("已是最新版本。")}</span>
            ),
          )}
          {translateNode(
            checkResult?.status === "indeterminate" && (
              <span>{t("暂时无法检查更新。")}</span>
            ),
          )}
        </div>
      </Card>
      <Card title={t("MIDI 导入")}>
        <div className="control-row">
          <div className="control-row__label">
            <Label>{t("原始踏板提示阈值")}</Label>
          </div>
          <SliderSpinbox
            min={1}
            max={200}
            value={settings.pedalPromptThreshold}
            onChange={settings.setPedalPromptThreshold}
          />
        </div>
        <span className="page-placeholder__hint">
          {t("MIDI 中的延音踏板事件达到此数量时，询问是否直接使用原始踏板。")}
        </span>
      </Card>
      <Card title={t("重置")}>
        <Button
          onClick={() =>
            setConfig((c) => ({
              ...DEFAULT_CONFIG,
              pedal_curve_on: c.pedal_curve_on,
              pedal_curve_off: c.pedal_curve_off,
            }))
          }
        >
          {t("重置演奏设置")}
        </Button>
        <span className="page-placeholder__hint">
          {t(
            "恢复播放与模拟人演奏默认参数。PedalAI 阈值可在演奏设置页单独重置。",
          )}
        </span>
      </Card>
    </div>
  );
}

function PrivacyPage() {
  const { redactPaths, setRedactPaths } = useLog();
  return (
    <div className="settings-tab__display">
      <Card title={t("调试日志")}>
        <div className="control-row">
          <ToggleSwitch
            checked={redactPaths}
            onChange={setRedactPaths}
            label={t("隐藏日志中的完整路径")}
          />
        </div>
        <span className="page-placeholder__hint">
          {t("日志中仅保留文件名，方便分享时保护路径隐私。")}
        </span>
      </Card>
    </div>
  );
}

export function SettingsTab() {
  const [nav, setNav] = usePersistedState<SettingsNav>(
    "ui_settings_page",
    "Display",
    {
      parse: parseOneOf(NAV_ITEMS),
    },
  );

  return (
    <div className="settings-tab">
      <TabPage
        tabs={NAV_ITEMS.map((name) => NAV_LABELS[name])}
        active={NAV_ITEMS.indexOf(nav)}
        onChange={(i) => setNav(NAV_ITEMS[i])}
      >
        {translateNode(nav === "Display" && <DisplayPage />)}
        {translateNode(nav === "Files" && <FilesPage />)}
        {translateNode(nav === "Hotkey" && <ShortcutSettings />)}
        {translateNode(nav === "Performance" && <GlobalHumanizationSettings />)}
        {translateNode(nav === "System" && <SystemPage />)}
        {translateNode(nav === "Privacy" && <PrivacyPage />)}
      </TabPage>
    </div>
  );
}
