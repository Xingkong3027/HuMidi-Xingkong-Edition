# Windows manual smoke-test checklist

Before publishing the EXE, run these checks on Windows:

1. Import one MIDI and confirm the normal track-selection dialog still works.
2. Import several MIDI files:
   - automatic mode;
   - manual mode;
   - one MIDI requiring the automatic-selection fallback;
   - Ignore and Ignore All;
   - Continue Settings and direct Add to Playlist.
3. Ctrl-select several playlist rows, right-click, and test all three batch actions.
4. Drag one row, then drag a non-contiguous multi-selection; verify the white insertion line and saved order after restart.
5. Export both normal and complete `.humidiplaylist` files; confirm the success dialog appears only after the file exists and can be imported.
6. Configure both shortcut slots for every action, restart HuMidi, and verify persistence.
7. Verify Media Play/Pause (`VK 0xB3`), Media Previous (`VK 0xB1`), Media Next (`VK 0xB0`), and Media Stop (`VK 0xB2`) on the target keyboard.
8. Import MIDI files containing UTF-8, GBK/GB18030, or Big5 Chinese track names and inspect the track-selection dialog.
9. Resize the expanded window down to its minimum size, open Settings, and verify every card keeps a readable height and the page scrolls vertically.
10. In Translator, add a Virtual Piano text sheet to the playlist, play it, right-click Modify, change its text/BPM/title, and complete the modification.
11. Verify a single text-sheet row has no Save MIDI As action; an all-sheet multi-selection has only Batch Delete; and a mixed selection offers MIDI-only actions with the Only Process MIDI warning.
12. Export/import both normal and complete playlists containing a mixture of MIDI and text-sheet songs.
13. Switch between Simplified Chinese and English and verify Translator tab labels, Virtual Piano format text, output placeholder, and Tempo Sway tooltip.

## Transport and interaction update

- Open Settings, place the pointer over Opacity, then rotate the mouse wheel: the page should scroll and opacity should not change.
- Repeat over the Theme and Language selectors: the page should scroll without changing the selection.
- In Playlist, hold Ctrl and drag across several rows: all swept rows should become selected and no reorder drag should begin.
- Release Ctrl and the mouse, then drag one of the selected rows: the whole selected block should move together.
- While reordering a long playlist, use the mouse wheel and hold the pointer near the top/bottom edge; the list should scroll and the white insertion line should remain accurate.
- On Translator > Import, paste a playable sheet and use the bottom-left Play button or configured play shortcut. Confirm playback starts without pressing Play Sheet and remains on the Translator page.
- Use the global Stop button/shortcut while the sheet is playing.
- On Playback, enable Countdown and verify the slider/input remain synchronized and the selected duration is used.
- Resize the main window narrower and confirm the Play label remains visible from the left side of the button.
- Confirm Save and Reset are present on the Playback page and absent from the bottom transport bar.
- Confirm Previous and Next appear immediately before Collapse and work with playlist playback.
- Enter mini mode: verify playback-mode selection, the scrollable playlist, Previous/Next, play/stop, scrubber, and Expand all work; double-click a compact-list song to play it.
- Resize the expanded window to its minimum height, open Playback, and verify the MIDI-file and playback-option cards remain readable while the left side gains a vertical scrollbar instead of squeezing controls together.
- On Windows, begin dragging a playlist song and rotate the mouse wheel without releasing the left button. Confirm the playlist scrolls in both directions and the dragged selection remains active.
- Repeat with multiple Ctrl-selected songs and verify the white insertion line follows the newly visible rows before dropping.


## Countdown time-label display

1. Enable countdown and set it to 3 seconds.
2. Start MIDI, saved Playback, playlist, and text-sheet playback.
3. Confirm the bottom time label shows `(倒计时3秒)`, then 2 and 1.
4. Confirm the suffix disappears as soon as actual playback starts.
5. Stop during countdown and confirm the suffix is cleared immediately.
6. Switch to English and confirm the suffix is shown in English.

## Strict MIDI / clip compatibility

- Import a normal standards-compliant MIDI and confirm no repair dialog appears.
- Import a MIDI containing a data byte outside 0..127 and confirm the dialog names that file.
- Choose No and confirm the MIDI is not imported.
- Choose Yes and confirm track selection opens and the song can preview, save, and be added to the playlist.
- Restart the program and play the repaired playlist song again; it should not fail strict parsing.
- Batch-import a mixture of normal and invalid MIDI files; confirm each invalid file is prompted and declined files appear in the final failure list.

## MIDI dialog localization

- Switch to Simplified Chinese, import a MIDI with an illegal data byte, and confirm the repair prompt buttons read `是` and `否`.
- Select a non-MIDI file and confirm the error explains in Chinese that the `MThd` MIDI header is missing, without showing the raw Mido English sentence.
- Repeat the invalid-file case inside a batch import and confirm the final failed-file list uses the localized reason.
- Switch to English and confirm the same dialogs remain readable in English.


## Dense MIDI performance optimization

1. Import `寄_日_快_乐.mid`, leave Performance Optimization off, and confirm playback still uses the previous behavior.
2. Stop playback, enable Performance Optimization, then replay the same dense section. Confirm the large simultaneous chords no longer cause the same accumulated delay.
3. Verify ordinary sparse MIDI files sound unchanged with the option on and off.
4. Test shifted black-key notes, unshifted white-key notes, 88-key layout, sustain pedal, pause/resume, seek, stop, saved Playback, playlist playback, and text-sheet playback.
5. Add a song to the playlist with Performance Optimization enabled, restart HuMidi, and confirm the setting is restored for that song.
6. Enable Debug Output only for diagnosis; it intentionally adds logging overhead and should not be used for the final performance comparison.


## Roblox input compatibility after performance fix

1. Import a simple MIDI, leave **Performance Optimization** disabled, focus the Roblox piano, and verify keys are injected exactly as in the pre-optimization build.
2. Enable **Performance Optimization**, restart playback, and verify Roblox still receives notes.
3. Test the supplied dense MIDI and compare timing with the switch off/on.
4. Put `"performance_optimization": "false"` temporarily in the config file and verify the checkbox and playback path remain disabled.
