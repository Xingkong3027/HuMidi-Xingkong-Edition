import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from managers.PlaylistManager import PlaylistFormatError, PlaylistManager


def playback(name: str, offset: float = 0.0, seed=12345):
    return {
        "metadata": {
            "source_midi_filename": name,
            "playback_settings": {
                "tempo": 100,
                "pedal_style": "hybrid",
                "humanization_mode": "individual",
                "humanization_seed_mode": "fixed_random",
                "humanization_seed": seed,
            },
        },
        "compiled_events": [
            {"time": offset, "priority": 2, "action": "press", "key_char": "a", "pitch": 60},
            {"time": offset + 1.25, "priority": 4, "action": "release", "key_char": "a", "pitch": 60},
        ],
        "visualizer_data": {
            "notes": [
                {
                    "id": 1,
                    "pitch": 60,
                    "velocity": 90,
                    "start_time": offset,
                    "duration": 1.25,
                    "hand": "right",
                    "original_track_index": 0,
                    "channel": 0,
                }
            ],
            "total_duration": offset + 1.25,
            "tempo_events": [[0.0, 500000]],
            "time_signatures": [[0.0, 4, 4]],
        },
    }


class FakeTrack:
    def __init__(self, index):
        self.index = index


class PlaylistManagerTests(unittest.TestCase):
    def test_text_sheet_add_update_and_export_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manager = PlaylistManager(root / "library")
            settings = {
                "humanization_mode": "global",
                "humanization_seed_mode": "dynamic",
                "use_88_key_layout": False,
            }
            item = manager.add_sheet(
                "e e [ty]--", "Virtual Piano", 132, settings,
                name="中文文本乐谱", duration_hint=2.5,
            )
            item_id = item["id"]
            metadata = manager.get_metadata(item_id)
            self.assertEqual(metadata["source_type"], "sheet")
            self.assertTrue(metadata["sheet_available"])
            self.assertFalse(metadata["midi_available"])
            self.assertIsNone(manager.get_midi_path(item_id))
            source = manager.get_sheet_source(item_id)
            self.assertEqual(source["sheet_text"], "e e [ty]--")
            self.assertEqual(source["format_name"], "Virtual Piano")
            self.assertEqual(source["bpm"], 132)
            with self.assertRaises(FileNotFoundError):
                manager.save_midi_as(item_id, str(root / "not-midi.mid"))

            manager.update_sheet(
                item_id, "q w e r", "Virtual Piano", 144,
                {**settings, "humanization_mode": "disabled"},
                name="修改后的乐谱", duration_hint=3.0,
            )
            self.assertEqual(manager.get_metadata(item_id)["name"], "修改后的乐谱")
            self.assertEqual(manager.get_sheet_source(item_id)["bpm"], 144)

            normal = root / "sheet-normal.humidiplaylist"
            self.assertEqual(manager.export_playlist(str(normal), complete=False), 1)
            payload = json.loads(normal.read_text(encoding="utf-8"))
            exported_source = payload["entries"][0]["song"]["source"]
            self.assertEqual(exported_source["type"], "sheet")
            self.assertEqual(exported_source["sheet_text"], "q w e r")
            normal_import = PlaylistManager(root / "normal-import")
            self.assertEqual(normal_import.import_playlist(str(normal)), 1)
            imported_id = normal_import.items()[0]["id"]
            self.assertEqual(normal_import.get_sheet_source(imported_id)["bpm"], 144)

            complete = root / "sheet-complete.humidiplaylist"
            self.assertEqual(manager.export_playlist(str(complete), complete=True), 1)
            with zipfile.ZipFile(complete, "r") as archive:
                manifest = json.loads(archive.read("playlist.json").decode("utf-8"))
                entry = manifest["entries"][0]
                self.assertEqual(entry["midi_member"], "")
                self.assertEqual(entry["song"]["source"]["sheet_text"], "q w e r")
            complete_import = PlaylistManager(root / "complete-import")
            self.assertEqual(complete_import.import_playlist(str(complete)), 1)
            complete_id = complete_import.items()[0]["id"]
            self.assertEqual(complete_import.get_source_type(complete_id), "sheet")
            self.assertEqual(complete_import.get_sheet_source(complete_id)["sheet_text"], "q w e r")

    def test_add_update_normal_and_complete_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            midi = root / "测试歌曲.mid"
            midi.write_bytes(b"MThd-test-midi")
            manager = PlaylistManager(root / "library")
            settings = {
                "midi_file": str(midi),
                "tempo": 100,
                "humanization_mode": "individual",
                "humanization_seed_mode": "fixed_random",
                "humanization_seed": 12345,
            }
            first = manager.add_song(
                str(midi), settings, [(FakeTrack(0), "Right Hand")], playback("测试歌曲.mid"),
                "测试歌曲", duration_hint=9.5,
            )
            self.assertEqual(len(manager.items()), 1)
            self.assertTrue(Path(manager.get_midi_path(first["id"])).exists())
            self.assertEqual(manager.get_song_data(first["id"])["selected_tracks"][0]["index"], 0)
            self.assertEqual(manager.get_playback_data(first["id"])["metadata"]["source_midi_filename"], "测试歌曲.mid")

            normal = root / "普通歌单.humidiplaylist"
            self.assertEqual(manager.export_playlist(str(normal), complete=False), 1)
            normal_payload = json.loads(normal.read_text(encoding="utf-8"))
            self.assertEqual(normal_payload["export_type"], "normal")
            self.assertNotIn("playback_data", normal_payload["entries"][0])

            normal_import = PlaylistManager(root / "normal-import")
            self.assertEqual(normal_import.import_playlist(str(normal)), 1)
            normal_id = normal_import.items()[0]["id"]
            self.assertTrue(Path(normal_import.get_midi_path(normal_id)).exists())
            with self.assertRaises(FileNotFoundError):
                normal_import.get_playback_data(normal_id)

            complete = root / "完整歌单.humidiplaylist"
            self.assertEqual(manager.export_playlist(str(complete), complete=True), 1)
            self.assertTrue(zipfile.is_zipfile(complete))
            with zipfile.ZipFile(complete, "r") as archive:
                manifest = json.loads(archive.read("playlist.json").decode("utf-8"))
                exported_source = manifest["entries"][0]["song"]["source"]
                self.assertEqual(exported_source["original_path"], "")
                self.assertEqual(exported_source["local_midi_filename"], "")
                self.assertTrue(manifest["entries"][0]["midi_member"].startswith("songs/"))
                cache_member = manifest["entries"][0]["cache_member"]
                packaged_cache = json.loads(archive.read(cache_member).decode("utf-8"))
                self.assertNotIn("midi_file", packaged_cache["metadata"]["playback_settings"])
            complete_import = PlaylistManager(root / "complete-import")
            self.assertEqual(complete_import.import_playlist(str(complete)), 1)
            imported_id = complete_import.items()[0]["id"]
            self.assertTrue(Path(complete_import.get_midi_path(imported_id)).exists())
            imported_cache = complete_import.get_playback_data(imported_id)
            self.assertEqual(imported_cache["visualizer_data"]["time_signatures"], [[0.0, 4, 4]])

            new_settings = dict(settings)
            new_settings["humanization_seed_mode"] = "dynamic"
            local_midi = manager.get_midi_path(first["id"])
            original_before = manager.get_song_data(first["id"])["source"]
            manager.update_song(
                first["id"], local_midi, new_settings, [(FakeTrack(0), "Left Hand")], None,
                duration_hint=8.75,
            )
            with self.assertRaises(FileNotFoundError):
                manager.get_playback_data(first["id"])
            updated_song = manager.get_song_data(first["id"])
            self.assertEqual(updated_song["selected_tracks"][0]["role"], "Left Hand")
            self.assertEqual(updated_song["source"]["original_path"], original_before["original_path"])
            self.assertEqual(updated_song["source"]["original_filename"], "测试歌曲.mid")
            self.assertEqual(manager.get_metadata(first["id"])["duration"], 8.75)

            saved = root / "saved.mid"
            manager.save_midi_as(first["id"], str(saved))
            self.assertEqual(saved.read_bytes(), midi.read_bytes())
            self.assertTrue(manager.delete(first["id"]))
            self.assertEqual(manager.items(), [])

    def test_legacy_playback_add_and_complete_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manager = PlaylistManager(root)
            item = manager.add_playback(playback("Legacy.mid"), "Legacy")
            self.assertEqual(manager.get_metadata(item["id"])["name"], "Legacy")
            self.assertTrue(manager.get_song_data(item["id"])["legacy_cache_only"])
            export_path = root / "legacy.humidiplaylist"
            manager.export_playlist(str(export_path), complete=True)
            imported = PlaylistManager(root / "imported")
            self.assertEqual(imported.import_playlist(str(export_path)), 1)
            self.assertEqual(len(imported.get_playback_data(imported.items()[0]["id"])["compiled_events"]), 2)

    def test_rejects_future_and_invalid_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manager = PlaylistManager(root)
            future = root / "future.json"
            future.write_text(json.dumps({
                "format": manager.FORMAT,
                "version": manager.VERSION + 1,
                "entries": [],
            }), encoding="utf-8")
            with self.assertRaises(PlaylistFormatError):
                manager.import_playlist(str(future))

            invalid = root / "invalid.json"
            invalid.write_text(json.dumps({"format": "Other", "version": 1, "entries": []}), encoding="utf-8")
            with self.assertRaises(PlaylistFormatError):
                manager.import_playlist(str(invalid))

    def test_corrupt_index_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            playlist_root = root / "playlist"
            playlist_root.mkdir(parents=True)
            (playlist_root / "index.json").write_text("{broken", encoding="utf-8")
            manager = PlaylistManager(root)
            self.assertEqual(manager.items(), [])
            backups = list(playlist_root.glob("index.corrupt-*.json"))
            self.assertEqual(len(backups), 1)

    def test_reorder_delete_many_and_export_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manager = PlaylistManager(root / "library")
            created = []
            for index in range(3):
                midi = root / f"song-{index}.mid"
                midi.write_bytes(b"MThd-test-midi" + bytes([index]))
                created.append(manager.add_song(
                    str(midi),
                    {"midi_file": str(midi), "humanization_mode": "disabled"},
                    [(FakeTrack(0), "Auto-Detect")],
                    playback(midi.name),
                ))
            ids = [item["id"] for item in created]
            manager.reorder([ids[2], ids[0], ids[1]])
            expected_order = [ids[2], ids[0], ids[1]]
            self.assertEqual([item["id"] for item in manager.items()], expected_order)

            # A malformed UI order must never make an omitted song silently
            # jump to the bottom of the playlist.
            with self.assertRaises(ValueError):
                manager.reorder([ids[2], ""])
            self.assertEqual([item["id"] for item in manager.items()], expected_order)

            progress = []
            destination = root / "progress.humidiplaylist"
            manager.export_playlist(
                str(destination), complete=False,
                progress_callback=lambda current, total, name: progress.append((current, total, name)),
            )
            self.assertTrue(destination.exists())
            self.assertEqual(progress[-1][:2], (3, 3))
            self.assertEqual(manager.delete_many([ids[0], ids[2], ids[0]]), 2)
            self.assertEqual([item["id"] for item in manager.items()], [ids[1]])

    def test_normal_export_uses_retained_midi_when_original_was_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            midi = root / "temporary-source.mid"
            midi.write_bytes(b"MThd-retained-midi")
            manager = PlaylistManager(root / "library")
            item = manager.add_song(
                str(midi),
                {"midi_file": str(midi), "humanization_mode": "disabled"},
                [(FakeTrack(0), "Auto-Detect")],
                playback(midi.name),
            )
            retained = Path(manager.get_midi_path(item["id"]))
            self.assertTrue(retained.exists())
            midi.unlink()
            export_path = root / "normal-after-move.humidiplaylist"
            manager.export_playlist(str(export_path), complete=False)
            payload = json.loads(export_path.read_text(encoding="utf-8"))
            exported_path = Path(payload["entries"][0]["song"]["source"]["original_path"])
            self.assertEqual(exported_path, retained)
            imported = PlaylistManager(root / "imported")
            self.assertEqual(imported.import_playlist(str(export_path)), 1)
            self.assertTrue(Path(imported.get_midi_path(imported.items()[0]["id"])).exists())


if __name__ == "__main__":
    unittest.main()
