# Changelog

All notable Xingkong Edition changes are documented here. The detailed
development history remains available in `CHANGELOG_PLAYLIST_EDITION.md`.

## 2.0.0-xk.1 — Preview

### Added

- Simplified Chinese and English runtime language switching.
- Advanced local playlists with five playback modes.
- Normal and self-contained `.humidiplaylist` import/export.
- Editable playlist songs, retained MIDI sources, deterministic caches, and
  dynamic/fixed/custom random seeds.
- Multi-file MIDI import, batch playlist operations, text-sheet playlist
  support, expanded shortcuts, and media-key handling.
- Optional dense-MIDI performance optimization using the original `pynput`
  input backend.
- Explicit repair flow for selected malformed MIDI data-byte errors.

### Changed

- Product identity is now `HuMidi: Xingkong Edition`.
- Application configuration is isolated under `~/.humidi-xingkong`.
- Update checks target the Xingkong Edition release page and never install an
  executable automatically.
- Release tags use `v2.0.0-xk.N` to avoid confusion with upstream HuMidi tags.

### Security and distribution

- Added attribution, third-party notices, a security policy, and preserved
  license texts.
- Release automation generates SHA-256 checksums for downloadable binaries.

