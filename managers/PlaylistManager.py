from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
import zipfile
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any


class PlaylistFormatError(ValueError):
    pass


class PlaylistManager:
    """Persistent playlist library.

    Version 3 supports both MIDI songs and self-contained text-sheet songs. MIDI
    entries keep the original MIDI, selected track roles, playback settings, and
    an optional compiled Playback cache. Text sheets keep their source text,
    canonical format name, BPM, and playback settings.
    """

    FORMAT = "HuMidi Playlist"
    VERSION = 3

    def __init__(self, config_dir: Path):
        self.root_dir = Path(config_dir) / "playlist"
        self.items_dir = self.root_dir / "items"
        self.midi_dir = self.root_dir / "midi"
        self.cache_dir = self.root_dir / "cache"
        self.index_path = self.root_dir / "index.json"
        for directory in (self.items_dir, self.midi_dir, self.cache_dir):
            directory.mkdir(parents=True, exist_ok=True)
        self._items: list[dict[str, Any]] = []
        self.load()

    # ------------------------------------------------------------------
    # Index and item access

    def load(self) -> list[dict[str, Any]]:
        if not self.index_path.exists():
            self._items = []
            return self.items()
        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
            raw_items = data.get("items", []) if isinstance(data, dict) else []
            self._items = [self._normalize_metadata(item) for item in raw_items if isinstance(item, dict)]
        except Exception:
            backup = self.index_path.with_suffix(f".corrupt-{datetime.now():%Y%m%d-%H%M%S}.json")
            try:
                self.index_path.replace(backup)
            except OSError:
                pass
            self._items = []
        self._remove_missing_entries()
        return self.items()

    def items(self) -> list[dict[str, Any]]:
        result = []
        for raw in self._items:
            item = deepcopy(raw)
            item_id = str(item.get("id"))
            source_type = self.get_source_type(item_id)
            item["source_type"] = source_type
            item["midi_available"] = source_type == "midi" and bool(self.get_midi_path(item_id))
            item["sheet_available"] = source_type == "sheet" and bool(self.get_sheet_source(item_id))
            item["source_label"] = self.source_label(item_id)
            item["cache_available"] = self._cache_path(item_id).exists()
            result.append(item)
        return result

    def get_metadata(self, item_id: str) -> dict[str, Any] | None:
        item = next((x for x in self._items if x.get("id") == item_id), None)
        if not item:
            return None
        result = deepcopy(item)
        source_type = self.get_source_type(item_id)
        result["source_type"] = source_type
        result["midi_available"] = source_type == "midi" and bool(self.get_midi_path(item_id))
        result["sheet_available"] = source_type == "sheet" and bool(self.get_sheet_source(item_id))
        result["source_label"] = self.source_label(item_id)
        result["cache_available"] = self._cache_path(item_id).exists()
        return result

    def get_song_data(self, item_id: str) -> dict[str, Any]:
        path = self._item_path(item_id)
        if not path.exists():
            raise FileNotFoundError(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise PlaylistFormatError("Playlist item data is invalid.")
        # Transparently migrate the old v1 item format (a raw Playback save).
        if "compiled_events" in data and "song_version" not in data:
            legacy_playback = deepcopy(data)
            metadata = data.get("metadata", {})
            data = {
                "song_version": 3,
                "source": {
                    "type": "midi",
                    "original_path": "",
                    "original_filename": str(metadata.get("source_midi_filename") or "Unknown MIDI"),
                    "local_midi_filename": "",
                },
                "playback_settings": deepcopy(metadata.get("playback_settings", {})),
                "selected_tracks": [],
                "cache_available": True,
                "legacy_cache_only": True,
            }
            self._atomic_write_json(self._cache_path(item_id), legacy_playback)
            self._atomic_write_json(path, data)
        source = data.setdefault("source", {})
        if isinstance(source, dict) and "type" not in source:
            source["type"] = "midi"
        data["song_version"] = max(3, int(data.get("song_version", 0) or 0))
        return data

    def get_playback_data(self, item_id: str) -> dict[str, Any]:
        path = self._cache_path(item_id)
        if not path.exists():
            # Compatibility with pre-v2 libraries where items/<id>.json was the cache.
            legacy = self._item_path(item_id)
            if legacy.exists():
                raw = json.loads(legacy.read_text(encoding="utf-8"))
                if isinstance(raw, dict) and "compiled_events" in raw:
                    self._validate_playback_data(raw)
                    return raw
            raise FileNotFoundError(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        self._validate_playback_data(data)
        return data

    def get_source_type(self, item_id: str) -> str:
        metadata = next((x for x in self._items if x.get("id") == item_id), None)
        if metadata and str(metadata.get("source_type") or "") in {"midi", "sheet"}:
            return str(metadata.get("source_type"))
        try:
            data = self.get_song_data(item_id)
        except Exception:
            return "midi"
        source = data.get("source", {}) if isinstance(data, dict) else {}
        return "sheet" if str(source.get("type") or "midi") == "sheet" else "midi"

    def get_sheet_source(self, item_id: str) -> dict[str, Any] | None:
        try:
            data = self.get_song_data(item_id)
        except Exception:
            return None
        source = data.get("source", {}) if isinstance(data, dict) else {}
        if not isinstance(source, dict) or str(source.get("type") or "midi") != "sheet":
            return None
        text = str(source.get("sheet_text") or "")
        format_name = str(source.get("format_name") or "")
        if not text or not format_name:
            return None
        return {
            "type": "sheet",
            "sheet_text": text,
            "format_name": format_name,
            "bpm": int(source.get("bpm", 120) or 120),
            "humanize": bool(source.get("humanize", False)),
        }

    def source_label(self, item_id: str) -> str:
        if self.get_source_type(item_id) == "sheet":
            source = self.get_sheet_source(item_id) or {}
            return str(source.get("format_name") or "Text Sheet")
        metadata = next((x for x in self._items if x.get("id") == item_id), None) or {}
        return str(metadata.get("source_midi_filename") or "Unknown MIDI")

    def get_midi_path(self, item_id: str) -> str | None:
        try:
            data = self.get_song_data(item_id)
        except (OSError, ValueError, json.JSONDecodeError):
            return None
        source = data.get("source", {}) if isinstance(data, dict) else {}
        if str(source.get("type") or "midi") != "midi":
            return None
        local_name = os.path.basename(str(source.get("local_midi_filename") or ""))
        if local_name:
            local_path = self.midi_dir / local_name
            if local_path.exists():
                return str(local_path)
        original = str(source.get("original_path") or "")
        return original if original and Path(original).exists() else None

    # ------------------------------------------------------------------
    # Create/update/delete

    @staticmethod
    def serialize_tracks(selected_tracks_info: list) -> list[dict[str, Any]]:
        return [
            {"index": int(track.index), "role": str(role)}
            for track, role in selected_tracks_info
        ]

    def add_song(
        self,
        midi_path: str,
        playback_settings: dict[str, Any],
        selected_tracks_info: list,
        playback_data: dict[str, Any] | None = None,
        name: str | None = None,
        duration_hint: float | None = None,
    ) -> dict[str, Any]:
        source_path = Path(midi_path)
        if not source_path.exists():
            raise FileNotFoundError(source_path)
        if playback_data is not None:
            self._validate_playback_data(playback_data)

        item_id = uuid.uuid4().hex
        local_name = self._copy_midi_for_item(item_id, source_path)
        display_name = (name or source_path.stem or source_path.name).strip()
        now = datetime.now().isoformat()
        song_data = {
            "song_version": 3,
            "source": {
                "type": "midi",
                "original_path": str(source_path.resolve()),
                "original_filename": source_path.name,
                "local_midi_filename": local_name,
            },
            "playback_settings": self._stored_settings(playback_settings),
            "selected_tracks": self.serialize_tracks(selected_tracks_info),
            "cache_available": playback_data is not None,
            "legacy_cache_only": False,
        }
        self._atomic_write_json(self._item_path(item_id), song_data)
        if playback_data is not None:
            self._atomic_write_json(self._cache_path(item_id), playback_data)

        duration = self._playback_duration(playback_data) or max(0.0, float(duration_hint or 0.0))
        item = {
            "id": item_id,
            "name": display_name,
            "source_midi_filename": source_path.name,
            "source_type": "midi",
            "source_label": source_path.name,
            "created_at": now,
            "modified_at": now,
            "duration": duration,
            "humanization_mode": str(playback_settings.get("humanization_mode", "individual")),
            "random_seed_mode": str(playback_settings.get("humanization_seed_mode", "dynamic")),
        }
        self._items.append(item)
        self._save_index()
        return deepcopy(item)

    def update_song(
        self,
        item_id: str,
        midi_path: str,
        playback_settings: dict[str, Any],
        selected_tracks_info: list,
        playback_data: dict[str, Any] | None,
        duration_hint: float | None = None,
    ) -> dict[str, Any]:
        metadata = next((x for x in self._items if x.get("id") == item_id), None)
        if metadata is None:
            raise FileNotFoundError(item_id)
        source_path = Path(midi_path)
        if not source_path.exists():
            raise FileNotFoundError(source_path)
        if playback_data is not None:
            self._validate_playback_data(playback_data)

        old_data = self.get_song_data(item_id)
        old_source = old_data.get("source", {})
        current_local = str(old_source.get("local_midi_filename") or "")
        current_local_path = self.midi_dir / os.path.basename(current_local) if current_local else None
        same_local = current_local_path and current_local_path.exists() and source_path.resolve() == current_local_path.resolve()
        if same_local:
            local_name = current_local_path.name
            original_path = str(old_source.get("original_path") or "")
            original_filename = str(old_source.get("original_filename") or source_path.name)
        else:
            if current_local_path:
                current_local_path.unlink(missing_ok=True)
            local_name = self._copy_midi_for_item(item_id, source_path)
            original_path = str(source_path.resolve())
            original_filename = source_path.name

        song_data = {
            "song_version": 3,
            "source": {
                "type": "midi",
                "original_path": original_path,
                "original_filename": original_filename,
                "local_midi_filename": local_name,
            },
            "playback_settings": self._stored_settings(playback_settings),
            "selected_tracks": self.serialize_tracks(selected_tracks_info),
            "cache_available": playback_data is not None,
            "legacy_cache_only": False,
        }
        self._atomic_write_json(self._item_path(item_id), song_data)
        if playback_data is None:
            self._cache_path(item_id).unlink(missing_ok=True)
        else:
            self._atomic_write_json(self._cache_path(item_id), playback_data)

        metadata["source_midi_filename"] = original_filename
        metadata["source_type"] = "midi"
        metadata["source_label"] = original_filename
        metadata["modified_at"] = datetime.now().isoformat()
        compiled_duration = self._playback_duration(playback_data)
        if compiled_duration > 0:
            metadata["duration"] = compiled_duration
        elif duration_hint is not None:
            metadata["duration"] = max(0.0, float(duration_hint))
        metadata["humanization_mode"] = str(playback_settings.get("humanization_mode", "individual"))
        metadata["random_seed_mode"] = str(playback_settings.get("humanization_seed_mode", "dynamic"))
        self._save_index()
        return deepcopy(metadata)

    def add_sheet(
        self,
        sheet_text: str,
        format_name: str,
        bpm: int,
        playback_settings: dict[str, Any],
        name: str | None = None,
        duration_hint: float | None = None,
    ) -> dict[str, Any]:
        text = str(sheet_text or "").strip()
        fmt = str(format_name or "").strip()
        if not text or not fmt:
            raise PlaylistFormatError("The text sheet for this playlist song is unavailable.")
        item_id = uuid.uuid4().hex
        now = datetime.now().isoformat()
        display_name = (name or "Text Sheet").strip() or "Text Sheet"
        humanize = str(playback_settings.get("humanization_mode", "disabled")) != "disabled"
        song_data = {
            "song_version": 3,
            "source": {
                "type": "sheet",
                "sheet_text": text,
                "format_name": fmt,
                "bpm": max(20, min(400, int(bpm))),
                "humanize": humanize,
            },
            "playback_settings": self._stored_settings(playback_settings),
            "selected_tracks": [],
            "cache_available": False,
            "legacy_cache_only": False,
        }
        self._atomic_write_json(self._item_path(item_id), song_data)
        item = {
            "id": item_id,
            "name": display_name,
            "source_midi_filename": "",
            "source_type": "sheet",
            "source_label": fmt,
            "created_at": now,
            "modified_at": now,
            "duration": max(0.0, float(duration_hint or 0.0)),
            "humanization_mode": str(playback_settings.get("humanization_mode", "disabled")),
            "random_seed_mode": str(playback_settings.get("humanization_seed_mode", "dynamic")),
        }
        self._items.append(item)
        self._save_index()
        return deepcopy(item)

    def update_sheet(
        self,
        item_id: str,
        sheet_text: str,
        format_name: str,
        bpm: int,
        playback_settings: dict[str, Any],
        name: str | None = None,
        duration_hint: float | None = None,
    ) -> dict[str, Any]:
        metadata = next((x for x in self._items if x.get("id") == item_id), None)
        if metadata is None:
            raise FileNotFoundError(item_id)
        text = str(sheet_text or "").strip()
        fmt = str(format_name or "").strip()
        if not text or not fmt:
            raise PlaylistFormatError("The text sheet for this playlist song is unavailable.")
        humanize = str(playback_settings.get("humanization_mode", "disabled")) != "disabled"
        song_data = {
            "song_version": 3,
            "source": {
                "type": "sheet",
                "sheet_text": text,
                "format_name": fmt,
                "bpm": max(20, min(400, int(bpm))),
                "humanize": humanize,
            },
            "playback_settings": self._stored_settings(playback_settings),
            "selected_tracks": [],
            "cache_available": False,
            "legacy_cache_only": False,
        }
        self._atomic_write_json(self._item_path(item_id), song_data)
        self._cache_path(item_id).unlink(missing_ok=True)
        metadata["name"] = (name or metadata.get("name") or "Text Sheet").strip() or "Text Sheet"
        metadata["source_midi_filename"] = ""
        metadata["source_type"] = "sheet"
        metadata["source_label"] = fmt
        metadata["modified_at"] = datetime.now().isoformat()
        if duration_hint is not None:
            metadata["duration"] = max(0.0, float(duration_hint))
        metadata["humanization_mode"] = str(playback_settings.get("humanization_mode", "disabled"))
        metadata["random_seed_mode"] = str(playback_settings.get("humanization_seed_mode", "dynamic"))
        self._save_index()
        return deepcopy(metadata)

    def update_playback_settings(
        self,
        item_id: str,
        playback_settings: dict[str, Any],
        clear_cache: bool = False,
    ) -> None:
        data = self.get_song_data(item_id)
        data["playback_settings"] = self._stored_settings(playback_settings)
        if clear_cache:
            self._cache_path(item_id).unlink(missing_ok=True)
            data["cache_available"] = False
        self._atomic_write_json(self._item_path(item_id), data)
        metadata = next((x for x in self._items if x.get("id") == item_id), None)
        if metadata is not None:
            metadata["humanization_mode"] = str(playback_settings.get("humanization_mode", "individual"))
            metadata["random_seed_mode"] = str(playback_settings.get("humanization_seed_mode", "dynamic"))
            metadata["modified_at"] = datetime.now().isoformat()
            self._save_index()

    def cache_playback(self, item_id: str, playback_data: dict[str, Any]) -> None:
        self._validate_playback_data(playback_data)
        self._atomic_write_json(self._cache_path(item_id), playback_data)
        data = self.get_song_data(item_id)
        data["cache_available"] = True
        self._atomic_write_json(self._item_path(item_id), data)
        metadata = next((x for x in self._items if x.get("id") == item_id), None)
        if metadata is not None:
            metadata["duration"] = self._playback_duration(playback_data)
            metadata["modified_at"] = datetime.now().isoformat()
            self._save_index()

    # Compatibility entry point used by older integrations/tests.
    def add_playback(self, playback_data: dict[str, Any], name: str | None = None) -> dict[str, Any]:
        self._validate_playback_data(playback_data)
        metadata = playback_data.get("metadata", {})
        settings = deepcopy(metadata.get("playback_settings", {}))
        midi_path = str(settings.get("midi_file") or "")
        if midi_path and Path(midi_path).exists():
            return self.add_song(midi_path, settings, [], playback_data, name=name)

        item_id = uuid.uuid4().hex
        source = str(metadata.get("source_midi_filename") or "Unknown MIDI")
        now = datetime.now().isoformat()
        song_data = {
            "song_version": 3,
            "source": {"type": "midi", "original_path": "", "original_filename": source, "local_midi_filename": ""},
            "playback_settings": self._stored_settings(settings),
            "selected_tracks": [],
            "cache_available": True,
            "legacy_cache_only": True,
        }
        self._atomic_write_json(self._item_path(item_id), song_data)
        self._atomic_write_json(self._cache_path(item_id), playback_data)
        item = {
            "id": item_id,
            "name": (name or Path(source).stem or source).strip(),
            "source_midi_filename": source,
            "source_type": "midi",
            "source_label": source,
            "created_at": now,
            "modified_at": now,
            "duration": self._playback_duration(playback_data),
            "humanization_mode": str(settings.get("humanization_mode", "individual")),
            "random_seed_mode": str(settings.get("humanization_seed_mode", "fixed_random")),
        }
        self._items.append(item)
        self._save_index()
        return deepcopy(item)

    def delete(self, item_id: str) -> bool:
        before = len(self._items)
        self._items = [x for x in self._items if x.get("id") != item_id]
        if len(self._items) == before:
            return False
        try:
            data = None
            try:
                data = self.get_song_data(item_id)
            except Exception:
                pass
            if data:
                local_name = os.path.basename(str(data.get("source", {}).get("local_midi_filename") or ""))
                if local_name:
                    (self.midi_dir / local_name).unlink(missing_ok=True)
            self._item_path(item_id).unlink(missing_ok=True)
            self._cache_path(item_id).unlink(missing_ok=True)
        finally:
            self._save_index()
        return True

    def clear(self) -> None:
        for item in list(self._items):
            self.delete(str(item.get("id")))
        self._items = []
        self._save_index()

    def delete_many(self, item_ids: list[str]) -> int:
        removed = 0
        for item_id in list(dict.fromkeys(str(value) for value in item_ids)):
            if self.delete(item_id):
                removed += 1
        return removed

    def reorder(self, ordered_ids: list[str]) -> None:
        """Persist a complete, validated user-defined playlist order.

        A reorder request must contain every current item exactly once.  Refuse
        partial or malformed orders rather than silently appending omitted songs
        to the bottom, which could hide a UI drag/drop data-loss bug.
        """
        requested = [str(value) for value in ordered_ids]
        current_ids = [str(item.get("id")) for item in self._items]
        if (
            len(requested) != len(current_ids)
            or len(set(requested)) != len(requested)
            or set(requested) != set(current_ids)
        ):
            raise ValueError("The playlist reorder request is incomplete or invalid.")

        by_id = {str(item.get("id")): item for item in self._items}
        reordered = [by_id[item_id] for item_id in requested]
        if requested != current_ids:
            self._items = reordered
            self._save_index()

    def save_midi_as(self, item_id: str, destination: str) -> None:
        midi_path = self.get_midi_path(item_id)
        if not midi_path:
            raise FileNotFoundError("The original MIDI file is not available for this song.")
        dest = Path(destination)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(midi_path, dest)

    # ------------------------------------------------------------------
    # Import/export

    def export_playlist(self, destination: str, complete: bool = False, progress_callback=None) -> int:
        return (
            self._export_complete(destination, progress_callback)
            if complete else
            self._export_normal(destination, progress_callback)
        )

    def _export_normal(self, destination: str, progress_callback=None) -> int:
        entries = []
        total = max(1, len(self._items))
        for index, item in enumerate(self._items, start=1):
            if progress_callback:
                progress_callback(index - 1, total, str(item.get("name") or ""))
            try:
                song = self.get_song_data(str(item.get("id")))
            except Exception:
                continue
            source = deepcopy(song.get("source", {}))
            source_type = "sheet" if str(source.get("type") or "midi") == "sheet" else "midi"
            if source_type == "midi":
                source.pop("local_midi_filename", None)
                # Normal MIDI exports are path-based. Text sheets are already
                # self-contained and keep their source text in the manifest.
                available_midi = self.get_midi_path(str(item.get("id")))
                if available_midi:
                    source["original_path"] = available_midi
            entries.append({
                "metadata": deepcopy(item),
                "song": {
                    "song_version": 3,
                    "source": source,
                    "playback_settings": deepcopy(song.get("playback_settings", {})),
                    "selected_tracks": deepcopy(song.get("selected_tracks", [])),
                },
            })
        payload = {
            "format": self.FORMAT,
            "version": self.VERSION,
            "export_type": "normal",
            "exported_at": datetime.now().isoformat(),
            "entries": entries,
        }
        self._atomic_write_json(Path(destination), payload)
        if progress_callback:
            progress_callback(total, total, "")
        return len(entries)

    def _export_complete(self, destination: str, progress_callback=None) -> int:
        entries = []
        temp_path = Path(destination).with_name(f".{Path(destination).name}.{uuid.uuid4().hex}.tmp")
        try:
            with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                total = max(1, len(self._items))
                for index, item in enumerate(self._items, start=1):
                    if progress_callback:
                        progress_callback(index - 1, total, str(item.get("name") or ""))
                    item_id = str(item.get("id"))
                    try:
                        song = self.get_song_data(item_id)
                    except Exception:
                        continue
                    exported_song = deepcopy(song)
                    # A complete package carries its own MIDI copy, so absolute
                    # source paths (often containing a Windows user name) are
                    # unnecessary and should not leak when the file is shared.
                    exported_source = exported_song.get("source", {})
                    source_type = "sheet" if isinstance(exported_source, dict) and str(exported_source.get("type") or "midi") == "sheet" else "midi"
                    if isinstance(exported_source, dict) and source_type == "midi":
                        exported_source["original_path"] = ""
                        exported_source["local_midi_filename"] = ""
                    entry = {
                        "metadata": deepcopy(item),
                        "song": exported_song,
                        "midi_member": "",
                        "cache_member": "",
                    }
                    midi_path = self.get_midi_path(item_id) if source_type == "midi" else None
                    if midi_path:
                        suffix = Path(midi_path).suffix.lower() or ".mid"
                        member = f"songs/{item_id}{suffix}"
                        archive.write(midi_path, member)
                        entry["midi_member"] = member
                    cache_path = self._cache_path(item_id)
                    if cache_path.exists():
                        member = f"cache/{item_id}.json"
                        cache_data = self.get_playback_data(item_id)
                        cache_settings = cache_data.get("metadata", {}).get("playback_settings", {})
                        if isinstance(cache_settings, dict):
                            cache_settings.pop("midi_file", None)
                        archive.writestr(
                            member,
                            json.dumps(cache_data, ensure_ascii=False, separators=(",", ":")),
                        )
                        entry["cache_member"] = member
                    entries.append(entry)
                manifest = {
                    "format": self.FORMAT,
                    "version": self.VERSION,
                    "export_type": "complete",
                    "exported_at": datetime.now().isoformat(),
                    "entries": entries,
                }
                archive.writestr("playlist.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            os.replace(temp_path, destination)
            if progress_callback:
                progress_callback(max(1, len(self._items)), max(1, len(self._items)), "")
        finally:
            temp_path.unlink(missing_ok=True)
        return len(entries)

    def import_playlist(self, source: str) -> int:
        return self._import_complete(source) if zipfile.is_zipfile(source) else self._import_json(source)

    def _import_json(self, source: str) -> int:
        payload = json.loads(Path(source).read_text(encoding="utf-8"))
        self._validate_manifest(payload)
        entries = payload.get("entries", [])
        imported = 0
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            # v1 export: metadata + playback_data only.
            if isinstance(entry.get("playback_data"), dict):
                try:
                    self.add_playback(entry["playback_data"], str(entry.get("metadata", {}).get("name") or "") or None)
                    imported += 1
                except Exception:
                    continue
                continue
            song = entry.get("song")
            if not isinstance(song, dict):
                continue
            try:
                self._import_song_entry(entry, song, midi_bytes=None, cache_data=None)
                imported += 1
            except Exception:
                continue
        return imported

    def _import_complete(self, source: str) -> int:
        imported = 0
        with zipfile.ZipFile(source, "r") as archive:
            try:
                payload = json.loads(archive.read("playlist.json").decode("utf-8"))
            except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise PlaylistFormatError("Playlist package manifest is missing or invalid.") from exc
            self._validate_manifest(payload)
            for entry in payload.get("entries", []):
                if not isinstance(entry, dict) or not isinstance(entry.get("song"), dict):
                    continue
                midi_bytes = None
                cache_data = None
                midi_member = str(entry.get("midi_member") or "")
                cache_member = str(entry.get("cache_member") or "")
                try:
                    if midi_member:
                        midi_bytes = archive.read(midi_member)
                    if cache_member:
                        cache_data = json.loads(archive.read(cache_member).decode("utf-8"))
                    self._import_song_entry(entry, entry["song"], midi_bytes, cache_data)
                    imported += 1
                except Exception:
                    continue
        return imported

    def _import_song_entry(
        self,
        entry: dict[str, Any],
        song: dict[str, Any],
        midi_bytes: bytes | None,
        cache_data: dict[str, Any] | None,
    ) -> None:
        item_id = uuid.uuid4().hex
        metadata_in = entry.get("metadata", {}) if isinstance(entry.get("metadata"), dict) else {}
        source = deepcopy(song.get("source", {})) if isinstance(song.get("source"), dict) else {}
        source_type = "sheet" if str(source.get("type") or metadata_in.get("source_type") or "midi") == "sheet" else "midi"
        local_name = ""

        if source_type == "sheet":
            sheet_text = str(source.get("sheet_text") or "").strip()
            format_name = str(source.get("format_name") or "").strip()
            if not sheet_text or not format_name:
                raise PlaylistFormatError("The text sheet for this playlist song is unavailable.")
            stored_source = {
                "type": "sheet",
                "sheet_text": sheet_text,
                "format_name": format_name,
                "bpm": max(20, min(400, int(source.get("bpm", 120) or 120))),
                "humanize": bool(source.get("humanize", False)),
            }
            original_name = ""
        else:
            original_name = str(source.get("original_filename") or metadata_in.get("source_midi_filename") or "Imported.mid")
            if midi_bytes is not None:
                suffix = Path(original_name).suffix.lower()
                if suffix not in {".mid", ".midi"}:
                    suffix = ".mid"
                local_name = f"{item_id}{suffix}"
                (self.midi_dir / local_name).write_bytes(midi_bytes)
            else:
                original_path = str(source.get("original_path") or "")
                if original_path and Path(original_path).exists():
                    local_name = self._copy_midi_for_item(item_id, Path(original_path))
            stored_source = {
                "type": "midi",
                "original_path": str(source.get("original_path") or ""),
                "original_filename": original_name,
                "local_midi_filename": local_name,
            }

        if cache_data is not None:
            self._validate_playback_data(cache_data)
            self._atomic_write_json(self._cache_path(item_id), cache_data)

        stored_song = {
            "song_version": 3,
            "source": stored_source,
            "playback_settings": self._stored_settings(song.get("playback_settings", {})),
            "selected_tracks": deepcopy(song.get("selected_tracks", [])) if source_type == "midi" else [],
            "cache_available": cache_data is not None,
            "legacy_cache_only": bool(song.get("legacy_cache_only", False) and not local_name and source_type == "midi"),
        }
        self._atomic_write_json(self._item_path(item_id), stored_song)
        now = datetime.now().isoformat()
        settings = stored_song["playback_settings"]
        fallback_name = "Text Sheet" if source_type == "sheet" else (Path(original_name).stem or "Imported")
        source_label = str(stored_source.get("format_name") or original_name or fallback_name)
        item = {
            "id": item_id,
            "name": str(metadata_in.get("name") or fallback_name),
            "source_midi_filename": original_name,
            "source_type": source_type,
            "source_label": source_label,
            "created_at": now,
            "modified_at": now,
            "duration": self._playback_duration(cache_data) or float(metadata_in.get("duration", 0.0) or 0.0),
            "humanization_mode": str(settings.get("humanization_mode", "disabled" if source_type == "sheet" else "individual")),
            "random_seed_mode": str(settings.get("humanization_seed_mode", "dynamic")),
        }
        self._items.append(item)
        self._save_index()

    def _validate_manifest(self, payload: Any) -> None:
        if not isinstance(payload, dict) or payload.get("format") != self.FORMAT:
            raise PlaylistFormatError("Unsupported playlist format.")
        if int(payload.get("version", 0)) > self.VERSION:
            raise PlaylistFormatError("This playlist was created by a newer HuMidi version.")
        if not isinstance(payload.get("entries"), list):
            raise PlaylistFormatError("Playlist entries are missing or invalid.")

    # ------------------------------------------------------------------
    # Helpers

    def _save_index(self) -> None:
        payload = {"format": self.FORMAT, "version": self.VERSION, "items": self._items}
        self._atomic_write_json(self.index_path, payload)

    def _remove_missing_entries(self) -> None:
        filtered = [item for item in self._items if self._item_path(str(item.get("id"))).exists()]
        if len(filtered) != len(self._items):
            self._items = filtered
            self._save_index()

    def _item_path(self, item_id: str) -> Path:
        return self.items_dir / f"{os.path.basename(item_id)}.json"

    def _cache_path(self, item_id: str) -> Path:
        return self.cache_dir / f"{os.path.basename(item_id)}.json"

    def _copy_midi_for_item(self, item_id: str, source: Path) -> str:
        suffix = source.suffix.lower()
        if suffix not in {".mid", ".midi"}:
            suffix = ".mid"
        local_name = f"{item_id}{suffix}"
        shutil.copy2(source, self.midi_dir / local_name)
        return local_name

    @staticmethod
    def _stored_settings(settings: Any) -> dict[str, Any]:
        stored = deepcopy(settings) if isinstance(settings, dict) else {}
        stored.pop("midi_file", None)
        return stored

    @staticmethod
    def _normalize_metadata(item: dict[str, Any]) -> dict[str, Any]:
        source_type = "sheet" if str(item.get("source_type") or "midi") == "sheet" else "midi"
        source_midi = str(item.get("source_midi_filename", "" if source_type == "sheet" else "Unknown MIDI"))
        return {
            "id": str(item.get("id", "")),
            "name": str(item.get("name", "Unnamed")),
            "source_midi_filename": source_midi,
            "source_type": source_type,
            "source_label": str(item.get("source_label") or source_midi or ("Text Sheet" if source_type == "sheet" else "Unknown MIDI")),
            "created_at": str(item.get("created_at", "")),
            "modified_at": str(item.get("modified_at", item.get("created_at", ""))),
            "duration": float(item.get("duration", 0.0) or 0.0),
            "humanization_mode": str(item.get("humanization_mode", "disabled" if source_type == "sheet" else "individual")),
            "random_seed_mode": str(item.get("random_seed_mode", "fixed_random")),
        }

    @staticmethod
    def _playback_duration(playback_data: dict[str, Any] | None) -> float:
        if not playback_data:
            return 0.0
        visualizer = playback_data.get("visualizer_data", {})
        if isinstance(visualizer, dict) and visualizer.get("total_duration") is not None:
            try:
                return float(visualizer["total_duration"])
            except (TypeError, ValueError):
                pass
        events = playback_data.get("compiled_events", [])
        return max((float(ev.get("time", 0.0)) for ev in events if isinstance(ev, dict)), default=0.0)

    @staticmethod
    def _validate_playback_data(data: Any) -> None:
        if not isinstance(data, dict):
            raise PlaylistFormatError("Playback data is not an object.")
        if not isinstance(data.get("metadata"), dict):
            raise PlaylistFormatError("Playback metadata is missing.")
        events = data.get("compiled_events")
        if not isinstance(events, list) or not events:
            raise PlaylistFormatError("Compiled playback events are missing.")
        for event in events:
            if not isinstance(event, dict) or not {"time", "priority", "action", "key_char"}.issubset(event):
                raise PlaylistFormatError("A compiled event is invalid.")

    @staticmethod
    def _atomic_write_json(path: Path, payload: Any) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
