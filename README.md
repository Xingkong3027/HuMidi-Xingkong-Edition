# HuMidi: Xingkong Edition

> 非官方 HuMidi 衍生版本 / Unofficial derivative of HuMidi

HuMidi: Xingkong Edition 基于
[smyGitt/HuMidi-Roblox-Piano-Autoplayer](https://github.com/smyGitt/HuMidi-Roblox-Piano-Autoplayer)
修改，保留 HuMidi 的 MIDI 解析、模拟人演奏和 Roblox 钢琴键盘输出能力，并增加高级歌单、
简体中文界面、批量 MIDI、输入兼容性修复及可选性能优化。

HuMidi: Xingkong Edition is an unofficial derivative of HuMidi. It preserves
HuMidi's MIDI parsing, human-like performance, and Roblox piano keyboard output
while adding advanced playlists, Simplified Chinese localization, batch MIDI
tools, input compatibility fixes, and optional dense-MIDI optimizations.

当前版本 / Current version: **2.0.0-xk.1 Preview**

## 主要功能

- 简体中文 / English 运行时切换；
- 五种歌单播放模式和可滚动迷你歌单；
- MIDI 与文本乐谱歌单；
- 普通及自包含 `.humidiplaylist` 导入/导出；
- 歌曲修改、原 MIDI 保留和批量操作；
- 动态、固定随机及固定自定义种子；
- 多 MIDI 导入、自动/手动轨道选择；
- 多组播放快捷键及 Windows 媒体键；
- 非标准 MIDI 数据字节的显式 clip 修复流程；
- 可选密集 MIDI 性能优化；保留原有 `pynput` 输入后端，以维持 Roblox 兼容性。

完整功能说明见 [`README_PLAYLIST_EDITION.md`](README_PLAYLIST_EDITION.md)，
变更记录见 [`CHANGELOG.md`](CHANGELOG.md)，上传和发布步骤见
[`PUBLISHING.md`](PUBLISHING.md)。

## 运行源码

推荐使用 Python 3.11：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Linux/macOS：

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

## 测试

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m compileall -q .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

发布前还必须在真实 Windows 和 Roblox 钢琴体验中测试按键输入、暂停/恢复、停止释放按键、
性能优化模式和快捷键。自动化输入是否允许取决于 Roblox 及具体体验的规则。

## Windows 单文件打包

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

## 数据位置

Xingkong Edition 使用独立配置目录，不会与上游 HuMidi 共用设置：

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

项目根目录的 `saves` 用于 Playback 存档。`.humidi` 与
`.humidi-xingkong` 不会自动合并或删除。

## 更新

应用只检查 Xingkong Edition 自己的 GitHub Releases 页面。发现新版本时只询问是否打开下载
页面，不会静默下载或替换正在运行的程序。发布附件提供 SHA-256 校验值。

## 项目关系与免责声明

- 原项目：<https://github.com/smyGitt/HuMidi-Roblox-Piano-Autoplayer>
- Xingkong Edition：<https://github.com/Xingkong3027/HuMidi-Xingkong-Edition>
- 本项目不是 HuMidi 官方版本，也不隶属于或受 Roblox Corporation 认可。
- “Roblox”仅用于说明第三方体验兼容性。

详细署名见 [`NOTICE.md`](NOTICE.md)。

## 许可证

上游 HuMidi 源码以 MIT License 发布，原作者声明被完整保留。Xingkong Edition 使用的免费
PyQt6 采用 GPL v3，因此分发 PyInstaller 打包程序时不能将组合发行物描述为“仅 MIT”。
请同时阅读：

- [`LICENSE`](LICENSE)
- [`LICENSES/HuMidi-MIT.txt`](LICENSES/HuMidi-MIT.txt)
- [`LICENSES/GPL-3.0.txt`](LICENSES/GPL-3.0.txt)
- [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)

如需闭源或商业发行，应取得适当的 PyQt 商业许可证，或在完成许可证审查后迁移到其他 Qt
绑定。本说明不是正式法律意见。
