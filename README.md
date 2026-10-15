# HuMidi: Xingkong Edition

**English** | [简体中文](README.zh-CN.md) · [Downloads](https://github.com/Xingkong3027/HuMidi-Xingkong-Edition/releases/latest) · [Changelog](CHANGELOG.md)

[![Release](https://img.shields.io/github/v/release/Xingkong3027/HuMidi-Xingkong-Edition?display_name=tag)](https://github.com/Xingkong3027/HuMidi-Xingkong-Edition/releases)
[![CI](https://github.com/Xingkong3027/HuMidi-Xingkong-Edition/actions/workflows/ci.yml/badge.svg)](https://github.com/Xingkong3027/HuMidi-Xingkong-Edition/actions/workflows/ci.yml)

**Local test version: 2.1.2-xk.15 · Windows x64 portable EXE**

This version has not been published to GitHub. Releases still offers xk.14 as the latest public release; the xk.15 assets below are delivered locally.

Xingkong Edition is an unofficial fork of [smyGitt/HuMidi-Roblox-Piano-Autoplayer](https://github.com/smyGitt/HuMidi-Roblox-Piano-Autoplayer) that turns MIDI files and Virtual Piano text sheets into virtual-piano keyboard input. It uses **upstream 2.1.2's Rust / Tauri 2 / React architecture**, carrying forward the Python fork's advanced playlists, localization, per-song settings, trimming, seed policies and extended shortcuts, alongside the newer PedalAI integration.

This guide follows the older detailed README, with instructions, build commands and data locations updated for this version. The Python edition remains available in Git history and older releases. Xingkong3027 maintains this fork; smyGitt created HuMidi. This is not an official HuMidi or Roblox product and is not endorsed by either.

## Contents

- [Download and requirements](#download-and-requirements)
- [Quick start](#quick-start)
- [MIDI import and playback settings](#midi-import-and-playback-settings)
- [Sustain pedal and PedalAI](#sustain-pedal-and-pedalai)
- [Humanization and random seeds](#humanization-and-random-seeds)
- [Advanced playlists and batch operations](#advanced-playlists-and-batch-operations)
- [Playlist migration and backup](#playlist-migration-and-backup)
- [Global playback settings](#global-playback-settings)
- [Roblox window focus options](#roblox-window-focus-options)
- [Text-sheet conversion](#text-sheet-conversion)
- [Shortcuts and interface](#shortcuts-and-interface)
- [Data locations and updates](#data-locations-and-updates)
- [Compatibility and troubleshooting](#compatibility-and-troubleshooting)
- [Build and validation](#build-and-validation)
- [MIDI sources and sharing](#midi-sources-and-sharing)
- [Attribution licenses and support](#attribution-licenses-and-support)

## Download and requirements

Download from [this repository's Releases](https://github.com/Xingkong3027/HuMidi-Xingkong-Edition/releases/latest). Choose the EXE for normal use:

| Asset | Purpose |
| --- | --- |
| `HuMidi-Xingkong-Edition-2.1.2-xk.15-Windows-x64.exe` | Portable Windows x64 application; run directly. |
| `HuMidi-Xingkong-Edition-2.1.2-xk.15-Source.zip` | Complete source snapshot for this local version, for review, modification and rebuilding. |
| `HuMidi-Xingkong-Edition-2.1.2-xk.15-Licenses.zip` | Application, dependency and model notices and license texts. |
| `SHA256SUMS.txt`, `*.exe.sha256` | SHA-256 checksums for download integrity. |

The release targets **Windows 10/11 x64** and requires **Microsoft Edge WebView2 Runtime**, plus a Roblox piano experience that accepts keyboard input. The EXE embeds its UI, icon and PedalAI model. Python, Node.js, Rust and adjacent model files are not required to run it. WebView2 itself is not embedded; installation options are on [Microsoft's download page](https://developer.microsoft.com/en-us/microsoft-edge/webview2/).

No verified macOS or Linux release is currently offered by this fork. Public EXEs are not code-signed, so Windows may show an unknown-publisher warning; check the download source and hashes.

## Quick start

1. Run the EXE. In Settings → Display, select English, Simplified Chinese or the system language.
2. Import MIDI on Playback, or use the playlist's MIDI import/setup button. Choose tracks and left/right-hand roles for a single file; batches support automatic or per-file selection.
3. Check speed, transpose, keyboard layout, pedal, countdown and humanization. Defaults are a useful starting point.
4. Name and add the song to the playlist to retain it. Use an existing song's edit action to update it without importing the original again.
5. In Roblox, enter the piano interaction so that its keyboard input is ready.
6. Start playback and switch to the game during the countdown, or enable [automatic Roblox activation](#roblox-window-focus-options). Defaults: **F6 play/pause, F7 stop**.
7. Stop before changing the input target. HuMidi sends foreground keyboard input, not audio directly to the game; the target piano produces the sound.

## MIDI import and playback settings

Import one or multiple `.mid` / `.midi` files. Piano arrangements are usually easier to use directly. For mixed-instrument files, inspect the track selection to avoid mapping unwanted percussion or other parts to piano keys.

Batch import can select playable tracks automatically or let you assign tracks and hand roles per file. Review the success/failure summary and investigate each reported file. Playlist entries retain their own settings; opening another song does not replace them all.

| Setting | Meaning |
| --- | --- |
| Playback speed | Displayed as a percentage: `100%` is original speed, `50%` is half speed. Target BPM scales the original tempo. |
| Transpose | Changes pitch; check the target piano's supported key range too. |
| 88-key layout | Enable only for a target that supports the corresponding layout. Standard and 88-key mappings must match the game. |
| Countdown | Off or 1–10 seconds; saved separately for each playlist song. |
| Dense-MIDI performance optimization | Disabled by default and saved per song. Additional dense-score and AI acceleration paths require this switch. |

### Non-destructive trimming

Trim changes the compiled playback range without overwriting the original MIDI.

- **Automatic leading/trailing silence removal:** determines the range from playable notes in the selected tracks, separately for each song.
- **Manual range:** turn off automatic mode and enter start/end seconds. End `0` means the end of the song; any other end must exceed the start.
- Times are **playback seconds at the current speed**. Recheck manual ranges after changing speed.
- The retained range starts at a new zero point; notes crossing its boundaries are clipped. Trim settings are saved with the song, while the original MIDI remains available for export.

### Scope of dense-MIDI optimization

When enabled, extra calculation optimizations and merging of identical physical keys at the same timestamp may slightly change a performance. Leave it disabled when normal playback already works well.

Disabling it does not make this fork identical to upstream in every respect: import validation, invalid-MIDI repair confirmation, humanization policy, caching and stop cleanup still have fork-specific behavior. This version uses Rust keyboard output; the old Python/`pynput` backend description no longer applies.

## Sustain pedal and PedalAI

Options include no pedal, PedalAI, Adaptive, Rhythmic and Harmonic strategies, as well as original MIDI pedal data. Adjust them for the song and target piano. Selecting original MIDI pedal data does not mean every file contains usable pedal events.

PedalAI integrates upstream 2.1.2's model and onset features:

- **Automatic peaks:** analyzes AI confidence peaks; shaded chart areas show the resulting pedal intervals.
- **Custom thresholds:** edit separate press/release threshold curves to fine-tune sustain intervals.
- Generation/regeneration, hold-duration and switching-rate statistics, and warnings for frequent or unusually long holds.

Valid custom curves from existing songs are retained. A newer model can change the result under the same thresholds; audition it in the intended piano. Model and training-data credits are retained in [third-party notices](THIRD_PARTY_NOTICES.md) and the application's license page.

## Humanization and random seeds

Choose Disabled, Global settings or Individual song settings. Global parameters are in Settings → Performance and apply to songs using that policy on their next compilation. Individual settings retain each song's values.

Details include hand processing, slight chord rolls, timing/articulation variation, drift correction, mistakes and tempo sway. Enable only the effects you want.

| Seed policy | Behavior |
| --- | --- |
| Dynamic / new performance each time | Regenerates when an active effect uses randomness. Valid caches can be reused when no random effect is active. |
| Fixed / generated seed | Stores a generated seed; interactive changes to relevant performance parameters renew it. A button can generate another. |
| Fixed / custom seed | Enter a seed for repeatable comparisons using the same code version, source notes and all effective settings. |

Loading a song preserves its stored fixed seed. Python and Rust use different random algorithms, so matching seeds do not promise identical notes across architectures. Compare global presets, seed, selected tracks, pedal and trim as well as speed when checking different import routes.

## Advanced playlists and batch operations

MIDI entries retain original-file copies, source information, track/hand choices, speed, transpose, layout, pedal, countdown, trim, humanization settings and available compiled caches. Text sheets can also be named, saved, edited and exported.

### Selection, editing and ordering

- Click a row to select it; **Ctrl+click** toggles multiple selections and **Shift+click** selects a range. Ctrl-sweep selection is also supported.
- On the playlist page, **Ctrl+A** (Command+A) or **Select all** selects the **entire library, including songs hidden by search**. Text fields retain normal text selection; dialogs and native file choosers do not change song selection.
- Clear the search, then drag a selected row to move the selected block to the insertion position. Search and source labels help locate songs.
- Use the details panel or song menu to play, edit, rename, export original MIDI, batch-modify or delete.
- **Batch modification applies only checked fields**, retaining the others. MIDI-specific commands do not apply to plain text sheets.
- Imported caches may be prepared in the background. A fixed status area prevents the list from repeatedly jumping up and down.

### Five playback modes

| Mode | Behavior |
| --- | --- |
| Single play | Plays the current song without automatic continuation. |
| Single repeat | Replays it after natural completion. |
| Sequential | Advances in order and stops at the end. |
| Repeat all | Advances in order and wraps to the beginning. |
| Shuffle | Selects subsequent songs using shuffle after natural completion. |

Previous/Next are available in the main transport and compact mode. **Only natural completion advances the playlist**. Manual stop, cancelled countdown or replacing the playback source cancels automatic advancement. Focus pauses and activation failures do not count as natural completion.

## Playlist migration and backup

### You have an exported playlist file

Use **Playlist → Import playlist → the recommended new/legacy playlist file option**. Open `.humidiplaylist`, `.json` or a complete ZIP package directly: **do not extract it or select a folder**. Supported historical formats are identified by contents. You may also select an old library's `index.json` here.

### You only have an old local library

Use the local-library folder option and select the old data directory or its `playlist` directory containing `index.json`. This fallback is the option that opens a folder picker. Songs, original MIDI and available caches are copied without overwriting the old directory. Starting the new app does not automatically merge all old libraries.

### Export choices

| Choice | Contents and purpose |
| --- | --- |
| Normal playlist | Smaller settings/source package; MIDI songs may depend on paths on the original computer. Text and cache-only entries can be self-contained. |
| Complete package, recommended | Includes original MIDI, text and available caches for backup, migration and transfer. |

Cache-only legacy songs can restore their old results, but cannot edit parameters requiring original notes and need not equal a fresh compilation. Missing original paths without valid caches require the original files. Reading old formats does not imply old apps can read every newly exported field.

This version includes legacy speed-unit and missing/null pedal-curve fixes and can read previously affected songs. If a song was edited and resaved at an incorrect speed, keep the original package and import from it again. See the [migration guide](docs/MIGRATION.md) for details.

## Global playback settings

Playback now has Individual settings, Humanization and Global settings tabs. Without a loaded song, Individual settings explicitly edits new-song defaults for future imports; an edited song shows its scope. The per-song choice of a global humanization preset remains separate from these application runtime preferences.

These five preferences are saved automatically for the application, rather than individual MIDI/text songs or caches, and are not playlist batch-edit fields:

| Global preference | Purpose |
| --- | --- |
| Release Space/pedal on start | Release once before output; later pedal events are unchanged. Off by default. |
| Keep position at the end of single-song previews | Formerly keep-end-position-paused. On by default; seek back to replay a passage or press Play to restart. Playlists still follow their mode. |
| Debug output | Off by default. Log the session's global switches on the Debug page without changing notes, pedal or timing. |
| Automatically focus Roblox when playing | Off by default; see the next section. |
| Pause when HuMidi has focus | Off by default; see the next section. |

Changes apply on the **next playback start**, without MIDI re-import. The current session, including pause/resume, retains its starting preferences. The three former song switches migrate from saved import defaults; explicit application preferences take priority. Old playlist/archive fields cannot overwrite them, and new playlist exports omit runtime switches.

## Roblox window focus options

Both settings are under **Playback → Global settings → Window focus**; their duplicate location in application settings has been removed. They are **disabled by default**. Explicitly saved choices are preserved.

| Activate Roblox automatically | Pause when HuMidi has focus | Behavior |
| --- | --- | --- |
| Off | Off | Switch targets manually. Returning to HuMidi leaves the clock running, but HuMidi receives no performance keys. |
| Off | On | Pauses if HuMidi still has focus after the countdown, or regains it during playback. Switch to the target and resume with the playback shortcut. |
| On | Off | Tries to activate Roblox on each start/manual resume. Returning to HuMidi does not pause; input into HuMidi is still suppressed. |
| On | On | Confirms Roblox activation before evaluating focus-pause. Returning to HuMidi pauses; manual resume tries activation again. |

Activation is attempted once after the countdown and before note output. Waiting does not consume song time; starting a new song also attempts activation. It identifies Roblox Player processes, excludes browsers/Studio/launchers, and can request restoration of a minimized window. **It does not enter the in-game piano interaction and does not repeatedly steal focus during playback.**

A missing game window or Windows-rejected activation leaves playback paused with an explanation. Prepare the target and use the playback shortcut to retry. Stop cancels waiting. Actual foreground restrictions and game input reception still need real-game verification.

xk.14 includes xk.13's pedal-Space transport fix: after clicking Next or another transport button, injected pedal Space no longer reactivates that button and rapidly changes songs. Deliberate Tab/Space button operation remains available. Performance input into HuMidi's own foreground window is suppressed regardless of these settings; this does not protect every other application from foreground input.

## Text-sheet conversion

Paste a **Virtual Piano** text sheet on Translator, choose BPM and humanization, then play directly or name and add it to the playlist. Saved text entries can be edited. The conversion page also supports exporting text from current notes. Text sheets cannot represent every MIDI feature, so round-tripping is not a lossless MIDI conversion.

## Shortcuts and interface

| Default | Action and scope |
| --- | --- |
| F6 | Global play/pause. |
| F7 | Global stop. |
| Previous / Next | Unassigned until configured. |
| Ctrl+A | Select the entire playlist library; select text inside editable fields. |
| Ctrl+S | Save the current song to the playlist. Check/edit its binding under Settings → Shortcuts → Save performance. |
| Ctrl+K | Toggle compact mode. |

Settings → Shortcuts provides two slots each for play/pause, stop, previous and next. Function keys, combinations and supported media keys are accepted. Escape cancels recording; duplicate bindings are removed from their previous slot.

Display settings include automatic/Chinese/English language, themes and theme customization, opacity, always-on-top, piano/timeline visualization, pedal display and automatic visualization-page selection. Compact mode retains song/mode selection and Previous/Next; small-window pages can scroll.

## Data locations and updates

The default data directory is `%USERPROFILE%\.humidi-xingkong-v2`, holding configuration, themes, playlists and default performance archives. Settings → Files shows or changes archive, default MIDI and theme locations. The directory is separate from upstream and the old Python fork; old data is not automatically deleted or merged.

The application checks **this fork's** GitHub Releases and can open its download page when an update is available. It does not silently replace the running EXE. Export a complete playlist backup before upgrading; replace the program file rather than importing the source ZIP as a playlist.

## Compatibility and troubleshooting

**Why am I asked to repair a non-standard MIDI?** Normal files use normal import. Specific invalid channel-data bytes trigger an explicit compatibility-repair choice saved per song. Only imported data is repaired, not the original. Truly truncated or structurally broken files may remain unusable. Padding after complete tracks should not report `Truncated MIDI chunk header`; this version fixes that case.

**Why does the old-playlist picker show no file?** Choose the recommended new/legacy **file** option. The local-library **folder** option is only for directory migration. Renaming an extension is not a substitute for format support.

**Why is background processing needed, or why does a normal package fail on another PC?** Normal packages can reference original paths and need cache regeneration. Restore missing originals or use a complete package for transfer. Cache-only entries have editing limitations.

**Does playlist import play differently from direct MIDI import?** Tested old complete, new normal and new complete routes with identical originals and effective settings produced matching final notes, merged events and recorded keys. Dynamic randomness, global presets, model versions and cache origins affect comparisons. This is not a guarantee for every old cache or every upstream behavior.

**Why is playback paused or silent after switching windows?** Check both focus options and the game's piano interaction. Window activation does not guarantee in-game input reception. HuMidi itself does not synthesize the piano sound.

**Is overnight unattended playback or every Roblox piano verified?** Automated tests cover imports, playback events and simulated focus states, not real-game key injection, every experience or overnight operation. See [validation scope and limitations](docs/VALIDATION.md).

## Build and validation

The project requires Node.js 24, Rust stable, the Windows MSVC C++ toolchain and Windows SDK. Retain the lockfiles, icons and `src-tauri/resources/pedal_bilstm.safetensors`. Python/PyInstaller instructions apply only to historical versions.

Build the portable executable from the project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\build-portable.ps1
```

Individual checks and development startup:

```powershell
npm ci
npm test
npm run build
cargo test --manifest-path src-tauri/Cargo.toml --locked
npm run tauri dev
```

Local validation of the xk.15 application code passed **524 frontend** and **931 backend** tests and the portable build, including authorized private-sample regressions. Public CI does not distribute private MIDI/playlists and skips sample-dependent cases without their environment variables; equal test counts do not establish equal coverage.

[Full build instructions](BUILDING.md) · [Publishing](PUBLISHING.md) · [Validation](docs/VALIDATION.md) · [Manual checklist](MANUAL_TEST_CHECKLIST.md)

## MIDI sources and sharing

Opening or exporting a file does not grant rights to the composition, arrangement, MIDI or recording. Free downloads do not necessarily permit redistribution. Before publishing videos, livestreams or complete playlist packages, check the work's source, creator notes, metadata and license. Complete packages include MIDI copies; inspect text/cache contents in normal packages too.

Resource links retained from the old guide: [Mutopia Project](https://www.mutopiaproject.org/), [Wikimedia Commons](https://commons.wikimedia.org/), [OpenScore](https://github.com/OpenScore/), [MidiShow](https://www.midishow.com/) and [Online Sequencer](https://onlinesequencer.net/sequences). They are independent services; review each file's terms. This project does not verify every upload's rights. Follow the target game's rules as well.

## Attribution licenses and support

- Original project/author: [HuMidi / smyGitt](https://github.com/smyGitt/HuMidi-Roblox-Piano-Autoplayer), Copyright (c) 2026 smyGitt.
- Fork creator/maintainer: [Xingkong3027](https://github.com/Xingkong3027), modifications Copyright (c) 2026 Xingkong3027. OpenAI Codex assisted development, documentation and release preparation.
- Original and fork MIT notices are retained in [LICENSE](LICENSE), [NOTICE.md](NOTICE.md) and `LICENSES/`. Dependencies, model and training data retain their own notices; the project license does not replace them. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- The current Rust/Tauri/React edition does not embed the old Python/PyQt6 runtime. Historical notices are under `docs/legacy/`; old Qt distribution requirements do not describe this EXE.

For [Issues](https://github.com/Xingkong3027/HuMidi-Xingkong-Edition/issues), include the application/Windows version, reproduction steps and non-sensitive logs. Do not publish credentials, cookies, private songs or personal paths. Report security issues according to [SECURITY.md](SECURITY.md). Contributions target this repository's `main`; improvements suitable for upstream may be proposed separately there.
