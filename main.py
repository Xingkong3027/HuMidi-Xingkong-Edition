#!/usr/bin/env python3
import sys
import os
import bisect
import copy
import hashlib
import json
import random
import threading
import webbrowser
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QMessageBox, QFileDialog, QDialog, QProgressDialog
)
from PyQt6.QtCore import Qt, QTimer, QThread
from PyQt6.QtGui import QIcon

from core.core import MidiParser, MidiInvalidDataByteError, KeyMapper, TempoMap
from core.trimming import trimmed_duration_hint, selected_track_bounds
from core.translator import FormatRegistry
from managers.HotkeyManager import HotkeyManager
from managers.UpdateManager import UpdateChecker
from controllers.PlaybackController import PlaybackController, cache_matches_config
from managers.ConfigManager import ConfigManager
from managers.LanguageManager import LanguageManager
from managers.PlaylistManager import PlaylistManager, PlaylistFormatError
from ui.MainWindowUI import MainWindowUI
from ui.TrackSelectionDialog import TrackSelectionDialog
from ui.LoadSaveDialog import LoadSaveDialog
from ui.GlobalHumanizationDialog import GlobalHumanizationDialog
from ui.ShortcutSettingsDialog import ShortcutSettingsDialog
from ui.BatchMidiDialogs import BatchImportChoiceDialog, BatchImportSummaryDialog
from workers.PlaylistExportWorker import PlaylistExportWorker
from workers.BatchPlaylistEditPrepareWorker import BatchPlaylistEditPrepareWorker

APP_NAME = "HuMidi: Xingkong Edition"
APP_VERSION = "2.0.0-xk.1"
BUILD_NAME = "Xingkong Edition"

DEFAULT_WINDOW_SIZE = (1040, 640)
MINIMUM_WINDOW_SIZE = (900, 560)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(*MINIMUM_WINDOW_SIZE)
        self.resize(*DEFAULT_WINDOW_SIZE)

        # Set specific Icon base execution path (Required for OS Contexts)
        base_path = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        icon_name = 'icon.icns' if sys.platform == 'darwin' else 'icon.ico'
        icon_path = os.path.join(base_path, icon_name)
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Instantiate domains. Load configuration before constructing the UI so
        # the first visible frame already uses the selected language.
        self.config_manager = ConfigManager()
        loaded_cfg = self.config_manager.load()
        self.language_manager = LanguageManager(loaded_cfg.get('language_selection', 'auto'))
        self.language_manager.start_auto_translation()
        self.ui = MainWindowUI(self)
        self.playback_controller = PlaybackController()
        self.hotkey_manager = HotkeyManager(loaded_cfg.get("shortcuts", loaded_cfg.get("hotkey")))
        self.playlist_manager = PlaylistManager(self.config_manager.config_dir)

        # Global application states
        self.loaded_save_data = None
        self.loaded_save_filename = None
        self.selected_tracks_info = None
        self.current_notes = []
        self._note_start_times = []
        self.total_song_duration_sec = 1.0
        self._max_note_duration = 0.0
        self.current_pedal_intervals = []
        self.current_playlist_id = None
        self._playlist_session_active = False
        self._pending_playlist_item_id = None
        self._playlist_compile_in_progress = False
        self._playlist_compile_context = None
        self._editing_playlist_id = None
        self._editing_sheet_playlist_id = None
        self._pending_batch_imports: list[dict] = []
        self._batch_edit_entries: list[dict] = []
        self._batch_edit_baseline_config: dict | None = None
        self._batch_playlist_operation = None
        self._batch_progress_dialog = None
        self._batch_edit_prepare_thread = None
        self._batch_edit_prepare_worker = None
        self._batch_edit_prepare_progress = None
        self._batch_edit_prepare_cancel_event = None
        self._batch_edit_prepare_initial_failures: list[str] = []
        self._export_thread = None
        self._export_worker = None
        self._export_progress_dialog = None
        self._playback_status_title = ""
        self._playback_status_source = "none"
        self._playback_status_detail = ""

        self._bind_signals()

        if loaded_cfg:
            self.ui.load_config_to_ui(loaded_cfg, self.config_manager.save_dir)
        else:
            self.ui.reset_controls_to_default()
        self.ui.playlist_tab.set_mode(loaded_cfg.get('playlist_mode', 'single'))
        self._refresh_playlist()
        self._apply_language()
        self.ui.settings_tab.update_shortcut_summary(self.hotkey_manager, self._t)
        self._sync_play_button()
        self._update_global_play_availability()
        self._render_playback_status()

        # Xingkong Edition checks its own release page. Updates are never
        # installed silently; users choose whether to open GitHub and download.
        self._update_checker = UpdateChecker(APP_VERSION)
        self._update_checker.update_available.connect(self._on_update_available)
        self._update_checker.start()

    def _t(self, text: str) -> str:
        return self.language_manager.tr(text)

    def _playlist_mode_text(self) -> str:
        current = self.ui.playlist_tab.current_mode()
        for value, label in self.ui.playlist_tab.MODES:
            if value == current:
                return self._t(label)
        return self._t("Single Play")

    def _set_playback_status(self, title: str, source: str, detail: str = "") -> None:
        self._playback_status_title = str(title or "")
        self._playback_status_source = str(source or "none")
        self._playback_status_detail = str(detail or "")
        self._render_playback_status()

    def _clear_playback_status(self) -> None:
        self._set_playback_status("", "none")

    def _render_playback_status(self) -> None:
        title = self._playback_status_title
        source = self._playback_status_source
        detail = self._playback_status_detail

        if not title or source == "none":
            title_text = self._t("Now Playing: —")
            source_text = self._t("Source: —")
        else:
            title_text = self._t("Now Playing: {name}").format(name=title)
            if source == "playlist":
                source_text = self._t("Source: Playlist ({mode})").format(
                    mode=self._playlist_mode_text()
                )
            elif source == "saved_preview":
                source_text = self._t("Source: Playback Page (Saved Playback Preview)")
            elif source == "translator_preview":
                source_text = self._t("Source: Translator Preview")
            else:
                source_text = self._t("Source: Playback Page Preview")

            if detail and source == "translator_preview":
                title_text = self._t("Now Playing: Pasted Sheet ({format_name})").format(
                    format_name=detail
                )

        self.ui.update_playback_info(title_text, source_text)

    def _update_global_play_availability(self, *_args) -> None:
        if self.playback_controller.is_playing() or self.playback_controller.is_paused():
            self.ui.play_button.setEnabled(True)
            return
        current_page = self.ui.tabs.currentIndex()
        collapsed_ready = bool(
            self.ui._is_collapsed and self.ui.collapsed_selected_playlist_id()
        )
        playlist_ready = (
            current_page == 1
            and len(self.ui.playlist_tab.selected_ids()) == 1
        )
        translator_ready = (
            current_page == 3
            and self.ui.translator_tab.has_playable_input()
        )
        source_ready = bool(self.loaded_save_data or self.selected_tracks_info)
        self.ui.play_button.setEnabled(
            collapsed_ready or playlist_ready or translator_ready or source_ready
        )

    def _apply_language(self):
        self.ui.apply_language(self.language_manager)
        self.ui.settings_tab.update_shortcut_summary(self.hotkey_manager, self._t)
        if (not self.loaded_save_data and not self.selected_tracks_info
                and not self.ui.playback_tab.file_path_label.toolTip()):
            self.ui.update_file_label(self._t("No file selected."), "")
        if self._playlist_compile_in_progress:
            self.ui.playback_tab.add_to_playlist_btn.setText(self._t("Compiling..."))
        elif self._batch_edit_entries:
            self.ui.playback_tab.set_playlist_batch_editing(len(self._batch_edit_entries), self._t)
        elif self._pending_batch_imports:
            self.ui.playback_tab.set_batch_pending(len(self._pending_batch_imports), self._t)
        else:
            self.ui.playback_tab.set_playlist_editing(
                self._editing_playlist_id is not None, self._t
            )
        self.ui.settings_tab.update_global_humanization_summary(self._t)
        self._render_playback_status()
        self._sync_play_button()

    def _on_language_changed(self):
        selection = str(self.ui.settings_tab.language_combo.currentData() or 'auto')
        self.language_manager.set_selection(selection)
        self._apply_language()
        self._save_config()

    def _open_global_humanization_settings(self):
        dialog = GlobalHumanizationDialog(
            self.ui.settings_tab.global_humanization_config(),
            self,
            self.language_manager,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            config = dialog.get_config()
            self.ui.settings_tab.set_global_humanization_config(config)
            self.ui.playback_tab.set_global_humanization_config(config)
            self.ui.playback_tab.regenerate_fixed_random_seed()
            self.ui.settings_tab.update_global_humanization_summary(self._t)
            self._save_config()

    def _bind_signals(self):
        # UI controls bound strictly to Execution/Router logic
        self.ui.play_button.clicked.connect(self.handle_play)
        self.ui.stop_button.clicked.connect(self.handle_stop)
        self.ui.save_button.clicked.connect(self.handle_save)
        self.ui.reset_button.clicked.connect(self.ui.reset_controls_to_default)
        self.ui.playback_tab.browse_button.clicked.connect(self.select_file)
        self.ui.playback_tab.load_saved_btn.clicked.connect(self.open_load_dialog)
        self.ui.playback_tab.add_to_playlist_btn.clicked.connect(self.add_current_to_playlist)
        self.ui.settings_tab.save_browse_btn.clicked.connect(self._browse_save_dir)
        self.ui.previous_button.clicked.connect(self.play_previous_playlist_item)
        self.ui.next_button.clicked.connect(self.play_next_playlist_item)
        self.ui._collapsed_previous_btn.clicked.connect(self.play_previous_playlist_item)
        self.ui._collapsed_next_btn.clicked.connect(self.play_next_playlist_item)
        self.ui.settings_tab.hk_btn.clicked.connect(self._change_hotkey)
        self.ui.settings_tab.check_update_btn.clicked.connect(self._manual_check_update)
        self.ui.settings_tab.language_combo.currentIndexChanged.connect(self._on_language_changed)
        self.ui.settings_tab.global_humanization_btn.clicked.connect(self._open_global_humanization_settings)

        # Playlist tab
        self.ui.playlist_tab.play_requested.connect(self.play_playlist_item)
        self.ui.playlist_tab.previous_requested.connect(self.play_previous_playlist_item)
        self.ui.playlist_tab.next_requested.connect(self.play_next_playlist_item)
        self.ui.playlist_tab.import_requested.connect(self.import_playlist)
        self.ui.playlist_tab.export_requested.connect(self.export_playlist)
        self.ui.playlist_tab.delete_requested.connect(self.delete_playlist_item)
        self.ui.playlist_tab.delete_many_requested.connect(self.delete_playlist_items)
        self.ui.playlist_tab.clear_requested.connect(self.clear_playlist)
        self.ui.playlist_tab.edit_requested.connect(self.edit_playlist_item)
        self.ui.playlist_tab.batch_edit_requested.connect(self.edit_playlist_items)
        self.ui.playlist_tab.save_midi_as_requested.connect(self.save_playlist_midi_as)
        self.ui.playlist_tab.batch_save_midi_as_requested.connect(self.save_playlist_midis_as)
        self.ui.playlist_tab.reorder_requested.connect(self.reorder_playlist)
        self.ui.playlist_tab.mode_changed.connect(self._on_playlist_mode_changed)
        self.ui.playlist_tab.table.itemSelectionChanged.connect(self._update_global_play_availability)
        self.ui.tabs.currentChanged.connect(self._update_global_play_availability)

        # View manipulations bound to Window behavior
        self.ui.collapse_btn.clicked.connect(self._sync_play_button)
        self.ui.collapse_btn.clicked.connect(self._update_global_play_availability)
        self.ui.collapse_btn.clicked.connect(
            lambda: QTimer.singleShot(0, self._render_playback_status)
        )
        self.ui.settings_tab.always_top_check.toggled.connect(self._toggle_always_on_top)
        self.ui.settings_tab.opacity_slider.valueChanged.connect(self._change_opacity)

        # Settings-tab persistence — save immediately on change so closing without playing doesn't lose them
        self.ui.settings_tab.always_top_check.toggled.connect(self._save_config)
        self.ui.settings_tab.opacity_slider.valueChanged.connect(self._save_config)
        self.ui.settings_tab.timeline_vis_check.toggled.connect(self._save_config)
        self.ui.settings_tab.piano_vis_check.toggled.connect(self._save_config)
        self.ui.settings_tab.use_ai_pedal_check.toggled.connect(self._save_config)

        # Translator tab
        self.ui.translator_tab.play_sheet_requested.connect(self._on_play_sheet)
        self.ui.translator_tab.add_to_playlist_requested.connect(self._on_save_sheet_to_playlist)
        self.ui.translator_tab.export_requested.connect(self._on_export_sheet)
        self.ui.translator_tab.import_text.textChanged.connect(
            self._update_global_play_availability
        )
        self.ui.translator_tab.sub_tabs.currentChanged.connect(
            self._update_global_play_availability
        )

        # Timeline logic bridging
        self.ui.timeline_widget.seek_requested.connect(self._on_timeline_seek)
        self.ui.timeline_widget.scrub_position_changed.connect(self._on_visual_scrub)

        # External IO bridging
        self.hotkey_manager.play_pause_requested.connect(self.toggle_playback_state)
        self.hotkey_manager.stop_requested.connect(self.handle_stop)
        self.hotkey_manager.next_requested.connect(self.play_next_playlist_item)
        self.hotkey_manager.previous_requested.connect(self.play_previous_playlist_item)
        self.hotkey_manager.bindings_changed.connect(self._on_shortcuts_changed)

        # System Logic bridging to the View representations
        self.playback_controller.status_updated.connect(
            lambda message: self.ui.log_output.append(self._t(message))
        )
        self.playback_controller.progress_updated.connect(self.update_progress)
        self.playback_controller.playback_finished.connect(self.on_playback_finished)
        self.playback_controller.visualizer_updated.connect(lambda p: self.ui.piano_widget.set_active_pitches(p))
        self.playback_controller.pedal_updated.connect(self.ui.piano_widget.set_pedal_active)
        self.playback_controller.auto_paused.connect(self._on_auto_paused)
        self.playback_controller.countdown_updated.connect(self.ui.set_countdown_remaining)
        self.playback_controller.error_occurred.connect(self.show_error_dialog)
        self.playback_controller.timeline_data_ready.connect(self._on_timeline_data_ready)
        self.playback_controller.pedal_data_ready.connect(self._on_pedal_data_ready)
        self.playback_controller.save_successful.connect(self._on_save_successful)
        self.playback_controller.save_failed.connect(self._on_save_failed)
        self.playback_controller.playlist_compile_successful.connect(self._on_playlist_compile_successful)
        self.playback_controller.playlist_compile_failed.connect(self._on_playlist_compile_failed)

    def _on_playlist_mode_changed(self, _mode: str) -> None:
        self._save_config()
        if self._playback_status_source == "playlist":
            self._render_playback_status()

    # --- Windows Specific GUI Modifications ---
    def _toggle_always_on_top(self, checked):
        flags = self.windowFlags()
        if checked: self.setWindowFlags(flags | Qt.WindowType.WindowStaysOnTopHint)
        else: self.setWindowFlags(flags & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()

    def _change_opacity(self, value):
        self.setWindowOpacity(value / 100.0)

    # --- Standard Execution Behaviors ---
    def _save_config(self):
        config_data = self.ui.gather_app_config()
        config_data["shortcuts"] = self.hotkey_manager.serialize_bindings()
        # Keep the old field so older builds still restore the primary binding.
        config_data["hotkey"] = self.hotkey_manager.serialize_current_key()
        self.config_manager.save(config_data)

    def _browse_save_dir(self):
        path = QFileDialog.getExistingDirectory(self, self._t("Select Save Directory"), self.config_manager.save_dir)
        if path:
            self.config_manager.set_save_dir(path)
            self.ui.settings_tab.save_path_input.setText(path)
            self._save_config()

    def _change_hotkey(self):
        dialog = ShortcutSettingsDialog(
            self.hotkey_manager, self, self.language_manager
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._save_config()
        self.ui.settings_tab.update_shortcut_summary(self.hotkey_manager, self._t)
        self._sync_play_button()

    def _on_shortcuts_changed(self):
        self.ui.settings_tab.update_shortcut_summary(self.hotkey_manager, self._t)
        self._sync_play_button()

    def _sync_play_button(self):
        """Single authoritative update for the play button, derived from current playback state."""
        key_str = self.hotkey_manager.primary_display("play_pause")
        suffix = f" ({key_str})" if key_str else ""
        if self.ui._is_collapsed:
            if self.playback_controller.is_paused():
                self.ui.play_button.setText("\uE768")
                self.ui.play_button.setToolTip(self._t("Resume" + suffix))
            elif self.playback_controller.is_playing():
                self.ui.play_button.setText("\uE769")
                self.ui.play_button.setToolTip(self._t("Pause" + suffix))
            else:
                self.ui.play_button.setText("\uE768")
                self.ui.play_button.setToolTip(self._t("Play" + suffix))
        else:
            if self.playback_controller.is_paused():
                self.ui.play_button.setText(self._t("Resume" + suffix))
            elif self.playback_controller.is_playing():
                self.ui.play_button.setText(self._t("Pause" + suffix))
            else:
                self.ui.play_button.setText(self._t("Play" + suffix))
            self.ui.play_button.setToolTip(self._t("Start, pause, or resume playback"))

    def toggle_playback_state(self):
        if not self.playback_controller.is_paused():
            self.ui.piano_widget.clear()

        if self.playback_controller.is_playing() or self.playback_controller.is_paused():
            self.playback_controller.toggle_pause()
            self._sync_play_button()
            if not self.playback_controller.is_paused():
                current_t = self.ui.timeline_widget.current_time
                self._on_visual_scrub(current_t)
        elif (self.ui.play_button.isEnabled() or
              (self.ui.tabs.currentIndex() == 1 and self.ui.playlist_tab.selected_id())):
            self.handle_play()

    def _on_auto_paused(self):
        self._sync_play_button()
        self.ui.piano_widget.clear()
        self.ui.stop_button.setEnabled(True)

        # The original player pauses at the end of a song instead of ending its
        # worker thread. For playlist playback, convert that natural end into a
        # clean stop so the selected playback mode can advance deterministically.
        if self._playlist_session_active and self.current_playlist_id:
            next_id = self._automatic_next_playlist_id()
            if next_id:
                self._pending_playlist_item_id = next_id
            else:
                self._playlist_session_active = False
            self.playback_controller.stop()

    def _on_timeline_seek(self, time):
        self.ui.log_output.append(f"Seeking to {time:.2f}s...")
        self.playback_controller.seek(time)
    
    def _on_visual_scrub(self, time):
        active_pitches = set()
        lo = bisect.bisect_left(self._note_start_times, time - self._max_note_duration)
        hi = bisect.bisect_right(self._note_start_times, time)
        for note in self.current_notes[lo:hi]:
            if note.end_time > time:
                active_pitches.add(note.pitch)
        self.ui.piano_widget.set_active_pitches(list(active_pitches))
        pedal_down = any(s <= time < e for s, e in self.current_pedal_intervals)
        self.ui.piano_widget.set_pedal_active(pedal_down)
        self.ui.update_time_label(time, self.total_song_duration_sec)

    def _on_timeline_data_ready(self, notes, total_dur, tempo_map):
        self.current_notes = notes
        self._note_start_times = [n.start_time for n in notes]
        self._max_note_duration = max((n.duration for n in notes), default=0.0)
        self.total_song_duration_sec = total_dur
        self.ui.timeline_widget.set_data(notes, total_dur, tempo_map)
        self.ui.reset_timeline_position()

    def _on_pedal_data_ready(self, intervals: list):
        self.current_pedal_intervals = intervals
        self.ui.timeline_widget.set_pedal_intervals(intervals)

    def update_progress(self, current_time):
        self.ui.update_progress(current_time, self.total_song_duration_sec)

    # --- Loading & File State Dialogs ---
    def _clear_batch_edit_state(self) -> None:
        self.ui.playback_tab.end_batch_change_tracking()
        self._pending_batch_imports = []
        self._batch_edit_entries = []
        self._batch_edit_baseline_config = None
        if self._editing_playlist_id is None:
            self.ui.playback_tab.set_playlist_editing(False, self._t)
        if self._editing_sheet_playlist_id is not None:
            self._editing_sheet_playlist_id = None
            self.ui.translator_tab.set_playlist_editing(False, self._t)

    def select_file(self):
        if self.playback_controller.is_playing() or self.playback_controller.is_paused():
            return
        midi_filter = f"{self._t('MIDI Files')} (*.mid *.midi)"
        filepaths, _ = QFileDialog.getOpenFileNames(
            self, self._t("Select MIDI Files"), "", midi_filter
        )
        if not filepaths:
            return
        self._editing_playlist_id = None
        self._editing_sheet_playlist_id = None
        self.ui.translator_tab.set_playlist_editing(False, self._t)
        self.ui.playback_tab.end_batch_change_tracking()
        self._pending_batch_imports = []
        self._batch_edit_entries = []
        self._batch_edit_baseline_config = None
        self.ui.playback_tab.set_playlist_editing(False, self._t)
        if len(filepaths) == 1:
            self._clear_batch_edit_state()
            self._load_single_midi(filepaths[0])
            return

        choice_dialog = BatchImportChoiceDialog(
            len(filepaths), self, self.language_manager
        )
        if choice_dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if choice_dialog.choice not in {"auto", "manual"}:
            return
        self._run_batch_midi_import(filepaths, choice_dialog.choice)

    def _load_single_midi(self, filepath: str) -> None:
        self._playlist_session_active = False
        self._pending_playlist_item_id = None
        self.current_playlist_id = None
        self.loaded_save_data = None
        self.loaded_save_filename = None
        self.selected_tracks_info = None
        self._sync_trim_bounds([])
        self.ui.play_button.setEnabled(False)
        self.ui.scrubber_slider.setEnabled(False)
        self.ui._set_save_enabled(False)
        self.ui.playback_tab.add_to_playlist_btn.setEnabled(False)
        self.ui.playback_tab.playback_group.setEnabled(True)
        self.ui.playback_tab.humanization_group.setEnabled(True)
        self.ui.playback_tab.set_midi_clip_invalid_data(False)
        self.ui.update_file_label(os.path.basename(filepath), filepath)
        self.ui.log_output.append(self._t(f"Selected file: {filepath}"))
        self._parse_and_select_tracks(filepath)

    def _ask_localized_yes_no(self, title: str, message: str) -> bool:
        """Show a Yes/No question with explicitly localized button labels.

        Qt's native standard button text can remain English on some Windows
        installations even when the rest of this hand-built UI is translated.
        Creating the buttons ourselves keeps the labels deterministic.
        """
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle(self._t(title))
        box.setText(self._t(message))
        yes_button = box.addButton(self._t("Yes"), QMessageBox.ButtonRole.YesRole)
        no_button = box.addButton(self._t("No"), QMessageBox.ButtonRole.NoRole)
        box.setDefaultButton(no_button)
        box.setEscapeButton(no_button)
        box.exec()
        return box.clickedButton() is yes_button

    def _localized_midi_parse_error(self, exc: Exception) -> str:
        """Turn common parser errors into clear localized user messages."""
        message = str(exc).strip()
        prefix = "Could not read MIDI file:"
        reason = message[len(prefix):].strip() if message.startswith(prefix) else message
        lowered = reason.lower()

        if "mthd not found" in lowered:
            return self._t(
                "The selected file does not contain a valid MIDI header (MThd). "
                "It may not be a MIDI file or may be damaged."
            )
        if "mtrk not found" in lowered:
            return self._t(
                "The MIDI track header (MTrk) is missing. The file may be damaged."
            )
        if "unexpected end of file" in lowered or "unexpected end of data" in lowered:
            return self._t(
                "The MIDI file ended unexpectedly and may be incomplete or damaged."
            )
        return self._t("Could not read MIDI file: {reason}").format(reason=reason)

    def _parse_midi_with_clip_prompt(
        self, filepath: str, progress_dialog: QProgressDialog | None = None
    ):
        """Parse strictly, then offer an explicit clip retry for invalid bytes."""
        try:
            tracks, tempo_map = MidiParser.parse_structure(filepath, 1.0, None)
            return tracks, tempo_map, False
        except MidiInvalidDataByteError:
            was_visible = bool(progress_dialog and progress_dialog.isVisible())
            if was_visible:
                progress_dialog.hide()
                QApplication.processEvents()
            try:
                accepted = self._ask_localized_yes_no(
                    "Non-standard MIDI Data",
                    self._t(
                        '"{filename}" contains illegal MIDI data bytes. '
                        'Use clip repair automatically and continue importing?'
                    ).format(filename=os.path.basename(filepath)),
                )
            finally:
                if was_visible:
                    progress_dialog.show()
                    QApplication.processEvents()
            if not accepted:
                return None
            tracks, tempo_map = MidiParser.parse_structure(
                filepath, 1.0, None, clip_invalid_data=True
            )
            self.ui.log_output.append(
                self._t(
                    'Used clip repair for illegal MIDI data bytes in "{filename}".'
                ).format(filename=os.path.basename(filepath))
            )
            return tracks, tempo_map, True

    @staticmethod
    def _automatic_track_selection(tracks) -> list:
        # The original single-file dialog defaults to every non-drum track.
        # Keep the same predictable rule for batch mode and explicitly fall
        # back to user selection when it yields zero tracks.
        return [(track, "Auto-Detect") for track in tracks if not track.is_drum and track.note_count > 0]

    def _run_batch_midi_import(self, filepaths: list[str], mode: str) -> None:
        progress = QProgressDialog(
            self._t("Preparing MIDI files…"), self._t("Cancel"), 0, len(filepaths), self
        )
        progress.setWindowTitle(self._t("Batch Import MIDI"))
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.show()

        successes: list[dict] = []
        failures: list[dict] = []
        ignore_all_auto_failures = False
        for index, filepath in enumerate(filepaths, start=1):
            progress.setValue(index - 1)
            progress.setLabelText(
                self._t("Preparing {current}/{total}: {name}").format(
                    current=index, total=len(filepaths), name=os.path.basename(filepath)
                )
            )
            QApplication.processEvents()
            if progress.wasCanceled():
                for remaining in filepaths[index - 1:]:
                    failures.append({"path": remaining, "reason": self._t("Cancelled")})
                break
            try:
                parsed = self._parse_midi_with_clip_prompt(filepath, progress)
                if parsed is None:
                    failures.append({
                        "path": filepath,
                        "reason": self._t("Clip repair declined by user"),
                    })
                    continue
                tracks, tempo_map, used_clip = parsed
            except Exception as exc:
                failures.append({
                    "path": filepath,
                    "reason": self._localized_midi_parse_error(exc),
                })
                continue

            selected_tracks = []
            if mode == "manual":
                progress.hide()
                dialog = TrackSelectionDialog(
                    tracks, self, self.language_manager, midi_name=os.path.basename(filepath)
                )
                accepted = dialog.exec() == QDialog.DialogCode.Accepted
                progress.show()
                if accepted:
                    selected_tracks = dialog.get_selection()
                else:
                    failures.append({"path": filepath, "reason": self._t("Skipped by user")})
                    continue
            else:
                selected_tracks = self._automatic_track_selection(tracks)
                if not selected_tracks:
                    if ignore_all_auto_failures:
                        failures.append({
                            "path": filepath,
                            "reason": self._t("Automatic track selection found no playable tracks"),
                        })
                        continue
                    progress.hide()
                    dialog = TrackSelectionDialog(
                        tracks, self, self.language_manager,
                        mode="auto_failure", midi_name=os.path.basename(filepath),
                    )
                    accepted = dialog.exec() == QDialog.DialogCode.Accepted
                    progress.show()
                    if accepted:
                        selected_tracks = dialog.get_selection()
                    elif dialog.result_action == "ignore_all":
                        ignore_all_auto_failures = True
                        failures.append({"path": filepath, "reason": self._t("Ignored")})
                        continue
                    else:
                        failures.append({"path": filepath, "reason": self._t("Ignored")})
                        continue

            if not selected_tracks:
                failures.append({"path": filepath, "reason": self._t("No tracks selected")})
                continue
            successes.append({
                "path": filepath,
                "selected_tracks": selected_tracks,
                "tempo_map": tempo_map,
                "midi_clip_invalid_data": bool(used_clip),
            })

        progress.setValue(len(filepaths))
        progress.close()
        summary = BatchImportSummaryDialog(
            successes, failures, self, self.language_manager
        )
        if summary.exec() != QDialog.DialogCode.Accepted:
            return
        if summary.choice == "add":
            self._pending_batch_imports = []
            self._start_batch_playlist_operation(
                "add", successes, self.ui.gather_playback_config()
            )
        elif summary.choice == "continue":
            self._activate_batch_settings(successes)

    def _activate_batch_settings(self, entries: list[dict]) -> None:
        if not entries:
            return
        self._editing_playlist_id = None
        self.ui.playback_tab.end_batch_change_tracking()
        self._batch_edit_entries = []
        self._batch_edit_baseline_config = None
        self._pending_batch_imports = list(entries)
        first = entries[0]
        self._playlist_session_active = False
        self.current_playlist_id = None
        self.loaded_save_data = None
        self.loaded_save_filename = None
        self.selected_tracks_info = first["selected_tracks"]
        self.parsed_tempo_map = first["tempo_map"]
        self.ui.playback_tab.set_midi_clip_invalid_data(
            bool(first.get("midi_clip_invalid_data", False))
        )
        self._sync_trim_bounds(first["selected_tracks"])
        label = self._t("Batch import: {count} MIDI files (previewing {name})").format(
            count=len(entries), name=os.path.basename(first["path"])
        )
        self.ui.update_file_label(label, first["path"])
        self.ui.playback_tab.playback_group.setEnabled(True)
        self.ui.playback_tab.humanization_group.setEnabled(True)
        self.ui.playback_tab.set_batch_pending(len(entries), self._t)
        self.ui.playback_tab.add_to_playlist_btn.setEnabled(True)
        self.ui.play_button.setEnabled(True)
        self.ui.scrubber_slider.setEnabled(True)
        self.ui._set_save_enabled(True)
        self.ui.tabs.setCurrentIndex(0)

    def open_load_dialog(self):
        dialog = LoadSaveDialog(self.config_manager.save_dir, self, self.language_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_file, data = dialog.get_selected_data()
            if selected_file and data:
                self._clear_batch_edit_state()
                self._editing_playlist_id = None
                self._playlist_session_active = False
                self.current_playlist_id = None
                self.loaded_save_data = data
                self.loaded_save_filename = os.path.basename(selected_file)
                self.selected_tracks_info = None
                
                self.ui.update_file_label(self.loaded_save_filename, selected_file)
                self.ui.playback_tab.playback_group.setEnabled(False)
                self.ui.playback_tab.humanization_group.setEnabled(False)
                self.ui._set_save_enabled(False)
                self.ui.playback_tab.add_to_playlist_btn.setEnabled(False)
                self.ui.play_button.setEnabled(True)
                self.ui.scrubber_slider.setEnabled(True)
                self.ui.log_output.append(self._t(f"Loaded save file: {self.loaded_save_filename}"))

    def _parse_and_select_tracks(self, filepath):
        self.ui.log_output.append(self._t("Parsing MIDI structure..."))
        try:
            parsed = self._parse_midi_with_clip_prompt(filepath)
            if parsed is None:
                self.ui.log_output.append(self._t("Clip repair was declined; MIDI import cancelled."))
                return False
            tracks, tempo_map, used_clip = parsed
        except Exception as e:
            QMessageBox.critical(
                self,
                self._t("Error"),
                self._t("Failed to parse MIDI:")
                + "\n"
                + self._localized_midi_parse_error(e),
            )
            return False

        self.ui.playback_tab.set_midi_clip_invalid_data(used_clip)
        dialog = TrackSelectionDialog(
            tracks, self, self.language_manager, midi_name=os.path.basename(filepath)
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.selected_tracks_info = dialog.get_selection()
            self.parsed_tempo_map = tempo_map
            self._sync_trim_bounds(self.selected_tracks_info)
            self.ui.log_output.append(
                self._t("Tracks selected: {count}").format(count=len(self.selected_tracks_info))
            )
            has_tracks = bool(self.selected_tracks_info)
            self.ui.play_button.setEnabled(has_tracks)
            self.ui.scrubber_slider.setEnabled(has_tracks)
            self.ui._set_save_enabled(has_tracks)
            self.ui.playback_tab.add_to_playlist_btn.setEnabled(has_tracks)
            return has_tracks

        self.ui.log_output.append(self._t("Track selection cancelled."))
        self.selected_tracks_info = None
        self.ui.play_button.setEnabled(False)
        self.ui.scrubber_slider.setEnabled(False)
        self.ui._set_save_enabled(False)
        self.ui.playback_tab.add_to_playlist_btn.setEnabled(False)
        return False

    # --- Playlist ---
    def _refresh_playlist(self, selected_id: str | None = None):
        if selected_id is None:
            selected_id = self.current_playlist_id
        items = self.playlist_manager.items()
        self.ui.playlist_tab.refresh(items, selected_id)
        self.ui.refresh_collapsed_playlist(items, selected_id)
        self._update_global_play_availability()

    def _playlist_config_uses_dynamic_seed(self, config: dict) -> bool:
        return (
            config.get("humanization_mode") != "disabled"
            and config.get("humanization_seed_mode") == "dynamic"
        )

    @staticmethod
    def _humanization_basis(config: dict) -> str:
        keys = (
            "humanization_mode", "simulate_hands", "enable_chord_roll",
            "vary_timing", "timing_variance", "vary_articulation", "articulation",
            "enable_drift_correction", "drift_decay_factor", "enable_mistakes",
            "mistake_chance", "enable_tempo_sway", "tempo_sway_intensity",
            "invert_tempo_sway",
        )
        payload = {key: config.get(key) for key in keys}
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _playlist_duration_hint(config: dict, selected_tracks_info: list) -> float:
        return trimmed_duration_hint(config, selected_tracks_info)

    def _sync_trim_bounds(self, selected_tracks_info=None) -> None:
        self.ui.playback_tab.set_trim_source_bounds(
            selected_tracks_info if selected_tracks_info is not None
            else (self.selected_tracks_info or [])
        )

    def _reset_playlist_commit_button(self) -> None:
        self._playlist_compile_in_progress = False
        if self._batch_edit_entries:
            self.ui.playback_tab.set_playlist_batch_editing(len(self._batch_edit_entries), self._t)
        elif self._pending_batch_imports:
            self.ui.playback_tab.set_batch_pending(len(self._pending_batch_imports), self._t)
        else:
            self.ui.playback_tab.set_playlist_editing(
                self._editing_playlist_id is not None, self._t
            )
        self.ui.playback_tab.add_to_playlist_btn.setEnabled(bool(self.selected_tracks_info))

    def _start_batch_playlist_operation(
        self, kind: str, entries: list[dict], base_config: dict,
        apply_mode: str = "all", changed_keys: set[str] | None = None,
    ) -> None:
        if not entries:
            return
        if self.playback_controller.is_playing() or self.playback_controller.is_paused():
            QMessageBox.warning(
                self, self._t("Playlist Error"),
                self._t("Stop playback before starting a batch playlist operation."),
            )
            return
        self._batch_playlist_operation = {
            "kind": kind,
            "entries": list(entries),
            "index": 0,
            "base_config": copy.deepcopy(base_config),
            "apply_mode": str(apply_mode or "all"),
            "changed_keys": sorted(set(changed_keys or set())),
            "successes": [],
            "failures": [],
            "last_id": None,
        }
        self._batch_progress_dialog = QProgressDialog(
            self._t("Preparing batch playlist operation…"), "", 0, len(entries), self
        )
        self._batch_progress_dialog.setWindowTitle(
            self._t("Batch Add to Playlist" if kind == "add" else "Batch Modify Songs")
        )
        self._batch_progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._batch_progress_dialog.setCancelButton(None)
        self._batch_progress_dialog.setMinimumDuration(0)
        self._batch_progress_dialog.setAutoClose(False)
        self._batch_progress_dialog.show()
        self.ui.playback_tab.add_to_playlist_btn.setEnabled(False)
        self._process_next_batch_playlist_entry()

    def _process_next_batch_playlist_entry(self) -> None:
        operation = self._batch_playlist_operation
        if not operation:
            return
        index = int(operation["index"])
        entries = operation["entries"]
        if index >= len(entries):
            self._finish_batch_playlist_operation()
            return
        entry = entries[index]
        path = str(entry.get("path") or "")
        name = str(entry.get("name") or os.path.basename(path) or self._t("Unknown MIDI"))
        if self._batch_progress_dialog:
            self._batch_progress_dialog.setValue(index)
            self._batch_progress_dialog.setLabelText(
                self._t("Processing {current}/{total}: {name}").format(
                    current=index + 1, total=len(entries), name=name
                )
            )
        QApplication.processEvents()

        try:
            if not path or not os.path.exists(path):
                raise FileNotFoundError(self._t("The original MIDI file is unavailable."))
            selected_tracks = list(entry.get("selected_tracks") or [])
            if not selected_tracks:
                raise ValueError(self._t("No tracks selected"))
            if (operation["kind"] == "edit"
                    and operation.get("apply_mode") == "changed"):
                song_data = entry.get("song_data", {})
                config = self._effective_playlist_config(
                    str(entry.get("item_id") or ""),
                    song_data if isinstance(song_data, dict) else {},
                    path,
                )
                for key in operation.get("changed_keys", []):
                    if key in operation["base_config"]:
                        config[key] = copy.deepcopy(operation["base_config"][key])
            else:
                config = copy.deepcopy(operation["base_config"])
            config["midi_file"] = path
            if "midi_clip_invalid_data" in entry:
                config["midi_clip_invalid_data"] = bool(
                    entry.get("midi_clip_invalid_data", False)
                )

            # Auto Trim is resolved per MIDI, not copied from the preview song.
            # Persisting the detected range also makes later editing show the
            # correct bounds for each individual playlist item.
            if bool(config.get("trim_enabled")) and bool(config.get("trim_auto")):
                trim_start, trim_end = selected_track_bounds(
                    selected_tracks, float(config.get("tempo", 100.0) or 100.0)
                )
                config["trim_start_seconds"] = float(trim_start)
                config["trim_end_seconds"] = float(trim_end)

            if (config.get("humanization_mode") != "disabled"
                    and config.get("humanization_seed_mode") == "fixed_random"):
                basis = self._humanization_basis(config)
                existing_settings = {}
                if operation["kind"] == "edit":
                    song_data = entry.get("song_data", {})
                    if isinstance(song_data, dict):
                        existing_settings = song_data.get("playback_settings", {})
                    if not isinstance(existing_settings, dict):
                        existing_settings = {}
                existing_seed = existing_settings.get("humanization_seed")
                same_fixed_performance = (
                    existing_settings.get("humanization_mode") == config.get("humanization_mode")
                    and existing_settings.get("humanization_seed_mode") == "fixed_random"
                    and existing_settings.get("humanization_seed_basis") == basis
                    and isinstance(existing_seed, int)
                )
                # New songs receive their own stable seed. Existing songs keep
                # theirs until a simulated-performance option changes.
                config["humanization_seed"] = (
                    int(existing_seed) if same_fixed_performance
                    else random.SystemRandom().randint(1, 2_147_483_647)
                )
                config["humanization_seed_basis"] = basis
            context = {
                "action": "batch",
                "kind": operation["kind"],
                "entry": entry,
                "config": config,
                "midi_path": path,
                "selected_tracks": selected_tracks,
                "original_filename": str(entry.get("original_filename") or os.path.basename(path)),
                "duration_hint": self._playlist_duration_hint(config, selected_tracks),
            }
        except Exception as exc:
            operation["failures"].append({"name": name, "reason": str(exc)})
            operation["index"] = index + 1
            QTimer.singleShot(0, self._process_next_batch_playlist_entry)
            return

        if self._playlist_config_uses_dynamic_seed(config):
            self._commit_batch_playlist_entry(context, None)
            return

        self._playlist_compile_context = context
        self._playlist_compile_in_progress = True
        started = self.playback_controller.compile_for_playlist(
            config, selected_tracks, context["original_filename"]
        )
        if not started:
            self._playlist_compile_context = None
            self._playlist_compile_in_progress = False
            operation["failures"].append({
                "name": name, "reason": self._t("Another compilation is already running")
            })
            operation["index"] = index + 1
            QTimer.singleShot(0, self._process_next_batch_playlist_entry)

    def _commit_batch_playlist_entry(self, context: dict, playback_data: dict | None) -> None:
        operation = self._batch_playlist_operation
        if not operation:
            return
        entry = context["entry"]
        name = str(entry.get("name") or os.path.basename(context["midi_path"]))
        try:
            if context["kind"] == "edit":
                item = self.playlist_manager.update_song(
                    str(entry["item_id"]), context["midi_path"], context["config"],
                    context["selected_tracks"], playback_data,
                    duration_hint=context.get("duration_hint"),
                )
            else:
                item = self.playlist_manager.add_song(
                    context["midi_path"], context["config"],
                    context["selected_tracks"], playback_data,
                    name=entry.get("name"),
                    duration_hint=context.get("duration_hint"),
                )
            operation["successes"].append(str(item.get("name") or name))
            operation["last_id"] = str(item.get("id") or "")
        except Exception as exc:
            operation["failures"].append({"name": name, "reason": str(exc)})
        operation["index"] = int(operation["index"]) + 1
        self._playlist_compile_context = None
        self._playlist_compile_in_progress = False
        QTimer.singleShot(0, self._process_next_batch_playlist_entry)

    def _finish_batch_playlist_operation(self) -> None:
        operation = self._batch_playlist_operation
        if not operation:
            return
        if self._batch_progress_dialog:
            self._batch_progress_dialog.setValue(len(operation["entries"]))
            self._batch_progress_dialog.close()
        successes = list(operation["successes"])
        failures = list(operation["failures"])
        last_id = operation.get("last_id")
        kind = operation.get("kind")
        self._batch_playlist_operation = None
        self._batch_progress_dialog = None
        self._playlist_compile_context = None
        self._playlist_compile_in_progress = False
        self.ui.playback_tab.end_batch_change_tracking()
        self._pending_batch_imports = []
        self._batch_edit_entries = []
        self._batch_edit_baseline_config = None
        self._editing_playlist_id = None
        self.selected_tracks_info = None
        self.loaded_save_data = None
        self.loaded_save_filename = None
        self.current_playlist_id = str(last_id) if last_id else None
        self.ui.update_file_label(self._t("No file selected."), "")
        self.ui._set_save_enabled(False)
        self.ui.scrubber_slider.setEnabled(False)
        self.ui.playback_tab.set_playlist_editing(False, self._t)
        self._refresh_playlist(last_id)
        self.ui.tabs.setCurrentIndex(1)
        self._reset_playlist_commit_button()

        box = QMessageBox(self)
        box.setWindowTitle(self._t("Batch Add to Playlist" if kind == "add" else "Batch Modify Songs"))
        box.setIcon(QMessageBox.Icon.Information if not failures else QMessageBox.Icon.Warning)
        box.setText(self._t("Batch operation completed: {success} succeeded, {failed} failed.").format(
            success=len(successes), failed=len(failures)
        ))
        details = [self._t("Succeeded:")]
        details.extend(f"  ✓ {value}" for value in successes)
        details.append("")
        details.append(self._t("Failed:"))
        details.extend(f"  ✗ {value['name']}: {value['reason']}" for value in failures)
        box.setDetailedText("\n".join(details))
        box.exec()

    @staticmethod
    def _batch_changed_keys(before: dict | None, after: dict) -> set[str]:
        before = dict(before or {})
        ignored = {"midi_file"}
        keys = (set(before) | set(after)) - ignored
        changed = set()
        for key in keys:
            left = json.dumps(before.get(key), ensure_ascii=False, sort_keys=True, default=str)
            right = json.dumps(after.get(key), ensure_ascii=False, sort_keys=True, default=str)
            if left != right:
                changed.add(key)
        return changed

    def _choose_batch_edit_apply_mode(
        self, current_config: dict
    ) -> tuple[str, set[str]] | None:
        # Prefer explicit control interactions over a final-value comparison.
        # This matters when the preview song already uses Auto Trim: toggling
        # Auto off and back on is still an intentional request to apply Auto
        # Trim independently to every selected MIDI.
        touched_keys = self.ui.playback_tab.batch_changed_keys()
        changed_keys = set(touched_keys)

        # Enabling automatic trim is a paired operation.  Apply both switches
        # whenever either trim-mode control was touched, while each song still
        # calculates its own first/last playable note during compilation.
        trim_mode_touched = bool(
            {"trim_enabled", "trim_auto"} & touched_keys
        )
        if trim_mode_touched:
            changed_keys.add("trim_enabled")
            if bool(current_config.get("trim_enabled")):
                changed_keys.add("trim_auto")

        box = QMessageBox(self)
        box.setWindowTitle(self._t("Complete Batch Modification"))
        box.setIcon(QMessageBox.Icon.Question)
        box.setText(self._t("Choose how to apply the batch modification."))
        changed_button = box.addButton(
            self._t("Only Apply Changed Values"), QMessageBox.ButtonRole.AcceptRole
        )
        all_button = box.addButton(
            self._t("Apply All Values"), QMessageBox.ButtonRole.ActionRole
        )
        cancel_button = box.addButton(QMessageBox.StandardButton.Cancel)

        # QMessageBox uses a compact platform default width that can clip the
        # Chinese label. Size each button from its actual translated text.
        for button, minimum in (
            (changed_button, 176), (all_button, 132), (cancel_button, 96)
        ):
            text_width = button.fontMetrics().horizontalAdvance(button.text())
            button.setMinimumWidth(max(minimum, text_width + 36))

        box.exec()
        clicked = box.clickedButton()
        if clicked == changed_button:
            if not changed_keys:
                QMessageBox.information(
                    self, self._t("Complete Batch Modification"),
                    self._t("No playback setting has changed."),
                )
                return None
            return "changed", changed_keys
        if clicked == all_button:
            return "all", set(current_config) - {"midi_file"}
        return None

    def add_current_to_playlist(self):
        """Add a new song or finish editing the currently selected playlist song."""
        if self._pending_batch_imports:
            self._start_batch_playlist_operation(
                "add", self._pending_batch_imports, self.ui.gather_playback_config()
            )
            return
        if self._batch_edit_entries:
            current_config = self.ui.gather_playback_config()
            choice = self._choose_batch_edit_apply_mode(current_config)
            if choice is None:
                return
            apply_mode, changed_keys = choice
            self._start_batch_playlist_operation(
                "edit", self._batch_edit_entries, current_config,
                apply_mode=apply_mode, changed_keys=changed_keys,
            )
            return
        editing = self._editing_playlist_id is not None
        title = self._t("Complete Modification" if editing else "Add to Playlist")
        if self.playback_controller.is_playing() or self.playback_controller.is_paused():
            QMessageBox.warning(
                self, title,
                self._t("Stop playback before saving this song to the playlist."),
            )
            return
        if not self.selected_tracks_info:
            QMessageBox.warning(
                self, self._t("No Tracks"),
                self._t("Please select a MIDI file and choose tracks first."),
            )
            return
        config = self.ui.gather_playback_config()
        if (config.get("humanization_mode") != "disabled"
                and config.get("humanization_seed_mode") == "fixed_random"):
            config["humanization_seed_basis"] = self._humanization_basis(config)
        midi_path = str(config.get("midi_file") or "")
        if not midi_path or not os.path.exists(midi_path):
            QMessageBox.warning(
                self, title,
                self._t("The selected MIDI file can no longer be found."),
            )
            return

        original_filename = os.path.basename(midi_path)
        if editing and self._editing_playlist_id:
            try:
                edited_song = self.playlist_manager.get_song_data(self._editing_playlist_id)
                original_filename = str(
                    edited_song.get("source", {}).get("original_filename")
                    or original_filename
                )
            except Exception:
                pass
        context = {
            "action": "edit" if editing else "add",
            "item_id": self._editing_playlist_id,
            "config": copy.deepcopy(config),
            "midi_path": midi_path,
            "selected_tracks": list(self.selected_tracks_info),
            "original_filename": original_filename,
            "duration_hint": self._playlist_duration_hint(config, self.selected_tracks_info),
        }

        # Dynamic seeds intentionally compile on every performance. The playlist
        # stores the MIDI + settings, but no stale compiled cache is required.
        if self._playlist_config_uses_dynamic_seed(config):
            self._playlist_compile_context = context
            self._complete_playlist_commit(None)
            return

        self._playlist_compile_context = context
        self._playlist_compile_in_progress = True
        self.ui.playback_tab.add_to_playlist_btn.setEnabled(False)
        self.ui.playback_tab.add_to_playlist_btn.setText(self._t("Compiling..."))
        started = self.playback_controller.compile_for_playlist(
            config, self.selected_tracks_info, context["original_filename"]
        )
        if not started:
            self._playlist_compile_context = None
            self._reset_playlist_commit_button()

    def _complete_playlist_commit(self, playback_data: dict | None):
        context = self._playlist_compile_context
        self._playlist_compile_context = None
        if not context:
            self._reset_playlist_commit_button()
            return
        try:
            if context["action"] == "edit":
                item = self.playlist_manager.update_song(
                    str(context["item_id"]),
                    context["midi_path"],
                    context["config"],
                    context["selected_tracks"],
                    playback_data,
                    duration_hint=context.get("duration_hint"),
                )
                message = self._t("The playlist song was modified successfully.")
                box_title = self._t("Complete Modification")
            else:
                item = self.playlist_manager.add_song(
                    context["midi_path"],
                    context["config"],
                    context["selected_tracks"],
                    playback_data,
                    duration_hint=context.get("duration_hint"),
                )
                message = self._t("The song was added to the playlist successfully.")
                box_title = self._t("Add to Playlist")
        except Exception as exc:
            QMessageBox.critical(self, self._t("Playlist Error"), self._t(str(exc)))
            self._reset_playlist_commit_button()
            return

        self.current_playlist_id = item["id"]
        self._editing_playlist_id = None
        self.loaded_save_data = None
        self._refresh_playlist(item["id"])
        self.ui.playback_tab.set_playlist_editing(False, self._t)
        self.ui.tabs.setCurrentIndex(1)
        QMessageBox.information(self, box_title, message)
        self._reset_playlist_commit_button()

    def _on_playlist_compile_successful(self, playback_data: dict):
        self._playlist_compile_in_progress = False
        context = self._playlist_compile_context or {}
        if context.get("action") == "batch":
            self._playlist_compile_context = None
            self._commit_batch_playlist_entry(context, playback_data)
            return
        if context.get("action") == "play":
            self._playlist_compile_context = None
            item_id = str(context.get("item_id") or "")
            if context.get("cache_result") and item_id:
                try:
                    self.playlist_manager.cache_playback(item_id, playback_data)
                    self._refresh_playlist(item_id)
                except Exception as exc:
                    self.ui.log_output.append(self._t("Could not update playlist cache: ") + str(exc))
            self._play_compiled_playlist_data(item_id, playback_data)
            self._reset_playlist_commit_button()
            return
        self._complete_playlist_commit(playback_data)

    def _on_playlist_compile_failed(self, error_message: str):
        context = self._playlist_compile_context or {}
        self._playlist_compile_context = None
        self._playlist_compile_in_progress = False
        if context.get("action") == "batch":
            operation = self._batch_playlist_operation
            if operation:
                entry = context.get("entry", {})
                name = str(entry.get("name") or os.path.basename(str(context.get("midi_path") or "")))
                operation["failures"].append({"name": name, "reason": error_message})
                operation["index"] = int(operation["index"]) + 1
                QTimer.singleShot(0, self._process_next_batch_playlist_entry)
            return
        if context.get("action") == "play":
            self._playlist_session_active = False
        self._reset_playlist_commit_button()
        QMessageBox.critical(
            self, self._t("Playlist Error"),
            self._t("Could not compile this song for the playlist:") + f"\n{error_message}",
        )

    def play_playlist_item(self, item_id: str):
        if self._playlist_compile_in_progress:
            return
        if not self.playlist_manager.get_metadata(item_id):
            return
        self._playlist_session_active = True
        if self.playback_controller.is_playing() or self.playback_controller.is_paused():
            self._pending_playlist_item_id = item_id
            self.playback_controller.stop()
            return
        self._start_playlist_item(item_id)

    def _effective_playlist_config(self, item_id: str, song_data: dict, midi_path: str | None = None) -> dict:
        config = copy.deepcopy(song_data.get("playback_settings", {}))
        if midi_path:
            config["midi_file"] = midi_path
        else:
            config.pop("midi_file", None)
        config["use_ai_pedal"] = self.ui.settings_tab.use_ai_pedal_check.isChecked()
        mode = str(config.get("humanization_mode", "individual"))
        if mode == "global":
            config.update(self.ui.settings_tab.global_humanization_config())
            config["humanization_mode"] = "global"
        elif mode == "disabled":
            for key in (
                "simulate_hands", "enable_chord_roll", "vary_timing",
                "vary_articulation", "enable_drift_correction", "enable_mistakes",
                "enable_tempo_sway", "invert_tempo_sway",
            ):
                config[key] = False
            config["humanization_seed"] = None
        if mode != "disabled":
            if config.get("humanization_seed_mode") == "dynamic":
                config["humanization_seed"] = None
            elif config.get("humanization_seed_mode") == "fixed_random":
                basis = self._humanization_basis(config)
                if config.get("humanization_seed_basis") != basis:
                    config["humanization_seed"] = random.SystemRandom().randint(1, 2_147_483_647)
                    config["humanization_seed_basis"] = basis
                    self.playlist_manager.update_playback_settings(item_id, config, clear_cache=True)
        return config

    def _restore_playlist_tracks(self, midi_path: str, song_data: dict):
        settings = song_data.get("playback_settings", {})
        if not isinstance(settings, dict):
            settings = {}
        tracks, tempo_map = MidiParser.parse_structure(
            midi_path,
            1.0,
            None,
            clip_invalid_data=bool(settings.get("midi_clip_invalid_data", False)),
        )
        selection = song_data.get("selected_tracks", [])
        role_map = {
            int(raw.get("index")): str(raw.get("role") or "Auto-Detect")
            for raw in selection if isinstance(raw, dict) and "index" in raw
        }
        if role_map:
            selected = [(track, role_map[track.index]) for track in tracks if track.index in role_map]
        else:
            selected = [(track, "Auto-Detect") for track in tracks if not track.is_drum]
        return selected, tempo_map

    def _start_playlist_item(self, item_id: str):
        metadata = self.playlist_manager.get_metadata(item_id)
        if not metadata:
            return
        try:
            song_data = self.playlist_manager.get_song_data(item_id)
        except Exception as exc:
            self._playlist_session_active = False
            QMessageBox.critical(
                self, self._t("Missing Song"),
                self._t("The selected playlist item could not be loaded:") + f"\n{self._t(str(exc))}",
            )
            return

        source = song_data.get("source", {}) if isinstance(song_data, dict) else {}
        if str(source.get("type") or "midi") == "sheet":
            self._start_sheet_playlist_item(item_id, metadata, song_data)
            return

        midi_path = self.playlist_manager.get_midi_path(item_id)
        legacy_cache_only = bool(song_data.get("legacy_cache_only"))
        if legacy_cache_only and not midi_path:
            try:
                cached = self.playlist_manager.get_playback_data(item_id)
            except Exception as exc:
                self._playlist_session_active = False
                QMessageBox.critical(self, self._t("Missing Song"), str(exc))
                return
            self._play_compiled_playlist_data(item_id, cached)
            return
        if not midi_path:
            self._playlist_session_active = False
            QMessageBox.critical(
                self, self._t("Missing Song"),
                self._t("The original MIDI file for this playlist song is unavailable."),
            )
            return

        try:
            selected_tracks, tempo_map = self._restore_playlist_tracks(midi_path, song_data)
        except Exception as exc:
            self._playlist_session_active = False
            QMessageBox.critical(
                self, self._t("Missing Song"),
                self._t("Failed to parse MIDI:") + f"\n{exc}",
            )
            return
        if not selected_tracks:
            self._playlist_session_active = False
            QMessageBox.warning(self, self._t("No Tracks"), self._t("No stored playable tracks were found."))
            return

        config = self._effective_playlist_config(item_id, song_data, midi_path)
        dynamic = self._playlist_config_uses_dynamic_seed(config)
        cached = None
        if not dynamic:
            try:
                candidate = self.playlist_manager.get_playback_data(item_id)
                if cache_matches_config(candidate, config):
                    cached = candidate
            except Exception:
                cached = None
        if cached is not None:
            self._play_compiled_playlist_data(item_id, cached)
            return

        self.current_playlist_id = item_id
        self.ui.playlist_tab.select_id(item_id)
        self.ui.refresh_collapsed_playlist(self.playlist_manager.items(), item_id)
        self._set_playback_status(str(metadata.get("name") or metadata.get("source_midi_filename")), "playlist")
        self.ui.log_output.append(self._t("Compiling playlist performance..."))
        self._playlist_compile_context = {
            "action": "play",
            "item_id": item_id,
            "config": config,
            "selected_tracks": selected_tracks,
            "cache_result": not dynamic,
        }
        self._playlist_compile_in_progress = True
        started = self.playback_controller.compile_for_playlist(
            config, selected_tracks,
            str(metadata.get("source_midi_filename") or os.path.basename(midi_path)),
        )
        if not started:
            self._playlist_compile_context = None
            self._playlist_compile_in_progress = False
            self._playlist_session_active = False

    def _start_sheet_playlist_item(self, item_id: str, metadata: dict, song_data: dict) -> None:
        source = self.playlist_manager.get_sheet_source(item_id)
        if not source:
            self._playlist_session_active = False
            QMessageBox.critical(
                self, self._t("Missing Song"),
                self._t("The text sheet for this playlist song is unavailable."),
            )
            return
        format_name = str(source.get("format_name") or "")
        fmt = FormatRegistry.get(format_name)
        if not fmt:
            self._playlist_session_active = False
            QMessageBox.critical(
                self, self._t("Unknown Format"),
                self._t("No handler found for format: {format_name}").format(format_name=format_name),
            )
            return
        config = self._effective_playlist_config(item_id, song_data, None)
        use_88 = bool(config.get("use_88_key_layout", False))
        key_mapper = KeyMapper(use_88_key_layout=use_88)
        bpm = max(20, min(400, int(source.get("bpm", 120) or 120)))
        try:
            notes = fmt.parse(str(source.get("sheet_text") or ""), float(bpm), key_mapper)
        except Exception as exc:
            self._playlist_session_active = False
            QMessageBox.critical(
                self, self._t("Parse Error"),
                self._t("Failed to parse sheet:") + f"\n{exc}",
            )
            return
        if not notes:
            self._playlist_session_active = False
            QMessageBox.warning(
                self, self._t("No Notes"),
                self._t("No playable notes were found in the pasted sheet."),
            )
            return

        tempo_map = TempoMap([(0, int(60_000_000 / bpm))], [])
        self.current_playlist_id = item_id
        self.loaded_save_data = None
        self.loaded_save_filename = None
        self.selected_tracks_info = None
        self.ui.playlist_tab.select_id(item_id)
        self.ui.refresh_collapsed_playlist(self.playlist_manager.items(), item_id)
        title = str(metadata.get("name") or self._t("Text Sheet"))
        self._set_playback_status(title, "playlist")
        self.playback_controller.play_from_notes(config, notes, tempo_map)
        self.ui.set_controls_enabled(False)
        self.ui.play_button.setEnabled(True)
        self.ui.stop_button.setEnabled(True)
        self.ui.scrubber_slider.setEnabled(True)
        self._sync_play_button()
        if self.ui._nav_btns[2].isEnabled():
            self.ui.tabs.setCurrentIndex(2)

    def _play_compiled_playlist_data(self, item_id: str, data: dict):
        metadata = self.playlist_manager.get_metadata(item_id)
        if not metadata:
            return
        self.current_playlist_id = item_id
        self.loaded_save_data = data
        self.loaded_save_filename = str(metadata.get("name") or metadata.get("source_midi_filename"))
        self.selected_tracks_info = None
        self.ui.update_file_label(
            self.loaded_save_filename,
            str(metadata.get("source_midi_filename", self.loaded_save_filename)),
        )
        self.ui.playback_tab.playback_group.setEnabled(False)
        self.ui.playback_tab.humanization_group.setEnabled(False)
        self.ui.playback_tab.add_to_playlist_btn.setEnabled(False)
        self.ui._set_save_enabled(False)
        self.ui.play_button.setEnabled(True)
        self.ui.scrubber_slider.setEnabled(True)
        self.ui.playlist_tab.select_id(item_id)
        self.ui.refresh_collapsed_playlist(self.playlist_manager.items(), item_id)
        title = str(metadata.get('name') or metadata.get('source_midi_filename') or self._t("Unknown MIDI"))
        self._set_playback_status(title, "playlist")
        self.playback_controller.play_from_save(data)
        self.ui.set_controls_enabled(False, True)
        self.ui.play_button.setEnabled(True)
        self.ui.stop_button.setEnabled(True)
        self._sync_play_button()
        if self.ui._nav_btns[2].isEnabled():
            self.ui.tabs.setCurrentIndex(2)

    def play_previous_playlist_item(self):
        target = self._adjacent_playlist_id(-1, wrap=True)
        if target:
            self.play_playlist_item(target)

    def play_next_playlist_item(self):
        mode = self.ui.playlist_tab.current_mode()
        if mode == 'shuffle':
            target = self._random_playlist_id()
        else:
            target = self._adjacent_playlist_id(1, wrap=True)
        if target:
            self.play_playlist_item(target)

    def _adjacent_playlist_id(self, step: int, wrap: bool) -> str | None:
        items = self.playlist_manager.items()
        if not items:
            return None
        ids = [str(item['id']) for item in items]
        anchor = (
            self.ui.collapsed_selected_playlist_id()
            if self.ui._is_collapsed
            else None
        ) or self.current_playlist_id or self.ui.playlist_tab.selected_id()
        try:
            index = ids.index(anchor) if anchor else (0 if step < 0 else -1)
        except ValueError:
            index = -1
        target_index = index + step
        if wrap:
            target_index %= len(ids)
        elif target_index < 0 or target_index >= len(ids):
            return None
        return ids[target_index]

    def _random_playlist_id(self) -> str | None:
        ids = [str(item['id']) for item in self.playlist_manager.items()]
        if not ids:
            return None
        choices = [item_id for item_id in ids if item_id != self.current_playlist_id]
        return random.choice(choices or ids)

    def _automatic_next_playlist_id(self) -> str | None:
        mode = self.ui.playlist_tab.current_mode()
        if mode == 'single':
            return None
        if mode == 'single_repeat':
            return self.current_playlist_id
        if mode == 'shuffle':
            return self._random_playlist_id()
        if mode == 'repeat_all':
            return self._adjacent_playlist_id(1, wrap=True)
        if mode == 'sequential':
            return self._adjacent_playlist_id(1, wrap=False)
        return None

    def reorder_playlist(self, ordered_ids: list[str]) -> None:
        selected = self.ui.playlist_tab.selected_ids()
        try:
            self.playlist_manager.reorder(list(ordered_ids))
        except Exception as exc:
            QMessageBox.critical(self, self._t("Playlist Error"), str(exc))
            return
        self.ui.playlist_tab.refresh(
            self.playlist_manager.items(), selected_ids=selected
        )

    def _midi_only_selection(self, item_ids: list[str], title: str) -> list[str]:
        unique_ids = list(dict.fromkeys(str(value) for value in item_ids))
        midi_ids = []
        sheet_count = 0
        for item_id in unique_ids:
            metadata = self.playlist_manager.get_metadata(item_id) or {}
            if str(metadata.get("source_type") or "midi") == "sheet":
                sheet_count += 1
            else:
                midi_ids.append(item_id)
        if not sheet_count:
            return midi_ids
        if not midi_ids:
            QMessageBox.information(
                self, self._t(title),
                self._t("The selected songs are all text sheets and do not support this operation."),
            )
            return []

        box = QMessageBox(self)
        box.setWindowTitle(self._t(title))
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText(self._t("Some selected songs are text sheets and do not support this operation."))
        process_button = box.addButton(
            self._t("Only Process MIDI"), QMessageBox.ButtonRole.AcceptRole
        )
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.exec()
        return midi_ids if box.clickedButton() == process_button else []

    def edit_playlist_items(self, item_ids: list[str]) -> None:
        unique_ids = self._midi_only_selection(item_ids, "Batch Modify Songs")
        if len(unique_ids) < 2:
            if unique_ids:
                self.edit_playlist_item(unique_ids[0])
            return
        if self.playback_controller.is_playing() or self.playback_controller.is_paused():
            QMessageBox.warning(
                self, self._t("Batch Modify Songs"),
                self._t("Stop playback before modifying playlist songs."),
            )
            return
        if (self._batch_edit_prepare_thread is not None
                and self._batch_edit_prepare_thread.isRunning()):
            return

        descriptors = []
        initial_failures = []
        for item_id in unique_ids:
            metadata = self.playlist_manager.get_metadata(item_id)
            if not metadata:
                initial_failures.append(str(item_id))
                continue
            try:
                song_data = self.playlist_manager.get_song_data(item_id)
                midi_path = self.playlist_manager.get_midi_path(item_id)
                if not midi_path:
                    raise FileNotFoundError(
                        self._t("The original MIDI file is unavailable.")
                    )
            except Exception as exc:
                initial_failures.append(
                    f"{metadata.get('name', item_id)}: {exc}"
                )
                continue
            descriptors.append({
                "item_id": item_id,
                "metadata": metadata,
                "song_data": song_data,
                "path": midi_path,
            })

        if not descriptors:
            QMessageBox.critical(
                self, self._t("Batch Modify Songs"),
                self._t("None of the selected songs can be modified.")
                + ("\n" + "\n".join(initial_failures)
                   if initial_failures else ""),
            )
            return

        self._batch_edit_prepare_initial_failures = list(initial_failures)
        self._batch_edit_prepare_cancel_event = threading.Event()
        self._batch_edit_prepare_progress = QProgressDialog(
            self._t("Preparing songs for batch modification…"),
            self._t("Cancel"), 0, len(descriptors), self,
        )
        self._batch_edit_prepare_progress.setWindowTitle(
            self._t("Batch Modify Songs")
        )
        self._batch_edit_prepare_progress.setWindowModality(
            Qt.WindowModality.WindowModal
        )
        self._batch_edit_prepare_progress.setMinimumDuration(0)
        self._batch_edit_prepare_progress.setAutoClose(False)
        self._batch_edit_prepare_progress.setValue(0)
        self._batch_edit_prepare_progress.canceled.connect(
            self._batch_edit_prepare_cancel_event.set
        )

        self._batch_edit_prepare_thread = QThread(self)
        self._batch_edit_prepare_worker = BatchPlaylistEditPrepareWorker(
            descriptors,
            self._batch_edit_prepare_cancel_event,
            self._t("The original MIDI file is unavailable."),
            self._t("No stored playable tracks were found."),
        )
        self._batch_edit_prepare_worker.moveToThread(
            self._batch_edit_prepare_thread
        )
        self._batch_edit_prepare_thread.started.connect(
            self._batch_edit_prepare_worker.run
        )
        self._batch_edit_prepare_worker.progress.connect(
            self._update_batch_edit_prepare_progress
        )
        self._batch_edit_prepare_worker.prepared.connect(
            self._on_batch_edit_prepare_ready
        )
        self._batch_edit_prepare_worker.finished.connect(
            self._batch_edit_prepare_thread.quit
        )
        self._batch_edit_prepare_worker.finished.connect(
            self._batch_edit_prepare_worker.deleteLater
        )
        self._batch_edit_prepare_thread.finished.connect(
            self._cleanup_batch_edit_prepare
        )
        self._batch_edit_prepare_thread.finished.connect(
            self._batch_edit_prepare_thread.deleteLater
        )
        self._batch_edit_prepare_progress.show()
        self._batch_edit_prepare_thread.start()

    def _update_batch_edit_prepare_progress(
        self, current: int, total: int, name: str
    ) -> None:
        progress = self._batch_edit_prepare_progress
        if progress is None:
            return
        progress.setMaximum(max(1, int(total)))
        progress.setValue(max(0, int(current) - 1))
        progress.setLabelText(
            self._t("Reading {current}/{total}: {name}").format(
                current=current, total=total, name=name
            )
        )

    def _on_batch_edit_prepare_ready(
        self, entries: list[dict], failures: list[str], canceled: bool
    ) -> None:
        progress = self._batch_edit_prepare_progress
        if progress is not None:
            progress.setValue(progress.maximum())
            progress.close()
        all_failures = [
            *self._batch_edit_prepare_initial_failures,
            *list(failures or []),
        ]
        if canceled:
            QMessageBox.information(
                self, self._t("Batch Modify Songs"),
                self._t("Batch modification preparation was canceled."),
            )
            return
        self._enter_batch_edit_mode(list(entries or []), all_failures)

    def _cleanup_batch_edit_prepare(self) -> None:
        self._batch_edit_prepare_thread = None
        self._batch_edit_prepare_worker = None
        self._batch_edit_prepare_progress = None
        self._batch_edit_prepare_cancel_event = None
        self._batch_edit_prepare_initial_failures = []

    def _enter_batch_edit_mode(
        self, entries: list[dict], failures: list[str]
    ) -> None:
        if not entries:
            QMessageBox.critical(
                self, self._t("Batch Modify Songs"),
                self._t("None of the selected songs can be modified.")
                + ("\n" + "\n".join(failures) if failures else ""),
            )
            return
        if failures:
            QMessageBox.warning(
                self, self._t("Batch Modify Songs"),
                self._t("Some selected songs were skipped:")
                + "\n" + "\n".join(failures),
            )

        first = entries[0]
        first_config = self._effective_playlist_config(
            first["item_id"], first["song_data"], first["path"]
        )
        self._pending_batch_imports = []
        self._editing_playlist_id = None
        self._batch_edit_entries = entries
        self._playlist_session_active = False
        self.current_playlist_id = None
        self.loaded_save_data = None
        self.loaded_save_filename = None
        self.selected_tracks_info = first["selected_tracks"]
        self.parsed_tempo_map = first["tempo_map"]
        self.ui.playback_tab.end_batch_change_tracking()
        self.ui.playback_tab.load_song_config(
            first_config, self.ui.settings_tab.global_humanization_config()
        )
        self._sync_trim_bounds(first["selected_tracks"])
        self.ui.update_file_label(
            self._t("Batch modifying {count} songs (previewing {name})").format(
                count=len(entries), name=first["name"]
            ),
            first["path"],
        )
        self._batch_edit_baseline_config = copy.deepcopy(
            self.ui.gather_playback_config()
        )
        self.ui.playback_tab.begin_batch_change_tracking()
        self.ui.playback_tab.playback_group.setEnabled(True)
        self.ui.playback_tab.humanization_group.setEnabled(True)
        self.ui.playback_tab.file_group.setEnabled(True)
        self.ui.playback_tab.set_playlist_batch_editing(len(entries), self._t)
        self.ui.playback_tab.add_to_playlist_btn.setEnabled(True)
        self.ui.play_button.setEnabled(True)
        self.ui.scrubber_slider.setEnabled(True)
        self.ui._set_save_enabled(True)
        self.ui.tabs.setCurrentIndex(0)

    def save_playlist_midis_as(self, item_ids: list[str]) -> None:
        unique_ids = self._midi_only_selection(item_ids, "Batch Save MIDI As")
        if not unique_ids:
            return
        directory = QFileDialog.getExistingDirectory(
            self, self._t("Batch Save MIDI As"), ""
        )
        if not directory:
            return
        progress = QProgressDialog(
            self._t("Saving MIDI files…"), self._t("Cancel"), 0, len(unique_ids), self
        )
        progress.setWindowTitle(self._t("Batch Save MIDI As"))
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()
        successes = []
        failures = []
        used_names: set[str] = set()
        for index, item_id in enumerate(unique_ids, start=1):
            metadata = self.playlist_manager.get_metadata(item_id) or {}
            source_name = str(metadata.get("source_midi_filename") or f"song_{index}.mid")
            progress.setValue(index - 1)
            progress.setLabelText(
                self._t("Saving {current}/{total}: {name}").format(
                    current=index, total=len(unique_ids), name=source_name
                )
            )
            QApplication.processEvents()
            if progress.wasCanceled():
                break
            stem = Path(source_name).stem or f"song_{index}"
            suffix = Path(source_name).suffix or ".mid"
            candidate = f"{stem}{suffix}"
            counter = 2
            while candidate.lower() in used_names or (Path(directory) / candidate).exists():
                candidate = f"{stem} ({counter}){suffix}"
                counter += 1
            used_names.add(candidate.lower())
            destination = str(Path(directory) / candidate)
            try:
                self.playlist_manager.save_midi_as(item_id, destination)
                successes.append(candidate)
            except Exception as exc:
                failures.append(f"{source_name}: {exc}")
        progress.setValue(len(unique_ids))
        progress.close()
        box = QMessageBox(self)
        box.setWindowTitle(self._t("Batch Save MIDI As"))
        box.setIcon(QMessageBox.Icon.Information if not failures else QMessageBox.Icon.Warning)
        box.setText(self._t("Saved {success} MIDI file(s); {failed} failed.").format(
            success=len(successes), failed=len(failures)
        ))
        box.setDetailedText("\n".join([*successes, "", *failures]))
        box.exec()

    def delete_playlist_items(self, item_ids: list[str]) -> None:
        unique_ids = list(dict.fromkeys(str(value) for value in item_ids))
        if not unique_ids:
            return
        reply = QMessageBox.question(
            self, self._t("Batch Delete"),
            self._t("Delete {count} selected songs from the playlist? This cannot be undone.").format(
                count=len(unique_ids)
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if self.current_playlist_id in unique_ids:
            self._playlist_session_active = False
            self._pending_playlist_item_id = None
            if self.playback_controller.is_playing() or self.playback_controller.is_paused():
                self.playback_controller.stop()
            self.current_playlist_id = None
            self.loaded_save_data = None
            self.loaded_save_filename = None
            self.ui.update_file_label(self._t("No file selected."), "")
            self.ui.play_button.setEnabled(False)
            self.ui.scrubber_slider.setEnabled(False)
        if self._editing_playlist_id in unique_ids:
            self._editing_playlist_id = None
        if self._editing_sheet_playlist_id in unique_ids:
            self._editing_sheet_playlist_id = None
            self.ui.translator_tab.set_playlist_editing(False, self._t)
        if any(str(entry.get("item_id")) in unique_ids for entry in self._batch_edit_entries):
            self.ui.playback_tab.end_batch_change_tracking()
            self._batch_edit_entries = []
            self._batch_edit_baseline_config = None
        self.playlist_manager.delete_many(unique_ids)
        self._refresh_playlist()
        self.ui.playback_tab.set_playlist_editing(False, self._t)

    def edit_playlist_item(self, item_id: str):
        if self.playback_controller.is_playing() or self.playback_controller.is_paused():
            QMessageBox.warning(
                self, self._t("Modify Song"),
                self._t("Stop playback before modifying a playlist song."),
            )
            return
        metadata = self.playlist_manager.get_metadata(item_id)
        if not metadata:
            return
        if str(metadata.get("source_type") or "midi") == "sheet":
            self._edit_sheet_playlist_item(item_id, metadata)
            return
        try:
            song_data = self.playlist_manager.get_song_data(item_id)
            midi_path = self.playlist_manager.get_midi_path(item_id)
            if not midi_path:
                raise FileNotFoundError(self._t("The original MIDI file for this playlist song is unavailable."))
            selected_tracks, tempo_map = self._restore_playlist_tracks(midi_path, song_data)
        except Exception as exc:
            QMessageBox.critical(self, self._t("Modify Song"), str(exc))
            return
        if not selected_tracks:
            QMessageBox.warning(self, self._t("No Tracks"), self._t("No stored playable tracks were found."))
            return

        config = self._effective_playlist_config(item_id, song_data, midi_path)
        self.ui.playback_tab.end_batch_change_tracking()
        self._pending_batch_imports = []
        self._batch_edit_entries = []
        self._batch_edit_baseline_config = None
        self._editing_sheet_playlist_id = None
        self.ui.translator_tab.set_playlist_editing(False, self._t)
        self._playlist_session_active = False
        self._pending_playlist_item_id = None
        self._editing_playlist_id = item_id
        self.current_playlist_id = None
        self.loaded_save_data = None
        self.loaded_save_filename = None
        self.selected_tracks_info = selected_tracks
        self.parsed_tempo_map = tempo_map
        self.ui.playback_tab.load_song_config(
            config, self.ui.settings_tab.global_humanization_config()
        )
        self._sync_trim_bounds(selected_tracks)
        self.ui.update_file_label(str(metadata.get("name") or Path(midi_path).name), midi_path)
        self.ui.playback_tab.playback_group.setEnabled(True)
        self.ui.playback_tab.humanization_group.setEnabled(True)
        self.ui.playback_tab.file_group.setEnabled(True)
        self.ui.playback_tab.set_playlist_editing(True, self._t)
        self.ui.playback_tab.add_to_playlist_btn.setEnabled(True)
        self.ui.play_button.setEnabled(True)
        self.ui.scrubber_slider.setEnabled(True)
        self.ui._set_save_enabled(True)
        self.ui.tabs.setCurrentIndex(0)
        self.ui.log_output.append(self._t("Editing playlist song: ") + str(metadata.get("name", "")))

    def _edit_sheet_playlist_item(self, item_id: str, metadata: dict | None = None) -> None:
        metadata = metadata or self.playlist_manager.get_metadata(item_id)
        if not metadata:
            return
        try:
            song_data = self.playlist_manager.get_song_data(item_id)
            source = self.playlist_manager.get_sheet_source(item_id)
            if not source:
                raise FileNotFoundError(self._t("The text sheet for this playlist song is unavailable."))
        except Exception as exc:
            QMessageBox.critical(self, self._t("Modify Song"), str(exc))
            return

        self.ui.playback_tab.end_batch_change_tracking()
        self._pending_batch_imports = []
        self._batch_edit_entries = []
        self._batch_edit_baseline_config = None
        self._editing_playlist_id = None
        self.ui.playback_tab.set_playlist_editing(False, self._t)
        self._editing_sheet_playlist_id = item_id
        self._playlist_session_active = False
        self._pending_playlist_item_id = None
        self.current_playlist_id = None
        self.loaded_save_data = None
        self.loaded_save_filename = None
        self.selected_tracks_info = None
        config = song_data.get("playback_settings", {})
        humanize = str(config.get("humanization_mode", "disabled")) != "disabled"
        self.ui.translator_tab.load_sheet(
            str(source.get("sheet_text") or ""),
            str(source.get("format_name") or "Virtual Piano"),
            int(source.get("bpm", 120) or 120),
            humanize,
            str(metadata.get("name") or ""),
        )
        self.ui.translator_tab.set_playlist_editing(True, self._t)
        self.ui.tabs.setCurrentIndex(3)
        self.ui.log_output.append(
            self._t("Editing playlist sheet: ") + str(metadata.get("name", ""))
        )

    def save_playlist_midi_as(self, item_id: str):
        metadata = self.playlist_manager.get_metadata(item_id)
        if not metadata or str(metadata.get("source_type") or "midi") != "midi":
            return
        source_name = str(metadata.get("source_midi_filename") or "song.mid")
        default_name = source_name if Path(source_name).suffix else f"{source_name}.mid"
        path, _ = QFileDialog.getSaveFileName(
            self,
            self._t("Save MIDI As"),
            default_name,
            f"{self._t('MIDI Files')} (*.mid *.midi);;{self._t('All Files')} (*)",
        )
        if not path:
            return
        if not Path(path).suffix:
            path += ".mid"
        try:
            self.playlist_manager.save_midi_as(item_id, path)
        except Exception as exc:
            QMessageBox.critical(self, self._t("Save MIDI As"), str(exc))
            return
        QMessageBox.information(
            self, self._t("Save MIDI As"),
            self._t("The MIDI file was saved successfully.") + "\n" + path,
        )

    def import_playlist(self):
        path, _ = QFileDialog.getOpenFileName(
            self, self._t("Import Playlist"), "",
            f"HuMidi {self._t('Playlist file')} (*.humidiplaylist *.json);;{self._t('All Files')} (*)",
        )
        if not path:
            return
        try:
            count = self.playlist_manager.import_playlist(path)
        except (OSError, ValueError, PlaylistFormatError) as exc:
            QMessageBox.critical(self, self._t("Import Playlist"), str(exc))
            return
        self._refresh_playlist()
        QMessageBox.information(
            self, self._t("Import Playlist"),
            self._t("Imported {count} playlist item(s).").format(count=count),
        )

    def export_playlist(self):
        if self._export_thread and self._export_thread.isRunning():
            return
        choice = QMessageBox(self)
        choice.setWindowTitle(self._t("Export Playlist"))
        choice.setText(self._t("Choose how to export the playlist."))
        choice.setInformativeText(self._t(
            "Normal export stores MIDI paths plus all song parameters, track choices, seeds, and self-contained text sheets. "
            "Complete export additionally embeds the original MIDI files and compiled caches."
        ))
        normal_btn = choice.addButton(self._t("Normal Export"), QMessageBox.ButtonRole.AcceptRole)
        complete_btn = choice.addButton(self._t("Complete Export"), QMessageBox.ButtonRole.ActionRole)
        choice.addButton(QMessageBox.StandardButton.Cancel)
        choice.exec()
        clicked = choice.clickedButton()
        if clicked not in (normal_btn, complete_btn):
            return
        complete = clicked == complete_btn

        default_name = "HuMidi_Xingkong_Playlist.humidiplaylist"
        path, _ = QFileDialog.getSaveFileName(
            self, self._t("Export Playlist"), default_name,
            f"HuMidi {self._t('Playlist file')} (*.humidiplaylist);;{self._t('All Files')} (*)",
        )
        if not path:
            return
        if not os.path.splitext(path)[1]:
            path += ".humidiplaylist"

        total = max(1, len(self.playlist_manager.items()))
        self._export_progress_dialog = QProgressDialog(
            self._t("Exporting playlist…"), "", 0, total, self
        )
        self._export_progress_dialog.setWindowTitle(self._t("Export Playlist"))
        self._export_progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._export_progress_dialog.setCancelButton(None)
        self._export_progress_dialog.setMinimumDuration(0)
        self._export_progress_dialog.setAutoClose(False)
        self._export_progress_dialog.show()

        self._export_thread = QThread(self)
        self._export_worker = PlaylistExportWorker(
            self.playlist_manager, path, complete
        )
        self._export_worker.moveToThread(self._export_thread)
        self._export_thread.started.connect(self._export_worker.run)
        self._export_worker.progress.connect(self._on_export_progress)
        self._export_worker.succeeded.connect(self._on_export_success)
        self._export_worker.failed.connect(self._on_export_failure)
        self._export_worker.finished.connect(self._export_thread.quit)
        self._export_thread.finished.connect(self._on_export_finished)
        self._export_thread.start()

    def _on_export_progress(self, current: int, total: int, name: str) -> None:
        if not self._export_progress_dialog:
            return
        self._export_progress_dialog.setMaximum(max(1, total))
        self._export_progress_dialog.setValue(max(0, min(current, total)))
        if name:
            self._export_progress_dialog.setLabelText(
                self._t("Exporting {current}/{total}: {name}").format(
                    current=min(current + 1, total), total=total, name=name
                )
            )
        QApplication.processEvents()

    def _on_export_success(self, count: int, path: str) -> None:
        if self._export_progress_dialog:
            self._export_progress_dialog.setValue(self._export_progress_dialog.maximum())
            self._export_progress_dialog.close()
        QMessageBox.information(
            self, self._t("Export Playlist"),
            self._t("Exported {count} playlist item(s).").format(count=count)
            + "\n" + path,
        )

    def _on_export_failure(self, error: str) -> None:
        if self._export_progress_dialog:
            self._export_progress_dialog.close()
        QMessageBox.critical(self, self._t("Export Playlist"), error)

    def _on_export_finished(self) -> None:
        if self._export_worker:
            self._export_worker.deleteLater()
        if self._export_thread:
            self._export_thread.deleteLater()
        self._export_worker = None
        self._export_thread = None
        self._export_progress_dialog = None

    def delete_playlist_item(self, item_id: str):
        metadata = self.playlist_manager.get_metadata(item_id)
        if not metadata:
            return
        reply = QMessageBox.question(
            self, self._t("Delete Song"),
            self._t("Delete '{name}' from the playlist?").format(name=metadata.get('name', '')),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if item_id == self.current_playlist_id:
            self._playlist_session_active = False
            self._pending_playlist_item_id = None
            if self.playback_controller.is_playing() or self.playback_controller.is_paused():
                self.playback_controller.stop()
            self.current_playlist_id = None
            self.loaded_save_data = None
            self.loaded_save_filename = None
            self.ui.update_file_label(self._t("No file selected."), "")
            self.ui.play_button.setEnabled(False)
            self.ui.scrubber_slider.setEnabled(False)
        if item_id == self._editing_playlist_id:
            self._editing_playlist_id = None
            self.ui.playback_tab.set_playlist_editing(False, self._t)
        if item_id == self._editing_sheet_playlist_id:
            self._editing_sheet_playlist_id = None
            self.ui.translator_tab.set_playlist_editing(False, self._t)
        if any(str(entry.get("item_id")) == item_id for entry in self._batch_edit_entries):
            self.ui.playback_tab.end_batch_change_tracking()
            self._batch_edit_entries = []
            self._batch_edit_baseline_config = None
            self.ui.playback_tab.set_playlist_editing(False, self._t)
        self.playlist_manager.delete(item_id)
        self._refresh_playlist()

    def clear_playlist(self):
        if not self.playlist_manager.items():
            return
        reply = QMessageBox.question(
            self, self._t("Clear Playlist"),
            self._t("Remove every song from the playlist? This cannot be undone."),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._playlist_session_active = False
        self._pending_playlist_item_id = None
        if self.playback_controller.is_playing() or self.playback_controller.is_paused():
            self.playback_controller.stop()
        self.current_playlist_id = None
        self._editing_playlist_id = None
        self._editing_sheet_playlist_id = None
        self.ui.playback_tab.end_batch_change_tracking()
        self._pending_batch_imports = []
        self._batch_edit_entries = []
        self._batch_edit_baseline_config = None
        self.ui.playback_tab.set_playlist_editing(False, self._t)
        self.ui.translator_tab.set_playlist_editing(False, self._t)
        self.loaded_save_data = None
        self.loaded_save_filename = None
        self.ui.update_file_label(self._t("No file selected."), "")
        self.ui.play_button.setEnabled(False)
        self.ui.scrubber_slider.setEnabled(False)
        self.playlist_manager.clear()
        self._refresh_playlist()

    # --- Translator ---
    def _sheet_playback_config(
        self, humanize: bool, base_config: dict | None = None
    ) -> dict:
        # New sheets inherit the current Playback page settings. While editing an
        # existing sheet, preserve its stored performance/seed configuration so
        # changing only text, BPM, format, or title does not silently reset it.
        if isinstance(base_config, dict):
            config = dict(base_config)
        else:
            config = self.ui.gather_playback_config()
        config.pop("midi_file", None)
        if humanize:
            if str(config.get("humanization_mode", "disabled")) == "disabled":
                config.update(self.ui.settings_tab.global_humanization_config())
                config["humanization_mode"] = "global"
                config["humanization_seed_mode"] = "dynamic"
                config["humanization_seed"] = None
        else:
            config["humanization_mode"] = "disabled"
            config["humanization_seed"] = None
            for key in (
                "simulate_hands", "enable_chord_roll", "vary_timing",
                "vary_articulation", "enable_drift_correction", "enable_mistakes",
                "enable_tempo_sway", "invert_tempo_sway",
            ):
                config[key] = False
        return config

    def _parse_text_sheet(self, text: str, format_name: str, bpm: int, config: dict):
        fmt = FormatRegistry.get(format_name)
        if not fmt:
            raise ValueError(
                self._t("No handler found for format: {format_name}").format(
                    format_name=format_name
                )
            )
        use_88 = bool(config.get("use_88_key_layout", False))
        key_mapper = KeyMapper(use_88_key_layout=use_88)
        notes = fmt.parse(text, float(bpm), key_mapper)
        if not notes:
            raise ValueError(self._t("No playable notes were found in the pasted sheet."))
        tempo_map = TempoMap([(0, int(60_000_000 / bpm))], [])
        duration = max((float(note.end_time) for note in notes), default=0.0)
        return notes, tempo_map, duration

    def _default_sheet_name(self) -> str:
        base = self._t("Text Sheet")
        existing = {str(item.get("name") or "") for item in self.playlist_manager.items()}
        if base not in existing:
            return base
        index = 2
        while f"{base} {index}" in existing:
            index += 1
        return f"{base} {index}"

    def _on_save_sheet_to_playlist(
        self, text: str, format_name: str, bpm: int, humanize: bool, name: str
    ) -> None:
        if self.playback_controller.is_playing() or self.playback_controller.is_paused():
            QMessageBox.warning(
                self, self._t("Add to Playlist"),
                self._t("Stop playback before saving this song to the playlist."),
            )
            return
        editing_id = self._editing_sheet_playlist_id
        base_config = None
        if editing_id:
            try:
                existing = self.playlist_manager.get_song_data(editing_id)
                stored = existing.get("playback_settings", {}) if isinstance(existing, dict) else {}
                if isinstance(stored, dict):
                    base_config = stored
            except Exception:
                base_config = None
        config = self._sheet_playback_config(humanize, base_config)
        try:
            _notes, _tempo_map, duration = self._parse_text_sheet(
                text, format_name, bpm, config
            )
        except Exception as exc:
            QMessageBox.critical(
                self, self._t("Parse Error"),
                self._t("Failed to parse sheet:") + f"\n{exc}",
            )
            return

        try:
            if editing_id:
                item = self.playlist_manager.update_sheet(
                    editing_id, text, format_name, bpm, config,
                    name=name or None, duration_hint=duration,
                )
                message = self._t("The text sheet was modified successfully.")
            else:
                item = self.playlist_manager.add_sheet(
                    text, format_name, bpm, config,
                    name=name or self._default_sheet_name(),
                    duration_hint=duration,
                )
                message = self._t("The text sheet was added to the playlist successfully.")
        except Exception as exc:
            QMessageBox.critical(self, self._t("Playlist Error"), self._t(str(exc)))
            return

        self._editing_sheet_playlist_id = None
        self.ui.translator_tab.set_playlist_editing(False, self._t)
        self.current_playlist_id = str(item.get("id") or "") or None
        self._refresh_playlist(self.current_playlist_id)
        QMessageBox.information(self, self._t("Add to Playlist"), message)

    def _on_play_sheet(self, text: str, format_name: str, bpm: int, humanize: bool):
        self._playlist_session_active = False
        self.current_playlist_id = None
        if self.playback_controller.is_playing() or self.playback_controller.is_paused():
            return

        config = self._sheet_playback_config(humanize)
        try:
            notes, tempo_map, _duration = self._parse_text_sheet(
                text, format_name, bpm, config
            )
        except Exception as exc:
            QMessageBox.critical(
                self, self._t("Parse Error"),
                self._t("Failed to parse sheet:") + f"\n{exc}",
            )
            return

        self.ui.log_output.append(
            self._t("Importing sheet: {count} notes at {bpm} BPM ({format_name})").format(
                count=len(notes), bpm=bpm, format_name=self._t(format_name)
            )
        )
        self._set_playback_status(self._t("Pasted Sheet"), "translator_preview", self._t(format_name))
        self.playback_controller.play_from_notes(config, notes, tempo_map)
        self.ui.set_controls_enabled(False)
        self.ui.play_button.setEnabled(True)
        self.ui.stop_button.setEnabled(True)
        self.ui.scrubber_slider.setEnabled(True)
        self._sync_play_button()
        # Stay on the Translator page so the global play/stop controls remain
        # a direct transport for the pasted sheet. The Visualizer is still
        # available from the sidebar.

    def _on_export_sheet(self, format_name: str):
        if not self.current_notes:
            QMessageBox.warning(self, self._t("No MIDI Loaded"),
                                self._t("Load and prepare a MIDI file on the Playback tab first."))
            return

        fmt = FormatRegistry.get(format_name)
        if not fmt:
            QMessageBox.critical(self, self._t("Unknown Format"), self._t("No handler found for format: {format_name}").format(format_name=format_name))
            return

        use_88 = self.ui.playback_tab.use_88_key_check.isChecked()
        key_mapper = KeyMapper(use_88_key_layout=use_88)
        tempo_map = getattr(self, 'parsed_tempo_map', TempoMap([(0, 500000)], []))

        try:
            text = fmt.serialize(self.current_notes, key_mapper, tempo_map)
        except Exception as e:
            QMessageBox.critical(self, self._t("Export Error"), self._t("Failed to generate sheet:") + f"\n{e}")
            return

        self.ui.translator_tab.set_export_text(text)
        self.ui.log_output.append(f"Sheet exported: {format_name} ({len(text.splitlines())} lines)")

    def show_error_dialog(self, error_message: str):
        self._playlist_session_active = False
        self._pending_playlist_item_id = None
        self._clear_playback_status()
        self.ui.log_output.append("ERROR: Playback thread terminated unexpectedly due to an execution failure.")
        QMessageBox.critical(self, self._t("Hardware/Execution Failure"), error_message)

    # --- Core Executions ---
    def handle_save(self):
        config = self.ui.gather_playback_config()
        if not self.selected_tracks_info:
            QMessageBox.warning(self, self._t("No Tracks"), self._t("Please select a MIDI file and choose tracks first."))
            return
            
        self._save_config()
        original_filename = os.path.basename(self.ui.playback_tab.file_path_label.toolTip())
        self.playback_controller.save(config, self.selected_tracks_info, self.config_manager.save_dir, original_filename)

    def _on_save_successful(self, filepath: str, message: str):
        QMessageBox.information(self, self._t("Save Successful"), f"{self._t(message)}\n{filepath}")

    def _on_save_failed(self, error_message: str):
        QMessageBox.critical(self, self._t("Save Error"), error_message)

    def handle_play(self):
        if self.playback_controller.is_playing() or self.playback_controller.is_paused():
            self.toggle_playback_state()
            return

        # In mini mode, the selected compact-playlist item owns the transport.
        if self.ui._is_collapsed:
            collapsed_id = self.ui.collapsed_selected_playlist_id()
            if collapsed_id:
                self.play_playlist_item(collapsed_id)
                return

        # The global transport and playback hotkey respect the active page.
        # On the Translator import page they play the currently pasted sheet.
        if self.ui.tabs.currentIndex() == 3 and self.ui.translator_tab.has_playable_input():
            self.ui.translator_tab.request_current_playback()
            return

        # Every fresh playlist start goes through _start_playlist_item so dynamic
        # seeds are regenerated and fixed/global caches are revalidated.
        if self.ui.tabs.currentIndex() == 1:
            selected_ids = self.ui.playlist_tab.selected_ids()
            if len(selected_ids) == 1:
                self.play_playlist_item(selected_ids[0])
                return
            if len(selected_ids) > 1:
                return
        if self.current_playlist_id:
            self.play_playlist_item(self.current_playlist_id)
            return

        if self.loaded_save_data:
            if self.current_playlist_id:
                self._playlist_session_active = True
                metadata = self.playlist_manager.get_metadata(self.current_playlist_id) or {}
                title = str(metadata.get('name') or self.loaded_save_filename or self._t("Unknown MIDI"))
                self._set_playback_status(title, "playlist")
            else:
                metadata = self.loaded_save_data.get('metadata', {})
                source_name = str(
                    metadata.get('custom_name')
                    or metadata.get('source_midi_filename')
                    or self.loaded_save_filename
                    or self._t("Unknown MIDI")
                )
                title = os.path.splitext(os.path.basename(source_name))[0]
                self._set_playback_status(title, "saved_preview")
            self.playback_controller.play_from_save(self.loaded_save_data)
        else:
            config = self.ui.gather_playback_config()
            if not self.selected_tracks_info:
                QMessageBox.warning(self, self._t("No Tracks"), self._t("Please select a MIDI file and choose tracks first."))
                return
            midi_path = str(config.get('midi_file') or self.ui.playback_tab.file_path_label.toolTip())
            title = os.path.splitext(os.path.basename(midi_path))[0] or self._t("Unknown MIDI")
            if self._editing_playlist_id:
                edited_metadata = self.playlist_manager.get_metadata(self._editing_playlist_id) or {}
                title = str(edited_metadata.get("name") or title)
            self._set_playback_status(title, "playback_preview")
            self.playback_controller.play(config, self.selected_tracks_info)

        self.ui.set_controls_enabled(False, bool(self.loaded_save_data))
        self.ui.play_button.setEnabled(True)
        self.ui.stop_button.setEnabled(True)
        self._sync_play_button()
        if self.ui._nav_btns[2].isEnabled():
            self.ui.tabs.setCurrentIndex(2)

    def handle_stop(self):
        self._playlist_session_active = False
        self._pending_playlist_item_id = None
        self._clear_playback_status()
        self.playback_controller.stop()

    def on_playback_finished(self):
        self.ui.set_countdown_remaining(0)
        self.ui.log_output.append(self._t("Playback process finished.") + "\n" + "="*50 + "\n")
        self.ui.set_controls_enabled(True, bool(self.loaded_save_data))
        self.ui.stop_button.setEnabled(False)
        self._sync_play_button()
        self.ui.piano_widget.set_pedal_active(False)

        pending = self._pending_playlist_item_id
        self._pending_playlist_item_id = None
        if pending:
            QTimer.singleShot(0, lambda item_id=pending: self._start_playlist_item(item_id))
            return

        if self._playlist_session_active and self.current_playlist_id:
            next_id = self._automatic_next_playlist_id()
            if next_id:
                QTimer.singleShot(0, lambda item_id=next_id: self._start_playlist_item(item_id))
                return
            self._playlist_session_active = False

        self._clear_playback_status()
        self._update_global_play_availability()

    # --- Update ---
    def _manual_check_update(self):
        btn = self.ui.settings_tab.check_update_btn
        btn.setEnabled(False)
        btn.setText(self._t("Checking..."))
        self._manual_checker = UpdateChecker(APP_VERSION, force=True)
        self._manual_checker.update_available.connect(self._on_update_available)
        self._manual_checker.update_available.connect(lambda *_: self._reset_update_btn())
        self._manual_checker.no_update.connect(self._on_no_update)
        self._manual_checker.check_failed.connect(self._on_check_failed)
        self._manual_checker.start()

    def _reset_update_btn(self):
        btn = self.ui.settings_tab.check_update_btn
        btn.setEnabled(True)
        btn.setText(self._t("Check for updates"))

    def _on_no_update(self):
        self._reset_update_btn()
        QMessageBox.information(self, self._t("Up to Date"),
            self._t("HuMidi Xingkong Edition v{version} is the latest version.").format(
                version=APP_VERSION
            ))

    def _on_check_failed(self):
        self._reset_update_btn()
        QMessageBox.warning(self, self._t("Update Check Failed"),
            self._t("Could not reach GitHub.\nPlease check your internet connection."))

    def _on_update_available(self, latest_tag: str, releases_url: str):
        reply = QMessageBox.question(
            self, self._t("Update Available"),
            self._t("Update available to {latest_tag}. Open the GitHub Releases page?").format(
                latest_tag=latest_tag
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes:
            webbrowser.open(releases_url)

    def closeEvent(self, event):
        if self._update_checker is not None:
            self._update_checker.quit()
        self._save_config()
        self.hotkey_manager.shutdown()
        self.playback_controller.shutdown()
        if self._batch_edit_prepare_cancel_event is not None:
            self._batch_edit_prepare_cancel_event.set()
        if (self._batch_edit_prepare_thread is not None
                and self._batch_edit_prepare_thread.isRunning()):
            self._batch_edit_prepare_thread.quit()
            self._batch_edit_prepare_thread.wait()
        if self._export_thread and self._export_thread.isRunning():
            self._export_thread.quit()
            self._export_thread.wait()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
