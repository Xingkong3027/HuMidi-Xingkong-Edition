import { t, translateNode } from "../../lib/i18n";
import { useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { shortcutCombo } from "../../lib/shortcutKeys";
import { Card } from "../../components/Card";
import { Button } from "../../components/Button";
import {
  isTauri,
  getHotkeys,
  onEvent,
  startSaveBinding,
} from "../../lib/tauri";

type Action = "play_pause" | "stop" | "previous" | "next";
interface Shortcuts {
  version: number;
  bindings: Record<Action, [string | null, string | null]>;
}
const LABELS: Record<Action, string> = {
  play_pause: "播放 / 暂停",
  stop: "停止",
  previous: "上一首",
  next: "下一首",
};
const DEFAULT: Shortcuts = {
  version: 3,
  bindings: {
    play_pause: ["F6", null],
    stop: ["F7", null],
    previous: [null, null],
    next: [null, null],
  },
};

export function ShortcutSettings() {
  const [shortcuts, setShortcuts] = useState<Shortcuts>(DEFAULT);
  const [capturing, setCapturing] = useState<string | null>(null);
  const recording = useRef<string | null>(null);
  const ready = useRef<Promise<unknown>>(Promise.resolve());
  const finishing = useRef(false);
  const justRecorded = useRef<{combo:string;until:number} | null>(null);
  function protectRecordedKey(combo: string | null | undefined) {
    if (combo && !finishing.current) justRecorded.current = {combo,until:performance.now()+300};
  }
  function endCapture() { recording.current = null; finishing.current = false; setCapturing(null); }
  const [saveLabel, setSaveLabel] = useState("Ctrl+S");
  const [error, setError] = useState("");
  useEffect(() => {
    if (!isTauri()) return;
    void invoke<Shortcuts>("get_shortcuts")
      .then(setShortcuts)
      .catch((e) => setError(String(e)));
    void getHotkeys()
      .then(([, label]) => setSaveLabel(label))
      .catch(() => {});
    const events = [
      onEvent("xk_shortcut_error", (msg) => {
        setError(msg);
        endCapture();
      }),
      onEvent("xk_shortcut_bound", (payload) => {
        const [action,slot] = (recording.current ?? "").split(":");
        if (action && action !== "save") protectRecordedKey(payload.bindings[action as Action]?.[Number(slot)]);
        setShortcuts(payload);
        endCapture();
      }),
      onEvent("hotkey_bound_save_updated", (label) => {
        if (recording.current === "save") protectRecordedKey(label);
        setSaveLabel(label);
        endCapture();
      }),
    ];
    return () => {
      recording.current = null;
      events.forEach((p) => {
        void p.then((unlisten) => unlisten());
      });
      void invoke("cancel_shortcut_binding").catch(() => {});
    };
  }, []);
  useEffect(() => {
    const keydown = (event: KeyboardEvent) => {
      const session = recording.current;
      if (!session) {
        const recent = justRecorded.current;
        if (recent && performance.now() < recent.until && shortcutCombo(event) === recent.combo) {
          event.preventDefault(); event.stopImmediatePropagation();
        }
        return;
      }
      event.preventDefault(); event.stopImmediatePropagation();
      if (event.repeat || finishing.current) return;
      const combo = shortcutCombo(event);
      if (!combo) return;
      finishing.current = true;
      void (async () => {
        try {
          await ready.current;
          if (recording.current !== session) return;
          if (combo === "Escape") {
            await invoke("cancel_shortcut_binding");
          } else {
            const result = await invoke<{shortcuts:Shortcuts;save_label:string}>("finish_shortcut_binding", {combo});
            setShortcuts(result.shortcuts); setSaveLabel(result.save_label);
          }
          endCapture();
        } catch (e) {
          setError(String(e)); endCapture();
          void invoke("cancel_shortcut_binding").catch(() => {});
        }
      })();
    };
    const keyup = () => { justRecorded.current = null; };
    document.addEventListener("keydown", keydown, true);
    document.addEventListener("keyup", keyup, true);
    return () => {
      document.removeEventListener("keydown", keydown, true);
      document.removeEventListener("keyup", keyup, true);
    };
  }, []);
  async function capture(action: Action | "save", slot: 0 | 1 = 0) {
    setError("");
    const session = action === "save" ? "save" : `${action}:${slot}`;
    justRecorded.current = null;
    recording.current = session; finishing.current = false; setCapturing(session);
    ready.current = action === "save" ? startSaveBinding() : invoke("start_shortcut_binding", { action, slot });
    try { await ready.current; }
    catch (e) { endCapture(); setError(String(e)); }
  }
  async function clear(action: Action, slot: 0 | 1) {
    const next: Shortcuts = {
      version: 3,
      bindings: {
        ...shortcuts.bindings,
        [action]: [...shortcuts.bindings[action]],
      },
    };
    next.bindings[action][slot] = null;
    try {
      setShortcuts(
        await invoke<Shortcuts>("set_shortcuts", { shortcuts: next }),
      );
      setError("");
    } catch (e) {
      setError(String(e));
    }
  }
  return (
    <div className="settings-tab__display">
      <Card title={t("全局播放快捷键")}>
        <p className="page-placeholder__hint">
          {t(
            "每个操作最多两个快捷键，支持功能键、组合键与媒体键。重复绑定会从原位置移除。按 Esc 取消录入。",
          )}
        </p>
        <div className="shortcut-grid">
          {translateNode(
            (Object.keys(LABELS) as Action[]).map((action) => (
              <div className="shortcut-grid__row" key={action}>
                <span>{translateNode(LABELS[action])}</span>
                {translateNode(
                  ([0, 1] as const).map((slot) => (
                    <div className="shortcut-grid__binding" key={slot}>
                      <Button
                        aria-label={`${LABELS[action]}快捷键 ${slot + 1}`}
                        disabled={!isTauri() || capturing !== null}
                        onClick={() => void capture(action, slot)}
                      >
                        {translateNode(
                          capturing === `${action}:${slot}`
                            ? "请按下快捷键…"
                            : shortcuts.bindings[action]?.[slot] || "未设置",
                        )}
                      </Button>
                      <Button
                        aria-label={`清除${LABELS[action]}快捷键 ${slot + 1}`}
                        disabled={
                          !isTauri() ||
                          capturing !== null ||
                          !shortcuts.bindings[action]?.[slot]
                        }
                        onClick={() => void clear(action, slot)}
                      >
                        {t("清除")}
                      </Button>
                    </div>
                  )),
                )}
              </div>
            )),
          )}
        </div>
        {translateNode(
          capturing && (
            <Button
              onClick={() => {
                void invoke("cancel_shortcut_binding").catch((e) => setError(String(e)));
                endCapture();
              }}
            >
              {t("取消录入")}
            </Button>
          ),
        )}
        {translateNode(
          error && (
            <p role="alert" className="trim-card__error">
              {translateNode(error)}
            </p>
          ),
        )}
      </Card>
      <Card title={t("保存演奏")}>
        <div className="control-row">
          <span className="control-row__label">
            {translateNode(capturing === "save" ? "请按下快捷键…" : saveLabel)}
          </span>
          <Button
            disabled={!isTauri() || capturing !== null}
            onClick={() => {
              void capture("save");
            }}
          >
            {t("更改")}
          </Button>
        </div>
      </Card>
    </div>
  );
}
