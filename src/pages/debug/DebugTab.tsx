import { t, translateNode } from "../../lib/i18n";
import { useEffect, useMemo, useRef } from "react";
import { Card } from "../../components/Card";
import { ToggleSwitch } from "../../components/ToggleSwitch";
import {
  useLog,
  type LogLevel,
  type SnapshotKey,
} from "../../state/LogContext";
import { Button } from "../../components/Button";
import { Select } from "../../components/Field";
import { usePersistedState } from "../../state/usePersistedState";
import { parseBoolean, parseOneOf } from "../../state/persistedParsers";

const LEVELS: LogLevel[] = ["INFO", "DEBUG", "WARN", "OK"];
const FILTER_OPTIONS = ["All", ...LEVELS];

const SNAPSHOT_ROWS: { key: SnapshotKey; label: string }[] = [
  { key: "file", label: "File" },
  { key: "source", label: "Source" },
  { key: "tracks", label: "Tracks" },
  { key: "notes", label: "Notes" },
  { key: "duration", label: "Duration" },
  { key: "pedal", label: "Pedal" },
  { key: "tempo", label: "Tempo" },
  { key: "pedal_style", label: "Pedal Style" },
];

export function DebugTab() {
  const { entries, clear, snapshot } = useLog();
  const [filter, setFilter] = usePersistedState("ui_debug_filter", "All", {
    parse: parseOneOf(FILTER_OPTIONS),
  });
  const [autoScroll, setAutoScroll] = usePersistedState(
    "ui_debug_auto_scroll",
    true,
    { parse: parseBoolean },
  );
  const consoleRef = useRef<HTMLDivElement>(null);

  const filtered = useMemo(
    () =>
      filter === "All" ? entries : entries.filter((e) => e.level === filter),
    [entries, filter],
  );

  useEffect(() => {
    if (autoScroll && consoleRef.current)
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
  }, [filtered, autoScroll]);

  const counts = useMemo(() => {
    const c: Record<LogLevel, number> = { INFO: 0, DEBUG: 0, WARN: 0, OK: 0 };
    for (const e of entries) c[e.level]++;
    return c;
  }, [entries]);

  return (
    <div className="debug-tab">
      <div className="debug-tab__body">
        <Card title={t("")} className="debug-tab__console-card">
          <div ref={consoleRef} className="debug-tab__console">
            {translateNode(
              filtered.length === 0 ? (
                <span className="page-placeholder__hint">
                  {t("No log entries.")}
                </span>
              ) : (
                filtered.map((e, i) => (
                  <div
                    key={i}
                    className={`debug-tab__line debug-tab__line--${e.level.toLowerCase()}`}
                  >
                    {translateNode(e.line)}
                  </div>
                ))
              ),
            )}
          </div>
        </Card>

        <div className="debug-tab__sidebar">
          <Card title={t("Filter")}>
            <Select value={filter} onChange={(e) => setFilter(e.target.value)}>
              {translateNode(
                FILTER_OPTIONS.map((f) => (
                  <option key={f} value={f}>
                    {translateNode(f)}
                  </option>
                )),
              )}
            </Select>
            <ToggleSwitch
              checked={autoScroll}
              onChange={setAutoScroll}
              label={t("Auto-scroll")}
            />
          </Card>

          <Card title={t("Levels")}>
            <div className="debug-tab__levels-grid">
              {translateNode(
                LEVELS.map((l) => (
                  <div key={l} className="debug-tab__level-row">
                    <span>{translateNode(l)}</span>
                    <span>{translateNode(counts[l])}</span>
                  </div>
                )),
              )}
            </div>
          </Card>

          <Card title={t("Session Snapshot")}>
            <div className="debug-tab__snapshot-grid">
              {translateNode(
                SNAPSHOT_ROWS.map(({ key, label }) => (
                  <div key={key} className="debug-tab__snapshot-row">
                    <span>{translateNode(label)}</span>
                    <span>{translateNode(snapshot[key] ?? "-")}</span>
                  </div>
                )),
              )}
            </div>
          </Card>
        </div>
      </div>

      <div className="debug-tab__footer">
        <Button onClick={clear}>{t("Clear")}</Button>
        <Button
          onClick={() =>
            navigator.clipboard.writeText(
              filtered.map((e) => e.line).join("\n"),
            )
          }
        >
          {t("Copy Log")}
        </Button>
        <Button
          onClick={() => {
            const blob = new Blob([entries.map((e) => e.line).join("\n")], {
              type: "text/plain",
            });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `humidi_log_${Date.now()}.txt`;
            a.click();
            URL.revokeObjectURL(url);
          }}
        >
          {t("Export Log")}
        </Button>
      </div>
    </div>
  );
}
