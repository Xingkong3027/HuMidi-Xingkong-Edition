# HuMidi

[![Static Badge](https://img.shields.io/badge/SourceForge-HuMidi_v2.0-orange?logo=sourceforge)](https://sourceforge.net/projects/humidi-roblox-piano-autoplayer/)
[![Static Badge](https://img.shields.io/badge/Releases-HuMidi_v2.0-blue?logo=github)](https://github.com/smyGitt/HuMidi-Roblox-Piano-Autoplayer/releases)
![GitHub Repo stars](https://img.shields.io/github/stars/smyGitt/HuMidi-Roblox-Piano-Autoplayer?style=flat)
[![Download HuMidi](https://img.shields.io/sourceforge/dt/humidi-roblox-piano-autoplayer.svg)](https://sourceforge.net/projects/humidi-roblox-piano-autoplayer/files/latest/download)
[![Download HuMidi](https://img.shields.io/sourceforge/dw/humidi-roblox-piano-autoplayer.svg)](https://sourceforge.net/projects/humidi-roblox-piano-autoplayer/files/latest/download)
[![](https://dcbadge.limes.pink/api/server/https://discord.gg/bRaXP9gYZN?style=flat)](https://discord.gg/bRaXP9gYZN)
### You can download the latest version of HuMidi from the Releases or from Sourceforge.
### If you have any issues with HuMidi, please create a new issue here or in the Discord server. Thank you!



## About HuMidi
HuMidi includes various humanization options for a natural, human-like playback. Including automatic pedal timing and 88-key keyboard support. Easy to run via executable or source code, with GUI support included.


<img width="326" height="396" alt="HuMidi v2.0 Expanded view with all Humanization and related options in playback" src="https://github.com/user-attachments/assets/e253ae9e-9280-4cb9-97bb-4ad6ac302237" />
<img width="326" height="396" alt="A minimized, compact view of HuMidi v2.0. Only necessary buttons are shown." src="https://github.com/user-attachments/assets/11065766-a107-461a-a46f-84f8119098cf" />
<img width="180" height="326" alt="HuMidi v2.0 with a new Light mode theme, showing a settings page with option to change color theme." src="https://github.com/user-attachments/assets/344cf20a-ffe2-482c-bc71-53c4c378a5ad" />

## Note on ML Components
Future versions of HuMidi may incorporate a trained model from [PedalAI](https://github.com/smyGitt/PedalAI) for sustain pedal generation. For information on training data sources, licensing, and related legal considerations, refer to [PedalAI's README](https://github.com/smyGitt/PedalAI#copyright--intended-use).

# How do you run it?
### If you downloaded the file from the releases:
  just run the `.exe` or `.dmg`! 

### Or, if you don't trust me...
You can create your own `.exe` or `.dmg` with pyinstaller. I've provided the icon `icon.ico` (or `icon.icns` for MacOS), so use with this command:

For Windows:
    
    pyinstaller --onefile --noconsole --name HuMidi --icon icon.ico --add-data "icon.ico;." main.py

For Mac:

    pyinstaller --onefile --windowed --name HuMidi --icon icon.icns --add-data "icon.ico:." main.py

  make sure the `.ico` or `.icns` file and `.py` file is in the same directory.

### ...if you choose to do neither above:
You need to run this in a command prompt. After you navigate to where the `.py` files are. type for example:

    python main.py
    
  else if you are not going to use the `main.py` with GUI, for whatever reason, navigate to the backup folder, open command prompt there, then enter:

    python final_beforeGUI.py --help

  (of course, you may replace `final_beforeGUI.py` with `noDuration.py`, or any in the backup if desired)

this will show you all the available flags and formatting. Though I can't guarantee the same quality from the GUI versions, because the noGUI version hasn't been updated at all.

Remember that it accepts `.mid` files only. it works best with piano-only `.mid`, but I've seen it work with mixed instruments.

# Dependencies
If you chose to not trust me (not judging) and did not want to use the `exe` in the releases, you might need to install a few python libraries. You will see that `main.py` and other `.py` files import various libraries. You can't run this application without downloading all of them. Some (not all) are:

    import mido, time, headpq, threading, random, copy, numpy, sys, dataclasses, import, collections, os, PyQt6  

and there may be more for the other `.py` files. Please check if you have every one of these libraries installed.

if you get some warning about pyinstaller not being compatible with some module, like `typing`, then just uninstall it with 

    pip uninstall <MODULE NAME>
    
  or
  
    python -m pip uninstall <MODULE NAME>
