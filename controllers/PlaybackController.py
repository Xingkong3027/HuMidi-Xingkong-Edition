import copy
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal as Signal

from core.models import Note, KeyEvent
from core.core import MidiParser, TempoMap
from core.section_analyzer import SectionAnalyzer, assign_hands
from core.player import Player
from core.trimming import apply_trim


SERIALIZATION_VERSION = 2


def _serialize_event(ev: KeyEvent) -> Dict[str, Any]:
    return {
        'time': float(ev.time),
        'priority': int(ev.priority),
        'action': str(ev.action),
        'key_char': str(ev.key_char),
        'pitch': int(ev.pitch) if ev.pitch is not None else None,
    }


def _serialize_note(note: Note) -> Dict[str, Any]:
    return {
        'id': int(note.id),
        'pitch': int(note.pitch),
        'velocity': int(note.velocity),
        'start_time': float(note.start_time),
        'duration': float(note.duration),
        'hand': str(note.hand),
        'original_track_index': int(note.original_track_index),
        'channel': int(note.channel),
    }


def _deserialize_note(raw: Dict[str, Any], fallback_id: int = 0) -> Note:
    return Note(
        id=int(raw.get('id', fallback_id)),
        pitch=int(raw['pitch']),
        velocity=int(raw.get('velocity', 64)),
        start_time=float(raw['start_time']),
        duration=max(0.01, float(raw['duration'])),
        hand=str(raw.get('hand', 'unknown')),
        original_track_index=int(raw.get('original_track_index', -1)),
        channel=int(raw.get('channel', -1)),
    )


def _serialize_tempo_map(tempo_map: TempoMap) -> Dict[str, Any]:
    return {
        'tempo_events': [[float(t), int(tempo)] for t, tempo in tempo_map.events],
        'time_signatures': [
            [float(t), int(numerator), int(denominator)]
            for t, numerator, denominator in tempo_map.time_signatures
        ],
    }


def _deserialize_tempo_map(raw: Any) -> TempoMap:
    if not isinstance(raw, dict):
        return TempoMap([(0.0, 500000)], [])
    try:
        tempo_events = [
            (float(item[0]), int(item[1]))
            for item in raw.get('tempo_events', [])
            if isinstance(item, (list, tuple)) and len(item) >= 2
        ]
        signatures = [
            (float(item[0]), int(item[1]), int(item[2]))
            for item in raw.get('time_signatures', [])
            if isinstance(item, (list, tuple)) and len(item) >= 3
        ]
        return TempoMap(tempo_events or [(0.0, 500000)], signatures)
    except (TypeError, ValueError):
        return TempoMap([(0.0, 500000)], [])


def _compilation_signature(config: Dict, selected_tracks_info: List) -> str:
    """Stable identity for determining whether a preview can be reused.

    The signature includes every playback setting and the selected track roles.
    If the user changes even one parameter after previewing, the playlist/save
    path compiles again instead of incorrectly reusing stale events.
    """
    normalized_tracks = sorted(
        (int(track.index), str(role)) for track, role in selected_tracks_info
    )
    midi_path = Path(str(config.get('midi_file') or ''))
    try:
        stat = midi_path.stat()
        midi_identity = {
            'path': str(midi_path.resolve()),
            'size': int(stat.st_size),
            'mtime_ns': int(stat.st_mtime_ns),
        }
    except OSError:
        midi_identity = {'path': str(midi_path)}

    signature_config = copy.deepcopy(config)
    # Startup-only options do not alter compiled notes/events and therefore
    # should not invalidate the preview cache.
    for key in ('countdown', 'countdown_seconds', 'performance_optimization', 'debug_mode'):
        signature_config.pop(key, None)

    payload = {
        'config': signature_config,
        'tracks': normalized_tracks,
        'midi_identity': midi_identity,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)



def cache_matches_config(playback_data: Dict[str, Any], config: Dict[str, Any]) -> bool:
    """Return whether a compiled cache was produced from the same effective settings."""
    if not isinstance(playback_data, dict):
        return False
    stored = copy.deepcopy(playback_data.get('metadata', {}).get('playback_settings', {}))
    if not isinstance(stored, dict):
        return False
    current = copy.deepcopy(config)
    current.pop('midi_file', None)
    # These options affect startup/logging only, not the compiled event sequence.
    for key in ('countdown', 'countdown_seconds', 'performance_optimization', 'debug_mode'):
        stored.pop(key, None)
        current.pop(key, None)
    return json.dumps(stored, sort_keys=True, default=str) == json.dumps(current, sort_keys=True, default=str)

def _build_save_data_from_bundle(
    config: Dict,
    original_filename: str,
    bundle: Dict[str, Any],
) -> Dict[str, Any]:
    events = list(bundle.get('compiled_events') or [])
    notes = list(bundle.get('visualization_notes') or [])
    tempo_map = bundle.get('tempo_map')
    if not events:
        raise ValueError(
            "Compilation produced zero events — nothing to save.\n"
            "Verify that the selected tracks contain notes within the keyboard's playable range."
        )
    if not isinstance(tempo_map, TempoMap):
        tempo_map = TempoMap([(0.0, 500000)], [])

    stored_config = copy.deepcopy(config)
    # Compiled playback is self-contained; retaining the absolute MIDI path is
    # unnecessary and may expose a Windows user name when a playlist is shared.
    stored_config.pop('midi_file', None)
    metadata = {
        'serialization_version': SERIALIZATION_VERSION,
        'creation_timestamp': datetime.now().isoformat(),
        'source_midi_filename': original_filename,
        'playback_settings': stored_config,
    }
    total_duration = float(
        bundle.get('total_duration')
        or max((float(ev.time) for ev in events), default=0.0)
    )
    return {
        'metadata': metadata,
        'compiled_events': [_serialize_event(ev) for ev in events],
        'visualizer_data': {
            'notes': [_serialize_note(note) for note in notes],
            'total_duration': total_duration,
            **_serialize_tempo_map(tempo_map),
        },
    }


def _copy_serialized_playback(data: Dict[str, Any]) -> Dict[str, Any]:
    copied = copy.deepcopy(data)
    copied.setdefault('metadata', {})['creation_timestamp'] = datetime.now().isoformat()
    return copied


def _extract_pedal_intervals(pedal_events) -> list:
    """Convert a flat list of pedal KeyEvents into (start_sec, end_sec) interval tuples."""
    intervals = []
    down_time = None
    for ev in pedal_events:
        if ev.action != 'pedal':
            continue
        if ev.key_char == 'down':
            down_time = ev.time
        elif ev.key_char == 'up' and down_time is not None:
            intervals.append((down_time, ev.time))
            down_time = None
    return intervals


def _prepare_notes(config: Dict, selected_tracks_info: List, log=None):
    """Parse MIDI, apply track role assignments, and run hand simulation.

    Shared by PlaybackController.play() and _SaveWorker.run() to eliminate the
    duplicated note-preparation pipeline that previously existed in both places.

    Returns (final_notes, tempo_map). Raises on MIDI parse failure — callers
    should catch and surface the exception appropriately.
    """
    tempo_scale = config.get('tempo', 100.0) / 100.0
    tracks, tempo_map = MidiParser.parse_structure(
        config['midi_file'],
        tempo_scale,
        None,
        clip_invalid_data=bool(config.get('midi_clip_invalid_data', False)),
    )
    selected_indices = [t.index for t, _ in selected_tracks_info]
    role_map = {t.index: r for t, r in selected_tracks_info}
    final_notes = []

    for track in tracks:
        if track.index in selected_indices:
            role = role_map[track.index]
            if log:
                log(f"Track {track.index} ({track.name}): {len(track.notes)} Notes | Role: {role}")
            for note in track.notes:
                new_note = copy.deepcopy(note)
                if role == "Left Hand": new_note.hand = 'left'
                elif role == "Right Hand": new_note.hand = 'right'
                final_notes.append(new_note)

    final_notes.sort(key=lambda n: n.start_time)
    final_notes, tempo_map, _trim_start, _trim_end = apply_trim(
        final_notes, tempo_map, config
    )

    if config.get('simulate_hands'):
        if log: log("Simulating hands for unassigned notes...")
        assign_hands(final_notes)
    else:
        for note in final_notes:
            if note.hand == 'unknown':
                note.hand = 'left' if note.pitch < 60 else 'right'

    return final_notes, tempo_map


def _build_save_data(config: Dict, selected_tracks_info: List, original_filename: str, status=None) -> Dict:
    if status:
        status("Compiling data for serialization...")
    final_notes, tempo_map = _prepare_notes(config, selected_tracks_info)
    analyzer = SectionAnalyzer(final_notes, tempo_map)
    sections = analyzer.analyze()
    compiler_player = Player(config, final_notes, sections, tempo_map)
    if status:
        compiler_player.status_updated.connect(status)
    bundle = compiler_player.export_compiled_bundle()
    return _build_save_data_from_bundle(config, original_filename, bundle)


class _CompileWorker(QObject):
    status_updated = Signal(str)
    compile_successful = Signal(object)
    compile_failed = Signal(str)
    finished = Signal()

    def __init__(self, config: Dict, selected_tracks_info: List, original_filename: str):
        super().__init__()
        self.config = config
        self.selected_tracks_info = selected_tracks_info
        self.original_filename = original_filename

    def run(self):
        try:
            data = _build_save_data(
                self.config, self.selected_tracks_info, self.original_filename,
                status=self.status_updated.emit,
            )
            self.compile_successful.emit(data)
        except Exception as exc:
            self.compile_failed.emit(str(exc))
        finally:
            self.finished.emit()


class _SaveWorker(QObject):
    status_updated = Signal(str)
    save_successful = Signal(str, str)
    save_failed = Signal(str)
    finished = Signal()

    def __init__(
        self,
        config: Dict,
        selected_tracks_info: List,
        save_dir: str,
        original_filename: str,
        precompiled_data: Dict | None = None,
    ):
        super().__init__()
        self.config = config
        self.selected_tracks_info = selected_tracks_info
        self.save_dir = save_dir
        self.original_filename = original_filename
        self.precompiled_data = precompiled_data

    def run(self):
        try:
            if self.precompiled_data is not None:
                self.status_updated.emit("Using the exact compiled preview for saving...")
                save_data = _copy_serialized_playback(self.precompiled_data)
            else:
                save_data = _build_save_data(
                    self.config, self.selected_tracks_info, self.original_filename,
                    status=self.status_updated.emit,
                )
        except Exception as e:
            self.save_failed.emit(f"Error preparing save data:\n{e}")
            self.finished.emit()
            return

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{Path(self.original_filename).stem}_{timestamp_str}.json"
        output_path = Path(self.save_dir) / output_filename

        try:
            with open(output_path, 'w', encoding='utf-8', newline='\n') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=4)
            self.status_updated.emit(f"Serialization successful: {output_path}")
            self.save_successful.emit(str(output_path), "Playback sequence serialized and saved successfully.")
        except Exception as e:
            self.status_updated.emit(f"Serialization failed: {e}")
            self.save_failed.emit(f"Failed to serialize playback data to Windows file system:\n{e}")

        self.finished.emit()


class PlaybackController(QObject):
    # Signals to communicate back to the GUI
    status_updated = Signal(str)
    progress_updated = Signal(float)
    playback_finished = Signal()
    visualizer_updated = Signal(list)
    auto_paused = Signal()
    countdown_updated = Signal(int)
    error_occurred = Signal(str)
    
    pedal_updated = Signal(bool)          # Bridged from Player: True=down, False=up
    # Custom signals for specific orchestration events
    timeline_data_ready = Signal(list, float, object) # notes, total_duration, tempo_map
    pedal_data_ready = Signal(list)       # List of (start_sec, end_sec) pedal intervals
    save_successful = Signal(str, str) # filepath, success message
    save_failed = Signal(str) # error message
    playlist_compile_successful = Signal(object)
    playlist_compile_failed = Signal(str)

    def __init__(self):
        super().__init__()
        self.player = None
        self.player_thread = None
        self._save_worker = None
        self._save_thread = None
        self._compile_worker = None
        self._compile_thread = None
        self._last_compiled_signature = None
        self._last_compiled_save_data = None
        self._active_compile_context = None

    def is_playing(self) -> bool:
        return self.player_thread is not None and self.player_thread.isRunning()

    def is_paused(self) -> bool:
        return self.player is not None and self.player.pause_event.is_set()

    def toggle_pause(self):
        if self.player:
            self.player.toggle_pause()

    def stop(self):
        if self.player:
            self.player.stop()

    def seek(self, target_time: float):
        if self.player:
            self.player.seek(target_time)

    def shutdown(self):
        if self.player and self.player_thread and self.player_thread.isRunning():
            self.player.stop()
            self.player_thread.wait()
        # Save/playlist compilation workers are not safely cancellable halfway
        # through event generation. Waiting prevents "QThread destroyed while
        # running" crashes when the application is closed during compilation.
        for thread in (self._save_thread, self._compile_thread):
            if thread and thread.isRunning():
                thread.wait()

    def _on_playback_finished(self):
        if self.player_thread:
            self.player_thread.quit()
            self.player_thread.wait()
        self.player = None
        self.player_thread = None
        self.playback_finished.emit()

    def save(self, config: Dict, selected_tracks_info: List, save_dir: str, original_filename: str):
        if self._save_thread and self._save_thread.isRunning():
            return
        signature = _compilation_signature(config, selected_tracks_info)
        precompiled_data = None
        dynamic_seed = (config.get('humanization_mode') != 'disabled' and config.get('humanization_seed_mode') == 'dynamic')
        if not dynamic_seed and signature == self._last_compiled_signature and self._last_compiled_save_data:
            precompiled_data = self._last_compiled_save_data
        self._save_thread = QThread()
        self._save_worker = _SaveWorker(
            config,
            selected_tracks_info,
            save_dir,
            original_filename,
            precompiled_data=precompiled_data,
        )
        self._save_worker.moveToThread(self._save_thread)

        self._save_thread.started.connect(self._save_worker.run)
        self._save_worker.status_updated.connect(self.status_updated)
        self._save_worker.save_successful.connect(self.save_successful)
        self._save_worker.save_failed.connect(self.save_failed)
        self._save_worker.finished.connect(
            self._save_thread.quit, Qt.ConnectionType.DirectConnection
        )
        self._save_worker.finished.connect(self._on_save_finished)

        self._save_thread.start()

    def _on_save_finished(self):
        if self._save_thread:
            self._save_thread.quit()
            self._save_thread.wait()
        self._save_worker = None
        self._save_thread = None

    def compile_for_playlist(self, config: Dict, selected_tracks_info: List, original_filename: str):
        if self._compile_thread and self._compile_thread.isRunning():
            return False
        signature = _compilation_signature(config, selected_tracks_info)
        dynamic_seed = (config.get('humanization_mode') != 'disabled' and config.get('humanization_seed_mode') == 'dynamic')
        if not dynamic_seed and signature == self._last_compiled_signature and self._last_compiled_save_data:
            self.status_updated.emit("Using the exact compiled preview for the playlist...")
            self.playlist_compile_successful.emit(
                _copy_serialized_playback(self._last_compiled_save_data)
            )
            return True
        self._compile_thread = QThread()
        self._compile_worker = _CompileWorker(config, selected_tracks_info, original_filename)
        self._compile_worker.moveToThread(self._compile_thread)
        self._compile_thread.started.connect(self._compile_worker.run)
        self._compile_worker.status_updated.connect(self.status_updated)
        self._compile_worker.compile_successful.connect(self.playlist_compile_successful)
        self._compile_worker.compile_failed.connect(self.playlist_compile_failed)
        self._compile_worker.finished.connect(
            self._compile_thread.quit, Qt.ConnectionType.DirectConnection
        )
        self._compile_worker.finished.connect(self._on_compile_finished)
        self._compile_thread.start()
        return True

    def _on_live_compiled_bundle(self, bundle: Dict[str, Any]):
        """Publish the exact data that the Player is about to execute.

        This replaces the previous pre-humanization timeline. It also caches the
        same randomized result so Add to Playlist and Save do not roll a second,
        subtly different performance after the user has previewed it.
        """
        notes = list(bundle.get('visualization_notes') or [])
        events = list(bundle.get('compiled_events') or [])
        tempo_map = bundle.get('tempo_map')
        if not isinstance(tempo_map, TempoMap):
            tempo_map = TempoMap([(0.0, 500000)], [])
        total_duration = float(
            bundle.get('total_duration')
            or max((float(ev.time) for ev in events), default=1.0)
            or 1.0
        )
        self.timeline_data_ready.emit(notes, total_duration, tempo_map)
        self.pedal_data_ready.emit(
            _extract_pedal_intervals([ev for ev in events if ev.action == 'pedal'])
        )

        context = self._active_compile_context
        if context:
            config, original_filename, signature = context
            try:
                save_data = _build_save_data_from_bundle(config, original_filename, bundle)
            except Exception as exc:
                self.status_updated.emit(f"Could not cache compiled preview: {exc}")
            else:
                self._last_compiled_signature = signature
                self._last_compiled_save_data = save_data

    def _on_compile_finished(self):
        if self._compile_thread:
            self._compile_thread.quit()
            self._compile_thread.wait()
        self._compile_worker = None
        self._compile_thread = None

    def play(self, config: Dict, selected_tracks_info: List):
        self.status_updated.emit("Preparing playback...")
        original_filename = Path(str(config.get('midi_file') or 'Unknown MIDI')).name
        self._active_compile_context = (
            copy.deepcopy(config),
            original_filename,
            _compilation_signature(config, selected_tracks_info),
        )

        debug_log = self.status_updated.emit if config.get('debug_mode') else None
        if debug_log:
            debug_log("\n" + "=" * 60)
            debug_log("=== PLAYBACK SESSION START (MIDI file) ===")
            debug_log("=" * 60)
            debug_log("[CONFIG] " + " | ".join(
                f"{k}={v}" for k, v in sorted(config.items())
                if k not in ('midi_file',)
            ))
            debug_log(f"[CONFIG] midi_file: {config.get('midi_file', 'N/A')}")
            debug_log(f"[CONFIG] Tracks selected: {len(selected_tracks_info)}")
            for t, role in selected_tracks_info:
                debug_log(f"  Track {t.index} ({t.name}): {t.note_count} notes | Role: {role} | Instrument: {t.instrument_name}")
            debug_log("\n=== RAW MIDI DATA (Selected Tracks) ===")

        try:
            final_notes, tempo_map = _prepare_notes(config, selected_tracks_info, log=debug_log)
        except Exception as e:
            self.error_occurred.emit(f"Error preparing playback:\n{e}")
            return

        self.status_updated.emit("Analyzing musical structure...")
        analyzer = SectionAnalyzer(final_notes, tempo_map, debug_log=debug_log)
        sections = analyzer.analyze()

        self.player_thread = QThread()
        self.player = Player(config, final_notes, sections, tempo_map)
        self.player.moveToThread(self.player_thread)

        self.player_thread.started.connect(self.player.play)

        # Bridge Player signals through the Orchestrator
        self.player.playback_finished.connect(
            self.player_thread.quit, Qt.ConnectionType.DirectConnection
        )
        self.player.playback_finished.connect(self._on_playback_finished)
        self.player.status_updated.connect(self.status_updated.emit)
        self.player.progress_updated.connect(self.progress_updated.emit)
        self.player.visualizer_updated.connect(self.visualizer_updated.emit)
        self.player.pedal_updated.connect(self.pedal_updated.emit)
        self.player.auto_paused.connect(self.auto_paused.emit)
        self.player.countdown_updated.connect(self.countdown_updated.emit)
        self.player.error_occurred.connect(self.error_occurred.emit)
        self.player.compiled_bundle_ready.connect(self._on_live_compiled_bundle)

        self.player_thread.start()

    def play_from_notes(self, config: Dict, notes: List[Note], tempo_map: TempoMap):
        """Start playback from pre-built Note objects, bypassing MIDI file parsing.

        Used by the Translator tab to play imported sheet text directly through
        the normal humanization and playback pipeline.
        """
        self.status_updated.emit("Preparing playback from imported sheet...")
        self._active_compile_context = None
        debug_log = self.status_updated.emit if config.get('debug_mode') else None

        if config.get('simulate_hands'):
            assign_hands(notes)
        else:
            for note in notes:
                if note.hand == 'unknown':
                    note.hand = 'left' if note.pitch < 60 else 'right'

        analyzer = SectionAnalyzer(notes, tempo_map, debug_log=debug_log)
        sections = analyzer.analyze()

        self.player_thread = QThread()
        self.player = Player(config, notes, sections, tempo_map)
        self.player.moveToThread(self.player_thread)
        self.player_thread.started.connect(self.player.play)

        self.player.playback_finished.connect(
            self.player_thread.quit, Qt.ConnectionType.DirectConnection
        )
        self.player.playback_finished.connect(self._on_playback_finished)
        self.player.status_updated.connect(self.status_updated.emit)
        self.player.progress_updated.connect(self.progress_updated.emit)
        self.player.visualizer_updated.connect(self.visualizer_updated.emit)
        self.player.pedal_updated.connect(self.pedal_updated.emit)
        self.player.auto_paused.connect(self.auto_paused.emit)
        self.player.countdown_updated.connect(self.countdown_updated.emit)
        self.player.error_occurred.connect(self.error_occurred.emit)
        self.player.compiled_bundle_ready.connect(self._on_live_compiled_bundle)

        self.player_thread.start()

    def play_from_save(self, loaded_save_data: Dict):
        self.status_updated.emit("Initializing playback from pre-compiled serialization...")
        self._active_compile_context = None
        config = loaded_save_data.get('metadata', {}).get('playback_settings', {})
        events_data = loaded_save_data.get('compiled_events', [])

        debug_log = self.status_updated.emit if config.get('debug_mode') else None
        if debug_log:
            metadata = loaded_save_data.get('metadata', {})
            debug_log("\n" + "=" * 60)
            debug_log("=== PLAYBACK SESSION START (Saved file) ===")
            debug_log("=" * 60)
            debug_log(f"[SAVE] Source: {metadata.get('source_midi_filename', 'unknown')}")
            debug_log(f"[SAVE] Created: {metadata.get('creation_timestamp', 'unknown')}")
            debug_log(f"[SAVE] Raw events in file: {len(events_data)}")
        
        reconstructed_events = []
        for ev in events_data:
            pitch_val = ev.get('pitch')
            # Strictly typecast properties to prevent silent pynput failure.
            if pitch_val is not None:
                pitch_val = int(pitch_val)
            reconstructed_events.append(KeyEvent(
                time=float(ev['time']),
                priority=int(ev['priority']),
                action=str(ev['action']),
                key_char=str(ev['key_char']),
                pitch=pitch_val,
            ))

        # Enforce chronological ordering on physical execution events.
        reconstructed_events.sort(key=lambda x: (x.time, x.priority))
        event_duration = reconstructed_events[-1].time if reconstructed_events else 1.0

        visualizer_data = loaded_save_data.get('visualizer_data')
        reconstructed_notes = []
        if isinstance(visualizer_data, dict) and isinstance(visualizer_data.get('notes'), list):
            # Serialization v2 stores the exact notes used to generate the
            # physical events, so playlist/save playback matches the preview.
            for index, raw_note in enumerate(visualizer_data.get('notes', [])):
                if not isinstance(raw_note, dict):
                    continue
                try:
                    reconstructed_notes.append(_deserialize_note(raw_note, index))
                except (KeyError, TypeError, ValueError):
                    continue
            reconstructed_notes.sort(key=lambda n: (n.start_time, n.pitch, n.id))
            total_dur = max(
                float(visualizer_data.get('total_duration') or 0.0),
                float(event_duration),
                0.1,
            )
            playback_tempo = _deserialize_tempo_map(visualizer_data)
        else:
            # Backward compatibility for v1 saves/playlists. A list is used per
            # pitch instead of one start time, preserving overlapping same-pitch
            # notes that the old dictionary reconstruction silently discarded.
            active_presses = defaultdict(list)
            note_id_counter = 0
            for event in reconstructed_events:
                if event.pitch is None:
                    continue
                if event.action == 'press':
                    active_presses[event.pitch].append(float(event.time))
                    continue
                if event.action != 'release' or not active_presses[event.pitch]:
                    continue

                starts = active_presses[event.pitch]
                release_time = float(event.time)
                # At a same-time retrigger, pair the release with an older press
                # instead of the new attack at this exact timestamp.
                eligible = [i for i, value in enumerate(starts) if value < release_time - 1e-9]
                index = eligible[-1] if eligible else len(starts) - 1
                start_time = starts.pop(index)
                duration = max(0.01, release_time - start_time)
                reconstructed_notes.append(Note(
                    id=note_id_counter,
                    pitch=event.pitch,
                    velocity=64,
                    start_time=start_time,
                    duration=duration,
                    hand='left' if event.pitch < 60 else 'right',
                ))
                note_id_counter += 1

            reconstructed_notes.sort(key=lambda n: (n.start_time, n.pitch, n.id))
            total_dur = max(float(event_duration), 0.1)
            playback_tempo = TempoMap([(0.0, 500000)], [])

        if debug_log:
            press_ct = sum(1 for e in reconstructed_events if e.action == 'press')
            release_ct = sum(1 for e in reconstructed_events if e.action == 'release')
            pedal_ct = sum(1 for e in reconstructed_events if e.action == 'pedal')
            visual_source = 'stored exact data' if isinstance(visualizer_data, dict) else 'legacy reconstruction'
            debug_log(
                f"[SAVE] Reconstructed: {len(reconstructed_events)} events "
                f"(press={press_ct} release={release_ct} pedal={pedal_ct}) | "
                f"{len(reconstructed_notes)} visual notes ({visual_source}) | duration={total_dur:.2f}s"
            )

        self.timeline_data_ready.emit(reconstructed_notes, total_dur, playback_tempo)

        _pedal_evs = [ev for ev in reconstructed_events if ev.action == 'pedal']
        self.pedal_data_ready.emit(_extract_pedal_intervals(_pedal_evs))

        self.player_thread = QThread()
        self.player = Player(config, [], [], playback_tempo)
        self.player.load_compiled_events(reconstructed_events, total_dur)

        self.player.moveToThread(self.player_thread)
        self.player_thread.started.connect(self.player.play_saved_events)

        self.player.playback_finished.connect(
            self.player_thread.quit, Qt.ConnectionType.DirectConnection
        )
        self.player.playback_finished.connect(self._on_playback_finished)
        self.player.status_updated.connect(self.status_updated.emit)
        self.player.progress_updated.connect(self.progress_updated.emit)
        self.player.visualizer_updated.connect(self.visualizer_updated.emit)
        self.player.pedal_updated.connect(self.pedal_updated.emit)
        self.player.auto_paused.connect(self.auto_paused.emit)
        self.player.countdown_updated.connect(self.countdown_updated.emit)
        self.player.error_occurred.connect(self.error_occurred.emit)

        self.player_thread.start()