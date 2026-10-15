# HuMidi · Xingkong Edition

[简体中文](README.zh-CN.md) · [Downloads](https://github.com/Xingkong3027/HuMidi-Xingkong-Edition/releases) · [Changelog](CHANGELOG.md)

Current version: **2.1.2-xk.12**, based on [HuMidi 2.1.2](https://github.com/smyGitt/HuMidi-Roblox-Piano-Autoplayer), using Rust, Tauri 2 and React. This unofficial fork is maintained by Xingkong3027. Original HuMidi is by smyGitt.

Features include an advanced playlist, Chinese and English UI, per-song settings, trimming, humanization with repeatable seed options, extended shortcuts, and optional dense-MIDI optimizations. Upstream 2.1.2's PedalAI model, onset features and automatic peak strategy are integrated.

## Download and run

Download `HuMidi-Xingkong-Edition-<version>-Windows-x64.exe` from this repository's Releases. The portable Windows x64 executable embeds the UI, icon and AI model. Python, Node.js and Rust are not required to run it; **Microsoft Edge WebView2 Runtime is required**.

Only Windows x64 is covered by this delivery. No verified macOS or Linux release is offered. Application data is stored under `%USERPROFILE%/.humidi-xingkong-v2`.

## Playlist migration

Use **Playlist → Import playlist → the recommended new/legacy playlist file option** to open an exported `.humidiplaylist`, JSON or ZIP package directly. Do not extract the package or select a folder. The local-library folder option is for importing an existing on-disk library without an exported package. See the [migration guide](docs/MIGRATION.md).

Complete packages include original MIDI files, text sheets and caches, making them suitable for backup and transfer. Normal packages may still depend on MIDI paths on the original computer. Cache-only legacy songs restore their existing events; they cannot always reproduce a fresh compilation from MIDI.

Version xk.11 fixes missing/null pedal curves that could prevent legacy songs from playing after background cache preparation, and keeps the background status area stable to prevent list movement.

## Selection and playback

The bottom-right **Select all** button selects the entire library, including songs hidden by search. **Ctrl+A (Command+A) selects songs on the playlist page.** Text inputs retain normal text selection; dialogs and native file choosers do not change song selection. Ctrl and Shift support multi-selection and range selection.

Dense-MIDI optimization is off by default and saved per song. Disabling it does not make every import, humanization, cache and cleanup behavior identical to upstream. Dynamic randomization may change each performance; use a fixed seed when repeatability matters. See [validation scope and limitations](docs/VALIDATION.md).

Default playback shortcuts are F6 to play/pause and F7 to stop. Previous/next song shortcuts are unassigned until configured. Ctrl+S saves the current song while the app has focus; Ctrl+K toggles compact mode.

## Build and attribution

[Build instructions](BUILDING.md) · [Publishing guide](PUBLISHING.md)

Original code: Copyright (c) 2026 smyGitt. Xingkong modifications: Copyright (c) 2026 Xingkong3027. MIT license texts and attribution are retained in `LICENSE`, `LICENSES/` and `NOTICE.md`; see [third-party notices](THIRD_PARTY_NOTICES.md) for dependency and model credits. Use and share only MIDI and sheet files you are entitled to use, and follow the rules of third-party games.
