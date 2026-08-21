# HuMidi: Xingkong Edition v2.0.0-xk.1 — 高级歌单与模拟人演奏版

本版本基于 HuMidi v2.0 扩展，保留原有 UI、MIDI 处理与 Roblox 钢琴播放核心，并加入中英文界面、高级歌单、可迁移歌单包、歌曲修改、原 MIDI 管理，以及可重复或动态变化的“模拟人演奏”系统。


### Performance Optimization

The Playback page includes an optional **Performance Optimization** switch for exceptionally dense MIDI files. When enabled, HuMidi collapses physically identical same-timestamp attacks, improves Windows timer precision, and reduces UI update pressure while retaining the original `pynput` input backend. Leave it disabled to use the original playback logic.

## 主要功能

### 歌单歌曲不再只是 Playback 缓存

每首新歌会保存：

- 原始 MIDI 的本地副本；
- 原 MIDI 文件名及原路径信息；
- 轨道选择和左右手分配；
- 速度、移调、踏板、88 键布局等播放参数；
- 模拟人演奏模式、详细参数与随机种子设置；
- 固定演奏模式下的可选编译缓存，用于快速开始播放；
- 精确可视化音符、踏板区间、Tempo 和拍号信息（缓存存在时）。

本地歌单目录：

```text
%USERPROFILE%\.humidi-xingkong\playlist
├── index.json
├── items\       # 歌曲参数与来源信息
├── midi\        # 歌单保存的 MIDI 副本
└── cache\       # 固定演奏的编译缓存
```

### 修改歌单歌曲

在“歌单”页面右键歌曲：

- **播放**；
- **修改歌曲**：回到“播放”页面，载入这首歌的 MIDI、轨道和参数；
- **将 MIDI 另存为…**：提取歌单中保存的原 MIDI 副本；
- **删除**。

进入修改状态后，“加入歌单”按钮会变成 **完成修改**。点击后会覆盖当前歌曲的参数、轨道选择和缓存，而不是新增重复歌曲。

### 模拟人演奏模式

播放页面新增“模拟人演奏模式”：

- **禁用**：关闭所有模拟人演奏选项，详细设置变灰；
- **启用（使用全局配置）**：使用“设置 → 全局模拟人演奏”中的统一参数，歌曲页面中的详细选项只读；
- **启用（单独配置）**：为当前 MIDI 或歌单歌曲单独设置。

“设置”页面提供 **全局模拟人演奏** 配置按钮。修改全局配置会在使用全局配置的歌曲下次编译时生效。

### 随机性与种子

启用模拟人演奏后，可以选择：

- **动态随机种子**：每次播放重新生成演奏结果；种子输入框不可编辑；歌单每次从 MIDI 重新编译，不保存固定缓存；
- **固定随机种子**：程序随机生成一个种子并显示在灰色输入框中；只要模拟人演奏模式和相关选项不变，每次演奏一致，并保存编译缓存；修改相关选项或全局预设后会生成新种子；
- **固定自定义种子**：种子输入框可编辑；相同 MIDI、参数和种子会生成可重复的演奏，并保存编译缓存。

因此可以同时满足：

- 每次略有不同的“真人重新演奏”；
- 可稳定复现、快速加载的固定演奏；
- 用户指定种子的跨电脑复现。

### 歌单导入与导出

导出时可以选择两种方式，扩展名都为 `.humidiplaylist`：

1. **普通导出**
   - 保存歌曲路径、参数、轨道选择和种子设置；
   - 文件较小；
   - 不嵌入 MIDI 与缓存；
   - 换电脑后原路径不存在时，歌曲需要重新定位或重新加入。

2. **完整导出**
   - 内嵌每首歌的 MIDI 副本；
   - 内嵌已有的固定编译缓存；
   - 保留全部歌曲参数和轨道选择；
   - 适合分享和迁移；
   - 分享包会移除无必要的绝对 MIDI 路径，避免泄露 Windows 用户目录。

完整 `.humidiplaylist` 内部是压缩包结构，程序会自动识别，无需手动解压。

### 歌单播放模式

支持：

- 单曲播放；
- 单曲循环；
- 全部循环；
- 顺序播放；
- 随机播放。

在歌单页面选择歌曲后，歌单内播放按钮、底部全局播放按钮和播放快捷键都会从当前歌单项开始播放。

### 中英文与窗口状态

语言选项：

- 自动选择（当前系统语言）；
- 简体中文；
- English。

简体中文或繁体中文系统在自动模式下使用简体中文。默认窗口为 `1040 × 640`，最小展开尺寸为 `900 × 560`。播放进度下方会显示当前歌曲与来源，例如播放页面试听、已保存 Playback、歌单模式或乐谱转换试听。

## 可视化一致性

新缓存会保存最终编译事件和同一批最终可视化数据。固定种子模式下，播放页面试听、保存、加入歌单及再次播放会使用一致的编译结果；重叠同音会使用引用计数，避免长音条消失或钢琴键过早熄灭。

动态随机种子本来就会在每次演奏时生成不同结果，因此不保证两次时间轴完全相同，但同一次播放中的可视化与实际按键事件保持一致。

## 运行源码

```powershell
python -m pip install -r requirements.txt
python main.py
```

## 打包单文件 EXE

在包含 `main.py` 和 `icon.ico` 的项目根目录运行：

```powershell
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "HuMidi-Xingkong-Edition" --icon ".\icon.ico" --add-data ".\icon.ico;." --add-data ".\NOTICE.md;." --add-data ".\THIRD_PARTY_NOTICES.md;." main.py
```

生成文件：

```text
dist\HuMidi-Xingkong-Edition.exe
```

配置和歌单写入 `%USERPROFILE%\.humidi-xingkong`，不会写入 PyInstaller 的临时解压目录，也不会与上游 HuMidi 共用配置。建议在没有安装 Python 的 Windows 电脑上再做一次发布前测试。

## 兼容性与注意事项

- 旧版仅含编译事件的 Playback 和歌单项仍可播放，并会按需迁移；缺失的原 MIDI 无法凭缓存反向恢复，因此“修改歌曲”和“将 MIDI 另存为”会不可用。
- 普通导出依赖原 MIDI 路径；完整导出才是可独立迁移的分享包。
- 动态随机歌曲每次播放需要重新解析和编译，大型 MIDI 的开始时间会比固定缓存模式长。
- 导入同一歌单多次会保留重复条目，不会自动覆盖现有歌曲。
- 更新检查仅连接 Xingkong Edition 自己的 Releases 页面，并由用户手动选择下载，不会自动替换程序。

---

## English overview

This build keeps the original HuMidi v2.0 playback core and adds a bilingual UI, an advanced playlist song model, editable playlist songs, embedded MIDI packages, optional compiled caches, global/individual human-like performance settings, and dynamic/fixed/custom random seeds.

A playlist song stores its MIDI copy, track roles, playback parameters, simulation settings, seed policy, and—when deterministic—an exact compiled cache. Right-click a song to **Modify Song** or **Save MIDI As…**. Modification opens the Playback page and changes **Add to Playlist** into **Complete Modification**.

Normal `.humidiplaylist` exports store paths and settings only. Complete exports embed MIDI files and available caches for sharing. Dynamic seeds recompile on every performance; fixed random and custom seeds produce repeatable cached performances.

## Batch MIDI import

Use **Import MIDI (Multi-select)** on the Playback page to select one or more `.mid`/`.midi` files. For multiple files, HuMidi offers:

- **Process All Automatically**: selects playable non-drum tracks automatically.
- **Let Me Choose**: opens the track/hand chooser for each MIDI.
- If automatic selection cannot find a track, HuMidi asks you to choose manually, ignore that file, or ignore all later files with the same problem.

After preparation, the result window lists successful and failed files. You can add all prepared files directly to the playlist or continue to the Playback page and apply the current playback/simulated-performance settings to the whole batch.

## Playlist multi-selection and ordering

- Hold **Ctrl** while clicking rows to select multiple songs.
- Drag one selected row to move it, or drag any row in a multi-selection to move the selected songs together.
- A white insertion line shows the destination position.
- Right-click a multi-selection for batch modify, batch MIDI save-as, or batch delete.

## Keyboard shortcuts

Open **Settings → Keyboard Shortcuts**. Play/Pause, Stop, Previous Song, and Next Song each accept up to two bindings. Standard keys, function keys, letters, numbers, and Windows media transport keys are supported.

## 设置页面滚动与文本乐谱歌单

- 设置页面保持原窗口尺寸；各设置卡片不再被纵向压扁，空间不足时使用右侧滚动条。
- “乐谱转换”页面可为文本乐谱填写名称并直接加入歌单。
- 文本乐谱歌单项保存原始乐谱、格式、BPM、时长和演奏设置，可从歌单播放并右键修改。
- 单个文本乐谱不会显示“将 MIDI 另存为…”。仅选择文本乐谱时，多选菜单只保留批量删除。
- MIDI 与文本乐谱混合多选时仍显示 MIDI 批量操作；执行前会提示文本乐谱不支持，并允许“只处理 MIDI”。
- 普通与完整 `.humidiplaylist` 均可保存文本乐谱；文本乐谱本身已自包含，不依赖外部 MIDI 文件。

## Text-sheet playlist support

The Settings page now scrolls vertically instead of compressing its cards. Translator text sheets can be named, added to the playlist, played in every playlist mode, and modified from the single-item context menu. Text-sheet entries are self-contained in both normal and complete playlist exports. MIDI-only commands are hidden for sheet-only selections, while mixed selections can explicitly process only their MIDI entries.

## Latest interaction improvements

- Settings scrolls normally even when the pointer is over Opacity, Theme, or Language controls.
- Ctrl + pointer sweep selects multiple playlist rows; after releasing Ctrl and the mouse, the selected block can be reordered together.
- Reorder dragging supports mouse-wheel and edge-triggered scrolling.
- Translator text sheets can be started from the global Play button or play shortcut.
- Countdown duration can be adjusted from the Playback page.
- Save/Reset now live on the Playback page; Previous/Next are available in the global transport.
- Mini mode contains a playback-mode selector and a scrollable compact playlist.
