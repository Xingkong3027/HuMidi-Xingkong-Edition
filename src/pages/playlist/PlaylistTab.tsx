import { t, translateNode } from "../../lib/i18n";
import { useEffect, useRef, useState, type MouseEvent } from "react";
import { isNativeFileDialogOpen } from "../../lib/appDialogs";
import {
  MusicNotesIcon,
  PlusIcon,
  UploadSimpleIcon,
  DownloadSimpleIcon,
  PlayIcon,
  DotsThreeIcon,
  TrashIcon,
  ArrowsClockwiseIcon,
} from "@phosphor-icons/react";
import { usePlaylist } from "../../state/PlaylistContext";
import { usePlaybackConfig } from "../../state/PlaybackConfigContext";
import { Button } from "../../components/Button";
import {
  Checkbox,
  Select,
  TextInput,
  NumberInput,
  TextArea,
} from "../../components/Field";
import { Modal } from "../../components/Modal";
import { Card } from "../../components/Card";
import {
  getPlaylistSong,
  putPlaylistSong,
  playlistSourceLabel,
  type PlaylistDetail,
  type PlaylistMode,
} from "../../lib/playlist";
import type { PlaybackConfig } from "../playback/types";
import "./playlist.css";

export const MODE_LABELS: Record<PlaylistMode, string> = {
  single: "单曲播放",
  repeat_one: "单曲循环",
  sequential: "顺序播放",
  repeat_all: "列表循环",
  shuffle: "随机播放",
};
const time = (duration: number) =>
  duration > 0
    ? `${Math.floor(duration / 60)}:${String(Math.floor(duration % 60)).padStart(2, "0")}`
    : "待编译";
export function NameDialog({
  title,
  initial,
  onClose,
  onSave,
}: {
  title: string;
  initial: string;
  onClose: () => void;
  onSave: (name: string) => void;
}) {
  const [name, setName] = useState(initial);
  return (
    <Modal
      title={title}
      width={440}
      height={220}
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>{t("取消")}</Button>
          <Button
            variant="accent"
            disabled={!name.trim()}
            onClick={() => onSave(name.trim())}
          >
            {t("保存")}
          </Button>
        </>
      }
    >
      <TextInput
        autoFocus
        value={name}
        onChange={(e) => setName(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && name.trim()) onSave(name.trim());
        }}
      />
    </Modal>
  );
}

type BatchField = {
  key: keyof PlaybackConfig;
  label: string;
  min?: number;
  max?: number;
  step?: number;
  choices?: Record<string, string>;
};
const BATCH_FIELDS: BatchField[] = [
  { key: "tempo", label: "速度 %", min: 10, max: 400 },
  { key: "transpose", label: "移调（半音）", min: -48, max: 48 },
  {
    key: "pedal_style",
    label: "踏板模式",
    choices: {
      none: "关闭",
      ai: "PedalAI",
      hybrid: "自适应",
      rhythmic: "节奏",
      legato: "连奏",
    },
  },
  { key: "use_midi_pedal", label: "使用 MIDI 原始踏板" },
  { key: "pedal_before_humanize", label: "先生成踏板再模拟演奏" },
  { key: "use_88_key_layout", label: "88 键布局" },
  { key: "countdown", label: "播放前倒计时" },
  { key: "countdown_seconds", label: "倒计时秒数", min: 1, max: 10 },
  { key: "trim_enabled", label: "裁剪播放范围" },
  { key: "trim_auto", label: "按每首曲目自动裁剪" },
  { key: "trim_start_seconds", label: "开始秒数", min: 0, step: 0.1 },
  { key: "trim_end_seconds", label: "结束秒数（0 为曲尾）", min: 0, step: 0.1 },
  { key: "performance_optimization", label: "密集 MIDI 优化" },
  {
    key: "humanization_mode",
    label: "模拟人演奏",
    choices: {
      disabled: "关闭",
      global: "使用全局预设",
      individual: "每首独立参数",
    },
  },
  {
    key: "humanization_seed_mode",
    label: "随机种子策略",
    choices: {
      dynamic: "每次随机",
      fixed_random: "固定随机种子",
      fixed_custom: "自定义种子",
    },
  },
  { key: "random_seed", label: "种子值", min: 0, max: Number.MAX_SAFE_INTEGER },
  { key: "simulate_hands", label: "模拟双手" },
  { key: "enable_chord_roll", label: "和弦滚奏" },
  { key: "vary_timing", label: "时间变化" },
  {
    key: "timing_variance",
    label: "时间变化幅度",
    min: 0,
    max: 0.1,
    step: 0.001,
  },
  { key: "vary_articulation", label: "音长变化" },
  { key: "articulation", label: "音长比例 %", min: 50, max: 100, step: 0.1 },
  { key: "enable_drift_correction", label: "双手漂移" },
  { key: "drift_decay_factor", label: "漂移恢复 %", min: 0, max: 100 },
  { key: "enable_tempo_sway", label: "速度起伏" },
  {
    key: "tempo_sway_intensity",
    label: "速度起伏幅度",
    min: 0,
    max: 0.1,
    step: 0.001,
  },
  { key: "invert_tempo_sway", label: "反向起伏" },
  { key: "enable_mistakes", label: "偶发错音" },
  { key: "mistake_chance", label: "错音概率 %", min: 0, max: 10, step: 0.1 },
];
function BatchDialog({ onClose }: { onClose: () => void }) {
  const playlist = usePlaylist();
  const { config } = usePlaybackConfig();
  const [draft, setDraft] = useState(config);
  const [touched, setTouched] = useState<Set<keyof PlaybackConfig>>(new Set());
  function set(key: keyof PlaybackConfig, value: unknown) {
    setDraft((c) => ({ ...c, [key]: value }));
    setTouched(
      (old) =>
        new Set([
          ...old,
          key,
          ...(key === "trim_enabled" || key === "trim_auto"
            ? (["trim_enabled", "trim_auto"] as const)
            : []),
        ]),
    );
  }
  const patch = () =>
    Object.fromEntries(
      [...touched].map((key) => [key, draft[key]]),
    ) as Partial<PlaybackConfig>;
  return (
    <Modal
      title={`批量修改 ${playlist.selected.length} 首歌曲`}
      width={700}
      height={560}
      onClose={onClose}
      footer={
        <>
          <span className="playlist-muted">
            {t("只应用勾选的字段，保留其他设置。")}
          </span>
          <Button onClick={onClose}>{t("取消")}</Button>
          <Button
            variant="accent"
            disabled={!touched.size}
            onClick={() => {
              void playlist.batchPatch(patch());
              onClose();
            }}
          >
            {t("应用")}
            {translateNode(touched.size)}
            {t("项")}
          </Button>
        </>
      }
    >
      <div className="playlist-batch-grid">
        {translateNode(
          BATCH_FIELDS.map((field) => {
            const value = draft[field.key];
            return (
              <div className="playlist-batch-field" key={field.key}>
                <label>
                  <Checkbox
                    checked={touched.has(field.key)}
                    onChange={(e) =>
                      setTouched((old) => {
                        const n = new Set(old);
                        if (e.target.checked) n.add(field.key);
                        else n.delete(field.key);
                        return n;
                      })
                    }
                  />
                  {translateNode(field.label)}
                </label>
                {translateNode(
                  field.choices ? (
                    <Select
                      value={String(value)}
                      onChange={(e) => set(field.key, e.target.value)}
                    >
                      {translateNode(
                        Object.entries(field.choices).map(([v, label]) => (
                          <option value={v} key={v}>
                            {translateNode(label)}
                          </option>
                        )),
                      )}
                    </Select>
                  ) : typeof value === "boolean" ? (
                    <Select
                      value={String(value)}
                      onChange={(e) =>
                        set(field.key, e.target.value === "true")
                      }
                    >
                      <option value="true">{t("开启")}</option>
                      <option value="false">{t("关闭")}</option>
                    </Select>
                  ) : (
                    <NumberInput
                      value={typeof value === "number" ? value : 0}
                      min={field.min}
                      max={field.max}
                      step={field.step ?? 1}
                      onChange={(e) => {
                        const n = Number(e.target.value);
                        if (Number.isFinite(n)) set(field.key, n);
                      }}
                    />
                  ),
                )}
              </div>
            );
          }),
        )}
      </div>
    </Modal>
  );
}
function SheetEditDialog({
  detail,
  onClose,
}: {
  detail: PlaylistDetail;
  onClose: () => void;
}) {
  const playlist = usePlaylist();
  const [name, setName] = useState(detail.metadata.name);
  const [text, setText] = useState(detail.song.source.sheet_text ?? "");
  const [bpm, setBpm] = useState(detail.song.source.bpm ?? 120);
  const [error, setError] = useState("");
  async function apply() {
    try {
      await putPlaylistSong(
        name,
        {
          ...detail.song,
          source: { ...detail.song.source, sheet_text: text, bpm },
        },
        null,
        0,
        detail.metadata.id,
      );
      await playlist.refresh();
      onClose();
    } catch (e) {
      setError(String(e));
    }
  }
  return (
    <Modal
      title={t("修改文本曲谱")}
      width={680}
      height={500}
      onClose={onClose}
      footer={
        <>
          <span className="playlist-error">{translateNode(error)}</span>
          <Button onClick={onClose}>{t("取消")}</Button>
          <Button
            variant="accent"
            disabled={!name.trim() || !text.trim()}
            onClick={() => void apply()}
          >
            {t("保存")}
          </Button>
        </>
      }
    >
      <div className="playlist-sheet-edit">
        <TextInput
          value={name}
          onChange={(e) => setName(e.target.value)}
          aria-label={t("歌曲名称")}
        />
        <TextArea
          value={text}
          onChange={(e) => setText(e.target.value)}
          aria-label={t("曲谱内容")}
        />
        <label>
          {t("BPM")}
          <NumberInput
            min={20}
            max={400}
            value={bpm}
            onChange={(e) =>
              setBpm(Math.max(20, Math.min(400, Number(e.target.value))))
            }
          />
        </label>
      </div>
    </Modal>
  );
}

export function PlaylistTab({
  onEditPlayback,
  onImportMidi,
}: {
  onEditPlayback: () => void;
  onImportMidi: () => void;
}) {
  const playlist = usePlaylist();
  const [query, setQuery] = useState("");
  const [transfer, setTransfer] = useState<"import" | "export" | null>(null);
  const [nameDialog, setNameDialog] = useState<{
    id?: string;
    title: string;
    initial: string;
  } | null>(null);
  const [batchOpen, setBatchOpen] = useState(false);
  const [sheetDetail, setSheetDetail] = useState<PlaylistDetail | null>(null);
  const [menu, setMenu] = useState<{ x: number; y: number } | null>(null);
  const anchor = useRef<string | null>(null);
  const dragging = useRef<string[]>([]);
  const [dropAt, setDropAt] = useState<string | null>(null);
  const visible = playlist.items.filter((item) =>
    `${item.name} ${item.source_label}`
      .toLocaleLowerCase()
      .includes(query.toLocaleLowerCase()),
  );
  const selectedItems = playlist.items.filter((item) =>
    playlist.selected.includes(item.id),
  );
  const lead = selectedItems[0];
  useEffect(() => {
    const selectAll = (event: KeyboardEvent) => {
      if (
        event.defaultPrevented || event.isComposing ||
        !(event.ctrlKey || event.metaKey) || event.altKey || event.shiftKey ||
        event.key.toLowerCase() !== "a" || playlist.busy || !playlist.items.length ||
        isNativeFileDialogOpen() || document.querySelector('[role="dialog"]')
      ) return;
      const target = event.target;
      if (target instanceof Element && target.closest(
        'input, textarea, select, [contenteditable]:not([contenteditable="false"]), [role="textbox"]',
      )) return;
      event.preventDefault();
      window.getSelection()?.removeAllRanges();
      playlist.setSelected(playlist.items.map((item) => item.id));
    };
    document.addEventListener("keydown", selectAll);
    return () => document.removeEventListener("keydown", selectAll);
  }, [playlist.items, playlist.setSelected, playlist.busy]);
  function select(id: string, event: MouseEvent) {
    if (event.shiftKey && anchor.current) {
      const a = playlist.items.findIndex((i) => i.id === anchor.current);
      const b = playlist.items.findIndex((i) => i.id === id);
      playlist.setSelected(
        playlist.items
          .slice(Math.min(a, b), Math.max(a, b) + 1)
          .map((i) => i.id),
      );
    } else if (event.ctrlKey || event.metaKey) {
      playlist.setSelected(
        playlist.selected.includes(id)
          ? playlist.selected.filter((i) => i !== id)
          : [...playlist.selected, id],
      );
      anchor.current = id;
    } else {
      playlist.setSelected([id]);
      anchor.current = id;
    }
  }
  async function edit(id: string) {
    onEditPlayback();
    await playlist.edit(id);
  }
  function drop(before: string | null) {
    if (query || !dragging.current.length) return;
    const ids = playlist.items.map((i) => i.id);
    const moving = ids.filter((id) => dragging.current.includes(id));
    const rest = ids.filter((id) => !dragging.current.includes(id));
    const index = before === null ? rest.length : rest.indexOf(before);
    if (index < 0) return;
    rest.splice(index, 0, ...moving);
    void playlist.reorder(rest);
    setDropAt(null);
    dragging.current = [];
  }
  return (
    <div className="playlist-page" onClick={() => setMenu(null)}>
      <div className="playlist-title-row">
        <div>
          <div className="playlist-eyebrow">{t("XINGKONG LIBRARY")}</div>
          <h1>{t("我的歌单")}</h1>
          <p>
            {translateNode(playlist.items.length)}
            {t("首曲目 · 每首保留独立演奏设置与原始文件")}
          </p>
        </div>
        <Button
          variant="accent"
          disabled={playlist.busy}
          onClick={onImportMidi}
        >
          <PlusIcon />
          {t("导入 MIDI 并设置")}
        </Button>
      </div>
      <p className="playlist-background-status" role="status" aria-live="polite" aria-atomic="true" title={playlist.backgroundProgress}>
        {playlist.backgroundProgress || "\u00a0"}
      </p>
      <div className="playlist-toolbar">
        <TextInput
          placeholder={t("搜索曲目或来源…")}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <Select
          value={playlist.mode}
          onChange={(e) => playlist.setMode(e.target.value as PlaylistMode)}
          aria-label={t("歌单播放模式")}
        >
          {translateNode(
            Object.entries(MODE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {translateNode(label)}
              </option>
            )),
          )}
        </Select>
        <Button
          disabled={playlist.busy}
          onClick={() => void playlist.refresh()}
          title={t("刷新")}
        >
          <ArrowsClockwiseIcon />
        </Button>
        <Button disabled={playlist.busy} onClick={() => setTransfer("import")}>
          <DownloadSimpleIcon />
          {t("导入歌单")}
        </Button>
        <Button
          disabled={playlist.busy || !playlist.items.length}
          onClick={() => setTransfer("export")}
        >
          <UploadSimpleIcon />
          {t("导出歌单")}
        </Button>
      </div>
      <div className="playlist-workspace">
        <div
          className="playlist-list"
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            if (e.target === e.currentTarget) drop(null);
          }}
        >
          <div className="playlist-table-head">
            <span>{t("曲目 / 来源")}</span>
            <span>{t("演奏")}</span>
            <span>{t("时长")}</span>
            <span />
          </div>
          {translateNode(
            !visible.length && (
              <div className="playlist-empty">
                <MusicNotesIcon size={42} weight="duotone" />
                <h2>
                  {translateNode(
                    query ? "没有匹配曲目" : "把喜欢的曲目放在这里",
                  )}
                </h2>
                <p>
                  {t(
                    "先在演奏设置导入 MIDI 并加入歌单，或在转换页添加文本曲谱。",
                  )}
                </p>
                <Button
                  onClick={onImportMidi}
                  disabled={playlist.busy}
                >
                  {t("前往演奏设置导入")}
                </Button>
              </div>
            ),
          )}
          {translateNode(
            visible.map((item, index) => (
              <div
                tabIndex={0}
                role="option"
                aria-selected={playlist.selected.includes(item.id)}
                key={item.id}
                className={`playlist-row${playlist.selected.includes(item.id) ? " is-selected" : ""}${playlist.currentId === item.id ? " is-current" : ""}${dropAt === item.id ? " is-drop-target" : ""}`}
                draggable={!query && !playlist.busy}
                onClick={(e) => select(item.id, e)}
                onDoubleClick={() => void playlist.play(item.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void playlist.play(item.id);
                }}
                onMouseEnter={(e) => {
                  if (
                    e.ctrlKey &&
                    e.buttons === 1 &&
                    !playlist.selected.includes(item.id)
                  )
                    playlist.setSelected([...playlist.selected, item.id]);
                }}
                onContextMenu={(e) => {
                  e.preventDefault();
                  if (!playlist.selected.includes(item.id))
                    playlist.setSelected([item.id]);
                  setMenu({
                    x: Math.min(e.clientX, window.innerWidth - 210),
                    y: Math.min(e.clientY, window.innerHeight - 240),
                  });
                }}
                onDragStart={(e) => {
                  dragging.current = playlist.selected.includes(item.id)
                    ? playlist.selected
                    : [item.id];
                  e.dataTransfer.effectAllowed = "move";
                  e.dataTransfer.setData("text/plain", item.id);
                }}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDropAt(item.id);
                  const list = e.currentTarget.parentElement;
                  if (list) {
                    const r = list.getBoundingClientRect();
                    if (e.clientY < r.top + 50) list.scrollTop -= 12;
                    else if (e.clientY > r.bottom - 50) list.scrollTop += 12;
                  }
                }}
                onDragEnd={() => {
                  setDropAt(null);
                  dragging.current = [];
                }}
                onDrop={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  drop(item.id);
                }}
              >
                <div className="playlist-row-main">
                  <span className="playlist-row-number">
                    {translateNode(
                      playlist.currentId === item.id && playlist.active ? (
                        <PlayIcon weight="fill" />
                      ) : (
                        index + 1
                      ),
                    )}
                  </span>
                  <div>
                    <strong>{item.name}</strong>
                    <span>
                      {item.source_type === "sheet"
                        ? t("文本曲谱")
                        : t(playlistSourceLabel(item))}
                      {translateNode(
                        !item.midi_available && item.source_type === "midi"
                          ? item.cache_available
                            ? " · 仅缓存"
                            : " · 文件缺失"
                          : "",
                      )}
                    </span>
                  </div>
                </div>
                <span className="playlist-mode-pill">
                  {translateNode(
                    item.humanization_mode === "disabled" || item.humanization_active === false
                      ? "未启用模拟"
                      : item.humanization_mode === "global" ? "跟随全局模拟预设"
                      : item.random_seed_mode === "dynamic" && item.random_effect_active !== false
                        ? "每次随机"
                        : "固定演奏",
                  )}
                </span>
                <span className="playlist-duration">
                  {translateNode(time(item.duration))}
                </span>
                <Button
                  variant="icon"
                  title={t("歌曲操作")}
                  onClick={(e) => {
                    e.stopPropagation();
                    if (!playlist.selected.includes(item.id))
                      playlist.setSelected([item.id]);
                    setMenu({
                      x: Math.min(e.clientX, window.innerWidth - 210),
                      y: Math.min(e.clientY, window.innerHeight - 240),
                    });
                  }}
                >
                  <DotsThreeIcon />
                </Button>
              </div>
            )),
          )}
        </div>
        <aside className="playlist-inspector">
          <Card
            title={
              selectedItems.length > 1
                ? `已选择 ${selectedItems.length} 首`
                : "曲目详情"
            }
          >
            {translateNode(
              lead ? (
                <>
                  <h2>{lead.name}</h2>
                  <p className="playlist-muted">
                    {t(playlistSourceLabel(lead))}
                  </p>
                  <dl>
                    <dt>{t("类型")}</dt>
                    <dd>
                      {translateNode(
                        lead.source_type === "sheet" ? "文本曲谱" : "MIDI",
                      )}
                    </dd>
                    <dt>{t("时长")}</dt>
                    <dd>{translateNode(time(lead.duration))}</dd>
                    <dt>{t("原始文件")}</dt>
                    <dd>
                      {translateNode(
                        lead.source_type === "sheet"
                          ? "包含完整文本"
                          : lead.midi_available
                            ? "已保留本地副本"
                            : "未提供",
                      )}
                    </dd>
                    <dt>{t("编译缓存")}</dt>
                    <dd>
                      {translateNode(
                        lead.cache_available ? "可用" : "播放时生成",
                      )}
                    </dd>
                  </dl>
                  <Button
                    variant="accent"
                    disabled={playlist.busy}
                    onClick={() => void playlist.play(lead.id)}
                  >
                    <PlayIcon />
                    {t("播放选中曲目")}
                  </Button>
                  <Button
                    disabled={playlist.busy}
                    onClick={() =>
                      selectedItems.length === 1
                        ? void edit(lead.id)
                        : setBatchOpen(true)
                    }
                  >
                    {translateNode(
                      selectedItems.length === 1 ? "修改歌曲" : "批量修改设置",
                    )}
                  </Button>
                  {lead.source_type === "sheet" &&
                    selectedItems.length === 1 && (
                      <Button
                        disabled={playlist.busy}
                        onClick={async () =>
                          setSheetDetail(await getPlaylistSong(lead.id))
                        }
                      >
                        {t("修改曲谱内容")}
                      </Button>
                    )}
                  <Button
                    disabled={
                      playlist.busy ||
                      !selectedItems.some((i) => i.midi_available)
                    }
                    onClick={() => void playlist.saveMidi(playlist.selected)}
                  >
                    {t("原始 MIDI 另存为")}
                  </Button>
                  <Button
                    danger
                    disabled={playlist.busy}
                    onClick={() => void playlist.remove(playlist.selected)}
                  >
                    <TrashIcon />
                    {t("删除所选")}
                  </Button>
                </>
              ) : (
                <p className="playlist-muted">
                  {t(
                    "选择曲目查看信息。按住 Ctrl 多选，按住 Shift 连选，拖动调整顺序。",
                  )}
                </p>
              ),
            )}
          </Card>
          <div className="playlist-hint">
            {t(
              "普通歌单保存路径与参数；完整包包含 MIDI、文本与缓存，可用于迁移。",
            )}
          </div>
        </aside>
      </div>
      <div className="playlist-footer">
        <span>
          {translateNode(
            playlist.progress || `已选择 ${playlist.selected.length} 首`,
          )}
        </span>
        <div>
          <Button
            disabled={playlist.busy || !playlist.items.length}
            title={t("全选整个歌库（包含搜索隐藏项），快捷键 Ctrl+A")}
            onClick={() =>
              playlist.setSelected(playlist.items.map((i) => i.id))
            }
          >
            {t("全选")}
          </Button>
          <Button
            danger
            disabled={playlist.busy || !playlist.items.length}
            onClick={() =>
              void playlist.remove(playlist.items.map((i) => i.id))
            }
          >
            {t("清空歌单")}
          </Button>
        </div>
      </div>
      {translateNode(
        menu && (
          <div
            className="playlist-context-menu"
            style={{ left: menu.x, top: menu.y }}
          >
            {translateNode(
              lead && (
                <>
                  <Button
                    variant="bare"
                    onClick={() => void playlist.play(lead.id)}
                  >
                    {t("播放")}
                  </Button>
                  <Button
                    variant="bare"
                    onClick={() =>
                      selectedItems.length > 1
                        ? setBatchOpen(true)
                        : void edit(lead.id)
                    }
                  >
                    {translateNode(
                      selectedItems.length > 1 ? "批量修改歌曲" : "修改歌曲",
                    )}
                  </Button>
                  <Button
                    variant="bare"
                    disabled={selectedItems.length !== 1}
                    onClick={() =>
                      setNameDialog({
                        id: lead.id,
                        title: "重命名歌曲",
                        initial: lead.name,
                      })
                    }
                  >
                    {t("重命名")}
                  </Button>
                  <Button
                    variant="bare"
                    disabled={!selectedItems.some((i) => i.midi_available)}
                    onClick={() => void playlist.saveMidi(playlist.selected)}
                  >
                    {t("批量保存 MIDI")}
                  </Button>
                  <Button
                    variant="bare"
                    danger
                    onClick={() => void playlist.remove(playlist.selected)}
                  >
                    {t("删除所选")}
                  </Button>
                </>
              ),
            )}
          </div>
        ),
      )}
      {transfer && (
        <Modal
          title={t(transfer === "import" ? "导入歌单" : "导出歌单")}
          width={560}
          height={310}
          onClose={() => setTransfer(null)}
          footer={
            <Button onClick={() => setTransfer(null)}>{t("取消")}</Button>
          }
        >
          <div className="transfer-choices">
            {transfer === "import" ? (
              <>
                <Button
                  variant="accent"
                  onClick={() => {
                    setTransfer(null);
                    void playlist.importPackage();
                  }}
                >
                  {t("选择新旧版歌单文件（推荐）")}
                </Button>
                <p>{t("自动识别新旧版 .humidiplaylist、.json 和 ZIP 完整包；也可选择旧歌库的 index.json。")}</p>
                <Button
                  onClick={() => {
                    setTransfer(null);
                    void playlist.importOldLibrary();
                  }}
                >
                  {t("读取本地歌库文件夹")}
                </Button>
                <p>{t("仅在没有导出文件时使用；这里选择本地歌库文件夹，不能选择歌单文件。")}</p>
              </>
            ) : (
              <>
                <Button
                  variant="accent"
                  onClick={() => {
                    setTransfer(null);
                    void playlist.exportPackage(true);
                  }}
                >
                  {t("完整包（推荐）")}
                </Button>
                <p>
                  {t(
                    "包含 MIDI 原件、文本曲谱、独立设置和可用缓存，适合备份与迁移。",
                  )}
                </p>
                <Button
                  onClick={() => {
                    setTransfer(null);
                    void playlist.exportPackage(false);
                  }}
                >
                  {t("普通歌单")}
                </Button>
                <p>{t("仅保存设置与文件路径，MIDI 仍需存在于本机。")}</p>
              </>
            )}
          </div>
        </Modal>
      )}
      {translateNode(
        nameDialog && (
          <NameDialog
            {...nameDialog}
            onClose={() => setNameDialog(null)}
            onSave={(name) => {
              if (nameDialog.id) void playlist.rename(nameDialog.id, name);
              setNameDialog(null);
            }}
          />
        ),
      )}
      {translateNode(
        batchOpen && <BatchDialog onClose={() => setBatchOpen(false)} />,
      )}
      {translateNode(
        sheetDetail && (
          <SheetEditDialog
            detail={sheetDetail}
            onClose={() => setSheetDetail(null)}
          />
        ),
      )}
    </div>
  );
}

export function PlaylistMini() {
  const playlist = usePlaylist();
  return (
    <div className="playlist-mini">
      <Select
        aria-label={t("歌单曲目")}
        value={playlist.selected[0] ?? playlist.currentId ?? ""}
        onChange={(e) => playlist.setSelected([e.target.value])}
      >
        <option value="" disabled>
          {t("选择曲目")}
        </option>
        {translateNode(
          playlist.items.map((i) => (
            <option key={i.id} value={i.id}>
              {i.name}
            </option>
          )),
        )}
      </Select>
      <Select
        value={playlist.mode}
        aria-label={t("歌单模式")}
        onChange={(e) => playlist.setMode(e.target.value as PlaylistMode)}
      >
        {translateNode(
          Object.entries(MODE_LABELS).map(([v, label]) => (
            <option key={v} value={v}>
              {translateNode(label)}
            </option>
          )),
        )}
      </Select>
    </div>
  );
}
