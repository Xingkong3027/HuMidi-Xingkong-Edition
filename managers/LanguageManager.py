from __future__ import annotations

from PyQt6.QtCore import QEvent, QLocale, QObject
from PyQt6.QtWidgets import (
    QApplication,
    QAbstractButton,
    QDialog,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMainWindow,
    QWidget,
)


ZH_CN = {
    # Navigation and primary controls
    "Playback": "播放",
    "Playlist": "歌单",
    "Visualizer": "可视化",
    "Translator": "乐谱转换",
    "Settings": "设置",
    "Debug": "调试",
    "License": "许可证",
    "Humanize": "模拟人演奏",
    "▶  Play": "▶  播放",
    "■  Stop": "■  停止",
    "Save": "保存",
    "Save Playback": "保存存档",
    "Reset": "重置",
    "▲  Collapse": "▲  收起",
    "▼  Expand": "▼  展开",
    "Play": "播放",
    "Pause": "暂停",
    "Resume": "继续",
    "Stop": "停止",
    "Previous": "上一首",
    "Next": "下一首",
    "Import": "导入",
    "Export": "导出",
    "Delete": "删除",
    "Clear": "清空",
    "Modify Song": "修改歌曲",
    "Save MIDI As…": "将 MIDI 另存为…",
    "Save MIDI As": "将 MIDI 另存为",
    "Normal Export": "普通导出",
    "Complete Export": "完整导出",
    "Browse": "浏览",
    "Browse…": "浏览…",
    "Load": "加载",
    "Load Save": "加载存档",
    "Change": "更改",
    "Listening...": "正在监听…",
    "Checking...": "正在检查…",
    "Check for updates": "检查更新",
    "Customize…": "自定义…",
    "Copy Log": "复制日志",
    "Copy to Clipboard": "复制到剪贴板",

    # Playback tab
    "MIDI File": "MIDI 文件",
    "No file selected.": "尚未选择文件。",
    "Playback Settings": "播放设置",
    "Tempo": "速度",
    "Pedal": "踏板",
    "Pedal Style": "踏板模式",
    "Transpose": "移调",
    "88-Key Layout": "88 键布局",
    "Countdown": "倒计时",
    "Trim": "裁剪",
    "Auto": "自动",
    "Trim leading and trailing silence by selecting a playback range": "通过选择播放范围裁剪 MIDI 前后的空白时间",
    "Automatically detect the first and last playable notes": "自动检测第一个和最后一个可播放音符",
    "Trim end must be later than trim start.": "裁剪结束时间必须晚于开始时间。",
    "The selected trim range contains no playable notes.": "所选裁剪范围内没有可播放的音符。",
    "Performance Optimization": "性能优化",
    "Reduce input overhead for complex MIDI files by collapsing duplicate simultaneous physical keystrokes while retaining HuMidi's pynput input backend. Disable to use the original playback logic.": "通过合并同时发生的重复物理按键来降低复杂 MIDI 的输入开销，同时保留 HuMidi 的 pynput 输入方式。关闭后使用原有播放逻辑。",
    "Debug Output": "调试输出",
    "Humanization": "模拟人演奏",
    "Human-like Performance": "模拟人演奏",
    "Human-like Performance Mode": "模拟人演奏模式",
    "Disabled": "禁用",
    "Enabled (Use Global Settings)": "启用（使用全局配置）",
    "Enabled (Individual Settings)": "启用（单独配置）",
    "Randomness": "随机性",
    "Dynamic Random Seed": "动态随机种子",
    "Fixed Random Seed": "固定随机种子",
    "Fixed Custom Seed": "固定自定义种子",
    "Random Seed": "随机种子",
    "Generated for every playback": "每次演奏时重新生成",
    "Complete Modification": "完成修改",
    "All": "全部",
    "Simulate Hands": "模拟双手",
    "Chord Roll": "和弦滚奏",
    "Chord Rolling": "和弦滚奏",
    "Mistake Chance": "失误概率",
    "Hybrid": "混合",
    "Legato": "连奏",
    "Inverted": "反转",
    "Vary Timing": "时序变化",
    "Vary Articulation": "奏法变化",
    "Hand Drift": "双手漂移",
    "Mistakes": "失误",
    "Tempo Sway": "速度摇摆",
    "Invert Tempo Sway": "反转速度摇摆",
    "Invert Sway": "反转摇摆",
    "Add to Playlist": "加入歌单",
    "Auto (Default)": "自动（默认）",
    "Harmonic": "和声",
    "Rhythmic": "节奏",
    "None": "无",

    # Playlist
    "My Playlist": "我的歌单",
    "Playback Mode": "播放模式",
    "Single Play": "单曲播放",
    "Single Repeat": "单曲循环",
    "Repeat All": "全部循环",
    "Sequential": "顺序播放",
    "Shuffle": "随机播放",
    "No songs in the playlist.": "歌单中还没有歌曲。",
    "Name": "名称",
    "Source": "来源",
    "Duration": "时长",
    "Songs": "歌曲",
    "Playlist file": "歌单文件",
    "MIDI Files": "MIDI 文件",
    "JSON Files": "JSON 文件",
    "All Files": "所有文件",

    # Settings
    "Save Path": "保存路径",
    "Hotkey": "快捷键",
    "Hotkey: ": "快捷键：",
    "Overlay": "窗口叠加",
    "Always on Top": "窗口置顶",
    "Opacity": "透明度",
    "Timeline": "时间轴",
    "Piano Keys": "钢琴键盘",
    "AI Model": "AI 模型",
    "Enable AI Pedal": "启用 AI 踏板",
    "Sorry, still in development!": "抱歉，此功能仍在开发中！",
    "Theme": "主题",
    "Language": "语言",
    "Global Human-like Performance": "全局模拟人演奏",
    "Global Human-like Performance Settings": "全局模拟人演奏设置",
    "Configure…": "配置…",
    "No simulated-performance options enabled": "未启用任何模拟人演奏选项",
    "Automatic (Simplified Chinese)": "自动选择（简体中文）",
    "Automatic (English)": "自动选择（English）",
    "Simplified Chinese": "简体中文",
    "English": "English",

    # Playback status
    "Now Playing: —": "正在播放：—",
    "Source: —": "来源：—",
    "Now Playing: {name}": "正在播放：{name}",
    "Now Playing: Pasted Sheet ({format_name})": "正在播放：粘贴的乐谱（{format_name}）",
    "Source: Playback Page Preview": "来源：播放页面试听",
    "Source: Playback Page (Saved Playback Preview)": "来源：播放页面（Playback 存档试听）",
    "Source: Playlist ({mode})": "来源：歌单（{mode}）",
    "Source: Translator Preview": "来源：乐谱转换试听",
    "Pasted Sheet": "粘贴的乐谱",

    # Translator / visualizer / debug / license
    "Format": "格式",
    "Virtual Piano": "虚拟钢琴格式 (Virtual Piano)",
    "Song Name": "歌曲名称",
    "Optional; defaults to Text Sheet": "可选；留空时使用“文本乐谱”",
    "Text Sheet": "文本乐谱",
    "Text Sheet ({format_name})": "文本乐谱（{format_name}）",
    "BPM": "BPM",
    "Paste sheet text:": "粘贴乐谱文本：",
    "▶  Play Sheet": "▶  播放乐谱",
    "Add the pasted text sheet and its settings to the playlist": "将粘贴的文本乐谱及其设置加入歌单",
    "Save the modified text sheet back to this playlist song": "将修改后的文本乐谱保存回这首歌单歌曲",
    "Generated {count} line(s).": "已生成 {count} 行。",
    "Importing sheet: {count} notes at {bpm} BPM ({format_name})": "正在导入乐谱：{count} 个音符，{bpm} BPM（{format_name}）",
    "Output": "输出",
    "Generate Sheet": "生成乐谱",
    "Load a MIDI file on the Playback tab, then click Generate.": "请先在播放页面加载 MIDI 文件，然后点击生成。",
    "Generated sheet will appear here…": "生成的乐谱将显示在这里…",
    "Select the Roblox piano sheet format": "选择 Roblox 钢琴乐谱格式",
    "Tempo used to calculate note durations from the sheet": "用于根据乐谱计算音符时长的速度",
    "Apply current humanization settings during playback.\nWhen unchecked, the sheet plays back exactly as written.": "播放时应用当前模拟人演奏设置。\n取消勾选后将严格按乐谱播放。",
    "Convert the pasted sheet to keystrokes and begin playback": "将粘贴的乐谱转换为按键并开始播放",
    "Convert the currently loaded MIDI notes to sheet text in the selected format": "将当前加载的 MIDI 音符转换为所选格式的乐谱文本",
    "Copy the generated sheet to the clipboard": "将生成的乐谱复制到剪贴板",
    "Clear all log entries": "清空所有日志内容",
    "Copy the full log to clipboard": "将完整日志复制到剪贴板",
    "Software": "软件",
    "Licenses & Credits": "许可证与致谢",
    "HuMidi": "HuMidi",
    "PedalAI Dataset": "PedalAI 数据集",
    "Third-Party Libraries": "第三方库",
    "View:": "查看：",

    # Dialogs
    "Select MIDI File": "选择 MIDI 文件",
    "Select Save Directory": "选择保存目录",
    "Select Tracks": "选择轨道",
    "Track Name": "轨道名称",
    "Instrument": "乐器",
    "Notes": "音符数",
    "Hand Assignment": "手部分配",
    "Select the tracks to include in playback. Optionally override the hand assignment for each track.": "选择要包含在播放中的轨道，并可为每条轨道手动指定左右手。",
    "Notes": "音符数",
    "Role": "作用",
    "Auto-Detect": "自动识别",
    "Left Hand": "左手",
    "Right Hand": "右手",
    "Ignore": "忽略",
    "Load Saved Playback": "加载已保存的 Playback",
    "Rename": "重命名",
    "Rename Save": "重命名存档",
    "Enter custom name (leave blank to revert to timestamp):": "输入自定义名称（留空则恢复为时间戳）：",
    "Are you sure you want to permanently delete this save?": "确定要永久删除此存档吗？",
    "Could not rename file:": "无法重命名文件：",
    "Could not delete file:": "无法删除文件：",
    "Delete Save": "删除存档",
    "Theme Manager": "主题管理器",
    "New": "新建",
    "Delete Theme": "删除主题",
    "Revert": "还原",
    "Choose colour": "选择颜色",
    "Name required": "需要名称",
    "Themes": "主题列表",
    "Built-in — read only": "内置主题（只读）",
    "Custom theme name…": "自定义主题名称…",
    "Duplicate the selected theme as a new custom preset": "复制所选主题为新的自定义预设",
    "Delete this custom theme (built-in themes cannot be deleted)": "删除此自定义主题（内置主题无法删除）",
    "Persist edits to this custom theme": "保存对此自定义主题的修改",
    "Discard unsaved edits": "放弃未保存的修改",
    "Save Changes": "保存更改",

    # Message box titles
    "Information": "提示",
    "Warning": "警告",
    "Error": "错误",
    "No Tracks": "没有轨道",
    "No MIDI Loaded": "未加载 MIDI",
    "No Notes": "没有音符",
    "Parse Error": "解析错误",
    "Export Error": "导出错误",
    "Save Successful": "保存成功",
    "Save Error": "保存错误",
    "Playlist Error": "歌单错误",
    "Add to Playlist": "加入歌单",
    "Import Playlist": "导入歌单",
    "Export Playlist": "导出歌单",
    "Delete Song": "删除歌曲",
    "Clear Playlist": "清空歌单",
    "Missing Song": "歌曲数据缺失",
    "Modify Song": "修改歌曲",
    "Complete Modification": "完成修改",
    "Save MIDI As": "将 MIDI 另存为",
    "Bind Key": "绑定按键",
    "Unknown Format": "未知格式",
    "Hardware/Execution Failure": "硬件/执行失败",
    "Up to Date": "已是最新版本",
    "Update Available": "发现更新",
    "Update Check Failed": "更新检查失败",
    "Update Failed": "更新失败",

    # Common values
    "Yes": "是",
    "No": "否",
    "Cancel": "取消",
    "OK": "确定",
    "None selected": "未选择任何选项",
    "Unknown MIDI": "未知 MIDI",
    "Compiling...": "正在编译…",
    "Using the exact compiled preview for the playlist...": "正在为歌单复用与试听完全一致的编译结果…",
    "Using the exact compiled preview for saving...": "正在保存与试听完全一致的编译结果…",
    "Could not cache compiled preview: ": "无法缓存试听编译结果：",
    "Press the key you want to bind now.": "请按下要绑定的按键。",
    "Please select a MIDI file and choose tracks first.": "请先选择 MIDI 文件并选择轨道。",
    "Please select at least one track.": "请至少选择一条轨道。",
    "Stop playback before adding the adjusted Playback to the playlist.": "请先停止播放，再将调整好的 Playback 加入歌单。",
    "The selected MIDI file can no longer be found.": "找不到当前选择的 MIDI 文件。",
    "The adjusted Playback was added to the playlist successfully.": "已成功将调整好的 Playback 加入歌单。",
    "Could not compile this Playback for the playlist:": "无法为歌单编译此 Playback：",
    "The selected playlist item could not be loaded:": "无法加载选中的歌单歌曲：",
    "Imported {count} playlist item(s).": "已导入 {count} 首歌曲。",
    "Exported {count} playlist item(s).": "已导出 {count} 首歌曲。",
    "Delete '{name}' from the playlist?": "确定从歌单中删除“{name}”吗？",
    "Remove every song from the playlist? This cannot be undone.": "确定清空歌单吗？此操作无法撤销。",
    "Unsupported playlist format.": "不支持的歌单文件格式。",
    "This playlist was created by a newer HuMidi version.": "此歌单由更新版本的 HuMidi 创建，当前版本无法导入。",
    "Playlist entries are missing or invalid.": "歌单条目缺失或格式无效。",
    "Playback data is not an object.": "Playback 数据格式无效。",
    "Playback metadata is missing.": "Playback 元数据缺失。",
    "Compiled playback events are missing.": "编译后的 Playback 事件缺失。",
    "A compiled event is invalid.": "歌单中存在无效的 Playback 事件。",
    "Failed to parse MIDI:": "MIDI 解析失败：",
    "Could not read MIDI file: {reason}": "无法读取 MIDI 文件：{reason}",
    "The selected file does not contain a valid MIDI header (MThd). It may not be a MIDI file or may be damaged.": "所选文件没有有效的 MIDI 文件头（MThd）。它可能不是 MIDI 文件，或文件已经损坏。",
    "The MIDI track header (MTrk) is missing. The file may be damaged.": "缺少 MIDI 轨道文件头（MTrk），文件可能已经损坏。",
    "The MIDI file ended unexpectedly and may be incomplete or damaged.": "MIDI 文件意外结束，文件可能不完整或已经损坏。",
    "Non-standard MIDI Data": "非标准 MIDI 数据",
    '"{filename}" contains illegal MIDI data bytes. Use clip repair automatically and continue importing?': '"{filename}" 此 MIDI 含有非法数据字节，是否使用 clip 自动修正后继续导入？',
    'Used clip repair for illegal MIDI data bytes in "{filename}".': '已对“{filename}”中的非法 MIDI 数据字节使用 clip 修正。',
    "Clip repair was declined; MIDI import cancelled.": "已拒绝 clip 修正，MIDI 导入已取消。",
    "Clip repair declined by user": "用户拒绝了 clip 修正",
    "No handler found for format: {format_name}": "找不到格式处理器：{format_name}",
    "Failed to parse sheet:": "乐谱解析失败：",
    "No playable notes were found in the pasted sheet.": "粘贴的乐谱中没有找到可播放音符。",
    "Load and prepare a MIDI file on the Playback tab first.": "请先在播放页面加载并准备 MIDI 文件。",
    "Failed to generate sheet:": "生成乐谱失败：",
    "Compilation produced zero events — nothing to save.": "编译结果没有任何事件，无法保存。",
    "Playback process finished.": "播放过程已结束。",
    "HuMidi Xingkong Edition v{version} is the latest version.": "HuMidi Xingkong Edition v{version} 已是最新版本。",
    "Could not reach GitHub.\nPlease check your internet connection.": "无法连接 GitHub。\n请检查网络连接。",
    "Update available to {latest_tag}. Open the GitHub Releases page?": "发现新版本 {latest_tag}，是否打开 GitHub Releases 页面？",
    "Stop playback before saving this song to the playlist.": "请先停止播放，再保存这首歌的歌单设置。",
    "The song was added to the playlist successfully.": "歌曲已成功加入歌单。",
    "The playlist song was modified successfully.": "歌单歌曲已修改成功。",
    "Could not compile this song for the playlist:": "无法为歌单编译这首歌曲：",
    "Could not update playlist cache: ": "无法更新歌单缓存：",
    "The original MIDI file for this playlist song is unavailable.": "这首歌单歌曲的原始 MIDI 文件不可用。",
    "The text sheet for this playlist song is unavailable.": "这首歌单歌曲的文本乐谱不可用。",
    "The text sheet was added to the playlist successfully.": "文本乐谱已成功加入歌单。",
    "The text sheet was modified successfully.": "文本乐谱已修改成功。",
    "Editing playlist sheet: ": "正在修改歌单乐谱：",
    "No stored playable tracks were found.": "没有找到已保存的可播放轨道。",
    "Compiling playlist performance...": "正在编译歌单演奏…",
    "Stop playback before modifying a playlist song.": "请先停止播放，再修改歌单歌曲。",
    "Editing playlist song: ": "正在修改歌单歌曲：",
    "The MIDI file was saved successfully.": "MIDI 文件已成功保存。",
    "Choose how to export the playlist.": "请选择歌单导出方式。",
    "Normal export stores song paths, parameters, track choices, and seed settings. Complete export additionally embeds the original MIDI files and compiled caches.": "普通导出保存歌曲路径、参数、轨道选择和随机种子设置；完整导出还会嵌入原始 MIDI 文件和已编译缓存。",
    "Playlist item data is invalid.": "歌单歌曲数据无效。",
    "Playlist package manifest is missing or invalid.": "完整歌单包的清单缺失或无效。",
    "The original MIDI file is not available for this song.": "这首歌曲的原始 MIDI 文件不可用。",
    "Songs set to 'Enabled (Use Global Settings)' use these options. Changing this preset affects their next compilation.": "设置为“启用（使用全局配置）”的歌曲会使用这些选项；修改此预设会影响它们下一次编译。",

    # Tooltips / descriptions
    "Enable or disable all humanization at once": "一次启用或禁用全部模拟人演奏选项",
    "Open a MIDI file for playback": "打开用于播放的 MIDI 文件",
    "Open a MIDI file to play": "打开一个 MIDI 文件进行播放",
    "Load a saved playback": "加载已保存的 Playback",
    "Load a previously saved humanized performance": "加载此前保存的模拟人演奏",
    "Save the current playback": "保存当前 Playback",
    "Start, pause, or resume playback": "开始、暂停或继续播放",
    "Stop playback and reset to the beginning": "停止播放并回到开头",
    "Save the current humanized performance to a file for later replay": "保存当前模拟人演奏，供以后直接播放",
    "Save the current simulated performance to a file for later replay": "保存当前模拟人演奏，供以后直接播放",
    "Reset all playback settings to their default values": "将播放设置恢复为默认值",
    "Reset all settings to their default values": "将所有设置恢复为默认值",
    "Collapse to mini mode": "收起到迷你模式",
    "Restore full window": "恢复完整窗口",
    "Playback speed as a percentage of the original tempo": "以原始速度百分比调整播放速度",
    "Auto (Default): AI-driven pedal using a hybrid of rhythmic and harmonic analysis\nHarmonic: Hold pedal through harmonic regions, releasing at chord/bass changes\nRhythmic: Release pedal on beat boundaries only\nNone: No sustain pedal": "自动（默认）：结合节奏与和声分析的智能踏板\n和声：在和声区域持续踩下，并在和弦或低音变化时释放\n节奏：仅在节拍边界释放踏板\n无：不使用延音踏板",
    "Shift all notes up or down by the given number of semitones": "按指定半音数升高或降低全部音符",
    "Map notes to the full 88-key piano layout instead of a compressed keyboard layout": "将音符映射到完整 88 键钢琴布局，而不是压缩键盘布局",
    "Show a 3-second countdown before playback begins": "播放开始前显示 3 秒倒计时",
    "Show a {seconds}-second countdown before playback begins": "播放开始前显示 {seconds} 秒倒计时",
    "Countdown {seconds} seconds": "倒计时{seconds}秒",
    "Print verbose event logs to the Debug tab during playback": "播放期间在调试页面输出详细事件日志",
    "Enable or disable all humanization options at once": "一次启用或禁用全部模拟人演奏选项",
    "Assign notes to left/right hand and limit simultaneous finger usage to simulate realistic hand behavior": "分配左右手并限制同时使用的手指数量，以模拟更真实的演奏",
    "Slightly stagger the notes within each chord to simulate the natural roll of fingers across the keys": "轻微错开和弦内音符，模拟手指自然滚过琴键",
    "Add random timing offsets to note events (in seconds)": "为音符事件添加随机时序偏移（秒）",
    "Randomize note hold duration — lower values create a more staccato feel": "随机改变音符保持时长；数值越低越偏向断奏",
    "Simulate gradual timing drift between the left and right hands": "模拟左右手之间逐渐产生的时序漂移",
    "Randomly skip notes to simulate human errors": "随机跳过音符以模拟人为失误",
    "Add a slow sinusoidal tempo variation over musical sections": "在乐段中加入缓慢的正弦速度变化",
    "Apply a sinusoidal tempo variation across the song for a more expressive feel": "在整首歌曲中应用正弦速度变化，使演奏更富有表现力",
    "Invert the phase of the tempo sway curve": "反转速度摇摆曲线的相位",
    "Directory where humanized performance saves are stored": "模拟人演奏存档的保存目录",
    "Choose where to save humanized performance files": "选择模拟人演奏文件的保存位置",
    "Click to bind a new hotkey for toggling playback": "点击绑定用于切换播放状态的新热键",
    "Keep this window above all other windows": "让此窗口保持在其他窗口上方",
    "Adjust window transparency (20–100%)": "调整窗口透明度（20–100%）",
    "Check GitHub for a newer version of HuMidi Xingkong Edition": "在 GitHub 检查 HuMidi Xingkong Edition 新版本",
    "Show the piano-roll timeline in the Visualizer tab (disable for a simple seek slider)": "在可视化页面显示钢琴卷帘时间轴（关闭后仅显示进度滑块）",
    "Show the piano key visualizer in the Visualizer tab": "在可视化页面显示钢琴键盘",
    "Switch the application colour theme": "切换应用程序配色主题",
    "Open the theme editor to create or modify colour presets": "打开主题编辑器以创建或修改配色预设",
    "Compile the adjusted Playback settings and add this song to the playlist": "编译当前调整好的 Playback 参数并将歌曲加入歌单",
    "Play the selected playlist item": "播放选中的歌单歌曲",
    "Play the previous playlist item": "播放上一首歌单歌曲",
    "Play the next playlist item": "播放下一首歌单歌曲",
    "Import a HuMidi playlist file": "导入 HuMidi 歌单文件",
    "Export the complete playlist, including compiled playback data": "导出完整歌单（包含编译后的 Playback 数据）",
    "Delete the selected song from the playlist": "从歌单中删除选中的歌曲",
    "Remove every song from the playlist": "移除歌单中的全部歌曲",
    "Enable or disable simulated human performance": "启用或禁用模拟人演奏",
    "Enable or disable all human-like performance options at once": "一次启用或禁用全部模拟人演奏选项",
    "Store the original MIDI, current settings, track choices, and optional compiled cache in the playlist": "将原始 MIDI、当前参数、轨道选择和可选编译缓存保存到歌单",
    "Save the modified settings back to this playlist song": "将修改后的设置保存回这首歌单歌曲",
    "Configure the preset used by songs set to Enabled (Use Global Settings)": "配置“启用（使用全局配置）”歌曲所使用的预设",
    # Batch MIDI import, playlist multi-selection, and shortcuts
    "Import MIDI (Multi-select)": "导入 MIDI（可多选）",
    "Import one or more MIDI files": "导入一个或多个 MIDI 文件",
    "Select MIDI Files": "选择 MIDI 文件（可多选）",
    "Batch Import MIDI": "批量导入 MIDI",
    "Importing {count} MIDI files. How should track selection and hand assignment be handled?": "正在导入 {count} 个 MIDI 文件，请选择如何处理轨道与手部分配设置。",
    "Process All Automatically": "全部自动处理",
    "Let Me Choose": "由我选择",
    "Preparing MIDI files…": "正在准备 MIDI 文件…",
    "Preparing {current}/{total}: {name}": "正在准备 {current}/{total}：{name}",
    "This MIDI could not be selected automatically. Please choose at least one track to continue.": "该 MIDI 无法被自动选择，请至少勾选一条轨道后继续。",
    "Ignore All": "忽略所有",
    "Confirm and Continue": "确定并继续",
    "Batch Import Results": "批量导入结果",
    "Successfully prepared {success} MIDI file(s); {failed} file(s) were not prepared.": "成功准备 {success} 个 MIDI 文件，{failed} 个未成功。",
    "Successfully imported:": "成功导入：",
    "Not imported:": "未成功导入：",
    "Continue Settings": "继续设置",
    "Skipped by user": "用户已跳过",
    "Automatic track selection found no playable tracks": "自动选择未找到可播放轨道",
    "Ignored": "已忽略",
    "No tracks selected": "未选择轨道",
    "Cancelled": "已取消",
    "Batch import: {count} MIDI files (previewing {name})": "批量导入：{count} 个 MIDI（当前预览 {name}）",
    "Add {count} MIDI Files to Playlist": "将 {count} 个 MIDI 加入歌单",
    "Apply the current playback settings to every prepared MIDI file and add them to the playlist": "将当前播放设置应用到全部已准备的 MIDI，并加入歌单",
    "Complete Batch Modification ({count})": "完成批量修改（{count}）",
    "Apply the current playback settings to all selected playlist songs": "将当前播放设置应用到全部选中的歌单歌曲",
    "Choose whether to apply only changed values or all values to the selected songs": "完成时可选择仅修改变动值，或将全部设置应用到所选歌曲",
    "Batch Modify Songs": "批量修改歌曲",
    "Preparing songs for batch modification…": "正在准备批量修改歌曲…",
    "Reading {current}/{total}: {name}": "正在读取 {current}/{total}：{name}",
    "Batch modification preparation was canceled.": "已取消准备批量修改。",
    "Complete Batch Modification": "完成批量修改",
    "Choose how to apply the batch modification.": "请选择如何应用本次批量修改。",
    "Only Apply Changed Values": "仅修改变动值",
    "Apply All Values": "全部修改",
    "No playback setting has changed.": "没有检测到发生变化的播放设置。",
    "Batch Save MIDI As…": "批量将 MIDI 另存为…",
    "Batch Save MIDI As": "批量将 MIDI 另存为",
    "Batch Delete": "批量删除",
    "Delete the selected song or songs from the playlist": "删除歌单中选中的一首或多首歌曲",
    "Export the playlist with visible progress": "导出歌单并显示进度",
    "Stop playback before starting a batch playlist operation.": "开始批量歌单操作前请先停止播放。",
    "Preparing batch playlist operation…": "正在准备批量歌单操作…",
    "Batch Add to Playlist": "批量加入歌单",
    "Processing {current}/{total}: {name}": "正在处理 {current}/{total}：{name}",
    "Another compilation is already running": "另一个编译任务正在运行",
    "Batch operation completed: {success} succeeded, {failed} failed.": "批量操作完成：成功 {success} 个，失败 {failed} 个。",
    "Succeeded:": "成功：",
    "Failed:": "失败：",
    "Stop playback before modifying playlist songs.": "批量修改歌单歌曲前请先停止播放。",
    "The original MIDI file is unavailable.": "原始 MIDI 文件不可用。",
    "Some selected songs are text sheets and do not support this operation.": "所选歌曲中包含文本乐谱，文本乐谱不支持此操作。",
    "Only Process MIDI": "只处理 MIDI",
    "The selected songs are all text sheets and do not support this operation.": "所选歌曲全部是文本乐谱，不支持此操作。",
    "None of the selected songs can be modified.": "所选歌曲均无法修改。",
    "Some selected songs were skipped:": "部分所选歌曲已跳过：",
    "Batch modifying {count} songs (previewing {name})": "正在批量修改 {count} 首歌曲（当前预览 {name}）",
    "The current playback settings will be applied to all selected songs. Each song keeps its own MIDI and track selection.": "当前播放设置将应用到全部所选歌曲；每首歌曲会保留各自的 MIDI 和轨道选择。",
    "Saving MIDI files…": "正在保存 MIDI 文件…",
    "Saving {current}/{total}: {name}": "正在保存 {current}/{total}：{name}",
    "Saved {success} MIDI file(s); {failed} failed.": "已保存 {success} 个 MIDI 文件，{failed} 个失败。",
    "Delete {count} selected songs from the playlist? This cannot be undone.": "确定从歌单删除选中的 {count} 首歌曲吗？此操作无法撤销。",
    "Exporting playlist…": "正在导出歌单…",
    "Exporting {current}/{total}: {name}": "正在导出 {current}/{total}：{name}",
    "Normal export stores MIDI paths plus all song parameters, track choices, seeds, and self-contained text sheets. Complete export additionally embeds the original MIDI files and compiled caches.": "普通导出会保存 MIDI 路径、全部歌曲参数、轨道选择、随机种子，以及可独立保存的文本乐谱；完整导出还会嵌入原始 MIDI 文件和已编译缓存。",
    "Parsing MIDI structure...": "正在解析 MIDI 结构…",
    "Tracks selected: {count}": "已选择 {count} 条轨道",
    "Track selection cancelled.": "已取消轨道选择。",

    "Keyboard Shortcuts": "快捷键",
    "Configure play, stop, previous, and next shortcuts": "配置播放、停止、上一首与下一首快捷键",
    "Configure up to two keyboard shortcuts for each playback action": "为每个播放操作配置最多两个快捷键",
    "Each action can use up to two shortcuts. Media Play/Pause, Media Previous, Media Next, function keys, letters, numbers, and other keyboard keys are supported.": "每个操作最多可以设置两个快捷键，并支持媒体播放/暂停、媒体上一首、媒体下一首、功能键、字母、数字及其他键盘按键。",
    "Action": "操作",
    "Shortcut 1": "快捷键 1",
    "Shortcut 2": "快捷键 2",
    "Play / Pause": "播放 / 暂停",
    "Next Song": "下一首",
    "Previous Song": "上一首",
    "Not Set": "未设置",
    "Press a key…": "请按键…",
    "Press the key you want to use. Press Esc to bind Esc.": "请按下要使用的按键；按 Esc 可将 Esc 设为快捷键。",
    "Shortcut captured.": "快捷键已记录。",
    "Clear this shortcut": "清除此快捷键",
    "Media Next": "媒体下一首",
    "Media Previous": "媒体上一首",
    "Media Stop": "媒体停止",
    "Media Play/Pause": "媒体播放/暂停",
    "Space": "空格",
    "Enter": "回车",
    "Esc": "Esc",
    "Page Up": "上一页",
    "Page Down": "下一页",
    "Print Screen": "截图键",
    "Scroll Lock": "滚动锁定",
    "Pause/Break": "Pause/Break",

}


class LanguageManager(QObject):
    """Small runtime translator used by the existing hand-built PyQt UI."""

    VALID_SELECTIONS = {"auto", "zh_CN", "en_US"}

    def __init__(self, selection: str = "auto"):
        super().__init__()
        self.selection = "auto"
        self.effective_language = "en_US"
        self.set_selection(selection)

    def start_auto_translation(self) -> None:
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Show and isinstance(watched, QWidget):
            self._translate_widget(watched)
            for child in watched.findChildren(QWidget):
                self._translate_widget(child)
        return super().eventFilter(watched, event)

    @staticmethod
    def system_language() -> str:
        # Both Simplified and Traditional Chinese systems intentionally use zh_CN.
        return "zh_CN" if QLocale.system().name().lower().startswith("zh") else "en_US"

    def set_selection(self, selection: str) -> str:
        if selection not in self.VALID_SELECTIONS:
            selection = "auto"
        self.selection = selection
        self.effective_language = self.system_language() if selection == "auto" else selection
        return self.effective_language

    def tr(self, text: str) -> str:
        if not text or self.effective_language != "zh_CN":
            return text
        if text in ZH_CN:
            return ZH_CN[text]

        # Common dynamic labels.
        prefixes = {
            "Hotkey: ": "快捷键：",
            "Play (": "播放（",
            "Pause (": "暂停（",
            "Resume (": "继续（",
            "Selected file: ": "已选择文件：",
            "Loaded save file: ": "已加载存档：",
            "Seeking to ": "正在跳转到 ",
            "Could not cache compiled preview: ": "无法缓存试听编译结果：",
        }
        for prefix, translated in prefixes.items():
            if text.startswith(prefix):
                result = translated + text[len(prefix):]
                if prefix in {"Play (", "Pause (", "Resume ("} and result.endswith(")"):
                    result = result[:-1] + "）"
                return result
        return text

    def language_option_text(self, option: str) -> str:
        if option == "auto":
            resolved = self.system_language()
            key = "Automatic (Simplified Chinese)" if resolved == "zh_CN" else "Automatic (English)"
            return self.tr(key)
        if option == "zh_CN":
            return self.tr("Simplified Chinese")
        return "English"

    def translate_widget_tree(self, root: QWidget) -> None:
        widgets = [root, *root.findChildren(QWidget)]
        for widget in widgets:
            self._translate_widget(widget)

    def _translate_widget(self, widget: QWidget) -> None:
        if isinstance(widget, (QMainWindow, QDialog)):
            self._translate_attr(widget, "windowTitle", "setWindowTitle", "_i18n_window_title")

        if (isinstance(widget, (QLabel, QAbstractButton, QGroupBox))
                and not bool(widget.property("i18n_dynamic"))):
            self._translate_attr(widget, "text" if not isinstance(widget, QGroupBox) else "title",
                                 "setText" if not isinstance(widget, QGroupBox) else "setTitle",
                                 "_i18n_text")

        self._translate_attr(widget, "toolTip", "setToolTip", "_i18n_tooltip")

        if isinstance(widget, QLineEdit):
            self._translate_attr(widget, "placeholderText", "setPlaceholderText", "_i18n_placeholder")

    def _translate_attr(self, obj, getter_name: str, setter_name: str, cache_name: str) -> None:
        getter = getattr(obj, getter_name, None)
        setter = getattr(obj, setter_name, None)
        if getter is None or setter is None:
            return
        original = getattr(obj, cache_name, None)
        if original is None:
            try:
                original = getter()
            except TypeError:
                return
            setattr(obj, cache_name, original)
        if original:
            setter(self.tr(original))

    def refresh_application(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        for widget in app.topLevelWidgets():
            self.translate_widget_tree(widget)
