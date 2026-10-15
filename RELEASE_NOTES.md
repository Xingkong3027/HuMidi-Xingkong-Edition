# HuMidi · Xingkong Edition 2.1.2-xk.15

[中文](#中文) | [English](#english)

## 中文

本版在 xk.14 基础上整理演奏设置，包含全局开关左对齐修正。

- 演奏页分为“独立设置 / 模拟人演奏 / 全局设置”三个标签；独立设置明确区分新曲目默认值、导入草稿与当前编辑曲目。
- “调试输出”“开始时释放空格（踏板）”“单曲试听结束后停留在曲尾”改为全局设置；“播放时自动切换到 Roblox 窗口”“本窗口获得焦点时暂停演奏”一并移入此页。
- 五项开关自动保存，下次开始演奏时统一读取。当前演奏及暂停后继续沿用本次开始时的设置；歌单播放仍按播放模式继续，不因单曲试听的曲尾选项停住。
- 首次升级从已保存的旧默认配置接续全局值，已有明确全局选择优先。旧歌曲、导入歌单、缓存或演奏存档中的同名字段不会再覆盖全局选择；新歌单包不再携带这些运行开关。
- 修改全局开关无需重新导入 MIDI，不改变音符或音乐缓存。开启调试输出时记录本次会话设置。
- 修正五个全局开关和文本的位置，使其靠左并与说明对齐，适配中英文与较窄窗口。保留 xk.14 的窗口焦点联动和踏板空格防误触修复。

**下载与升级：** 普通用户下载 `HuMidi-Xingkong-Edition-2.1.2-xk.15-Windows-x64.exe`，退出旧程序后运行。程序内可切换中文/English，无需分别下载。建议更新前导出完整歌单备份；无需删除原数据或重新导入歌曲。详细操作见 [中文指南](README.zh-CN.md)。

**验证范围：** 本地前端 524 项、后端 931 项通过，包含授权私人 MIDI 和真实 88 首旧完整包回归；类型检查、生产构建和 Windows x64 单文件构建通过。左对齐另经中英文及两种窗口尺寸的实际浏览器检查。公开 CI 不附带私人样本。真实 Roblox 窗口切换、游戏收键和长时间挂机尚未实机验证，范围见 [验证记录](docs/VALIDATION.md)。

## English

This release reorganizes playback settings on top of xk.14 and includes the corrected left alignment of global controls.

- Playback has Individual settings / Humanization / Global settings tabs. Individual settings distinguish new-song defaults, import drafts and the song being edited.
- Debug output, initial Space/pedal release and keeping the end position after a single-song preview are application preferences. Automatic Roblox activation and pause-on-own-focus move into the same tab.
- All five preferences save automatically and apply together on the next playback start. Current playback and pause/resume retain their starting values. Playlist playback continues according to its mode, independently of the single-song end-position option.
- On first upgrade, saved legacy defaults supply global values unless explicit global choices already exist. Old song, imported package, cache and performance-archive fields no longer override them. New playlist exports omit these runtime switches.
- Global changes require no MIDI re-import and do not alter notes or musical caches. Optional debug output records the session preferences.
- All five switches and labels align with their explanatory text on the left, in both languages and narrower windows. The xk.14 focus coordination and pedal-Space transport protection remain included.

**Download and upgrade:** Download `HuMidi-Xingkong-Edition-2.1.2-xk.15-Windows-x64.exe`, close the previous application, then run it. Chinese and English are selectable in the same EXE. Exporting a complete playlist backup before upgrading is recommended; deleting existing data or re-importing songs is unnecessary. See the [English guide](README.md).

**Validation:** 524 frontend and 931 backend tests passed locally, including authorized private MIDI and real 88-song legacy-package regressions. Type checking, production frontend and Windows x64 portable builds passed. Browser checks cover both languages and two window sizes for the alignment fix. Public CI does not distribute private samples. Real Roblox activation, game input reception and extended unattended playback remain unverified; see [validation scope](docs/VALIDATION.md).

EXE SHA256: `09bab5c2742c81c77d64dc61e0b396f6f5da6eb5afbf38804f2005743b15668e`
