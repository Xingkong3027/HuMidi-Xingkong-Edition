import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StaticIntegrationTests(unittest.TestCase):
    def test_all_application_python_files_parse(self):
        for path in ROOT.rglob("*.py"):
            if "backup" in path.parts:
                continue
            with self.subTest(path=path.relative_to(ROOT)):
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    def test_requested_modes_and_sidebar_are_present(self):
        playlist = (ROOT / "ui" / "PlaylistTab.py").read_text(encoding="utf-8")
        for mode in ("single", "single_repeat", "repeat_all", "sequential", "shuffle"):
            self.assertIn(f'("{mode}",', playlist)
        main_ui = (ROOT / "ui" / "MainWindowUI.py").read_text(encoding="utf-8")
        self.assertIn('("\\uE8D5", "Playlist")', main_ui)
        self.assertIn("self.tabs.addWidget(self.playlist_tab)", main_ui)

    def test_language_auto_maps_all_chinese_locales(self):
        language = (ROOT / "managers" / "LanguageManager.py").read_text(encoding="utf-8")
        self.assertIn('.name().lower().startswith("zh")', language)
        self.assertIn('"Automatic (Simplified Chinese)": "自动选择（简体中文）"', language)

    def test_compiled_playlist_omits_absolute_midi_path(self):
        controller = (ROOT / "controllers" / "PlaybackController.py").read_text(encoding="utf-8")
        self.assertIn("stored_config.pop('midi_file', None)", controller)

    def test_natural_end_advances_playlist_by_clean_stop(self):
        main = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("def _on_auto_paused", main)
        self.assertIn("self._pending_playlist_item_id = next_id", main)
        self.assertIn("self.playback_controller.stop()", main)

    def test_larger_window_and_playback_identity_status_are_present(self):
        main = (ROOT / "main.py").read_text(encoding="utf-8")
        main_ui = (ROOT / "ui" / "MainWindowUI.py").read_text(encoding="utf-8")
        language = (ROOT / "managers" / "LanguageManager.py").read_text(encoding="utf-8")
        self.assertIn("DEFAULT_WINDOW_SIZE = (1040, 640)", main)
        self.assertIn("MINIMUM_WINDOW_SIZE = (900, 560)", main)
        self.assertIn("self.now_playing_label", main_ui)
        self.assertIn("self.playback_source_label", main_ui)
        self.assertIn('"Source: Playlist ({mode})": "来源：歌单（{mode}）"', language)

    def test_playlist_page_routes_global_play_and_hotkey_to_selection(self):
        main = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("if self.ui.tabs.currentIndex() == 1:", main)
        self.assertIn("selected_ids = self.ui.playlist_tab.selected_ids()", main)
        self.assertIn("if len(selected_ids) == 1:", main)
        self.assertIn("self.play_playlist_item(selected_ids[0])", main)

    def test_preview_playlist_visualization_uses_one_compiled_bundle(self):
        controller = (ROOT / "controllers" / "PlaybackController.py").read_text(encoding="utf-8")
        player = (ROOT / "core" / "player.py").read_text(encoding="utf-8")
        self.assertIn("compiled_bundle_ready = Signal(object)", player)
        self.assertIn("self.visualization_notes", player)
        self.assertIn("'visualizer_data':", controller)
        self.assertIn("Using the exact compiled preview for the playlist", controller)
        self.assertIn("self.player.compiled_bundle_ready.connect(self._on_live_compiled_bundle)", controller)
        self.assertIn("active_presses = defaultdict(list)", controller)

    def test_overlapping_pitch_visual_state_uses_reference_counts(self):
        player = (ROOT / "core" / "player.py").read_text(encoding="utf-8")
        self.assertIn("self._pitch_net: Dict[int, int]", player)
        self.assertIn("self._pitch_net[event.pitch] = self._pitch_net.get(event.pitch, 0) + 1", player)
        self.assertIn("pitch_net = self._pitch_net.get(event.pitch, 0) - 1", player)

    def test_advanced_playlist_song_model_and_editing_are_present(self):
        manager = (ROOT / "managers" / "PlaylistManager.py").read_text(encoding="utf-8")
        main = (ROOT / "main.py").read_text(encoding="utf-8")
        playlist = (ROOT / "ui" / "PlaylistTab.py").read_text(encoding="utf-8")
        playback = (ROOT / "ui" / "PlaybackTab.py").read_text(encoding="utf-8")
        self.assertIn('self.midi_dir = self.root_dir / "midi"', manager)
        self.assertIn('self.cache_dir = self.root_dir / "cache"', manager)
        self.assertIn('archive.writestr("playlist.json"', manager)
        self.assertIn('exported_source["original_path"] = ""', manager)
        self.assertIn('edit_requested = Signal(str)', playlist)
        self.assertIn('save_midi_as_requested = Signal(str)', playlist)
        self.assertIn('self._tr("Modify Song")', playlist)
        self.assertIn('self._tr("Save MIDI As…")', playlist)
        self.assertIn('"Complete Modification" if editing else "Add to Playlist"', playback)
        self.assertIn('def edit_playlist_item', main)
        self.assertIn('def save_playlist_midi_as', main)

    def test_human_like_performance_modes_and_seed_controls_are_present(self):
        playback = (ROOT / "ui" / "PlaybackTab.py").read_text(encoding="utf-8")
        settings = (ROOT / "ui" / "SettingsTab.py").read_text(encoding="utf-8")
        dialog = (ROOT / "ui" / "GlobalHumanizationDialog.py").read_text(encoding="utf-8")
        language = (ROOT / "managers" / "LanguageManager.py").read_text(encoding="utf-8")
        player = (ROOT / "core" / "player.py").read_text(encoding="utf-8")
        humanizer = (ROOT / "core" / "humanizer.py").read_text(encoding="utf-8")
        for value in ("disabled", "global", "individual"):
            self.assertIn(f'("{value}",', playback)
        for value in ("dynamic", "fixed_random", "fixed_custom"):
            self.assertIn(f'("{value}",', playback)
        self.assertIn('self.random_seed_input.setEnabled(seed_editable)', playback)
        self.assertIn('def regenerate_fixed_random_seed', playback)
        self.assertIn('Global Human-like Performance', settings)
        self.assertIn('class GlobalHumanizationDialog', dialog)
        self.assertIn('"Human-like Performance": "模拟人演奏"', language)
        self.assertIn('self.rng = random.Random(seed', player)
        self.assertIn('Humanizer(self.config, self.debug_log, self.rng)', player)
        self.assertIn('self.rng = rng or random.Random()', humanizer)

    def test_disabled_humanization_controls_have_visible_disabled_styles(self):
        playback = (ROOT / "ui" / "PlaybackTab.py").read_text(encoding="utf-8")
        theme = (ROOT / "ui" / "theme.py").read_text(encoding="utf-8")
        self.assertIn("self.randomness_combo.setEnabled(enabled_mode)", playback)
        self.assertIn("QComboBox:disabled", theme)
        self.assertIn("QComboBox:hover:!disabled", theme)
        self.assertIn("QLineEdit:disabled", theme)
        self.assertIn("QLabel:disabled", theme)

    def test_dynamic_playlist_recompiles_and_fixed_modes_use_cache(self):
        main = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('if self._playlist_config_uses_dynamic_seed(config):', main)
        self.assertIn('"cache_result": not dynamic', main)
        self.assertIn('if cache_matches_config(candidate, config):', main)
        self.assertIn('config["humanization_seed"] = random.SystemRandom().randint', main)

    def test_batch_midi_import_playlist_multiselect_and_progress_are_present(self):
        main = (ROOT / "main.py").read_text(encoding="utf-8")
        playback = (ROOT / "ui" / "PlaybackTab.py").read_text(encoding="utf-8")
        playlist = (ROOT / "ui" / "PlaylistTab.py").read_text(encoding="utf-8")
        track_dialog = (ROOT / "ui" / "TrackSelectionDialog.py").read_text(encoding="utf-8")
        self.assertIn("QFileDialog.getOpenFileNames", main)
        self.assertIn("BatchImportChoiceDialog", main)
        self.assertIn("BatchImportSummaryDialog", main)
        self.assertIn("Process All Automatically", (ROOT / "ui" / "BatchMidiDialogs.py").read_text(encoding="utf-8"))
        self.assertIn('mode="auto_failure"', main)
        self.assertIn("Ignore All", track_dialog)
        self.assertIn("Please select at least one track.", track_dialog)
        self.assertIn("Import MIDI (Multi-select)", playback)
        self.assertIn("ExtendedSelection", playlist)
        self.assertIn("Batch Modify Songs", playlist)
        self.assertIn("Batch Save MIDI As…", playlist)
        self.assertIn("Batch Delete", playlist)
        self.assertIn("QPen(Qt.GlobalColor.white, 2)", playlist)
        self.assertIn("QDrag(self)", playlist)
        self.assertIn("build_reordered_ids(all_ids, moving_ids, target)", playlist)
        self.assertIn("QAbstractItemView.DragDropMode.DragDrop", playlist)
        self.assertNotIn("QAbstractItemView.DragDropMode.InternalMove", playlist)
        self.assertIn("The playlist reorder request is incomplete or invalid.", (ROOT / "managers" / "PlaylistManager.py").read_text(encoding="utf-8"))
        self.assertIn("PlaylistExportWorker", main)
        self.assertIn("QProgressDialog", main)
        self.assertIn("same_fixed_performance", main)
        self.assertIn("Existing songs keep", main)

    def test_shortcut_dialog_and_media_transport_actions_are_present(self):
        main = (ROOT / "main.py").read_text(encoding="utf-8")
        dialog = (ROOT / "ui" / "ShortcutSettingsDialog.py").read_text(encoding="utf-8")
        manager = (ROOT / "managers" / "HotkeyManager.py").read_text(encoding="utf-8")
        language = (ROOT / "managers" / "LanguageManager.py").read_text(encoding="utf-8")
        for action in ("play_pause", "stop", "next", "previous"):
            self.assertIn(action, dialog)
        self.assertIn("Shortcut 1", dialog)
        self.assertIn("Shortcut 2", dialog)
        self.assertIn("0xB3", manager)
        self.assertIn("0xB1", manager)
        self.assertIn("0xB0", manager)
        self.assertIn("self.hotkey_manager.stop_requested.connect(self.handle_stop)", main)
        self.assertIn('"Keyboard Shortcuts": "快捷键"', language)

    def test_settings_scroll_and_text_sheet_playlist_support_are_present(self):
        settings = (ROOT / "ui" / "SettingsTab.py").read_text(encoding="utf-8")
        translator = (ROOT / "ui" / "TranslatorTab.py").read_text(encoding="utf-8")
        playlist = (ROOT / "ui" / "PlaylistTab.py").read_text(encoding="utf-8")
        manager = (ROOT / "managers" / "PlaylistManager.py").read_text(encoding="utf-8")
        main = (ROOT / "main.py").read_text(encoding="utf-8")
        language = (ROOT / "managers" / "LanguageManager.py").read_text(encoding="utf-8")

        self.assertIn("QScrollArea", settings)
        self.assertIn("ScrollBarAlwaysOff", settings)
        self.assertIn("ScrollBarAsNeeded", settings)
        self.assertIn("QSizePolicy.Policy.Fixed", settings)
        self.assertIn("add_to_playlist_requested = Signal", translator)
        self.assertIn('self.sub_tabs.setTabText', translator)
        self.assertIn('Generated sheet will appear here…', translator)
        self.assertIn('FormatRegistry.names()', translator)
        self.assertIn('source_type") or "midi") == "sheet"', playlist)
        self.assertIn('def add_sheet(', manager)
        self.assertIn('def update_sheet(', manager)
        self.assertIn('"type": "sheet"', manager)
        self.assertIn('def _start_sheet_playlist_item', main)
        self.assertIn('def _edit_sheet_playlist_item', main)
        self.assertIn('Only Process MIDI', main)
        self.assertIn('"Virtual Piano": "虚拟钢琴格式 (Virtual Piano)"', language)
        self.assertIn('"Generated sheet will appear here…": "生成的乐谱将显示在这里…"', language)
        self.assertIn('"Apply a sinusoidal tempo variation across the song for a more expressive feel": "在整首歌曲中应用正弦速度变化，使演奏更富有表现力"', language)


    def test_transport_scroll_drag_and_countdown_enhancements_are_present(self):
        settings = (ROOT / "ui" / "SettingsTab.py").read_text(encoding="utf-8")
        widgets = (ROOT / "ui" / "widgets.py").read_text(encoding="utf-8")
        playlist = (ROOT / "ui" / "PlaylistTab.py").read_text(encoding="utf-8")
        playback = (ROOT / "ui" / "PlaybackTab.py").read_text(encoding="utf-8")
        main_ui = (ROOT / "ui" / "MainWindowUI.py").read_text(encoding="utf-8")
        translator = (ROOT / "ui" / "TranslatorTab.py").read_text(encoding="utf-8")
        main = (ROOT / "main.py").read_text(encoding="utf-8")
        player = (ROOT / "core" / "player.py").read_text(encoding="utf-8")
        controller = (ROOT / "controllers" / "PlaybackController.py").read_text(encoding="utf-8")
        language = (ROOT / "managers" / "LanguageManager.py").read_text(encoding="utf-8")

        self.assertIn("class NoWheelSlider", widgets)
        self.assertIn("class NoWheelComboBox", widgets)
        self.assertIn("NoWheelSlider(Qt.Orientation.Horizontal)", settings)
        self.assertIn("self.theme_combo = NoWheelComboBox()", settings)
        self.assertIn("self._ctrl_selecting", playlist)
        self.assertIn("QApplication.startDragDistance()", playlist)
        self.assertIn("app.installEventFilter(self)", playlist)
        self.assertIn("app.installNativeEventFilter(self._native_wheel_filter)", playlist)
        self.assertIn("WM_MOUSEWHEEL = 0x020A", playlist)
        self.assertIn("def _scroll_drag_by_delta", playlist)
        self.assertIn("def _auto_scroll_step", playlist)
        self.assertIn("countdown_seconds_slider", playback)
        self.assertIn('"countdown_seconds": self.countdown_seconds_spinbox.value()', playback)
        self.assertIn('self.config.get("countdown_seconds", 3)', player)
        self.assertIn("countdown_updated = Signal(int)", player)
        self.assertIn("self.countdown_updated.emit(i)", player)
        self.assertIn("self.countdown_updated.emit(0)", player)
        self.assertIn("countdown_updated = Signal(int)", controller)
        self.assertIn("self.player.countdown_updated.connect(self.countdown_updated.emit)", controller)
        self.assertIn("set_countdown_remaining", main_ui)
        self.assertIn('"Countdown {seconds} seconds"', language)
        self.assertIn('self.save_button = QPushButton("Save Playback")', playback)
        self.assertIn('file_actions.addWidget(self.reset_button, 1, 0)', playback)
        self.assertIn('file_actions.addWidget(self.save_button, 1, 1)', playback)
        self.assertNotIn('self.save_button.setObjectName("save_button")', playback)
        self.assertNotIn('self.reset_button.setObjectName("reset_button")', playback)
        self.assertNotIn('self.save_button = QPushButton("Save Playback")', main_ui)
        self.assertIn('self.previous_button = QPushButton("Previous")', main_ui)
        self.assertIn("self._collapsed_playlist_list = QListWidget()", main_ui)
        self.assertIn("self._collapsed_mode_combo = QComboBox()", main_ui)
        self.assertIn("def has_playable_input", translator)
        self.assertIn("request_current_playback", main)
        self.assertIn('"Show a {seconds}-second countdown before playback begins"', language)

    def test_playback_left_controls_keep_natural_height_and_scroll(self):
        playback = (ROOT / "ui" / "PlaybackTab.py").read_text(encoding="utf-8")
        self.assertIn('self.left_scroll_area = QScrollArea()', playback)
        self.assertIn('"playback_left_scroll_area"', playback)
        self.assertIn('ScrollBarAsNeeded', playback)
        self.assertIn('QSizePolicy.Policy.Fixed', playback)
        self.assertIn('self._keep_card_size(self.file_group)', playback)
        self.assertIn('self._keep_card_size(self.playback_group)', playback)
        self.assertIn('outer.addWidget(self.left_scroll_area, 1)', playback)
        self.assertNotIn('outer.addLayout(left_col, 1)', playback)
        self.assertIn('def _sync_column_card_heights', playback)
        self.assertIn('self.humanization_group.setMinimumHeight(target_height)', playback)
        self.assertIn('left_layout.sizeHint().height()', playback)

    def test_batch_partial_apply_trim_and_status_refresh_are_present(self):
        main = (ROOT / "main.py").read_text(encoding="utf-8")
        playback = (ROOT / "ui" / "PlaybackTab.py").read_text(encoding="utf-8")
        controller = (ROOT / "controllers" / "PlaybackController.py").read_text(encoding="utf-8")
        trimming = (ROOT / "core" / "trimming.py").read_text(encoding="utf-8")
        language = (ROOT / "managers" / "LanguageManager.py").read_text(encoding="utf-8")

        self.assertIn("Only Apply Changed Values", main)
        self.assertIn("Apply All Values", main)
        self.assertIn('operation.get("apply_mode") == "changed"', main)
        self.assertNotIn("The current playback settings will be applied to all selected songs. Each song keeps its own MIDI and track selection.", main)
        self.assertIn('self.trim_check = QCheckBox("Trim")', playback)
        self.assertIn('self.trim_auto_check = QCheckBox("Auto")', playback)
        self.assertIn('"trim_enabled": self.trim_check.isChecked()', playback)
        self.assertIn("apply_trim(", controller)
        self.assertIn("def apply_trim", trimming)
        self.assertIn("QTimer.singleShot(0, self._render_playback_status)", main)
        self.assertIn('"Only Apply Changed Values": "仅修改变动值"', language)
        self.assertIn("button.setMinimumWidth", main)
        self.assertIn("batch_changed_keys", main)
        self.assertIn("begin_batch_change_tracking", playback)
        self.assertIn("trim_mode_touched", main)
        self.assertIn("selected_track_bounds", main)

    def test_batch_edit_preparation_runs_off_gui_thread_with_progress(self):
        main = (ROOT / "main.py").read_text(encoding="utf-8")
        worker = (
            ROOT / "workers" / "BatchPlaylistEditPrepareWorker.py"
        ).read_text(encoding="utf-8")
        language = (ROOT / "managers" / "LanguageManager.py").read_text(encoding="utf-8")
        self.assertIn("BatchPlaylistEditPrepareWorker", main)
        self.assertIn("self._batch_edit_prepare_thread = QThread", main)
        self.assertIn("QProgressDialog", main)
        self.assertIn("threading.Event", main)
        self.assertIn("MidiParser.parse_structure", worker)
        self.assertIn("self.progress.emit", worker)
        self.assertIn('"Preparing songs for batch modification…"', language)
        self.assertIn('"Reading {current}/{total}: {name}"', language)

    def test_midi_parser_repairs_chinese_track_names(self):
        core = (ROOT / "core" / "core.py").read_text(encoding="utf-8")
        decoder = (ROOT / "core" / "midi_text.py").read_text(encoding="utf-8")
        self.assertIn("charset='latin1'", core)
        self.assertIn("decode_midi_text(msg.name)", core)
        for encoding in ("utf-8", "gb18030", "big5", "shift_jis"):
            self.assertIn(f'"{encoding}"', decoder)

    def test_strict_midi_parser_offers_explicit_clip_compatibility(self):
        core = (ROOT / "core" / "core.py").read_text(encoding="utf-8")
        controller = (ROOT / "controllers" / "PlaybackController.py").read_text(encoding="utf-8")
        playback = (ROOT / "ui" / "PlaybackTab.py").read_text(encoding="utf-8")
        main = (ROOT / "main.py").read_text(encoding="utf-8")
        language = (ROOT / "managers" / "LanguageManager.py").read_text(encoding="utf-8")
        self.assertIn("class MidiInvalidDataByteError", core)
        self.assertIn("clip=bool(clip_invalid_data)", core)
        self.assertIn("def _parse_midi_with_clip_prompt", main)
        self.assertIn("midi_clip_invalid_data", playback)
        self.assertIn("midi_clip_invalid_data", controller)
        self.assertIn("contains illegal MIDI data bytes", main)
        self.assertIn("def _ask_localized_yes_no", main)
        self.assertIn('box.addButton(self._t("Yes")', main)
        self.assertIn('box.addButton(self._t("No")', main)
        self.assertIn("def _localized_midi_parse_error", main)
        self.assertIn("mthd not found", main.lower())
        self.assertIn("此 MIDI 含有非法数据字节", language)
        self.assertIn("所选文件没有有效的 MIDI 文件头", language)


    def test_optional_dense_midi_performance_mode_is_present(self):
        playback = (ROOT / "ui" / "PlaybackTab.py").read_text(encoding="utf-8")
        player = (ROOT / "core" / "player.py").read_text(encoding="utf-8")
        performance = (ROOT / "core" / "performance.py").read_text(encoding="utf-8")
        controller = (ROOT / "controllers" / "PlaybackController.py").read_text(encoding="utf-8")
        language = (ROOT / "managers" / "LanguageManager.py").read_text(encoding="utf-8")

        self.assertIn('self.performance_optimization_check = QCheckBox("Performance Optimization")', playback)
        self.assertIn('"performance_optimization": self.performance_optimization_check.isChecked()', playback)
        self.assertIn('self._execute_chord_event_optimized', player)
        self.assertNotIn('WindowsSendInputBatcher', player)
        self.assertIn('input_backend=pynput', player)
        self.assertIn('config_bool', player)
        self.assertIn('build_press_action_plan', player)
        self.assertIn('timeBeginPeriod(1)', performance)
        self.assertIn('gc.disable()', performance)
        self.assertIn("'performance_optimization'", controller)
        self.assertIn('"Performance Optimization": "性能优化"', language)



if __name__ == "__main__":
    unittest.main()
