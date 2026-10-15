# HuMidi · Xingkong Edition 2.1.2-xk.14

[中文](#中文) · [English](#english)

## 中文

本次发布为 **2.1.2-xk.14**，基于上游 HuMidi 2.1.2。包含此前本地 xk.13 的修复；没有单独发布 xk.13。

### 从公开 xk.12 升级的变化

- 修复鼠标点击播放、上一首或下一首后，演奏踏板空格再次激活焦点按钮，造成连续切歌或反复暂停的问题。保留主动 Tab/空格操作。
- 新增“播放时自动切换到 Roblox 窗口”，位于 **设置 → 显示 → 窗口**，默认关闭。每次开始演奏或手动继续时尝试一次，支持请求还原最小化的游戏窗口，不会持续抢焦点。
- “本窗口获得焦点时暂停演奏”在 xk.14 **默认关闭**，保留用户明确保存的选择。两项同时开启时，倒计时后先确认 Roblox 已获得焦点，再判断暂停条件；切换等待不消耗歌曲时间。
- 找不到游戏或切换未获允许时暂停并提示，手动继续可重试；停止取消等待。演奏中主动切回程序仍按暂停选项处理。
- 焦点暂停保持位置，不当作自然结束，不自动跳歌。无论开关如何，程序抑制向自身窗口发送演奏按键。
- 从旧版详细指南重新整理对应的中文与英文 README，补齐导入、逐曲设置、裁剪、踏板、模拟演奏、歌单迁移、快捷键、焦点联动、数据与构建说明。

### 下载与升级

普通使用者下载 `HuMidi-Xingkong-Edition-2.1.2-xk.14-Windows-x64.exe`。需要 Microsoft Edge WebView2 Runtime；无需 Python、Node.js、Rust 或旁置模型。源码、许可证和 SHA256SUMS 同时提供。

建议先导出完整歌单备份，再替换 EXE。现有 v2 数据目录继续使用；旧 Python 歌单从“导入歌单 → 选择新旧版歌单文件（推荐）”直接选择导出文件，不用解压或选择文件夹。自动切换窗口不会替你进入游戏钢琴交互区域。

### 验证与限制

本地前端 **518** 项、后端 **926** 项测试及 Windows x64 单文件构建通过，包括原 MIDI、真实 88 首旧包、四种焦点开关组合、倒计时、恢复、失败及取消。两种窗口尺寸检查了 88 首模拟歌单和设置界面。实际 Roblox 窗口切换、游戏收键和长期挂机尚未实机验证。公开 CI 不携带私人样本，详见 [验证范围](docs/VALIDATION.md)。

这次未改变 MIDI 编译、音符时序、踏板算法或密集优化策略。密集 MIDI 优化继续默认关闭。EXE 与此前本地交付的 xk.14 相同，发布准备仅更新文档和配套源码/许可证包。

## English

This is **2.1.2-xk.14**, based on upstream HuMidi 2.1.2. It includes the previously local xk.13 fixes; xk.13 is not published separately.

### Changes since public xk.12

- Fix pedal Space reactivating focused Play/Previous/Next buttons after a mouse click, causing rapid song changes or repeated pause toggles. Deliberate Tab/Space button operation remains available.
- Add automatic Roblox window activation under **Settings → Display → Window**, disabled by default. It attempts once on each start/manual resume, can request restoration of a minimized game, and does not continuously steal focus.
- Pause-on-HuMidi-focus is **disabled by default in xk.14**; explicitly saved choices are preserved. With both options enabled, Roblox activation is confirmed after the countdown before checking focus-pause. Waiting does not consume song time.
- Missing/rejected activation pauses with an explanation; manual resume retries and Stop cancels waiting. Returning to HuMidi during playback follows the pause setting.
- Focus pauses retain position and do not trigger natural completion or automatic advancement. Performance keys into HuMidi's own window are suppressed regardless of the settings.
- Restore detailed, corresponding English and Chinese READMEs from the older guide, covering import, per-song settings, trimming, pedal, humanization, playlist migration, shortcuts, focus behavior, data and builds.

### Download and upgrade

For normal use, download `HuMidi-Xingkong-Edition-2.1.2-xk.14-Windows-x64.exe`. Microsoft Edge WebView2 Runtime is required; Python, Node.js, Rust and adjacent model files are not. Source, license notices and SHA256SUMS accompany the EXE.

Export a complete playlist backup before replacing the EXE. Existing v2 data remains in use. Import Python-era exported playlists directly through the recommended new/legacy playlist file option without extracting them or choosing a folder. Automatic activation does not enter the in-game piano interaction.

### Validation and limitations

Local **518 frontend** and **926 backend** tests and the Windows x64 portable build passed, including the original MIDI, a real 88-song legacy package, all four focus-setting combinations, countdown, resume, failure and cancellation. Two window sizes were checked with an 88-song simulated library and settings UI. Actual Roblox activation, in-game key reception and extended unattended playback have not been tested in a live game. Public CI does not include private samples; see [validation scope](docs/VALIDATION.md).

MIDI compilation, musical timing, pedal algorithms and dense-optimization policy are unchanged by this update. Dense-MIDI optimization remains off by default. The EXE is identical to the previously delivered local xk.14 build; release preparation updates documentation and accompanying source/license archives only.

---

EXE SHA256: `c8e65c2440bddc1009e458d2ecad60431fa4c12b37d6fea955c0d170e2b20e9f`
