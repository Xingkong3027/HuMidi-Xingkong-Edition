# HuMidi：Xingkong Edition

[English](README.md) | [**简体中文**](README.zh-CN.md)

[![Release](https://img.shields.io/github/v/release/Xingkong3027/HuMidi-Xingkong-Edition?display_name=tag)](https://github.com/Xingkong3027/HuMidi-Xingkong-Edition/releases)
[![CI](https://github.com/Xingkong3027/HuMidi-Xingkong-Edition/actions/workflows/ci.yml/badge.svg)](https://github.com/Xingkong3027/HuMidi-Xingkong-Edition/actions/workflows/ci.yml)
[![Platform](https://img.shields.io/badge/platform-Windows-0078D6?logo=windows)](#系统要求)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](#从源码运行)

> 用于在 Roblox 钢琴键盘上播放 MIDI 与文本乐谱的非官方 HuMidi 衍生版本。

**当前正式版本：`2.0.0-xk.1`**

HuMidi：Xingkong Edition 基于
[smyGitt/HuMidi-Roblox-Piano-Autoplayer](https://github.com/smyGitt/HuMidi-Roblox-Piano-Autoplayer)
修改。它保留了 HuMidi 的 MIDI 解析、模拟人演奏、可视化和键盘输出核心，并增加高级歌单、简体中文本地化、多文件工作流、可自定义倒计时、非破坏性播放范围裁剪、Roblox 输入兼容性修复及可选的密集 MIDI 性能优化。

本项目不是 HuMidi 或 Roblox 的官方产品，也不隶属于或受 smyGitt、Roblox Corporation 认可。

## MIDI 文件、版权与第三方来源

HuMidi: Xingkong Edition 是一个 MIDI 处理与键盘输入自动化工具。本项目不会因软件能够打开、处理、播放或导出某个 MIDI 文件，而授予用户对该 MIDI 文件、相关编曲、乐谱、录音、歌词或原始音乐作品的任何权利。

请注意：

- “免费下载”不等于“无版权”或“可以任意使用”。
- 原始音乐作品已进入公有领域，不代表后来制作的编曲、转录、乐谱版本或 MIDI 文件也属于公有领域。
- MIDI 文件、编曲、录音以及视频中使用的其他素材可能分别受到不同的版权或许可条款约束。
- 在下载、播放、录制、发布、上传或重新分发 MIDI 文件之前，请确认你拥有相应权利或已获得有效许可。
- 完整 `.humidiplaylist` 歌单包可能包含 MIDI 文件副本。请勿将无权分发的 MIDI 文件包含在公开分享的歌单包、GitHub 仓库、软件安装包或 Release 附件中。
- 如果许可要求署名、提供许可链接、注明修改或以相同许可发布，请完整履行这些要求。

在适用法律允许的最大范围内，用户应对其导入、处理、播放、录制、发布和分发的 MIDI 文件及其他内容负责。项目维护者和贡献者不对用户提供或使用的第三方内容作出版权保证，也不对未经授权使用第三方内容所产生的索赔、下架、账号处罚或其他损失负责。

### 可查明许可的 MIDI 来源

以下网站可以帮助寻找公有领域或采用开放许可的音乐资料：

- [Mutopia Project](https://www.mutopiaproject.org/) — 提供 PDF、MIDI 和 LilyPond 文件；作品采用公有领域或 Creative Commons 许可，请查看每个作品页面标注的具体许可。
- [Wikimedia Commons](https://commons.wikimedia.org/) — 收录部分 MIDI 文件；每个文件都有独立的许可说明，建议优先选择明确标注为 Public Domain 或 CC0 的文件。
- [OpenScore](https://github.com/OpenScore/) — 提供以 CC0 发布的数字乐谱集合，部分内容可转换或导出为 MIDI。

这些链接指向独立的第三方网站，仅为方便用户查找资料而提供。本项目与这些网站没有隶属、合作、赞助或认可关系，也不保证其内容始终可用、准确、合法或适合特定用途。第三方网站的内容和条款可能发生变化，请在每次使用前自行核对具体文件的作者、来源和许可。

本节仅提供一般性信息，不构成法律意见。

## 下载

请从 [GitHub Releases](https://github.com/Xingkong3027/HuMidi-Xingkong-Edition/releases/latest) 下载最新版本。

| 文件 | 用途 |
| --- | --- |
| `HuMidi-Xingkong-Edition-Windows.zip` | 推荐下载的完整 Windows 包，包含程序和许可证声明。 |
| `HuMidi-Xingkong-Edition.exe` | Windows 单文件可执行程序。 |
| `SHA256SUMS.txt` | 用于检查下载文件完整性的 SHA-256 校验值。 |

使用 ZIP 包时，请先把所有文件解压到普通文件夹，再运行程序。由于公开构建未购买代码签名证书，Windows 可能显示“未知发布者”。请只运行从本仓库下载的文件，并尽可能核对 SHA-256。

## 主要功能

### MIDI 播放与轨道选择

- 导入一个或多个 `.mid` / `.midi` 文件。
- 自动选择可播放的非鼓轨道，或者手动选择轨道并分配左右手。
- 设置速度、移调、踏板行为、88 键映射和模拟人演奏参数。
- 保存编译后的 Playback 存档，方便快速重新使用。
- 默认严格解析 MIDI；遇到特定的数据字节越界错误时，由用户明确选择是否使用 clip 修复方式重试。

### 可自定义的播放前倒计时

- 可以在播放页面启用或关闭倒计时。
- 通过互相同步的滑块和数字输入框，将倒计时时间设置为 **1–10 秒**。
- 播放开始前，主时间栏会显示当前剩余倒计时秒数。
- 每首歌单歌曲都可以保留自己的倒计时开关和时长设置。

### 非破坏性 MIDI 播放范围裁剪

播放页面的 **裁剪** 功能可以去掉不需要播放的前后空白时间，并且不会覆盖原始 MIDI 文件。

- **自动裁剪：**以第一个可播放音符作为开始，以最后一个可播放音符作为结束。
- **手动裁剪：**输入开始和结束时间，只播放选择的时间范围。
- 选中范围内的音符、Tempo 和拍号信息会整体移动，使保留范围从时间 0 开始播放。
- 跨越裁剪边界的音符会被截取到保留范围内。
- 裁剪范围会随 Playback 或歌单设置保存，歌单中保留的原始 MIDI 仍然可用。

当 MIDI 在第一个音符之前或演奏结束之后包含较长空白时，这项功能尤其有用。

### 高级歌单

每个 MIDI 歌单项目可以保留：

- 原始 MIDI 的本地副本；
- 原文件名和路径信息；
- 轨道与左右手选择；
- 速度、移调、踏板、88 键、倒计时、裁剪和性能设置；
- 模拟人演奏模式与随机种子策略；
- 用于快速开始播放的可选固定编译缓存；
- 可用时保存可视化音符、踏板范围、Tempo 和拍号数据。

在“乐谱转换”页面创建的文本乐谱也可以命名、加入歌单、播放、导出和修改。

### 歌单多选与右键批量处理

在歌单页面中：

1. 按住 **Ctrl** 并点击歌曲，可以选择或取消选择多个项目。
2. 也可以按住 **Ctrl**，让鼠标指针拖过多行，进行范围式多选。
3. 在多选项目上点击右键，可以使用相应的批量命令：
   - **批量修改歌曲**：只把你实际改动的播放设置应用到选中的 MIDI 歌曲；
   - **批量将 MIDI 另存为…**：把歌单中保留的原始 MIDI 批量提取到指定文件夹；
   - **批量删除**：确认后删除选中的歌单项目。
4. 松开 Ctrl 后，拖动其中一个已选项目，可以把整个多选歌曲组一起移动；白色插入线会显示目标位置。

如果选择的全部是文本乐谱，程序会隐藏仅适用于 MIDI 的命令。如果同时选择了 MIDI 与文本乐谱，程序会先警告，并允许“只处理 MIDI”。

### 五种歌单播放模式

- 单曲播放
- 单曲循环
- 全部循环
- 顺序播放
- 随机播放

主播放控制区和迷你模式都提供上一首、下一首控制。

### 模拟人演奏与可复现随机性

模拟人演奏模式可以设为：

- **禁用**；
- **启用（使用全局设置）**：使用“设置”页面中的统一配置；
- **启用（使用单独设置）**：为当前 MIDI 或歌单歌曲单独配置。

随机种子模式包括：

- **动态随机种子**：每次播放重新编译不同的演奏结果。
- **固定随机种子**：自动生成可复现种子，并保存编译缓存。
- **固定自定义种子**：允许自行输入种子；使用相同源文件和设置时，可在多次运行或不同电脑上复现演奏。

### 歌单导入与导出

两种导出方式都使用 `.humidiplaylist` 扩展名：

- **普通导出**：保存歌单结构、路径、设置、轨道选择和种子策略。文件较小，但可能依赖原 MIDI 路径。
- **完整导出**：内嵌保留的 MIDI 副本和已有固定缓存，适合迁移或分享；分享包会移除不必要的源文件绝对路径。

文本乐谱在两种格式中都是自包含的。

### 批量导入 MIDI

使用 **导入 MIDI（可多选）** 选择一个或多个文件。批量导入时可以：

- 自动处理全部文件；
- 为每个文件手动选择轨道和左右手；
- 分别处理自动选轨失败的文件；
- 在最终结果中查看成功和失败列表；
- 把准备好的歌曲直接加入歌单，或者先统一应用播放设置。

### 快捷键与 Windows 媒体键

在“设置 → 键盘快捷键”中，每项操作最多可以设置两个按键：

- 播放/暂停
- 停止
- 上一首
- 下一首

支持普通按键、功能键、字母、数字以及受支持的 Windows 媒体控制键。

### 本地化、主题、可视化与迷你模式

- 运行时语言：自动选择、简体中文或 English。
- 支持自定义主题和窗口透明度。
- 钢琴与时间线可视化会与编译后的实际播放事件同步。
- 迷你模式包含播放模式选择、上一首/下一首和可滚动的紧凑歌单。
- 播放和设置页面在较小窗口尺寸下可以独立滚动。

### 可选的密集 MIDI 性能优化

播放页面提供可选的 **性能优化** 开关，适合音符特别密集的 MIDI。启用后会减少同一时间点的重复物理按键、改善 Windows 计时精度并降低界面更新压力，同时继续使用原有 `pynput` 输入后端以维持 Roblox 兼容性。

如果某首歌曲使用原始播放方式已经正常，建议保持关闭。

## 快速开始

1. 下载并解压 `HuMidi-Xingkong-Edition-Windows.zip`。
2. 运行 `HuMidi-Xingkong-Edition.exe`。
3. 打开“播放”页面，点击 **导入 MIDI（可多选）**。
4. 自动选择轨道，或手动给左右手分配轨道。
5. 设置播放参数、倒计时、裁剪和模拟人演奏选项。
6. 打开目标 Roblox 钢琴体验，并让钢琴输入区域获得焦点。
7. 点击播放按钮或使用已经设置的快捷键。
8. 切换体验或输入目标前，请先停止播放。

Roblox 或具体体验可能限制自动键盘输入。使用者有责任遵守 Roblox 条款以及所使用体验的规则。

## 系统要求

- Windows 10 或 Windows 11，推荐 64 位系统。
- 支持键盘输入的 Roblox 钢琴体验，或其他兼容的虚拟钢琴目标。
- 使用打包好的 `.exe` 不需要安装 Python。

Xingkong Edition 目前只正式发布并测试 Windows 包。其他桌面平台的源码运行不属于维护者已正式测试的发布目标。

## 从源码运行

推荐使用 Python 3.11：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

运行检查：

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m compileall -q .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 构建 Windows 可执行文件

```powershell
.\.venv\Scripts\python.exe -m PyInstaller `
  --noconfirm --clean --onefile --noconsole `
  --name "HuMidi-Xingkong-Edition" `
  --icon ".\icon.ico" `
  --add-data ".\icon.ico;." `
  --add-data ".\NOTICE.md;." `
  --add-data ".\THIRD_PARTY_NOTICES.md;." `
  main.py
```

输出文件：

```text
dist\HuMidi-Xingkong-Edition.exe
```

仓库中的 `Release Windows` 工作流会在推送 `v*` 标签后构建发布包并生成 SHA-256。将版本标记为正式发布前，必须在真实 Windows 系统和目标 Roblox 钢琴体验中测试生成的程序。

## 数据位置

Xingkong Edition 使用独立配置目录，不会覆盖上游 HuMidi 的设置：

```text
%USERPROFILE%\.humidi-xingkong\
├── config.json
├── themes.json
└── playlist\
    ├── index.json
    ├── items\
    ├── midi\
    └── cache\
```

仓库根目录的 `saves` 用于 Playback 存档。`.humidi` 与 `.humidi-xingkong` 不会自动合并或删除。

## 更新与安全

- 应用只检查本仓库的 GitHub Releases 页面。
- 不会静默下载或替换正在运行的程序。
- 发现新版本时，会先询问是否打开发布页面。
- 建议使用 `SHA256SUMS.txt` 校验发布附件。
- 安全问题请通过 [GitHub 私密安全通告](https://github.com/Xingkong3027/HuMidi-Xingkong-Edition/security/advisories) 报告，不要在公开 Issue 中暴露敏感信息。

报告中不要包含 Roblox 凭据、会话 Cookie、私人 MIDI 文件或个人文件路径。

## 文档

- [歌单版详细说明](README_PLAYLIST_EDITION.md)
- [变更记录](CHANGELOG.md)
- [发布指南](PUBLISHING.md)
- [安全策略](SECURITY.md)
- [署名与修改声明](NOTICE.md)
- [第三方声明](THIRD_PARTY_NOTICES.md)

## 项目关系与署名

- 原项目：[smyGitt/HuMidi-Roblox-Piano-Autoplayer](https://github.com/smyGitt/HuMidi-Roblox-Piano-Autoplayer)
- Xingkong Edition：[Xingkong3027/HuMidi-Xingkong-Edition](https://github.com/Xingkong3027/HuMidi-Xingkong-Edition)
- HuMidi 原作者：[smyGitt](https://github.com/smyGitt)
- Xingkong Edition 创建者与维护者：[Xingkong3027](https://github.com/Xingkong3027)
- Xingkong Edition 的代码审查、文档、发布准备和工作流改进由 OpenAI Codex 辅助完成。

完整修改及署名信息见 [NOTICE.md](NOTICE.md)。

## 许可证

上游 HuMidi 源码以 MIT License 提供，其原始版权与许可证声明已经保留。此应用使用的免费 PyQt6 版本采用 GPL v3，因此打包后的组合发行物不能描述为“仅 MIT”。请阅读：

- [LICENSE](LICENSE)
- [HuMidi MIT License](LICENSES/HuMidi-MIT.txt)
- [GPL v3 许可证文本](LICENSES/GPL-3.0.txt)
- [第三方声明](THIRD_PARTY_NOTICES.md)

闭源或商业再发行需要取得适当的 PyQt 商业许可证，或迁移到经过单独许可证审查的其他 Qt 绑定。本说明不是正式法律意见。

## 支持与贡献

欢迎通过 [GitHub Issues](https://github.com/Xingkong3027/HuMidi-Xingkong-Edition/issues) 报告可复现的问题和兼容性情况。请提供 Xingkong Edition 版本、Windows 版本、受影响功能、复现步骤以及不包含敏感信息的相关日志。

Pull Request 应提交到本仓库的 `main` 分支。如果某项改动同样适合上游 HuMidi，可以另行向原项目提议。
