# HuMidi · Xingkong Edition 2.1.2-xk.12

本次更新基于 HuMidi 2.1.2 的 Rust / Tauri / React 架构，整合新版 PedalAI，并保留星空版歌单、中文/英文、独立设置、裁剪、模拟演奏和扩展快捷键。

## 本次新增与修复

- 歌单页支持 **Ctrl+A**（Command+A）选择全部歌曲，与“全选”按钮一致，**包含搜索隐藏项**。输入框继续选择文字，弹窗和文件选择器不改变歌曲选择。
- 包含此前本地修订：完整 MIDI 尾部零填充导入、旧歌单百分比速度、缺失/null 踏板曲线导致后台处理后无法播放，以及后台状态令列表跳动的修复。
- 密集 MIDI 性能优化仍默认关闭，按歌曲独立保存；此次未更改解析、音符时序或踏板算法。
- 更新使用、迁移、构建和第三方说明，改为 Windows 单文件构建流程。

## 下载与旧歌单

Windows x64 单文件 EXE 内嵌界面、图标和 AI 模型，无需 Python、Node.js 或 Rust。运行电脑仍需 **Microsoft Edge WebView2 Runtime**。本次不提供已验证的 macOS / Linux 包。

旧歌单通过“歌单 → 导入歌单 → 选择新旧版歌单文件（推荐）”直接打开 .humidiplaylist、JSON 或 ZIP，无需解压。目录入口仅用于本机旧歌库。新数据目录为 `%USERPROFILE%/.humidi-xingkong-v2`；换电脑推荐完整包。

附件包含 EXE、配套许可证包、对应版本的源码 ZIP 及 SHA256SUMS.txt。EXE SHA256：

```text
375a3207fe247d64c8393f29e536b088ec09e8c858bec6cd6cdf55d53639a927
```

## 验证范围

前端 **514 项**、后端 **911 项**本地回归与生产构建通过，包含原 MIDI 和真实 88 首旧包。两种窗口尺寸下的 Ctrl+A、搜索输入、弹窗和批量修改已验证。此前 xk.11 的 88 首对照确认：带原件的旧包、新普通包、新完整包与 MIDI 直接导入在相同有效设置下结果一致；xk.12 未更改相关演奏代码。

演奏对照记录产品播放器的动作，没有向 Roblox 发送真实按键；游戏接收、声音及实际 Windows 调度效果尚未实机验证。“每次随机”、只有旧缓存无原件及跨 Python/Rust 的随机算法存在兼容边界，详见 docs/VALIDATION.md。关闭密集优化也不代表所有分支行为与上游完全相同。

Original HuMidi © 2026 smyGitt; Xingkong modifications © 2026 Xingkong3027. Original MIT notices and third-party licenses are retained. This is an unofficial HuMidi derivative.
