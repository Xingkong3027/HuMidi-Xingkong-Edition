# Test Report

Build: HuMidi: Xingkong Edition 2.0.0-xk.1 Preview  
Date: 2026-08-22

## Automated verification

- Full-tree Python AST parsing: passed.
- Python bytecode compilation: passed.
- Unit and static integration suite: **58 tests passed**.
- Ruff correctness checks configured in `ruff.toml`: passed.
- GitHub Actions CI and Release YAML parsing: passed.
- ZIP input archive integrity: passed before modification.
- Obvious credential/private-key pattern scan: no matches found.

Automated tests cover configuration UTF-8 persistence, shortcut persistence,
media keys, deterministic humanization, strict/clip MIDI parsing, MIDI text
decoding, dense-MIDI action planning, playlist import/export and ordering,
trimming, Windows wheel-message parsing, and static integration of the requested
UI and playback features.

## Dense-MIDI optimization behavior

- Performance Optimization remains optional and defaults to off.
- Physically identical key/modifier attacks at the exact same timestamp are
  collapsed while logical note and release reference counts are preserved.
- Shifted and unshifted variants sharing a base key remain ordered re-strikes.
- The optimized path retains HuMidi's original `pynput` input backend for
  Roblox compatibility; it does **not** use the removed custom SendInput batcher.
- On Windows, playback may request 1 ms timer resolution, use above-normal
  playback-thread priority, temporarily suspend cyclic garbage collection, and
  reduce GUI update pressure for the duration of optimized playback.

## Distribution and identity checks

- Product identity is consistently documented as HuMidi: Xingkong Edition.
- Application version and release tag format use `2.0.0-xk.N`.
- Configuration is isolated under `~/.humidi-xingkong`.
- Update checks target the Xingkong Edition GitHub Releases page and never
  download or replace the executable automatically.
- Upstream MIT attribution, Xingkong modification notice, GPL v3 text, third-
  party notices, and a security policy are included.
- macOS `icon.icns` was restored from the upstream repository.

## Required target-system smoke tests

The verification environment is not a Windows Roblox desktop and cannot prove
real in-game keyboard acceptance or macOS Accessibility behavior. Before
promoting the preview to a stable release, manually test:

1. Normal and optimized playback in the intended Roblox piano experience.
2. Pause/resume/stop and release of all held notes, modifiers, and pedal keys.
3. Shortcut and media-key behavior on Windows.
4. Playlist persistence, complete export/import, and configuration isolation.
5. The GitHub Actions Windows/macOS packages produced from the release tag.

