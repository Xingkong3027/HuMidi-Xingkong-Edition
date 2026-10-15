# Windows x64 构建

当前版本：2.1.2-xk.15，Rust / Tauri 2 / React 架构。

需要 Node.js 24、Rust stable 的 `x86_64-pc-windows-msvc` 工具链，以及 Visual Studio 的“使用 C++ 的桌面开发”工作负载与 Windows SDK。首次构建需要下载依赖。

保留 `package-lock.json`、`src-tauri/Cargo.lock`、`src-tauri/resources/pedal_bilstm.safetensors` 和图标。不要将构建说明替换为旧 Python 版的 pip / PyInstaller 流程。

在项目根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\build-portable.ps1
```

脚本安装锁定的前端依赖、运行前后端测试并构建单文件程序，输出到 `portable/`：

```text
HuMidi-Xingkong-Edition-2.1.2-xk.15-Windows-x64.exe
HuMidi-Xingkong-Edition-2.1.2-xk.15-Windows-x64.exe.sha256
```

`-OutputDirectory` 可指定输出目录；`-SkipDependencyInstall` 用于依赖已经正确安装的情况。仅在同一份源码上已完成验证、重复打包时使用 `-SkipTests`。

独立运行检查：

```powershell
npm ci
npm test
npm run build
cargo test --manifest-path src-tauri/Cargo.toml --locked
```

完整后端回归应包含集成测试，因此以上命令不加 `--lib`。有权使用的私人回归样本可按 [验证说明](docs/VALIDATION.md) 配置。

前端、图标和 AI 模型嵌入 EXE；Windows C/C++ 运行库静态链接。目标电脑仍需 Microsoft Edge WebView2 Runtime。单文件不表示内嵌了浏览器运行时。

正式版本应核对 `package.json`、`package-lock.json` 的根包、`src-tauri/Cargo.toml`、`src-tauri/Cargo.lock` 的应用包和 `src-tauri/tauri.conf.json` 的版本，并检查界面中硬编码的版本文字。Git 标签应与版本一致，如 `v2.1.2-xk.15`。

Windows CI 和手动单文件构建流程见 `.github/workflows/`。发布流程须显式指定标签，先创建草稿；步骤见 [PUBLISHING.md](PUBLISHING.md)。
