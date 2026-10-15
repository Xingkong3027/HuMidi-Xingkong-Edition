# Third-party notices — HuMidi Xingkong Edition 2.1.2-xk.12

Original HuMidi: Copyright (c) 2026 smyGitt, MIT. Xingkong modifications: Copyright (c) 2026 Xingkong3027, MIT. Preserve `LICENSE`, `LICENSES/HuMidi-MIT.txt`, `LICENSES/Xingkong-MIT.txt` and `NOTICE.md` with the corresponding distribution.

This edition uses the Rust / Tauri 2 / React architecture from upstream HuMidi 2.1.2. It does not embed the old Python / PyQt6 runtime. Historical Python notices are retained under `docs/legacy/` for historical attribution; they describe that older edition.

The application embeds the unmodified upstream 2.1.2 PedalAI safetensors model. Its About/License page retains credits for the POP909, GiantMIDI-Piano and Saarland Music Data training datasets and their stated licenses. Saarland Music Data, MIDI-Audio Piano Music v2 is credited as Müller et al. (2024), CC BY 3.0, <https://doi.org/10.5281/zenodo.13753319>.

The frontend and Rust build use third-party dependencies including Tauri, React, Phosphor Icons, Candle, Enigo, rdev, midly, zip and encoding_rs. `package-lock.json` and `src-tauri/Cargo.lock` record the resolved package versions. Individual dependencies retain their own licenses; the project's MIT license does not replace them.

The release license bundle includes an inventory and available original copyright/license texts from locked Rust crates and production npm packages. See `LICENSES/DEPENDENCIES.json`, `LICENSES/RUST-DEPENDENCIES.txt` and `LICENSES/NPM-DEPENDENCIES.txt`. The inventory includes platform and build dependencies as a conservative superset; individual original texts remain authoritative. Regenerate it with `python qa/collect-licenses.py` after installing locked dependencies.
