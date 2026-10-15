import { t, translateNode } from "../lib/i18n";
import {
  PauseCircleIcon,
  PlayCircleIcon,
  ResizeIcon,
  SkipBackCircleIcon,
  SkipForwardCircleIcon,
  StopCircleIcon,
} from "@phosphor-icons/react";
import { Button } from "./Button";
import { RangeInput } from "./Field";
import { StatusIndicator, type PlaybackStatus } from "./StatusIndicator";
import type { PlaybackClock } from "../state/playbackClock";
import { useClockValue } from "../state/useClockValue";

const SCRUBBER_STEPS = 10000;

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

const exactTime = (time: number) => time;

interface TransportBarProps {
  isPlaying: boolean;
  clock: PlaybackClock;
  totalTime: number;
  isCollapsed: boolean;
  status: PlaybackStatus;
  statusLabel: string;
  showStatusText: boolean;
  playEnabled: boolean;
  onScrub: (time: number) => void;
  onPlayPause: () => void;
  onStop: () => void;
  onSeekStart: () => void;
  onSeekEnd: () => void;
  onToggleCollapsed: () => void;
  onPrevious?: () => void;
  onNext?: () => void;
  countdownRemaining?: number;
  sourceLabel?: string;
}

function ScrubberRow({
  clock,
  totalTime,
  onScrub,
}: {
  clock: PlaybackClock;
  totalTime: number;
  onScrub: (time: number) => void;
}) {
  const time = useClockValue(clock, exactTime);
  return (
    <div className="transport-bar__scrubber-row">
      <span className="transport-bar__time">
        {translateNode(formatTime(time))}
      </span>
      <RangeInput
        className="transport-bar__scrubber"
        min={0}
        max={SCRUBBER_STEPS}
        value={totalTime > 0 ? (time / totalTime) * SCRUBBER_STEPS : 0}
        onChange={(e) =>
          onScrub(
            totalTime > 0
              ? (Number(e.target.value) / SCRUBBER_STEPS) * totalTime
              : 0,
          )
        }
      />
      <span className="transport-bar__time">
        {translateNode(formatTime(totalTime))}
      </span>
    </div>
  );
}

function CollapsedTime({
  clock,
  totalTime,
}: {
  clock: PlaybackClock;
  totalTime: number;
}) {
  const seconds = useClockValue(clock, Math.floor);
  return (
    <span className="transport-bar__time">
      {translateNode(formatTime(seconds))}
      {t("/")}
      {translateNode(formatTime(totalTime))}
    </span>
  );
}

export function TransportBar({
  isPlaying,
  clock,
  totalTime,
  isCollapsed,
  status,
  statusLabel,
  showStatusText,
  playEnabled,
  onScrub,
  onPlayPause,
  onStop,
  onSeekStart,
  onSeekEnd,
  onToggleCollapsed,
  onPrevious,
  onNext,
  countdownRemaining = 0,
  sourceLabel,
}: TransportBarProps) {
  return (
    <div
      className={`transport-bar${isCollapsed ? " transport-bar--collapsed" : ""}`}
    >
      {translateNode(
        (sourceLabel || countdownRemaining > 0) && (
          <div className="transport-bar__song-status">
            <span title={sourceLabel}>{sourceLabel}</span>
            {translateNode(
              countdownRemaining > 0 && (
                <strong>
                  {t("倒计时")}
                  {translateNode(countdownRemaining)}
                  {t("秒")}
                </strong>
              ),
            )}
          </div>
        ),
      )}
      <ScrubberRow clock={clock} totalTime={totalTime} onScrub={onScrub} />

      <div className="transport-bar__btn-row">
        <div className="transport-bar__side">
          <StatusIndicator
            status={status}
            label={statusLabel}
            showLabel={showStatusText}
          />
          {translateNode(
            isCollapsed && (
              <CollapsedTime clock={clock} totalTime={totalTime} />
            ),
          )}
        </div>

        <div className="transport-bar__controls" onClickCapture={(event) => {
          // Mouse activation must not leave a transport button armed for pedal Space.
          // Keyboard activation (detail === 0) retains normal accessible focus.
          if (event.detail > 0 && event.target instanceof Element) event.target.closest<HTMLButtonElement>("button")?.blur();
        }}>
          <Button
            variant="icon"
            subtle
            size="lg"
            onClick={onPrevious ?? onSeekStart}
            disabled={!onPrevious && !playEnabled}
            title={onPrevious ? "上一首" : "回到开头"}
          >
            <SkipBackCircleIcon weight="duotone" />
          </Button>
          <Button
            variant="icon"
            subtle
            size="lg"
            onClick={onPlayPause}
            disabled={!playEnabled}
            title={isPlaying ? "暂停" : "播放"}
          >
            {translateNode(
              isPlaying ? (
                <PauseCircleIcon weight="duotone" />
              ) : (
                <PlayCircleIcon weight="duotone" />
              ),
            )}
          </Button>
          <Button
            variant="icon"
            subtle
            size="lg"
            onClick={onStop}
            disabled={status === "unloaded"}
            title={t("停止")}
          >
            <StopCircleIcon weight="duotone" />
          </Button>
          <Button
            variant="icon"
            subtle
            size="lg"
            onClick={onNext ?? onSeekEnd}
            disabled={!onNext && !playEnabled}
            title={onNext ? "下一首" : "跳到结尾"}
          >
            <SkipForwardCircleIcon weight="duotone" />
          </Button>
        </div>

        <div className="transport-bar__side transport-bar__side--end">
          <Button
            variant="icon"
            size="md"
            onClick={onToggleCollapsed}
            title={isCollapsed ? "展开窗口" : "迷你模式"}
          >
            <ResizeIcon
              weight="duotone"
              style={isCollapsed ? { transform: "rotate(180deg)" } : undefined}
            />
          </Button>
        </div>
      </div>
    </div>
  );
}
