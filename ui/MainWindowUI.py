from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QCheckBox, QSlider, QLabel, QGroupBox, QTabWidget,
                             QTextEdit, QComboBox, QDoubleSpinBox, QGridLayout,
                             QScrollArea, QStackedWidget, QLineEdit, QStatusBar, QApplication)
from PyQt6.QtCore import Qt, QObject
from PyQt6.QtGui import QFont

from ui.visualizer import PianoWidget, TimelineWidget

class MainWindowUI(QObject):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        
        self.pedal_mapping = {
            "Auto (Default)": "hybrid",
            "Harmonic": "legato",
            "Rhythmic": "rhythmic",
            "None": "none"
        }
        self.pedal_mapping_inv = {v: k for k, v in self.pedal_mapping.items()}
        
        self.setup_ui()

    def setup_ui(self):
        main_widget = QWidget()
        self.main_window.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 5)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        controls_tab, visual_tab, settings_tab, log_tab = QWidget(), QWidget(), QWidget(), QWidget()
        self.tabs.addTab(controls_tab, "Playback")
        self.tabs.addTab(visual_tab, "Visualizer")
        self.tabs.addTab(settings_tab, "Settings")
        self.tabs.addTab(log_tab, "Debug")

        # --- Visualizer Tab ---
        vis_layout = QVBoxLayout(visual_tab)
        vis_layout.setContentsMargins(5, 5, 5, 5)

        self._vis_stack = QStackedWidget()

        # Stack page 0: full piano-roll timeline
        timeline_page = QWidget()
        timeline_page_layout = QVBoxLayout(timeline_page)
        timeline_page_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.timeline_widget = TimelineWidget()
        self.scroll_area.setWidget(self.timeline_widget)
        timeline_page_layout.addWidget(self.scroll_area)
        self._vis_stack.addWidget(timeline_page)

        # Stack page 1: plain seek slider
        self._simple_slider = QSlider(Qt.Orientation.Horizontal)
        self._simple_slider.setRange(0, 10000)
        self._simple_slider.sliderPressed.connect(self._on_simple_slider_pressed)
        self._simple_slider.sliderMoved.connect(self._on_simple_slider_moved)
        self._simple_slider.sliderReleased.connect(self._on_simple_slider_released)
        self._vis_stack.addWidget(self._simple_slider)
        self._simple_slider_dragging = False

        vis_layout.addWidget(self._vis_stack)

        self.piano_widget = PianoWidget()
        vis_layout.addWidget(self.piano_widget)

        # --- Controls Tab ---
        controls_layout = QVBoxLayout(controls_tab)
        self.file_group = self._create_file_group()
        controls_layout.addWidget(self.file_group)
        self.playback_group = self._create_playback_group()
        controls_layout.addWidget(self.playback_group)
        self.humanization_group = self._create_humanization_group()
        controls_layout.addWidget(self.humanization_group)
        controls_layout.addStretch()

        # --- Settings Tab ---
        settings_layout = QVBoxLayout(settings_tab)
        hk_group = QGroupBox("Hotkey")
        hk_layout = QHBoxLayout(hk_group)
        self.hk_label = QLabel("Hotkey: ")
        self.hk_btn = QPushButton("Change")
        self.hk_btn.setToolTip("Click to bind a new hotkey for toggling playback")
        hk_layout.addWidget(self.hk_label)
        hk_layout.addWidget(self.hk_btn)
        settings_layout.addWidget(hk_group)

        overlay_group = QGroupBox("Overlay")
        ov_layout = QGridLayout(overlay_group)
        self.always_top_check = QCheckBox("Always on Top")
        self.always_top_check.setToolTip("Keep this window above all other windows")

        opacity_label = QLabel("Opacity")
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(20, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setToolTip("Adjust window transparency (20–100%)")

        ov_layout.addWidget(self.always_top_check, 0, 0, 1, 2)
        ov_layout.addWidget(opacity_label, 1, 0)
        ov_layout.addWidget(self.opacity_slider, 1, 1)
        settings_layout.addWidget(overlay_group)
        
        # --- Save Directory Settings ---
        save_group = QGroupBox("Save Path")
        save_layout = QHBoxLayout(save_group)
        self.save_path_input = QLineEdit()
        self.save_path_input.setReadOnly(True)
        self.save_path_input.setToolTip("Directory where humanized performance saves are stored")
        self.save_browse_btn = QPushButton("Browse")
        self.save_browse_btn.setToolTip("Choose where to save humanized performance files")
        save_layout.addWidget(self.save_path_input)
        save_layout.addWidget(self.save_browse_btn)
        settings_layout.addWidget(save_group)

        vis_settings_group = QGroupBox("Visualizer")
        vis_settings_layout = QVBoxLayout(vis_settings_group)
        self.timeline_vis_check = QCheckBox("Timeline")
        self.timeline_vis_check.setChecked(True)
        self.timeline_vis_check.setToolTip("Show the piano-roll timeline in the Visualizer tab (disable for a simple seek slider)")
        self.piano_vis_check = QCheckBox("Piano Keys")
        self.piano_vis_check.setChecked(True)
        self.piano_vis_check.setToolTip("Show the piano key visualizer in the Visualizer tab")
        vis_settings_layout.addWidget(self.timeline_vis_check)
        vis_settings_layout.addWidget(self.piano_vis_check)
        settings_layout.addWidget(vis_settings_group)
        self.timeline_vis_check.toggled.connect(self._on_timeline_toggle)
        self.piano_vis_check.toggled.connect(self._on_piano_toggle)

        ai_group = QGroupBox("AI Model")
        ai_layout = QVBoxLayout(ai_group)
        self.use_ai_pedal_check = QCheckBox("Enable AI Pedal")
        self.use_ai_pedal_check.setChecked(True)
        self.use_ai_pedal_check.setToolTip(
            "Use the ONNX BiLSTM model for pedal timing when 'Auto (Default)' is selected.\n"
            "Falls back to the algorithmic driver if the model file is missing.\n"
            "Disable to always use the algorithmic driver."
        )
        ai_layout.addWidget(self.use_ai_pedal_check)
        settings_layout.addWidget(ai_group)

        settings_layout.addStretch()

        # --- Log Tab ---
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont("Courier", 9))
        log_layout = QVBoxLayout(log_tab)
        log_layout.addWidget(self.log_output)
        
        log_btn_layout = QHBoxLayout()
        self.log_clear_btn = QPushButton("Clear")
        self.log_clear_btn.setToolTip("Clear all log entries")
        self.log_copy_btn = QPushButton("Copy Log")
        self.log_copy_btn.setToolTip("Copy the full log to clipboard")
        self.log_clear_btn.clicked.connect(self.log_output.clear)
        self.log_copy_btn.clicked.connect(self.copy_log_to_clipboard)
        log_btn_layout.addWidget(self.log_clear_btn)
        log_btn_layout.addWidget(self.log_copy_btn)
        log_layout.addLayout(log_btn_layout)

        # Main Action Buttons (Bottom)
        media_layout = QHBoxLayout()
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        media_layout.addWidget(self.time_label)

        button_layout = QHBoxLayout()
        self.play_button = QPushButton("Play")
        self.play_button.setToolTip("Start, pause, or resume playback")
        self.stop_button = QPushButton("Stop")
        self.stop_button.setToolTip("Stop playback and reset to the beginning")
        self.save_button = QPushButton("Save")
        self.save_button.setToolTip("Save the current humanized performance to a file for later replay")
        self.reset_button = QPushButton("Reset")
        self.reset_button.setToolTip("Reset all settings to their default values")
        button_layout.addWidget(self.play_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.save_button)
        button_layout.addStretch()
        button_layout.addWidget(self.reset_button)
        
        main_layout.addLayout(media_layout)
        main_layout.addLayout(button_layout)
        
        # --- GitHub Link Integration ---
        github_layout = QHBoxLayout()
        github_label = QLabel('<a href="https://github.com/smyGitt/HuMidi-Roblox-Piano-Autoplayer"><span style="color: gray; text-decoration: underline;">by smyGitt on GitHub</span></a>')
        github_label.setOpenExternalLinks(True)
        github_layout.addStretch()
        github_layout.addWidget(github_label)
        main_layout.addLayout(github_layout)

        # GUI initialization dependencies
        self.play_button.setEnabled(False) 
        self.stop_button.setEnabled(False)
        self.save_button.setEnabled(False)
        status_bar = QStatusBar()
        self.main_window.setStatusBar(status_bar)

    def _create_slider_and_spinbox(self, min_val, max_val, default_val, text_suffix="", factor=10000.0, decimals=4):
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(int(min_val * factor), int(max_val * factor))
        spinbox = QDoubleSpinBox()
        spinbox.setDecimals(decimals)
        spinbox.setRange(0.0, 9999.9999)
        spinbox.setSingleStep(1.0 / factor)
        spinbox.setSuffix(text_suffix)
        slider.setValue(int(default_val * factor))
        spinbox.setValue(default_val)
        slider.valueChanged.connect(lambda v: spinbox.setValue(v / factor))
        spinbox.valueChanged.connect(lambda v: slider.setValue(int(v * factor)))
        return slider, spinbox

    def _create_file_group(self):
        group = QGroupBox("MIDI")
        layout = QVBoxLayout(group)
        self.file_path_label = QLabel("No file selected.")
        self.file_path_label.setStyleSheet("font-style: italic; color: grey;")
        
        btn_layout = QHBoxLayout()
        self.browse_button = QPushButton("Browse...")
        self.browse_button.setToolTip("Open a MIDI file to play")
        self.load_saved_btn = QPushButton("Load Save")
        self.load_saved_btn.setToolTip("Load a previously saved humanized performance")

        btn_layout.addWidget(self.browse_button)
        btn_layout.addWidget(self.load_saved_btn)
        
        layout.addWidget(self.file_path_label)
        layout.addLayout(btn_layout)
        return group

    def _create_playback_group(self):
        group = QGroupBox("Playback")
        grid = QGridLayout(group)
        tempo_label = QLabel("Tempo")
        self.tempo_slider, self.tempo_spinbox = self._create_slider_and_spinbox(10.0, 200.0, 100.0, "%", factor=10.0, decimals=1)
        self.tempo_slider.setToolTip("Playback speed as a percentage of the original tempo")
        self.tempo_spinbox.setToolTip("Playback speed as a percentage of the original tempo")
        grid.addWidget(tempo_label, 0, 0)
        grid.addWidget(self.tempo_slider, 0, 2); grid.addWidget(self.tempo_spinbox, 0, 3)

        pedal_label = QLabel("Pedal")
        self.pedal_style_combo = QComboBox()
        self.pedal_style_combo.addItems(list(self.pedal_mapping.keys()))
        self.pedal_style_combo.setToolTip(
            "Auto (Default): AI-driven pedal using a hybrid of rhythmic and harmonic analysis\n"
            "Harmonic: Hold pedal through harmonic regions, releasing at chord/bass changes\n"
            "Rhythmic: Release pedal on beat boundaries only\n"
            "None: No sustain pedal"
        )

        grid.addWidget(pedal_label, 1, 0)
        grid.addWidget(self.pedal_style_combo, 1, 2, 1, 2)
        self.use_88_key_check = QCheckBox("88-Key Layout")
        self.use_88_key_check.setToolTip("Map notes to the full 88-key piano layout instead of a compressed keyboard layout")
        grid.addWidget(self.use_88_key_check, 2, 0, 1, 4)
        self.countdown_check = QCheckBox("Countdown")
        self.countdown_check.setToolTip("Show a 3-second countdown before playback begins")
        self.debug_check = QCheckBox("Debug Output")
        self.debug_check.setToolTip("Print verbose event logs to the Debug tab during playback")
        grid.addWidget(self.countdown_check, 3, 0, 1, 4)
        grid.addWidget(self.debug_check, 4, 0, 1, 4)
        grid.setColumnStretch(2, 1)
        return group

    def _create_humanization_group(self):
        group = QGroupBox("Humanization")
        main_v_layout = QVBoxLayout(group)
        self.select_all_humanization_check = QCheckBox("All")
        self.select_all_humanization_check.setToolTip("Enable or disable all humanization options at once")
        main_v_layout.addWidget(self.select_all_humanization_check)
        self.all_humanization_checks = {}
        self.all_humanization_spinboxes = {}
        self.all_humanization_sliders = {}

        simple_toggles_layout = QHBoxLayout()
        self.all_humanization_checks['simulate_hands'] = QCheckBox("Simulate Hands")
        self.all_humanization_checks['simulate_hands'].setToolTip(
            "Assign notes to left/right hand and limit simultaneous finger usage to simulate realistic hand behavior"
        )
        self.all_humanization_checks['enable_chord_roll'] = QCheckBox("Chord Roll")
        self.all_humanization_checks['enable_chord_roll'].setToolTip(
            "Slightly stagger the notes within each chord to simulate the natural roll of fingers across the keys"
        )
        simple_toggles_layout.addWidget(self.all_humanization_checks['simulate_hands'])
        simple_toggles_layout.addStretch(1)
        simple_toggles_layout.addWidget(self.all_humanization_checks['enable_chord_roll'])
        main_v_layout.addLayout(simple_toggles_layout)

        detailed_layout = QGridLayout()
        detailed_layout.setColumnStretch(2, 1)

        def add_detailed_row(row_idx, name, key, min_val, max_val, def_val, suffix, factor=1.0, decimals=3, tooltip=""):
            check = QCheckBox(name)
            slider, spinbox = self._create_slider_and_spinbox(min_val, max_val, def_val, suffix, factor=factor, decimals=decimals)
            check.toggled.connect(slider.setEnabled)
            check.toggled.connect(spinbox.setEnabled)
            if tooltip:
                check.setToolTip(tooltip)
                slider.setToolTip(tooltip)
                spinbox.setToolTip(tooltip)
            detailed_layout.addWidget(check, row_idx, 0)
            detailed_layout.addWidget(slider, row_idx, 2)
            detailed_layout.addWidget(spinbox, row_idx, 3)
            self.all_humanization_checks[key] = check
            self.all_humanization_sliders[key] = slider
            self.all_humanization_spinboxes[key] = spinbox

        add_detailed_row(0, "Vary Timing", "vary_timing", 0, 0.1, 0.01, " s", factor=10000.0,
                         tooltip="Add random timing offsets to note events (in seconds)")
        add_detailed_row(1, "Vary Articulation", "vary_articulation", 50, 100, 95, "%", factor=100.0, decimals=1,
                         tooltip="Randomize note hold duration — lower values create a more staccato feel")
        add_detailed_row(2, "Hand Drift", "hand_drift", 0, 100, 25, "%", factor=100.0, decimals=1,
                         tooltip="Simulate gradual timing drift between the left and right hands")
        add_detailed_row(3, "Mistakes", "mistake_chance", 0, 10, 0, "%", factor=100.0, decimals=1,
                         tooltip="Randomly skip notes to simulate human errors")
        add_detailed_row(4, "Tempo Sway", "tempo_sway", 0, 0.1, 0, " s", factor=10000.0,
                         tooltip="Apply a sinusoidal tempo variation across the song for a more expressive feel")

        self.invert_sway_check = QCheckBox("Invert Sway")
        self.invert_sway_check.setToolTip("Invert the phase of the tempo sway curve")
        self.all_humanization_checks['invert_tempo_sway'] = self.invert_sway_check
        self.all_humanization_checks['tempo_sway'].toggled.connect(self.invert_sway_check.setEnabled)
        detailed_layout.addWidget(self.invert_sway_check, 5, 0)
        main_v_layout.addLayout(detailed_layout)
        
        self.all_humanization_checks['vary_velocity'] = QCheckBox() # Dummy for logic compatibility
        self.select_all_humanization_check.toggled.connect(self._toggle_all_humanization)
        for check in self.all_humanization_checks.values():
            if check.text(): check.toggled.connect(self._update_select_all_state)
            
        return group

    def reset_controls_to_default(self):
        self.tempo_spinbox.setValue(100)
        self.pedal_style_combo.setCurrentText("Auto (Default)")
        self.use_88_key_check.setChecked(False)
        self.countdown_check.setChecked(True)
        self.debug_check.setChecked(False)
        self.use_ai_pedal_check.setChecked(True)

        self.all_humanization_spinboxes['vary_timing'].setValue(0.010)
        self.all_humanization_spinboxes['vary_articulation'].setValue(95.0)
        self.all_humanization_spinboxes['hand_drift'].setValue(25.0)
        self.all_humanization_spinboxes['mistake_chance'].setValue(0.5)
        self.all_humanization_spinboxes['tempo_sway'].setValue(0.015)
        for check in self.all_humanization_checks.values(): 
            if check.text(): check.setChecked(False)
        self.update_enabled_states()

    def _toggle_all_humanization(self, checked):
        for check in self.all_humanization_checks.values(): 
            if check.text(): check.setChecked(checked)

    def _update_select_all_state(self):
        checks = [c for c in self.all_humanization_checks.values() if c.text()]
        is_all_checked = all(c.isChecked() for c in checks)
        self.select_all_humanization_check.blockSignals(True)
        self.select_all_humanization_check.setChecked(is_all_checked)
        self.select_all_humanization_check.blockSignals(False)

    def set_controls_enabled(self, enabled, ignore_if_loaded=False):
        # Strictly explicit groups. Avoids disabling visualizer/settings tabs.
        groups_to_toggle = [self.file_group, self.playback_group, self.humanization_group]
        for group in groups_to_toggle:
            if group in (self.playback_group, self.humanization_group) and ignore_if_loaded and enabled:
                continue 
            group.setEnabled(enabled)

    def update_enabled_states(self):
        for key, check in self.all_humanization_checks.items():
            if not check.text(): continue
            is_checked = check.isChecked()
            if key in self.all_humanization_sliders: self.all_humanization_sliders[key].setEnabled(is_checked)
            if key in self.all_humanization_spinboxes: self.all_humanization_spinboxes[key].setEnabled(is_checked)
        self.invert_sway_check.setEnabled(self.all_humanization_checks['tempo_sway'].isChecked())

    def copy_log_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.log_output.toPlainText())
        self.main_window.statusBar().showMessage("Log copied to clipboard!", 2000)

    def update_progress(self, current_time, total_duration):
        if self._vis_stack.currentIndex() == 0:
            if not self.timeline_widget.is_dragging:
                self.timeline_widget.set_position(current_time)
                self.update_time_label(current_time, total_duration)
                timeline_width = self.timeline_widget.width()
                scroll_width = self.scroll_area.width()
                if total_duration > 0:
                    ratio = current_time / total_duration
                    cursor_x = ratio * timeline_width
                    target_scroll = cursor_x - (scroll_width / 2)
                    self.scroll_area.horizontalScrollBar().setValue(int(target_scroll))
        else:
            if not self._simple_slider_dragging:
                self._simple_slider.blockSignals(True)
                if total_duration > 0:
                    self._simple_slider.setValue(int(current_time / total_duration * 10000))
                self._simple_slider.blockSignals(False)
                self.update_time_label(current_time, total_duration)

    def reset_timeline_position(self):
        self.timeline_widget.current_time = 0.0
        self._simple_slider.blockSignals(True)
        self._simple_slider.setValue(0)
        self._simple_slider.blockSignals(False)

    def _on_timeline_toggle(self, checked):
        self._vis_stack.setCurrentIndex(0 if checked else 1)

    def _on_piano_toggle(self, checked):
        self.piano_widget.setVisible(checked)

    def _on_simple_slider_pressed(self):
        self._simple_slider_dragging = True

    def _on_simple_slider_moved(self, value):
        if self.timeline_widget.total_duration > 0:
            t = (value / 10000.0) * self.timeline_widget.total_duration
            self.timeline_widget.current_time = t
            self.timeline_widget.scrub_position_changed.emit(t)
            self.update_time_label(t, self.timeline_widget.total_duration)

    def _on_simple_slider_released(self):
        self._simple_slider_dragging = False
        self.timeline_widget.seek_requested.emit(self.timeline_widget.current_time)

    def update_time_label(self, current, total):
        def fmt(s):
            m = int(s // 60); sec = int(s % 60)
            return f"{m:02d}:{sec:02d}"
        self.time_label.setText(f"{fmt(current)} / {fmt(total)}")

    def load_config_to_ui(self, config, save_dir):
        self.tempo_spinbox.setValue(config.get('tempo', 100.0))
        internal_style = config.get('pedal_style', 'hybrid')
        display_text = self.pedal_mapping_inv.get(internal_style, "Auto (Default)")
        self.pedal_style_combo.setCurrentText(display_text)
        self.use_88_key_check.setChecked(config.get('use_88_key_layout', False))
        self.countdown_check.setChecked(config.get('countdown', True))
        self.debug_check.setChecked(config.get('debug_mode', False))
        self.select_all_humanization_check.setChecked(config.get('select_all_humanization', False))
        self.all_humanization_checks['simulate_hands'].setChecked(config.get('simulate_hands', False))
        self.all_humanization_checks['enable_chord_roll'].setChecked(config.get('enable_chord_roll', False))
        self.all_humanization_checks['vary_timing'].setChecked(config.get('enable_vary_timing', False))
        self.all_humanization_spinboxes['vary_timing'].setValue(config.get('value_timing_variance', 0.010))
        self.all_humanization_checks['vary_articulation'].setChecked(config.get('enable_vary_articulation', False))
        self.all_humanization_spinboxes['vary_articulation'].setValue(config.get('value_articulation', 95.0))
        self.all_humanization_checks['hand_drift'].setChecked(config.get('enable_hand_drift', False))
        self.all_humanization_spinboxes['hand_drift'].setValue(config.get('value_hand_drift_decay', 25.0))
        self.all_humanization_checks['mistake_chance'].setChecked(config.get('enable_mistakes', False))
        self.all_humanization_spinboxes['mistake_chance'].setValue(config.get('value_mistake_chance', 0.5))
        self.all_humanization_checks['tempo_sway'].setChecked(config.get('enable_tempo_sway', False))
        self.all_humanization_spinboxes['tempo_sway'].setValue(config.get('value_tempo_sway_intensity', 0.015))
        self.all_humanization_checks['invert_tempo_sway'].setChecked(config.get('invert_tempo_sway', False))
        self.use_ai_pedal_check.setChecked(config.get('use_ai_pedal', True))
        self.always_top_check.setChecked(config.get('always_on_top', False))
        self.opacity_slider.setValue(config.get('opacity', 100))
        self.timeline_vis_check.setChecked(config.get('show_timeline_visualizer', True))
        self.piano_vis_check.setChecked(config.get('show_piano_visualizer', True))
        self.save_path_input.setText(save_dir)
        self.update_enabled_states()

    def gather_playback_config(self):
        """Constructs strictly the properties necessary for executing/modifying MIDI objects"""
        display_text = self.pedal_style_combo.currentText()
        internal_style = self.pedal_mapping.get(display_text, 'hybrid')
        return {
            'midi_file': self.file_path_label.toolTip(), 
            'tempo': self.tempo_spinbox.value(), 
            'countdown': self.countdown_check.isChecked(),
            'use_88_key_layout': self.use_88_key_check.isChecked(),
            'pedal_style': internal_style, 
            'debug_mode': self.debug_check.isChecked(),
            'simulate_hands': self.all_humanization_checks['simulate_hands'].isChecked(),
            'vary_velocity': False,
            'enable_chord_roll': self.all_humanization_checks['enable_chord_roll'].isChecked(),
            'vary_timing': self.all_humanization_checks['vary_timing'].isChecked(), 
            'timing_variance': self.all_humanization_spinboxes['vary_timing'].value(),
            'vary_articulation': self.all_humanization_checks['vary_articulation'].isChecked(), 
            'articulation': self.all_humanization_spinboxes['vary_articulation'].value() / 100.0,
            'enable_drift_correction': self.all_humanization_checks['hand_drift'].isChecked(), 
            'drift_decay_factor': self.all_humanization_spinboxes['hand_drift'].value() / 100.0,
            'enable_mistakes': self.all_humanization_checks['mistake_chance'].isChecked(), 
            'mistake_chance': self.all_humanization_spinboxes['mistake_chance'].value(),
            'enable_tempo_sway': self.all_humanization_checks['tempo_sway'].isChecked(), 
            'tempo_sway_intensity': self.all_humanization_spinboxes['tempo_sway'].value(),
            'invert_tempo_sway': self.all_humanization_checks['invert_tempo_sway'].isChecked(),
            'use_ai_pedal': self.use_ai_pedal_check.isChecked(),
        }

    def gather_app_config(self):
        """Constructs an exhaustive dictionary of all physical widget states to be serialized"""
        display_text = self.pedal_style_combo.currentText()
        internal_style = self.pedal_mapping.get(display_text, 'hybrid')
        return {
            'tempo': self.tempo_spinbox.value(),
            'pedal_style': internal_style,
            'use_88_key_layout': self.use_88_key_check.isChecked(),
            'countdown': self.countdown_check.isChecked(),
            'debug_mode': self.debug_check.isChecked(),
            'select_all_humanization': self.select_all_humanization_check.isChecked(),
            'simulate_hands': self.all_humanization_checks['simulate_hands'].isChecked(),
            'enable_chord_roll': self.all_humanization_checks['enable_chord_roll'].isChecked(),
            'enable_vary_timing': self.all_humanization_checks['vary_timing'].isChecked(), 
            'value_timing_variance': self.all_humanization_spinboxes['vary_timing'].value(),
            'enable_vary_articulation': self.all_humanization_checks['vary_articulation'].isChecked(), 
            'value_articulation': self.all_humanization_spinboxes['vary_articulation'].value(),
            'enable_hand_drift': self.all_humanization_checks['hand_drift'].isChecked(), 
            'value_hand_drift_decay': self.all_humanization_spinboxes['hand_drift'].value(),
            'enable_mistakes': self.all_humanization_checks['mistake_chance'].isChecked(), 
            'value_mistake_chance': self.all_humanization_spinboxes['mistake_chance'].value(),
            'enable_tempo_sway': self.all_humanization_checks['tempo_sway'].isChecked(), 
            'value_tempo_sway_intensity': self.all_humanization_spinboxes['tempo_sway'].value(),
            'invert_tempo_sway': self.all_humanization_checks['invert_tempo_sway'].isChecked(),
            'use_ai_pedal': self.use_ai_pedal_check.isChecked(),
            'always_on_top': self.always_top_check.isChecked(),
            'opacity': self.opacity_slider.value(),
            'show_timeline_visualizer': self.timeline_vis_check.isChecked(),
            'show_piano_visualizer': self.piano_vis_check.isChecked(),
        }