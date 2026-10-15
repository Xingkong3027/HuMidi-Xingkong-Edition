# 发布方法

当前工程为 Rust / Tauri 2 / React，发布目标是 Windows x64 单文件 EXE。旧 Python 版本保留在 Git 历史和 v2.0.0-xk.1 标签中。

1. 同步 package.json、package-lock.json 根包、Cargo.toml、Cargo.lock 应用包、tauri.conf.json 及界面版本文字；更新 CHANGELOG 和 RELEASE_NOTES。
2. 运行 `python qa/check-release-version.py`，再运行 BUILDING.md 中的完整检查及 build-portable.ps1。私人样本测试的环境变量见 docs/VALIDATION.md。
3. 运行 `python qa/collect-licenses.py`，核对依赖许可清单与原文。更新依赖后如果发现缺失文本，应从其准确版本的原仓库补齐 LICENSES/upstream 记录。
4. 审查提交，排除本机路径、私人 MIDI/歌单和构建缓存。正式标签指向最终构建源码；旧标签不重写。
5. 运行 GitHub 的 Prepare Windows Release，输入已存在的 `v<应用版本>` 标签。流程在该标签上测试、构建 EXE、整理声明与校验和，并创建草稿；不会自动公开，也不会覆盖已有 Release。
6. 也可上传同一提交在本机构建的 EXE、许可证包、源码 ZIP 与 SHA256SUMS 到网页 Release 草稿。核对文件名、版本、提交和校验和后发布。
7. 发布后检查下载和应用更新入口。应用使用 /releases/latest，草稿和预发布不通过该接口提供给自动检查；正式版本可设为 Latest。

Windows CI 对主分支和 PR 运行固定回归。Build Windows artifact 仅生成手动下载的构建产物，不创建测试 Release。GitHub Actions 的实际运行结果应在 Actions 页面查看，不能用本地通过替代。

公开包不附带私人歌曲。第三方游戏的真实接收、声音和调度效果需单独实机验证；最新范围见 docs/VALIDATION.md 和 MANUAL_TEST_CHECKLIST.md。
