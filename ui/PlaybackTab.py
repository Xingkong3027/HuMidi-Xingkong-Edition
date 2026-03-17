from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox, QSlider,
    QLabel, QComboBox, QDoubleSpinBox, QSpinBox, QGridLayout, QFrame)
from PyQt6.QtCore import Qt

from ui.widgets import make_card


class PlaybackTab(QWidget):

    PEDAL_MAPPING = {
        "Auto (Default)": "hybrid",
        "PedalAI":        "ai",
        "Harmonic":        "legato",
        "Rhythmic":        "rhythmic",
        "None":            "none",
    }
    PEDAL_MAPPING_INV = {v: k for k, v in PEDAL_MAPPING.items()}

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(12)

        left_col = QVBoxLayout()
        left_col.setSpacing(10)
        self.file_group = self._create_file_group()
        left_col.addWidget(self.file_group)
        self.playback_group = self._create_playback_group()
        left_col.addWidget(self.playback_group, 1)

        right_col = QVBoxLayout()
        right_col.setSpacing(10)
        self.humanization_group = self._create_humanization_group()
        right_col.addWidget(self.humanization_group, 1)

        outer.addLayout(left_col, 1)
        outer.addLayout(right_col, 1)

    # ── Card builders ──────────────────────────────────────────────────

    def _create_file_group(self):
        card, layout = make_card("MIDI File")

        self.file_path_label = QLabel("No file selected.")
        self.file_path_label.setObjectName("file_path_label")
        self.file_path_label.setWordWrap(True)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        self.browse_button = QPushButton("Browse…")
        self.browse_button.setToolTip("Open a MIDI file to play")
        self.load_saved_btn = QPushButton("Load Save")
        self.load_saved_btn.setToolTip("Load a previously saved humanized performance")
        btn_layout.addWidget(self.browse_button)
        btn_layout.addWidget(self.load_saved_btn)

        layout.addWidget(self.file_path_label)
        layout.addLayout(btn_layout)
        return card

    def _create_playback_group(self):
        card, layout = make_card("Playback")
        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setColumnMinimumWidth(1, 8)
        grid.setColumnStretch(2, 1)

        tempo_label = QLabel("Tempo")
        self.tempo_slider, self.tempo_spinbox = self._make_slider_spinbox(
            10.0, 200.0, 100.0, "%", factor=10.0, decimals=1
        )
        self.tempo_spinbox.setFixedWidth(72)
        self.tempo_slider.setToolTip("Playback speed as a percentage of the original tempo")
        self.tempo_spinbox.setToolTip("Playback speed as a percentage of the original tempo")
        grid.addWidget(tempo_label, 0, 0)
        grid.addWidget(self.tempo_slider, 0, 2)
        grid.addWidget(self.tempo_spinbox, 0, 3)

        pedal_label = QLabel("Pedal")
        self.pedal_style_combo = QComboBox()
        self.pedal_style_combo.addItems(list(self.PEDAL_MAPPING.keys()))
        self.pedal_style_combo.setToolTip(
            "Auto (Default): Adaptive hybrid of rhythmic and harmonic analysis\n"
            "AI Pedal: BiLSTM model-generated pedal with adaptive fallback\n"
            "Harmonic: Hold pedal through harmonic regions, releasing at chord/bass changes\n"
            "Rhythmic: Release pedal on beat boundaries only\n"
            "None: No sustain pedal"
        )
        grid.addWidget(pedal_label, 1, 0)
        grid.addWidget(self.pedal_style_combo, 1, 2, 1, 2)

        transpose_label = QLabel("Transpose")
        self.transpose_spinbox = QSpinBox()
        self.transpose_spinbox.setRange(-24, 24)
        self.transpose_spinbox.setValue(0)
        self.transpose_spinbox.setSuffix(" st")
        self.transpose_spinbox.setFixedWidth(72)
        self.transpose_spinbox.setToolTip("Shift all notes up or down by the given number of semitones")
        grid.addWidget(transpose_label, 2, 0)
        grid.addWidget(self.transpose_spinbox, 2, 2, 1, 2)

        self.use_88_key_check = QCheckBox("88-Key Layout")
        self.use_88_key_check.setToolTip(
            "Map notes to the full 88-key piano layout instead of a compressed keyboard layout"
        )
        self.countdown_check = QCheckBox("Countdown")
        self.countdown_check.setToolTip("Show a 3-second countdown before playback begins")
        self.debug_check = QCheckBox("Debug Output")
        self.debug_check.setToolTip("Print verbose event logs to the Debug tab during playback")
        layout.addLayout(grid)
        layout.addWidget(self.use_88_key_check)
        layout.addWidget(self.countdown_check)
        layout.addWidget(self.debug_check)
        layout.addStretch()
        return card

    def _create_humanization_group(self):
        card, main_v_layout = make_card("Humanization")

        self.select_all_humanization_check = QCheckBox("All")
        self.select_all_humanization_check.setToolTip(
            "Enable or disable all humanization options at once"
        )

        self.all_humanization_checks = {}
        self.all_humanization_spinboxes = {}
        self.all_humanization_sliders = {}

        self.all_humanization_checks['simulate_hands'] = QCheckBox("Simulate Hands")
        self.all_humanization_checks['simulate_hands'].setToolTip(
            "Assign notes to left/right hand and limit simultaneous finger usage "
            "to simulate realistic hand behavior"
        )
        self.all_humanization_checks['enable_chord_roll'] = QCheckBox("Chord Roll")
        self.all_humanization_checks['enable_chord_roll'].setToolTip(
            "Slightly stagger the notes within each chord to simulate the natural "
            "roll of fingers across the keys"
        )

        main_v_layout.addWidget(self.select_all_humanization_check)
        main_v_layout.addWidget(self.all_humanization_checks['simulate_hands'])
        main_v_layout.addWidget(self.all_humanization_checks['enable_chord_roll'])

        h_sep = QFrame()
        h_sep.setObjectName("h_sep")
        h_sep.setFrameShape(QFrame.Shape.HLine)
        main_v_layout.addWidget(h_sep)

        detailed_layout = QGridLayout()
        detailed_layout.setSpacing(6)
        detailed_layout.setColumnStretch(2, 1)
        detailed_layout.setColumnMinimumWidth(1, 4)

        def add_row(row_idx, name, key, min_val, max_val, def_val,
                    suffix, factor=1.0, decimals=3, tooltip=""):
            check = QCheckBox(name)
            slider, spinbox = self._make_slider_spinbox(
                min_val, max_val, def_val, suffix, factor=factor, decimals=decimals
            )
            spinbox.setFixedWidth(80)
            check.toggled.connect(slider.setEnabled)
            check.toggled.connect(spinbox.setEnabled)
            if tooltip:
                check.setToolTip(tooltip)
                slider.setToolTip(tooltip)
                spinbox.setToolTip(tooltip)
            detailed_layout.addWidget(check,   row_idx, 0)
            detailed_layout.addWidget(slider,  row_idx, 2)
            detailed_layout.addWidget(spinbox, row_idx, 3)
            self.all_humanization_checks[key]   = check
            self.all_humanization_sliders[key]  = slider
            self.all_humanization_spinboxes[key] = spinbox

        add_row(0, "Vary Timing",       "vary_timing",       0,  0.1, 0.01, " s",
                factor=10000.0,
                tooltip="Add random timing offsets to note events (in seconds)")
        add_row(1, "Vary Articulation", "vary_articulation", 50, 100,   95, "%",
                factor=100.0, decimals=1,
                tooltip="Randomize note hold duration — lower values create a more staccato feel")
        add_row(2, "Hand Drift",        "hand_drift",         0, 100,   25, "%",
                factor=100.0, decimals=1,
                tooltip="Simulate gradual timing drift between the left and right hands")
        add_row(3, "Mistakes",          "mistake_chance",     0,  10,    0, "%",
                factor=100.0, decimals=1,
                tooltip="Randomly skip notes to simulate human errors")
        add_row(4, "Tempo Sway",        "tempo_sway",         0, 0.1,   0, " s",
                factor=10000.0,
                tooltip="Apply a sinusoidal tempo variation across the song for a more expressive feel")

        self.invert_sway_check = QCheckBox("Invert Sway")
        self.invert_sway_check.setToolTip("Invert the phase of the tempo sway curve")
        self.all_humanization_checks['invert_tempo_sway'] = self.invert_sway_check
        self.all_humanization_checks['tempo_sway'].toggled.connect(
            self.invert_sway_check.setEnabled
        )
        detailed_layout.addWidget(self.invert_sway_check, 5, 0)

        main_v_layout.addLayout(detailed_layout)
        main_v_layout.addStretch()

        self.all_humanization_checks['vary_velocity'] = QCheckBox()  # dummy for logic compat
        self.select_all_humanization_check.toggled.connect(self._toggle_all)
        for check in self.all_humanization_checks.values():
            if check.text():
                check.toggled.connect(self._update_select_all_state)

        return card

    # ── Widget factory ─────────────────────────────────────────────────

    @staticmethod
    def _make_slider_spinbox(min_val, max_val, default_val,
                             text_suffix="", factor=10000.0, decimals=4):
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

    # ── Humanization helpers ───────────────────────────────────────────

    def _toggle_all(self, checked: bool) -> None:
        for check in self.all_humanization_checks.values():
            if check.text():
                check.setChecked(checked)

    def _update_select_all_state(self) -> None:
        checks = [c for c in self.all_humanization_checks.values() if c.text()]
        self.select_all_humanization_check.blockSignals(True)
        self.select_all_humanization_check.setChecked(all(c.isChecked() for c in checks))
        self.select_all_humanization_check.blockSignals(False)

    # ── Public API ─────────────────────────────────────────────────────

    def update_file_label(self, text: str, tooltip: str = "") -> None:
        self.file_path_label.setText(text)
        self.file_path_label.setToolTip(tooltip)

    def set_groups_enabled(self, enabled: bool, skip_playback_humanization: bool = False) -> None:
        self.file_group.setEnabled(enabled)
        if not skip_playback_humanization:
            self.playback_group.setEnabled(enabled)
            self.humanization_group.setEnabled(enabled)

    def update_enabled_states(self) -> None:
        for key, check in self.all_humanization_checks.items():
            if not check.text():
                continue
            checked = check.isChecked()
            if key in self.all_humanization_sliders:
                self.all_humanization_sliders[key].setEnabled(checked)
            if key in self.all_humanization_spinboxes:
                self.all_humanization_spinboxes[key].setEnabled(checked)
        self.invert_sway_check.setEnabled(
            self.all_humanization_checks['tempo_sway'].isChecked()
        )

    def reset_to_default(self) -> None:
        self.tempo_spinbox.setValue(100)
        self.transpose_spinbox.setValue(0)
        self.pedal_style_combo.setCurrentText("Auto (Default)")
        self.use_88_key_check.setChecked(False)
        self.countdown_check.setChecked(True)
        self.debug_check.setChecked(False)
        self.all_humanization_spinboxes['vary_timing'].setValue(0.010)
        self.all_humanization_spinboxes['vary_articulation'].setValue(95.0)
        self.all_humanization_spinboxes['hand_drift'].setValue(25.0)
        self.all_humanization_spinboxes['mistake_chance'].setValue(0.5)
        self.all_humanization_spinboxes['tempo_sway'].setValue(0.015)
        for check in self.all_humanization_checks.values():
            if check.text():
                check.setChecked(False)
        self.update_enabled_states()

    def load_config(self, config: dict) -> None:
        self.tempo_spinbox.setValue(config.get('tempo', 100.0))
        self.transpose_spinbox.setValue(config.get('transpose', 0))
        display = self.PEDAL_MAPPING_INV.get(config.get('pedal_style', 'hybrid'), "Auto (Default)")
        self.pedal_style_combo.setCurrentText(display)
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
        self.update_enabled_states()

    def gather_playback_config(self) -> dict:
        internal = self.PEDAL_MAPPING.get(self.pedal_style_combo.currentText(), 'hybrid')
        return {
            'midi_file':             self.file_path_label.toolTip(),
            'tempo':                 self.tempo_spinbox.value(),
            'transpose':             self.transpose_spinbox.value(),
            'countdown':             self.countdown_check.isChecked(),
            'use_88_key_layout':     self.use_88_key_check.isChecked(),
            'pedal_style':           internal,
            'debug_mode':            self.debug_check.isChecked(),
            'simulate_hands':        self.all_humanization_checks['simulate_hands'].isChecked(),
            'vary_velocity':         False,
            'enable_chord_roll':     self.all_humanization_checks['enable_chord_roll'].isChecked(),
            'vary_timing':           self.all_humanization_checks['vary_timing'].isChecked(),
            'timing_variance':       self.all_humanization_spinboxes['vary_timing'].value(),
            'vary_articulation':     self.all_humanization_checks['vary_articulation'].isChecked(),
            'articulation':          self.all_humanization_spinboxes['vary_articulation'].value() / 100.0,
            'enable_drift_correction': self.all_humanization_checks['hand_drift'].isChecked(),
            'drift_decay_factor':    self.all_humanization_spinboxes['hand_drift'].value() / 100.0,
            'enable_mistakes':       self.all_humanization_checks['mistake_chance'].isChecked(),
            'mistake_chance':        self.all_humanization_spinboxes['mistake_chance'].value(),
            'enable_tempo_sway':     self.all_humanization_checks['tempo_sway'].isChecked(),
            'tempo_sway_intensity':  self.all_humanization_spinboxes['tempo_sway'].value(),
            'invert_tempo_sway':     self.all_humanization_checks['invert_tempo_sway'].isChecked(),
        }

    def gather_app_config(self) -> dict:
        internal = self.PEDAL_MAPPING.get(self.pedal_style_combo.currentText(), 'hybrid')
        return {
            'tempo':                   self.tempo_spinbox.value(),
            'transpose':               self.transpose_spinbox.value(),
            'pedal_style':             internal,
            'use_88_key_layout':       self.use_88_key_check.isChecked(),
            'countdown':               self.countdown_check.isChecked(),
            'debug_mode':              self.debug_check.isChecked(),
            'select_all_humanization': self.select_all_humanization_check.isChecked(),
            'simulate_hands':          self.all_humanization_checks['simulate_hands'].isChecked(),
            'enable_chord_roll':       self.all_humanization_checks['enable_chord_roll'].isChecked(),
            'enable_vary_timing':      self.all_humanization_checks['vary_timing'].isChecked(),
            'value_timing_variance':   self.all_humanization_spinboxes['vary_timing'].value(),
            'enable_vary_articulation': self.all_humanization_checks['vary_articulation'].isChecked(),
            'value_articulation':      self.all_humanization_spinboxes['vary_articulation'].value(),
            'enable_hand_drift':       self.all_humanization_checks['hand_drift'].isChecked(),
            'value_hand_drift_decay':  self.all_humanization_spinboxes['hand_drift'].value(),
            'enable_mistakes':         self.all_humanization_checks['mistake_chance'].isChecked(),
            'value_mistake_chance':    self.all_humanization_spinboxes['mistake_chance'].value(),
            'enable_tempo_sway':       self.all_humanization_checks['tempo_sway'].isChecked(),
            'value_tempo_sway_intensity': self.all_humanization_spinboxes['tempo_sway'].value(),
            'invert_tempo_sway':       self.all_humanization_checks['invert_tempo_sway'].isChecked(),
        }
