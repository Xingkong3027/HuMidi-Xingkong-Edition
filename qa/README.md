# 浏览器布局验证

启动本项目的 Vite 开发服务后，使用安装了 Playwright 的 Node 环境运行 `node qa/layout-smoke.cjs`。可以通过 `PLAYWRIGHT_MODULE` 指定本机 Playwright 模块位置，通过 `HUMIDI_QA_OUTPUT` 指定截图及报告目录。默认输出 `qa-output`。

测试使用 Edge 的无头浏览器和临时浏览器上下文。Tauri 后端是内存测试夹具，不会访问用户歌库，不会注入真实按键。后端实际命令另由 Rust 的临时歌库测试覆盖。

`node qa/dialog-smoke.cjs` 另验证确认、重命名、颜色选择、Windows 保存选择器的插件调用与取消、选择文件期间的快捷键保护以及标签换行。原生文件选择的返回值使用夹具模拟，不允许出现浏览器 alert／confirm／prompt；本脚本不操作真实 Windows 文件选择器。

`node qa/shortcuts-smoke.cjs` 验证上一首／下一首默认留空、组合键和媒体键录入、清除、Esc 取消以及录入时没有紧凑模式或播放副作用。浏览器媒体键使用 KeyboardEvent 模拟，不会向 Windows 或游戏注入按键。
