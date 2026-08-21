from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal as Signal

from core.core import MidiParser


class BatchPlaylistEditPrepareWorker(QObject):
    """Load and parse playlist MIDI entries without blocking the GUI thread."""

    progress = Signal(int, int, str)
    prepared = Signal(object, object, bool)
    finished = Signal()

    def __init__(
        self,
        descriptors: list[dict[str, Any]],
        cancel_event: threading.Event,
        missing_midi_message: str,
        no_tracks_message: str,
    ) -> None:
        super().__init__()
        self.descriptors = list(descriptors)
        self.cancel_event = cancel_event
        self.missing_midi_message = str(missing_midi_message)
        self.no_tracks_message = str(no_tracks_message)

    def run(self) -> None:
        entries: list[dict[str, Any]] = []
        failures: list[str] = []
        canceled = False
        total = len(self.descriptors)
        try:
            for index, descriptor in enumerate(self.descriptors, start=1):
                if self.cancel_event.is_set():
                    canceled = True
                    break

                item_id = str(descriptor.get("item_id") or "")
                metadata = descriptor.get("metadata") or {}
                song_data = descriptor.get("song_data") or {}
                midi_path = str(descriptor.get("path") or "")
                display_name = str(
                    metadata.get("name")
                    or (Path(midi_path).stem if midi_path else item_id)
                    or item_id
                )
                self.progress.emit(index, total, display_name)

                try:
                    if not midi_path or not os.path.exists(midi_path):
                        raise FileNotFoundError(self.missing_midi_message)
                    settings = song_data.get("playback_settings", {})
                    if not isinstance(settings, dict):
                        settings = {}
                    tracks, tempo_map = MidiParser.parse_structure(
                        midi_path,
                        1.0,
                        None,
                        clip_invalid_data=bool(
                            settings.get("midi_clip_invalid_data", False)
                        ),
                    )
                    selection = song_data.get("selected_tracks", [])
                    role_map = {
                        int(raw.get("index")): str(
                            raw.get("role") or "Auto-Detect"
                        )
                        for raw in selection
                        if isinstance(raw, dict) and "index" in raw
                    }
                    if role_map:
                        selected_tracks = [
                            (track, role_map[track.index])
                            for track in tracks
                            if track.index in role_map
                        ]
                    else:
                        selected_tracks = [
                            (track, "Auto-Detect")
                            for track in tracks
                            if not track.is_drum
                        ]
                    if not selected_tracks:
                        raise ValueError(self.no_tracks_message)

                    entries.append(
                        {
                            "item_id": item_id,
                            "path": midi_path,
                            "name": display_name,
                            "original_filename": str(
                                metadata.get("source_midi_filename")
                                or Path(midi_path).name
                            ),
                            "selected_tracks": selected_tracks,
                            "tempo_map": tempo_map,
                            "song_data": song_data,
                        }
                    )
                except Exception as exc:  # keep processing the remaining songs
                    failures.append(f"{display_name}: {exc}")
        finally:
            self.prepared.emit(entries, failures, canceled)
            self.finished.emit()
