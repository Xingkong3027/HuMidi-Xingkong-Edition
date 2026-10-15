# HuMidi · Xingkong Edition 2.1.2-xk.15

本地测试版，尚未更新 GitHub。

## 中文

- 界面修正：全局设置中的五个开关与文字靠左，与说明文字对齐。

- 演奏页改为“独立设置 / 模拟人演奏 / 全局设置”三个标签；独立页明确显示新曲目默认值或正在编辑的曲目。
- 调试输出、开始时释放踏板、曲终暂停改为全局设置；原程序设置的自动切换 Roblox 和焦点暂停也迁入这里。
- 曲终暂停改名“单曲试听结束后停留在曲尾”，歌单仍按播放模式继续。
- 五项全局开关自动保存，下次开始演奏生效；当前会话和暂停后继续保持原设置。
- 升级从旧默认配置接续全局值，旧 MIDI/文本歌曲、歌单包、缓存和演奏存档中的同名字段不再覆盖；新歌单包不保存这些运行开关。
- 全局修改不需要重新导入，不改变音符或音乐缓存。调试开启时在调试页记录会话设置。

前端 524 项、后端 931 项及原 MIDI/真实 88 首旧包补充回归通过。真实 Roblox 窗口切换、收键和长时间挂机未实机验证。

## English

- Layout correction: left-align all five global switches and labels with their explanatory text.

Local test build; not published to GitHub.

- Playback now has Individual settings / Humanization / Global settings tabs, with explicit new-song-default and edited-song scopes.
- Debug output, initial pedal release and end-position pause are application preferences. Roblox activation and focus-pause move here from application settings.
- End-position pause is labelled for single-song previews; playlist playback still follows its mode.
- All five preferences save automatically and apply on the next playback start. The current session and pause/resume retain their starting values.
- Migrate saved legacy defaults without allowing old song, package, cache or archive fields to override global choices. New playlist packages omit these runtime switches.
- Global changes require no re-import and do not change notes or musical caches. Optional debug output records session preferences.

524 frontend and 931 backend tests plus private MIDI/real 88-song package regressions passed. Real Roblox activation, input reception and overnight playback remain unverified.

EXE SHA256: `09bab5c2742c81c77d64dc61e0b396f6f5da6eb5afbf38804f2005743b15668e`
