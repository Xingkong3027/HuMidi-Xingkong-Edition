## Dense MIDI performance optimization

- Added an optional **Performance Optimization** switch on the Playback page. It is disabled by default so the original pynput execution path remains available unchanged.
- When enabled, identical simultaneous physical attacks are collapsed while the original `pynput` input backend is retained for Roblox compatibility.
- Identical physical key/modifier attacks at the same timestamp are collapsed while every original logical note and release count is still tracked.
- Shifted and unshifted notes sharing one physical keyboard key are retained as rapid re-strikes, but the old 1 ms sleep between every overlap is removed.
- Playback temporarily requests 1 ms Windows timer resolution, raises only the playback worker to above-normal priority, and suspends cyclic garbage collection until playback stops.
- Progress and visualizer signals are throttled to 30 Hz in optimized mode to reduce GUI-thread pressure.
- Saved Playback and playlist caches remain reusable when the switch changes because this setting affects execution only, not compiled note data.

## MIDI dialog localization fix

- The non-standard MIDI repair prompt now uses explicitly localized **Yes/No** buttons instead of relying on Windows/Qt standard-button translations.
- Common invalid-file errors such as a missing `MThd` MIDI header now show a clear Simplified Chinese explanation instead of raw Mido English text.
- Batch MIDI import uses the same localized error descriptions in its final results list.

## Countdown visibility update

- The transport time display now shows the active pre-playback countdown, for example `00:00 / 02:22 (倒计时3秒)`.
- The countdown suffix updates every second and disappears automatically when playback starts or is stopped.
- Countdown visibility no longer depends on debug output.

# Playlist Edition changes

## Advanced playlist song model

- Playlist items now retain an internal copy of the original MIDI, playback parameters, selected track roles, simulation settings, and optional compiled cache.
- Added separate `items`, `midi`, and `cache` storage directories under `%USERPROFILE%\.humidi-xingkong\playlist`.
- Dynamic-seed songs store MIDI and settings but recompile on every performance.
- Disabled, fixed-random, and fixed-custom performances use validated compiled caches for faster startup.
- Dynamic songs retain an estimated duration in the playlist even without a cache.
- Existing cache-only playlist items remain supported and are migrated when possible.

## Song editing and MIDI access

- Added **Modify Song** to the playlist right-click menu.
- Editing loads the stored MIDI, track selection, playback parameters, simulation mode, and seed settings into the Playback page.
- **Add to Playlist** changes to **Complete Modification** while editing.
- Added **Save MIDI As…** to extract the stored MIDI copy.
- Modify/Save MIDI actions are disabled for legacy cache-only songs without a MIDI source.

## Human-like performance and deterministic randomness

- Renamed the Simplified Chinese UI term from “人性化” to **“模拟人演奏”**.
- Added Human-like Performance Mode:
  - Disabled
  - Enabled (Use Global Settings)
  - Enabled (Individual Settings)
- Added a global human-like performance preset in Settings.
- Added seed policies:
  - Dynamic Random Seed
  - Fixed Random Seed
  - Fixed Custom Seed
- The fixed-random seed is displayed but read-only, is preserved during config/song loading, and is regenerated when relevant simulation settings or the global preset change.
- The fixed-custom seed field is editable; dynamic and fixed-random seed fields are disabled as appropriate.
- Humanizer, mistake generation, chord rolling, timing variance, drift, and articulation now share one seeded random generator, making fixed seeds reproducible.

## Playlist import/export

- Normal `.humidiplaylist` export stores paths, parameters, track choices, and seed settings without MIDI/cache payloads.
- Complete `.humidiplaylist` export is a self-contained ZIP package containing `playlist.json`, embedded MIDI files, and available compiled caches.
- Import auto-detects normal JSON and complete packages using the same extension.
- Complete exports strip absolute MIDI paths and sanitize cached playback settings to avoid exposing local Windows user paths.
- Imported dynamic songs preserve their displayed duration even when no cache is included.

## Existing playlist, language, UI, and visualizer work

- Added the Playlist sidebar with import/export, previous/next, delete, clear, and five playback modes.
- Added runtime Simplified Chinese/English selection and Chinese system-language auto detection.
- Increased the expanded default window to `1040 × 640` and minimum size to `900 × 560`.
- Added current song and playback source under the progress time.
- Playlist-page global Play and playback hotkey route to the selected playlist row.
- Playback preview and cached playlist playback use the same exact compiled visualization bundle.
- Overlapping same-pitch notes use reference counts in both timeline reconstruction and piano-key highlighting.
- Natural playlist completion performs a clean stop before automatic next-song transitions.
- Update checks now target the Xingkong Edition Releases page and never replace the executable automatically.
## Disabled-control appearance fix

- Added explicit disabled styling for combo boxes, line edits, spin boxes, and labels.
- The Randomness selector now visibly turns grey when Human-like Performance Mode is set to Disabled.
- Disabled controls no longer receive hover highlighting.
## Hotkey persistence fix

- Save the currently bound playback hotkey in `~/.humidi-xingkong/config.json`.
- Restore function keys, character keys, and virtual-key bindings on startup.
- Save immediately after a new key is bound, while retaining the normal close-time save.
- Accept simple string hotkeys from earlier custom builds for backwards compatibility.


## Batch MIDI, playlist ordering, and shortcut update

### Added
- The Playback page can import multiple MIDI files at once.
- Batch import supports automatic track/hand selection or a per-file manual workflow.
- Automatic selection failures can be ignored individually, ignored for all remaining files, or completed manually.
- Batch import and playlist export display progress and completion details.
- Playlist rows support Ctrl multi-selection and drag reordering, including moving several selected songs together.
- Multi-selection context actions: batch modify, batch save MIDI as, and batch delete.
- The shortcut editor supports Play/Pause, Stop, Previous, and Next, with two bindings per action.
- Windows media transport keys are recognized, including Media Play/Pause, Media Previous, Media Next, and Media Stop.
- MIDI track-name decoding now repairs common UTF-8, GB18030, Big5, and Shift-JIS mojibake.

### Changed
- The Playback file button is now labelled “Import MIDI (Multi-select)”.
- Chinese UI terminology uses “快捷键” instead of “热键”.
- Playlist export writes in a worker thread and reports success only after the destination file has been finalized.

## Drag reorder stability fix
- Replaced QTableWidget `InternalMove` with a private non-destructive `QDrag` flow.
- Prevented Qt from clearing the dragged row after the playlist had already been redrawn.
- Added strict reorder validation so malformed/partial row IDs cannot push an omitted song to the bottom.

## Settings scrolling and text-sheet playlist support

### Added
- Settings now uses a vertical scroll area with natural/fixed card heights, preventing controls from being squeezed together at smaller window heights.
- Text sheets from the Translator page can be named and added directly to the playlist.
- Text-sheet playlist items retain source text, canonical format, BPM, duration, and playback/simulated-performance settings.
- Text-sheet songs can be played from all playlist modes and modified from the single-item right-click menu.
- Normal and complete `.humidiplaylist` exports preserve text-sheet songs without requiring a MIDI source.
- Mixed MIDI/text-sheet multi-selection warns before MIDI-only batch operations and offers **Only Process MIDI**.

### Changed
- A single text-sheet song hides **Save MIDI As…**.
- An all-text-sheet multi-selection hides **Batch Modify Songs** and **Batch Save MIDI As…**.
- The Settings page remains usable at the existing minimum window size without increasing the window dimensions.
- Translator `Import`, `Export`, `Virtual Piano`, and generated-output placeholder strings are localized.
- The Tempo Sway tooltip is localized in Simplified Chinese.

## 2026-08-02 — Transport, scrolling, drag-selection, and mini-player update

- Settings-page opacity and theme controls no longer consume the mouse wheel; the settings page keeps scrolling instead.
- Holding Ctrl while sweeping across playlist rows now performs range-style multi-selection instead of starting a reorder drag.
- Playlist reorder dragging supports mouse-wheel scrolling and automatic scrolling near the top and bottom edges.
- The global play button and play shortcut can start a pasted text sheet directly from the Translator import page; playback stays on that page so the global stop control remains available.
- Playback countdown duration is configurable from 1–10 seconds with a linked slider and numeric input.
- Save and Reset were moved from the global transport bar into the Playback page.
- Previous and Next controls were added immediately to the left of Collapse.
- The play button uses left-aligned text so its label remains visible in narrower windows.
- Mini mode now includes playback-mode selection, Previous/Next controls, and a scrollable compact playlist; the old MIDI-load, saved-playback-load, and simulated-performance toggle controls were removed.
- Mini mode was enlarged to accommodate the compact playlist.

## Playback archive button layout refinement

- Moved **Reset** directly below **Import MIDI (Multi-select)** on the Playback page.
- Moved the save action directly below **Load Save** and renamed it **Save Playback** / **保存存档**.
- Save Playback and Reset now use the same standard button palette as the neighboring import/load buttons.

## Playback left-panel scrolling refinement

- Wrapped the Playback page's MIDI-file and playback-option cards in their own vertical scroll area.
- File and playback cards now keep their natural fixed height instead of being compressed at the minimum window size.
- A vertical scrollbar appears only when the available height is too small; the existing default and minimum window sizes remain unchanged.

## Windows drag-wheel scrolling fix

- Added a temporary Windows native event filter during playlist reordering.
- Captures `WM_MOUSEWHEEL` inside Qt's native `QDrag` loop, where ordinary `wheelEvent` and QObject event filters do not receive the wheel message.
- Forwards wheel deltas to the playlist vertical scrollbar and refreshes the white insertion line from the real cursor position.
- Keeps the existing top/bottom edge auto-scroll behavior as a fallback.

## Playback column visual balance

- Matched the right-side **Human-like Performance** card height to the complete left Playback column.
- Extra height is absorbed by the card's internal bottom spacer, so controls retain their natural size.
- The height is recalculated after MIDI-name or language changes, while both columns keep their independent scrollbars at smaller window sizes.


## Strict MIDI parsing with optional clip repair

- Restored the pre-DWM title-bar baseline; no Windows DWM dark-titlebar code is included.
- MIDI files are still parsed in strict mode first.
- If strict parsing detects an out-of-range MIDI data byte, the user is asked whether to retry with Mido `clip=True`.
- Single-file and batch MIDI import both show the filename-specific confirmation.
- Declining repair cancels that single import or records the file as not imported in the batch summary.
- Accepted clip mode is stored with the song settings so preview, saving, playlist compilation, editing, and later playback continue to use the compatible parser mode.

## Roblox input compatibility fix

- Removed the custom virtual-key-only Windows `SendInput` backend from Performance Optimization.
- Performance Optimization now keeps HuMidi's original `pynput` keyboard injection path, while still collapsing duplicate simultaneous physical actions and reducing scheduling overhead.
- Disabled mode is once again the untouched legacy playback path.
- Persisted boolean values are parsed strictly so strings such as `"false"` cannot accidentally enable Performance Optimization.
