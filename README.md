# HuMidi: Xingkong Edition

[**English**](README.md) | [简体中文](README.zh-CN.md)

[![Release](https://img.shields.io/github/v/release/Xingkong3027/HuMidi-Xingkong-Edition?display_name=tag)](https://github.com/Xingkong3027/HuMidi-Xingkong-Edition/releases)
[![CI](https://github.com/Xingkong3027/HuMidi-Xingkong-Edition/actions/workflows/ci.yml/badge.svg)](https://github.com/Xingkong3027/HuMidi-Xingkong-Edition/actions/workflows/ci.yml)
[![Platform](https://img.shields.io/badge/platform-Windows-0078D6?logo=windows)](#system-requirements)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](#run-from-source)

> An unofficial derivative of HuMidi for playing MIDI and text sheets on Roblox piano keyboards.

**Current stable version: `2.0.0-xk.1`**

HuMidi: Xingkong Edition is based on
[smyGitt/HuMidi-Roblox-Piano-Autoplayer](https://github.com/smyGitt/HuMidi-Roblox-Piano-Autoplayer).
It preserves HuMidi's MIDI parsing, human-like performance, visualizer, and keyboard-output core while adding advanced playlists, Simplified Chinese localization, multi-file workflows, configurable countdowns, non-destructive playback-range trimming, Roblox input compatibility fixes, and optional dense-MIDI optimizations.

This project is not an official HuMidi or Roblox product and is not affiliated with or endorsed by smyGitt or Roblox Corporation.

## MIDI Files, Copyright, and Third-Party Sources

HuMidi: Xingkong Edition is a MIDI-processing and keyboard-input automation tool. The ability of this software to open, process, play, or export a MIDI file does not automatically grant the user any rights to that MIDI file, its arrangement, score, recording, lyrics, or underlying musical composition.

Users generally do not need to be overly concerned when playing MIDI files locally for personal learning or software testing. However, MIDI files may come from different sources and may be subject to different licensing conditions. Additional care is recommended when publishing a performance, uploading a video, livestreaming, monetizing content, or redistributing a MIDI file or playlist package.

Please note:

* “Free to download” means that a file can be obtained from a website, but it does not necessarily mean that the file is copyright-free or may be redistributed without restriction.
* A musical composition being in the public domain does not automatically place a later arrangement, transcription, score edition, or MIDI file in the public domain.
* A MIDI file, arrangement, recording, lyrics, and other materials appearing in a video may each be governed by separate rights or licenses.
* If no license is shown, the file should be treated as having an unknown copyright status—not automatically as copyright-free or necessarily infringing.
* MIDI files with an unknown status are best limited to personal learning, local playback, and software testing in accordance with the source website’s rules. Before publishing or redistributing them, consider contacting the creator, checking the original source, or finding an openly licensed alternative.
* Before using a MIDI file or its rendered performance in a public video, livestream, software demonstration, GitHub repository, release asset, or other public material, review any creator notes, copyright notices, embedded metadata, and license information.
* A complete `.humidiplaylist` package may contain copies of MIDI files. Before sharing such a package publicly, check whether its MIDI files may be redistributed. If this cannot be confirmed, consider sharing a normal playlist without embedded MIDI files and allowing recipients to provide their own copies.
* When a license requires attribution, a license link, an indication of modifications, or distribution under the same license, follow those requirements.

This project cannot verify every MIDI file independently imported by its users. Users should make a reasonable decision based on the source of each file and their intended use, while following the source platform’s rules and applicable law. To the extent permitted by applicable law, the project maintainers and contributors make no representations regarding the copyright status of user-supplied third-party content.

### MIDI Sources with Identifiable Licensing

The following websites may help users find public-domain or openly licensed music materials. These sources are generally better suited to public demonstrations, videos, and distributable playlists:

* [Mutopia Project](https://www.mutopiaproject.org/) — Provides PDF, MIDI, and LilyPond files under public-domain or Creative Commons terms. Check the license displayed on each individual work page.
* [Wikimedia Commons](https://commons.wikimedia.org/) — Hosts some MIDI files with individual licensing information. Files explicitly marked Public Domain or CC0 are generally the simplest choices.
* [OpenScore](https://github.com/OpenScore/) — Provides collections of digitally engraved scores released under CC0, some of which may be converted or exported to MIDI.

Even when using these websites, review the individual work page because different files may be provided under different licenses.

### Larger and More Diverse Community MIDI Libraries

The following community platforms generally provide larger and more varied MIDI collections, including classical music, popular music, game and film music, original compositions, transcriptions, and user-created arrangements. They can be useful for discovering music, online preview, personal learning, and testing HuMidi’s features:

* [MidiShow](https://www.midishow.com/) — Offers a large collection covering many genres and different MIDI versions. Work pages may include uploader notes, copyright notices, source information, and MIDI file properties that can help users evaluate a file.
* [Online Sequencer – Sequences](https://onlinesequencer.net/sequences) — Offers many user-created compositions, transcriptions, arrangements, and remakes, with online playback and MIDI export.

The advantage of these community platforms is their larger and more diverse selection. However, because their content is primarily uploaded or created by users, licensing conditions may differ between files. The availability of preview, download, or export features does not necessarily grant permission to publish or redistribute the content.

Content without clear licensing information may be used for personal learning, local playback, and feature testing in accordance with the platform’s rules. Before using it in a public video, livestream, software release, or publicly distributed playlist package, consider verifying the rights to the underlying composition, arrangement, and MIDI sequence. When the status cannot be confirmed, a Public Domain, CC0, CC BY, or otherwise clearly licensed alternative may be a safer choice.

All links above lead to independent third-party websites and are provided solely for the convenience of users searching for MIDI materials. This project is not affiliated with, sponsored by, endorsed by, or responsible for these services, and cannot guarantee that their content, licensing information, or availability will remain unchanged. Always refer to the latest information shown on the individual file page.

This section provides general information only and does not constitute legal advice.

## Download

Download the latest version from [GitHub Releases](https://github.com/Xingkong3027/HuMidi-Xingkong-Edition/releases/latest).

| File | Purpose |
| --- | --- |
| `HuMidi-Xingkong-Edition-Windows.zip` | Recommended complete Windows package with the executable and license notices. |
| `HuMidi-Xingkong-Edition.exe` | Standalone Windows executable. |
| `SHA256SUMS.txt` | SHA-256 hashes for download-integrity verification. |

For the ZIP package, extract all files to a normal folder before launching the executable. Windows may show an **Unknown publisher** warning because public builds are not code-signed. Only run files obtained from this repository, and compare their SHA-256 hashes when possible.

## Highlights

### MIDI playback and track selection

- Import one or multiple `.mid` / `.midi` files.
- Automatically select playable non-drum tracks or choose tracks and left/right-hand roles manually.
- Configure tempo, transpose, pedal behavior, 88-key mapping, and simulated-performance options.
- Save compiled Playback archives for quick reuse.
- Use strict MIDI parsing first, with an explicit optional clip-repair prompt for selected out-of-range data-byte errors.

### Configurable pre-playback countdown

- Enable or disable the countdown on the Playback page.
- Choose any duration from **1 to 10 seconds** with a synchronized slider and numeric input.
- See the remaining countdown beside the transport time display before playback begins.
- Each playlist song can retain its own countdown setting and duration.

### Non-destructive MIDI playback-range trimming

The **Trim** controls remove unwanted leading or trailing silence from playback without overwriting the original MIDI file.

- **Automatic trim:** uses the first playable note as the start and the last playable note as the end.
- **Manual trim:** enter a start and end time to select the range that should be played.
- Notes and tempo/time-signature information inside the selected range are shifted to begin at time zero.
- Notes crossing the selected boundaries are clipped to the retained range.
- The trim range is saved with Playback and playlist settings, while the stored original MIDI remains available.

This is useful when a MIDI contains a long blank section before the first note or after the performance ends.

### Advanced playlists

Each MIDI playlist entry can retain:

- a local copy of the original MIDI;
- source filename and path information;
- track and hand selections;
- tempo, transpose, pedal, 88-key, countdown, trim, and performance settings;
- human-like performance mode and random-seed policy;
- an optional deterministic compiled cache for faster startup;
- visualization notes, pedal ranges, tempo, and time-signature data when available.

Text sheets created on the Translator page can also be named, added to the playlist, played, exported, and modified.

### Playlist multi-selection and batch operations

On the Playlist page:

1. Hold **Ctrl** and click songs to select or deselect multiple rows.
2. You can also hold **Ctrl** and sweep the pointer across rows for range-style multi-selection.
3. Right-click the selection to use the available batch commands:
   - **Batch Modify Songs** — apply only the playback settings you change to the selected MIDI songs;
   - **Batch Save MIDI As…** — extract the retained original MIDI files into a selected folder;
   - **Batch Delete** — remove the selected playlist entries after confirmation.
4. After releasing Ctrl, drag one selected row to move the selected block together. A white insertion line shows the destination.

MIDI-only commands are hidden for an all-text-sheet selection. For mixed MIDI/text-sheet selections, the program warns you and offers to process only the MIDI entries.

### Five playlist playback modes

- Single Play
- Single Repeat
- Repeat All
- Sequential
- Shuffle

Previous and Next controls are available in the main transport and compact mini mode.

### Human-like performance and reproducible randomness

Human-like performance can be:

- **Disabled**;
- **Enabled with global settings** from Settings;
- **Enabled with individual settings** for the current MIDI or playlist song.

Seed modes include:

- **Dynamic random seed:** recompiles a different performance each time.
- **Fixed random seed:** generates a repeatable seed and stores a compiled cache.
- **Fixed custom seed:** lets you enter a seed for reproducible performances across sessions or computers when the same source and settings are used.

### Playlist import and export

Both export types use the `.humidiplaylist` extension:

- **Normal export:** stores playlist structure, paths, settings, track choices, and seed policies. It is smaller but may depend on the original MIDI paths.
- **Complete export:** embeds retained MIDI copies and available deterministic caches for migration or sharing. Unnecessary absolute source paths are removed from the shared package.

Text-sheet entries are self-contained in both formats.

### Batch MIDI import

Use **Import MIDI (Multi-select)** to choose one or more files. For a batch, you can:

- process all files automatically;
- choose tracks and hand roles for every file manually;
- handle automatic-selection failures per file;
- review successful and failed files in a final summary;
- add the prepared batch directly to the playlist or apply shared settings first.

### Shortcuts and Windows media keys

Settings → Keyboard Shortcuts provides up to two bindings for each action:

- Play/Pause
- Stop
- Previous Song
- Next Song

Regular keys, function keys, letters, numbers, and supported Windows media transport keys can be used.

### Localization, themes, visualizer, and mini mode

- Runtime language selection: Automatic, Simplified Chinese, or English.
- Customizable themes and window opacity.
- Piano and timeline visualizers synchronized with compiled playback events.
- Compact mini mode with playback-mode selection, Previous/Next controls, and a scrollable playlist.
- Scrollable Playback and Settings layouts for smaller window sizes.

### Optional dense-MIDI optimization

The Playback page includes an optional **Performance Optimization** switch for exceptionally dense MIDI files. It reduces duplicate same-timestamp attacks, improves Windows timer precision, and lowers UI-update pressure while retaining the original `pynput` input backend for Roblox compatibility.

Leave this option disabled if the original playback behavior already works well for a song.

## Quick start

1. Download and extract `HuMidi-Xingkong-Edition-Windows.zip`.
2. Start `HuMidi-Xingkong-Edition.exe`.
3. Open **Playback** and choose **Import MIDI (Multi-select)**.
4. Select tracks automatically or assign tracks to the left and right hands manually.
5. Configure playback, countdown, trim, and human-like performance settings.
6. Open the target Roblox piano experience and focus its piano input.
7. Press Play or use a configured shortcut.
8. Stop playback before switching experiences or changing input targets.

Automated keyboard input may be restricted by Roblox or by individual experiences. You are responsible for following Roblox Terms and the rules of the experience you use.

## System requirements

- Windows 10 or Windows 11, 64-bit recommended.
- A keyboard-compatible Roblox piano experience or another compatible virtual-piano target.
- No Python installation is required for the packaged `.exe`.

Only the Windows package is currently released and tested by the Xingkong Edition maintainer. Source execution on other desktop platforms is not an officially tested release target.

## Run from source

Python 3.11 is recommended.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Run the checks:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m compileall -q .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Build the Windows executable

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

Output:

```text
dist\HuMidi-Xingkong-Edition.exe
```

The repository's `Release Windows` workflow builds the release package from a `v*` tag and publishes SHA-256 checksums. Always test a generated executable on a real Windows system and in the intended Roblox piano experience before marking a release as stable.

## Data locations

Xingkong Edition uses a separate configuration directory and does not overwrite upstream HuMidi settings:

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

The repository's `saves` directory is used for Playback archives. `.humidi` and `.humidi-xingkong` are not automatically merged or deleted.

## Updates and security

- The application checks only this repository's GitHub Releases page.
- It never silently downloads or replaces the running executable.
- When an update is available, it asks before opening the release page.
- Verify release assets against `SHA256SUMS.txt` when possible.
- Report security issues through [GitHub private security advisories](https://github.com/Xingkong3027/HuMidi-Xingkong-Edition/security/advisories) rather than exposing sensitive information in a public issue.

Do not include Roblox credentials, session cookies, private MIDI files, or personal filesystem paths in reports.

## Documentation

- [Detailed Playlist Edition guide](README_PLAYLIST_EDITION.md)
- [Changelog](CHANGELOG.md)
- [Publishing guide](PUBLISHING.md)
- [Security policy](SECURITY.md)
- [Attribution notice](NOTICE.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

## Project relationship and attribution

- Original project: [smyGitt/HuMidi-Roblox-Piano-Autoplayer](https://github.com/smyGitt/HuMidi-Roblox-Piano-Autoplayer)
- Xingkong Edition: [Xingkong3027/HuMidi-Xingkong-Edition](https://github.com/Xingkong3027/HuMidi-Xingkong-Edition)
- Original HuMidi author: [smyGitt](https://github.com/smyGitt)
- Xingkong Edition creator and maintainer: [Xingkong3027](https://github.com/Xingkong3027)
- Code review, documentation, release preparation, and workflow improvements for Xingkong Edition were assisted by OpenAI Codex.

See [NOTICE.md](NOTICE.md) for the complete modification and attribution notice.

## License

The upstream HuMidi source is provided under the MIT License, and its original copyright and license notice are preserved. The free PyQt6 distribution used by this application is licensed under GPL v3, so a packaged combined distribution must not be described as “MIT only.” Review:

- [LICENSE](LICENSE)
- [HuMidi MIT license](LICENSES/HuMidi-MIT.txt)
- [GPL v3 text](LICENSES/GPL-3.0.txt)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

Closed-source or commercial redistribution requires an appropriate PyQt commercial license or a separately reviewed alternative Qt binding. This summary is not legal advice.

## Support and contributions

Bug reports and reproducible compatibility reports are welcome in [GitHub Issues](https://github.com/Xingkong3027/HuMidi-Xingkong-Edition/issues). Include the Xingkong Edition version, Windows version, the affected feature, reproduction steps, and relevant non-sensitive logs.

Pull requests should target this repository's `main` branch. Changes that may also benefit upstream HuMidi can be proposed separately to the original project.
