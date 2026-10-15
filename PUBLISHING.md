# 发布方法

当前工程为 Rust / Tauri 2 / React，发布目标是 Windows x64 单文件 EXE。旧 Python 版本保留在 Git 历史和 v2.0.0-xk.1 标签中。

1. 同步 package.json、package-lock.json 根包、Cargo.toml、Cargo.lock 应用包、tauri.conf.json 及界面版本文字；更新 CHANGELOG 和 RELEASE_NOTES。
2. 运行 `python qa/check-release-version.py`，再运行 BUILDING.md 中的完整检查及 build-portable.ps1。私人样本测试的环境变量见 docs/VALIDATION.md。
3. 运行 `python qa/collect-licenses.py`，核对依赖许可清单与原文。更新依赖后如果发现缺失文本，应从其准确版本的原仓库补齐 LICENSES/upstream 记录。
4. 审查提交，排除本机路径、私人 MIDI/歌单和构建缓存。正式标签指向最终构建源码；旧标签不重写。
5. 运行 GitHub 的 Prepare Windows Release，输入已存在的 `v<应用版本>` 标签。流程在该标签上测试、构建 EXE、整理声明与校验和，并创建草稿；不会自动公开，也不会覆盖已有 Release。
6. 也可发布已在本地验证的同一产品源码构建：用正常 Git 认证推送最终文档提交和版本标签，再由临时发布分支的 GitHub Actions 校验附件 SHA256、源码 ZIP 与标签逐文件一致性，并等待该精确提交的 Windows CI 成功。流程使用 GitHub 自动提供的临时令牌创建草稿、上传 EXE/许可证包/源码 ZIP/校验和，核对服务端附件后公开并设为 Latest；不会替换已公开的 Release。发布后独立下载全部附件校验，并删除临时上传分支。也可在网页草稿中完成同样的核对和发布。
7. 发布后检查下载和应用更新入口。应用使用 /releases/latest，草稿和预发布不通过该接口提供给自动检查；正式版本可设为 Latest。

Windows CI 对主分支和 PR 运行固定回归。Build Windows artifact 仅生成手动下载的构建产物，不创建测试 Release。GitHub Actions 的实际运行结果应在 Actions 页面查看，不能用本地通过替代。

公开包不附带私人歌曲。第三方游戏的真实接收、声音和调度效果需单独实机验证；最新范围见 docs/VALIDATION.md 和 MANUAL_TEST_CHECKLIST.md。
