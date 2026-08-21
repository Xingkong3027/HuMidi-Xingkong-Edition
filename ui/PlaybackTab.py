from __future__ import annotations

import secrets

from PyQt6.QtCore import QRegularExpression, QTimer, Qt
from PyQt6.QtGui import QIntValidator, QRegularExpressionValidator
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.performance import config_bool
from ui.widgets import make_card


class PlaybackTab(QWidget):
    PEDAL_MAPPING = {
        "Auto (Default)": "hybrid",
        "Harmonic": "legato",
        "Rhythmic": "rhythmic",
        "None": "none",
    }
    PEDAL_MAPPING_INV = {v: k for k, v in PEDAL_MAPPING.items()}

    HUMANIZATION_MODES = [
        ("disabled", "Disabled"),
        ("global", "Enabled (Use Global Settings)"),
        ("individual", "Enabled (Individual Settings)"),
    ]
    SEED_MODES = [
        ("dynamic", "Dynamic Random Seed"),
        ("fixed_random", "Fixed Random Seed"),
        ("fixed_custom", "Fixed Custom Seed"),
    ]

    HUMANIZATION_DEFAULTS = {
        "simulate_hands": False,
        "enable_chord_roll": False,
        "vary_timing": False,
        "timing_variance": 0.010,
        "vary_articulation": False,
        "articulation": 0.95,
        "enable_drift_correction": False,
        "drift_decay_factor": 0.25,
        "enable_mistakes": False,
        "mistake_chance": 0.5,
        "enable_tempo_sway": False,
        "tempo_sway_intensity": 0.015,
        "invert_tempo_sway": False,
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loading_humanization = False
        self._midi_clip_invalid_data = False
        self._tr = lambda text: text
        self._global_humanization_config = dict(self.HUMANIZATION_DEFAULTS)
        self._trim_source_bounds = (0.0, 0.0)
        self._batch_change_tracking = False
        self._batch_dirty_keys: set[str] = set()
        self._setup_ui()

    @staticmethod
    def _keep_card_size(card: QWidget) -> None:
        """Keep playback cards at their natural height and scroll when needed."""
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _setup_ui(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(12)

        # The left-side file/playback controls used to be placed directly in
        # the page layout. At the minimum window height Qt therefore compressed
        # both cards until labels and controls overlapped. Keep their natural
        # height inside a scroll area instead, matching the Settings page.
        left_content = QWidget()
        left_content.setObjectName("playback_left_scroll_content")
        left_content.setMinimumWidth(360)
        self.left_content = left_content
        left_col = QVBoxLayout(left_content)
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.setSpacing(10)

        self.file_group = self._create_file_group()
        self._keep_card_size(self.file_group)
        left_col.addWidget(self.file_group)

        self.playback_group = self._create_playback_group()
        self._keep_card_size(self.playback_group)
        left_col.addWidget(self.playback_group)
        left_col.addStretch()

        self.left_scroll_area = QScrollArea()
        self.left_scroll_area.setObjectName("playback_left_scroll_area")
        self.left_scroll_area.setWidgetResizable(True)
        self.left_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.left_scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.left_scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.left_scroll_area.setWidget(left_content)

        self.humanization_group = self._create_humanization_group()
        self._keep_card_size(self.humanization_group)
        self.humanization_scroll_area = QScrollArea()
        self.humanization_scroll_area.setObjectName("humanization_scroll_area")
        self.humanization_scroll_area.setWidgetResizable(True)
        self.humanization_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.humanization_scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.humanization_scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.humanization_scroll_area.setWidget(self.humanization_group)

        outer.addWidget(self.left_scroll_area, 1)
        outer.addWidget(self.humanization_scroll_area, 1)

        # The two columns contain different numbers of cards, so their natural
        # heights are not identical. Match the right card to the complete left
        # column (file card + playback card + spacing) and put any extra room
        # into the existing bottom stretch inside the humanization card. This
        # keeps both bordered columns visually aligned without stretching or
        # squeezing individual controls.
        self._base_humanization_height = 0
        self._connect_batch_change_tracking()
        QTimer.singleShot(0, self._sync_column_card_heights)

    def _sync_column_card_heights(self) -> None:
        if not hasattr(self, "left_content") or not hasattr(self, "humanization_group"):
            return
        if self._base_humanization_height <= 0:
            self._base_humanization_height = max(
                1, self.humanization_group.sizeHint().height()
            )
        left_layout = self.left_content.layout()
        left_height = (
            left_layout.sizeHint().height()
            if left_layout is not None
            else self.left_content.sizeHint().height()
        )
        target_height = max(self._base_humanization_height, left_height)
        if self.humanization_group.minimumHeight() != target_height:
            self.humanization_group.setMinimumHeight(target_height)
            self.humanization_group.updateGeometry()

    def _schedule_column_height_sync(self) -> None:
        QTimer.singleShot(0, self._sync_column_card_heights)

    # ── Card builders ──────────────────────────────────────────────────

    def _create_file_group(self):
        card, layout = make_card("MIDI File")

        self.file_path_label = QLabel("No file selected.")
        self.file_path_label.setObjectName("file_path_label")
        self.file_path_label.setProperty("i18n_dynamic", True)
        self.file_path_label.setWordWrap(True)

        file_actions = QGridLayout()
        file_actions.setHorizontalSpacing(6)
        file_actions.setVerticalSpacing(6)

        self.browse_button = QPushButton("Import MIDI (Multi-select)")
        self.browse_button.setToolTip("Import one or more MIDI files")
        self.load_saved_btn = QPushButton("Load Save")
        self.load_saved_btn.setToolTip("Load a previously saved humanized performance")

        # Keep these as ordinary buttons so they use the same palette and hover
        # styling as the import/load actions above.
        self.reset_button = QPushButton("Reset")
        self.reset_button.setToolTip("Reset all playback settings to their default values")
        self.save_button = QPushButton("Save Playback")
        self.save_button.setToolTip(
            "Save the current simulated performance to a file for later replay"
        )

        file_actions.addWidget(self.browse_button, 0, 0)
        file_actions.addWidget(self.load_saved_btn, 0, 1)
        file_actions.addWidget(self.reset_button, 1, 0)
        file_actions.addWidget(self.save_button, 1, 1)
        file_actions.setColumnStretch(0, 1)
        file_actions.setColumnStretch(1, 1)

        self.add_to_playlist_btn = QPushButton("Add to Playlist")
        self.add_to_playlist_btn.setProperty("i18n_dynamic", True)
        self.add_to_playlist_btn.setToolTip(
            "Store the original MIDI, current settings, track choices, and optional compiled cache in the playlist"
        )
        self.add_to_playlist_btn.setEnabled(False)

        layout.addWidget(self.file_path_label)
        layout.addLayout(file_actions)
        layout.addWidget(self.add_to_playlist_btn)
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
        for display, internal in self.PEDAL_MAPPING.items():
            self.pedal_style_combo.addItem(display, internal)
        self.pedal_style_combo.setToolTip(
            "Auto (Default): AI-driven pedal using a hybrid of rhythmic and harmonic analysis\n"
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
        self.countdown_seconds_slider = QSlider(Qt.Orientation.Horizontal)
        self.countdown_seconds_slider.setRange(1, 10)
        self.countdown_seconds_slider.setValue(3)
        self.countdown_seconds_spinbox = QSpinBox()
        self.countdown_seconds_spinbox.setRange(1, 10)
        self.countdown_seconds_spinbox.setValue(3)
        self.countdown_seconds_spinbox.setSuffix(" s")
        self.countdown_seconds_spinbox.setFixedWidth(64)
        self.countdown_seconds_slider.valueChanged.connect(
            self.countdown_seconds_spinbox.setValue
        )
        self.countdown_seconds_spinbox.valueChanged.connect(
            self.countdown_seconds_slider.setValue
        )
        self.countdown_seconds_spinbox.valueChanged.connect(
            self._update_countdown_controls
        )
        self.countdown_check.toggled.connect(self._update_countdown_controls)
        countdown_row = QHBoxLayout()
        countdown_row.setSpacing(8)
        countdown_row.addWidget(self.countdown_check)
        countdown_row.addWidget(self.countdown_seconds_slider, 1)
        countdown_row.addWidget(self.countdown_seconds_spinbox)

        self.trim_check = QCheckBox("Trim")
        self.trim_auto_check = QCheckBox("Auto")
        self.trim_start_input = QLineEdit("00:00")
        self.trim_end_input = QLineEdit("00:00")
        time_validator = QRegularExpressionValidator(
            QRegularExpression(r"^(?:\d{1,3}:)?[0-5]?\d$"), self
        )
        for edit in (self.trim_start_input, self.trim_end_input):
            edit.setValidator(time_validator)
            edit.setFixedWidth(72)
            edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.trim_start_input.setPlaceholderText("00:00")
        self.trim_end_input.setPlaceholderText("00:00")
        self.trim_range_separator = QLabel("–")
        self.trim_range_separator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        trim_row = QHBoxLayout()
        trim_row.setSpacing(8)
        trim_row.addWidget(self.trim_check)
        trim_row.addWidget(self.trim_auto_check)
        trim_row.addStretch(1)
        trim_row.addWidget(self.trim_start_input)
        trim_row.addWidget(self.trim_range_separator)
        trim_row.addWidget(self.trim_end_input)
        self.trim_check.toggled.connect(self._update_trim_controls)
        self.trim_auto_check.toggled.connect(self._update_trim_controls)
        self.tempo_spinbox.valueChanged.connect(self._refresh_auto_trim_display)

        self.performance_optimization_check = QCheckBox("Performance Optimization")
        self.performance_optimization_check.setToolTip(
            "Reduce input overhead for complex MIDI files by collapsing duplicate simultaneous "
            "physical keystrokes while retaining HuMidi's pynput input backend. Disable to use "
            "the original playback logic."
        )
        self.debug_check = QCheckBox("Debug Output")
        self.debug_check.setToolTip("Print verbose event logs to the Debug tab during playback")
        layout.addLayout(grid)
        layout.addWidget(self.use_88_key_check)
        layout.addLayout(countdown_row)
        layout.addLayout(trim_row)
        layout.addWidget(self.performance_optimization_check)
        layout.addWidget(self.debug_check)
        self._update_countdown_controls()
        self._update_trim_controls()
        layout.addStretch()
        return card

    def _update_countdown_controls(self, *_args) -> None:
        enabled = self.countdown_check.isChecked()
        self.countdown_seconds_slider.setEnabled(enabled)
        self.countdown_seconds_spinbox.setEnabled(enabled)
        seconds = self.countdown_seconds_spinbox.value()
        tooltip = self._tr("Show a {seconds}-second countdown before playback begins").format(
            seconds=seconds
        )
        self.countdown_check.setToolTip(tooltip)
        self.countdown_seconds_slider.setToolTip(tooltip)
        self.countdown_seconds_spinbox.setToolTip(tooltip)

    @staticmethod
    def _format_time_value(seconds: float) -> str:
        total = max(0, int(round(float(seconds or 0.0))))
        return f"{total // 60:02d}:{total % 60:02d}"

    @staticmethod
    def _parse_time_value(text: str) -> float:
        value = str(text or "").strip()
        if not value:
            return 0.0
        if ":" not in value:
            return float(max(0, int(value)))
        minute_text, second_text = value.rsplit(":", 1)
        minutes = max(0, int(minute_text or 0))
        seconds = max(0, min(59, int(second_text or 0)))
        return float(minutes * 60 + seconds)

    def set_trim_source_bounds(self, selected_tracks_info) -> None:
        starts = []
        ends = []
        for track, role in selected_tracks_info or []:
            if str(role) == "Ignore":
                continue
            for note in getattr(track, "notes", []) or []:
                starts.append(float(note.start_time))
                ends.append(float(note.end_time))
        self._trim_source_bounds = (
            min(starts) if starts else 0.0,
            max(ends) if ends else 0.0,
        )
        self._refresh_auto_trim_display()
        if not self.trim_auto_check.isChecked() and self._parse_time_value(
            self.trim_end_input.text()
        ) <= 0:
            tempo_scale = max(0.01, self.tempo_spinbox.value() / 100.0)
            self.trim_end_input.setText(
                self._format_time_value(self._trim_source_bounds[1] / tempo_scale)
            )

    def _refresh_auto_trim_display(self, *_args) -> None:
        if not hasattr(self, "trim_auto_check") or not self.trim_auto_check.isChecked():
            return
        tempo_scale = max(0.01, self.tempo_spinbox.value() / 100.0)
        start, end = self._trim_source_bounds
        self.trim_start_input.setText(self._format_time_value(start / tempo_scale))
        self.trim_end_input.setText(self._format_time_value(end / tempo_scale))

    def _update_trim_controls(self, *_args) -> None:
        enabled = self.trim_check.isChecked()
        automatic = enabled and self.trim_auto_check.isChecked()
        self.trim_auto_check.setEnabled(enabled)
        self.trim_start_input.setEnabled(enabled and not automatic)
        self.trim_end_input.setEnabled(enabled and not automatic)
        self.trim_range_separator.setEnabled(enabled)
        if automatic:
            self._refresh_auto_trim_display()
        tooltip = self._tr(
            "Trim leading and trailing silence by selecting a playback range"
        )
        auto_tooltip = self._tr(
            "Automatically detect the first and last playable notes"
        )
        self.trim_check.setToolTip(tooltip)
        self.trim_start_input.setToolTip(tooltip)
        self.trim_end_input.setToolTip(tooltip)
        self.trim_auto_check.setToolTip(auto_tooltip)

    def _create_humanization_group(self):
        card, main_v_layout = make_card("Human-like Performance")

        mode_grid = QGridLayout()
        mode_grid.setSpacing(7)
        self.humanization_mode_label = QLabel("Human-like Performance Mode")
        self.humanization_mode_combo = QComboBox()
        for value, text in self.HUMANIZATION_MODES:
            self.humanization_mode_combo.addItem(text, value)
        self.randomness_label = QLabel("Randomness")
        self.randomness_combo = QComboBox()
        for value, text in self.SEED_MODES:
            self.randomness_combo.addItem(text, value)
        self.random_seed_label = QLabel("Random Seed")
        self.random_seed_input = QLineEdit()
        self.random_seed_input.setValidator(QIntValidator(0, 2147483647, self))
        self.random_seed_input.setPlaceholderText("Generated for every playback")
        mode_grid.addWidget(self.humanization_mode_label, 0, 0)
        mode_grid.addWidget(self.humanization_mode_combo, 0, 1)
        mode_grid.addWidget(self.randomness_label, 1, 0)
        mode_grid.addWidget(self.randomness_combo, 1, 1)
        mode_grid.addWidget(self.random_seed_label, 2, 0)
        mode_grid.addWidget(self.random_seed_input, 2, 1)
        main_v_layout.addLayout(mode_grid)

        h_sep_top = QFrame()
        h_sep_top.setObjectName("h_sep")
        h_sep_top.setFrameShape(QFrame.Shape.HLine)
        main_v_layout.addWidget(h_sep_top)

        self.humanization_options_widget = QWidget()
        options_layout = QVBoxLayout(self.humanization_options_widget)
        options_layout.setContentsMargins(0, 0, 0, 0)
        options_layout.setSpacing(6)

        self.select_all_humanization_check = QCheckBox("All")
        self.select_all_humanization_check.setToolTip(
            "Enable or disable all human-like performance options at once"
        )

        self.all_humanization_checks = {}
        self.all_humanization_spinboxes = {}
        self.all_humanization_sliders = {}

        self.all_humanization_checks["simulate_hands"] = QCheckBox("Simulate Hands")
        self.all_humanization_checks["simulate_hands"].setToolTip(
            "Assign notes to left/right hand and limit simultaneous finger usage to simulate realistic hand behavior"
        )
        self.all_humanization_checks["enable_chord_roll"] = QCheckBox("Chord Roll")
        self.all_humanization_checks["enable_chord_roll"].setToolTip(
            "Slightly stagger the notes within each chord to simulate the natural roll of fingers across the keys"
        )

        options_layout.addWidget(self.select_all_humanization_check)
        options_layout.addWidget(self.all_humanization_checks["simulate_hands"])
        options_layout.addWidget(self.all_humanization_checks["enable_chord_roll"])

        h_sep = QFrame()
        h_sep.setObjectName("h_sep")
        h_sep.setFrameShape(QFrame.Shape.HLine)
        options_layout.addWidget(h_sep)

        detailed_layout = QGridLayout()
        detailed_layout.setSpacing(6)
        detailed_layout.setColumnStretch(2, 1)
        detailed_layout.setColumnMinimumWidth(1, 4)

        def add_row(row_idx, name, key, min_val, max_val, def_val, suffix, factor=1.0, decimals=3, tooltip=""):
            check = QCheckBox(name)
            slider, spinbox = self._make_slider_spinbox(
                min_val, max_val, def_val, suffix, factor=factor, decimals=decimals
            )
            spinbox.setFixedWidth(80)
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

        add_row(0, "Vary Timing", "vary_timing", 0, 0.1, 0.01, " s", factor=10000.0,
                tooltip="Add random timing offsets to note events (in seconds)")
        add_row(1, "Vary Articulation", "vary_articulation", 50, 100, 95, "%", factor=100.0, decimals=1,
                tooltip="Randomize note hold duration — lower values create a more staccato feel")
        add_row(2, "Hand Drift", "hand_drift", 0, 100, 25, "%", factor=100.0, decimals=1,
                tooltip="Simulate gradual timing drift between the left and right hands")
        add_row(3, "Mistakes", "mistake_chance", 0, 10, 0, "%", factor=100.0, decimals=1,
                tooltip="Randomly skip notes to simulate human errors")
        add_row(4, "Tempo Sway", "tempo_sway", 0, 0.1, 0, " s", factor=10000.0,
                tooltip="Apply a sinusoidal tempo variation across the song for a more expressive feel")

        self.invert_sway_check = QCheckBox("Invert Sway")
        self.invert_sway_check.setToolTip("Invert the phase of the tempo sway curve")
        self.all_humanization_checks["invert_tempo_sway"] = self.invert_sway_check
        detailed_layout.addWidget(self.invert_sway_check, 5, 0)

        options_layout.addLayout(detailed_layout)
        main_v_layout.addWidget(self.humanization_options_widget)
        main_v_layout.addStretch()

        self.all_humanization_checks["vary_velocity"] = QCheckBox()  # compatibility dummy
        self.select_all_humanization_check.toggled.connect(self._toggle_all)
        self.humanization_mode_combo.currentIndexChanged.connect(self._on_humanization_mode_changed)
        self.randomness_combo.currentIndexChanged.connect(self._on_randomness_changed)

        for key, check in self.all_humanization_checks.items():
            if not check.text():
                continue
            check.toggled.connect(self._update_select_all_state)
            check.toggled.connect(self._on_humanization_option_modified)
            if key in self.all_humanization_sliders:
                self.all_humanization_sliders[key].valueChanged.connect(self._on_humanization_option_modified)
            if key in self.all_humanization_spinboxes:
                self.all_humanization_spinboxes[key].valueChanged.connect(self._on_humanization_option_modified)

        self._on_humanization_mode_changed()
        return card

    # ── Widget factory ─────────────────────────────────────────────────

    @staticmethod
    def _make_slider_spinbox(min_val, max_val, default_val, text_suffix="", factor=10000.0, decimals=4):
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(int(min_val * factor), int(max_val * factor))
        spinbox = QDoubleSpinBox()
        spinbox.setDecimals(decimals)
        spinbox.setRange(min_val, max_val)
        spinbox.setSingleStep(1.0 / factor)
        spinbox.setSuffix(text_suffix)
        slider.setValue(int(default_val * factor))
        spinbox.setValue(default_val)
        slider.valueChanged.connect(lambda v: spinbox.setValue(v / factor))
        spinbox.valueChanged.connect(lambda v: slider.setValue(int(v * factor)))
        return slider, spinbox

    # ── Humanization helpers ───────────────────────────────────────────

    @staticmethod
    def _new_seed() -> int:
        return secrets.randbelow(2_147_483_646) + 1

    def regenerate_fixed_random_seed(self) -> None:
        if (self.current_humanization_mode() != "disabled"
                and self.current_seed_mode() == "fixed_random"):
            self.random_seed_input.setText(str(self._new_seed()))

    def _toggle_all(self, checked: bool) -> None:
        for check in self.all_humanization_checks.values():
            if check.text():
                check.setChecked(checked)

    def _update_select_all_state(self) -> None:
        checks = [c for c in self.all_humanization_checks.values() if c.text()]
        self.select_all_humanization_check.blockSignals(True)
        self.select_all_humanization_check.setChecked(bool(checks) and all(c.isChecked() for c in checks))
        self.select_all_humanization_check.blockSignals(False)

    def _on_humanization_option_modified(self, *_args) -> None:
        if self._loading_humanization:
            return
        self.regenerate_fixed_random_seed()
        self.update_enabled_states()

    def _on_humanization_mode_changed(self, *_args) -> None:
        mode = self.current_humanization_mode()
        if mode == "global":
            self._apply_humanization_values(self._global_humanization_config)
        # Switching between disabled/global/individual changes the effective
        # simulation setup. A fixed-random seed therefore starts a fresh, then
        # stable, performance unless this method is running during config load.
        if not self._loading_humanization:
            self.regenerate_fixed_random_seed()
        self.update_enabled_states()

    def _on_randomness_changed(self, *_args) -> None:
        mode = self.current_seed_mode()
        if self._loading_humanization:
            self.update_enabled_states()
            return
        if mode == "fixed_random":
            # Always draw a new seed when the user explicitly selects this
            # mode; do not accidentally reuse a value from Fixed Custom Seed.
            self.random_seed_input.setText(str(self._new_seed()))
        elif mode == "dynamic":
            self.random_seed_input.clear()
        elif mode == "fixed_custom" and not self.random_seed_input.text().strip():
            self.random_seed_input.setText("1")
        self.update_enabled_states()

    def current_humanization_mode(self) -> str:
        return str(self.humanization_mode_combo.currentData() or "disabled")

    def current_seed_mode(self) -> str:
        return str(self.randomness_combo.currentData() or "dynamic")

    def set_global_humanization_config(self, config: dict) -> None:
        self._global_humanization_config = {
            **self.HUMANIZATION_DEFAULTS,
            **{k: config[k] for k in self.HUMANIZATION_DEFAULTS if k in config},
        }
        if self.current_humanization_mode() == "global":
            self._apply_humanization_values(self._global_humanization_config)
            self.update_enabled_states()

    def _current_humanization_values(self) -> dict:
        return {
            "simulate_hands": self.all_humanization_checks["simulate_hands"].isChecked(),
            "enable_chord_roll": self.all_humanization_checks["enable_chord_roll"].isChecked(),
            "vary_timing": self.all_humanization_checks["vary_timing"].isChecked(),
            "timing_variance": self.all_humanization_spinboxes["vary_timing"].value(),
            "vary_articulation": self.all_humanization_checks["vary_articulation"].isChecked(),
            "articulation": self.all_humanization_spinboxes["vary_articulation"].value() / 100.0,
            "enable_drift_correction": self.all_humanization_checks["hand_drift"].isChecked(),
            "drift_decay_factor": self.all_humanization_spinboxes["hand_drift"].value() / 100.0,
            "enable_mistakes": self.all_humanization_checks["mistake_chance"].isChecked(),
            "mistake_chance": self.all_humanization_spinboxes["mistake_chance"].value(),
            "enable_tempo_sway": self.all_humanization_checks["tempo_sway"].isChecked(),
            "tempo_sway_intensity": self.all_humanization_spinboxes["tempo_sway"].value(),
            "invert_tempo_sway": self.all_humanization_checks["invert_tempo_sway"].isChecked(),
        }

    def _apply_humanization_values(self, config: dict) -> None:
        self._loading_humanization = True
        try:
            self.all_humanization_checks["simulate_hands"].setChecked(bool(config.get("simulate_hands", False)))
            self.all_humanization_checks["enable_chord_roll"].setChecked(bool(config.get("enable_chord_roll", False)))
            self.all_humanization_checks["vary_timing"].setChecked(bool(config.get("vary_timing", config.get("enable_vary_timing", False))))
            self.all_humanization_spinboxes["vary_timing"].setValue(float(config.get("timing_variance", config.get("value_timing_variance", 0.010))))
            self.all_humanization_checks["vary_articulation"].setChecked(bool(config.get("vary_articulation", config.get("enable_vary_articulation", False))))
            articulation = float(config.get("articulation", config.get("value_articulation", 95.0)))
            self.all_humanization_spinboxes["vary_articulation"].setValue(articulation * 100.0 if articulation <= 1.0 else articulation)
            self.all_humanization_checks["hand_drift"].setChecked(bool(config.get("enable_drift_correction", config.get("enable_hand_drift", False))))
            drift = float(config.get("drift_decay_factor", config.get("value_hand_drift_decay", 25.0)))
            self.all_humanization_spinboxes["hand_drift"].setValue(drift * 100.0 if drift <= 1.0 else drift)
            self.all_humanization_checks["mistake_chance"].setChecked(bool(config.get("enable_mistakes", False)))
            self.all_humanization_spinboxes["mistake_chance"].setValue(float(config.get("mistake_chance", config.get("value_mistake_chance", 0.5))))
            self.all_humanization_checks["tempo_sway"].setChecked(bool(config.get("enable_tempo_sway", False)))
            self.all_humanization_spinboxes["tempo_sway"].setValue(float(config.get("tempo_sway_intensity", config.get("value_tempo_sway_intensity", 0.015))))
            self.all_humanization_checks["invert_tempo_sway"].setChecked(bool(config.get("invert_tempo_sway", False)))
        finally:
            self._loading_humanization = False
        self._update_select_all_state()

    # ── Batch edit change tracking ────────────────────────────────────

    def _mark_batch_dirty(self, *keys: str) -> None:
        if not self._batch_change_tracking:
            return
        self._batch_dirty_keys.update(str(key) for key in keys if key)

    def _connect_batch_change_tracking(self) -> None:
        """Remember which controls the user touched during a batch edit.

        A final-value comparison is not sufficient here: a user may toggle a
        control off and back on specifically to apply that option to every
        selected song.  Tracking interactions also lets automatic trim be
        applied independently to each song even when the preview song already
        had the same visible value.
        """
        self.tempo_spinbox.valueChanged.connect(
            lambda _value: self._mark_batch_dirty("tempo")
        )
        self.transpose_spinbox.valueChanged.connect(
            lambda _value: self._mark_batch_dirty("transpose")
        )
        self.pedal_style_combo.currentIndexChanged.connect(
            lambda _index: self._mark_batch_dirty("pedal_style")
        )
        self.use_88_key_check.toggled.connect(
            lambda _checked: self._mark_batch_dirty("use_88_key_layout")
        )
        self.countdown_check.toggled.connect(
            lambda _checked: self._mark_batch_dirty("countdown")
        )
        self.countdown_seconds_spinbox.valueChanged.connect(
            lambda _value: self._mark_batch_dirty("countdown_seconds")
        )
        self.trim_check.toggled.connect(
            lambda _checked: self._mark_batch_dirty("trim_enabled")
        )
        self.trim_auto_check.toggled.connect(
            lambda _checked: self._mark_batch_dirty("trim_auto")
        )
        self.trim_start_input.textEdited.connect(
            lambda _text: self._mark_batch_dirty("trim_start_seconds")
        )
        self.trim_end_input.textEdited.connect(
            lambda _text: self._mark_batch_dirty("trim_end_seconds")
        )
        self.performance_optimization_check.toggled.connect(
            lambda _checked: self._mark_batch_dirty("performance_optimization")
        )
        self.debug_check.toggled.connect(
            lambda _checked: self._mark_batch_dirty("debug_mode")
        )
        self.humanization_mode_combo.currentIndexChanged.connect(
            lambda _index: self._mark_batch_dirty(
                "humanization_mode", "humanization_seed"
            )
        )
        self.randomness_combo.currentIndexChanged.connect(
            lambda _index: self._mark_batch_dirty(
                "humanization_seed_mode", "humanization_seed"
            )
        )
        self.random_seed_input.textEdited.connect(
            lambda _text: self._mark_batch_dirty("humanization_seed")
        )

        check_keys = {
            "simulate_hands": "simulate_hands",
            "enable_chord_roll": "enable_chord_roll",
            "vary_timing": "vary_timing",
            "vary_articulation": "vary_articulation",
            "hand_drift": "enable_drift_correction",
            "mistake_chance": "enable_mistakes",
            "tempo_sway": "enable_tempo_sway",
            "invert_tempo_sway": "invert_tempo_sway",
        }
        value_keys = {
            "vary_timing": "timing_variance",
            "vary_articulation": "articulation",
            "hand_drift": "drift_decay_factor",
            "mistake_chance": "mistake_chance",
            "tempo_sway": "tempo_sway_intensity",
        }
        for control_key, config_key in check_keys.items():
            check = self.all_humanization_checks.get(control_key)
            if check is not None:
                check.toggled.connect(
                    lambda _checked, key=config_key: self._mark_batch_dirty(key)
                )
        for control_key, config_key in value_keys.items():
            spinbox = self.all_humanization_spinboxes.get(control_key)
            if spinbox is not None:
                spinbox.valueChanged.connect(
                    lambda _value, key=config_key: self._mark_batch_dirty(key)
                )

    def begin_batch_change_tracking(self) -> None:
        self._batch_dirty_keys.clear()
        self._batch_change_tracking = True

    def end_batch_change_tracking(self) -> None:
        self._batch_change_tracking = False
        self._batch_dirty_keys.clear()

    def batch_changed_keys(self) -> set[str]:
        return set(self._batch_dirty_keys)

    # ── Public API ─────────────────────────────────────────────────────

    def update_file_label(self, text: str, tooltip: str = "") -> None:
        self.file_path_label.setText(text)
        self.file_path_label.setToolTip(tooltip)
        self._schedule_column_height_sync()

    def set_groups_enabled(self, enabled: bool, skip_playback_humanization: bool = False) -> None:
        self.file_group.setEnabled(enabled)
        if not skip_playback_humanization:
            self.playback_group.setEnabled(enabled)
            self.humanization_group.setEnabled(enabled)

    def set_playlist_editing(self, editing: bool, tr=lambda text: text) -> None:
        self.add_to_playlist_btn.setText(tr("Complete Modification" if editing else "Add to Playlist"))
        self.add_to_playlist_btn.setToolTip(tr(
            "Save the modified settings back to this playlist song"
            if editing else
            "Store the original MIDI, current settings, track choices, and optional compiled cache in the playlist"
        ))

    def set_batch_pending(self, count: int, tr=lambda text: text) -> None:
        self.add_to_playlist_btn.setText(
            tr("Add {count} MIDI Files to Playlist").format(count=count)
        )
        self.add_to_playlist_btn.setToolTip(tr(
            "Apply the current playback settings to every prepared MIDI file and add them to the playlist"
        ))

    def set_playlist_batch_editing(self, count: int, tr=lambda text: text) -> None:
        self.add_to_playlist_btn.setText(
            tr("Complete Batch Modification ({count})").format(count=count)
        )
        self.add_to_playlist_btn.setToolTip(tr(
            "Choose whether to apply only changed values or all values to the selected songs"
        ))

    def update_enabled_states(self) -> None:
        enabled_mode = self.current_humanization_mode() != "disabled"
        individual = self.current_humanization_mode() == "individual"
        self.randomness_label.setEnabled(enabled_mode)
        self.randomness_combo.setEnabled(enabled_mode)
        self.random_seed_label.setEnabled(enabled_mode)
        seed_mode = self.current_seed_mode()
        seed_editable = enabled_mode and seed_mode == "fixed_custom"
        self.random_seed_input.setEnabled(seed_editable)
        self.random_seed_input.setReadOnly(not seed_editable)
        self.humanization_options_widget.setEnabled(individual)

        for key, check in self.all_humanization_checks.items():
            if not check.text():
                continue
            checked = check.isChecked() and individual
            if key in self.all_humanization_sliders:
                self.all_humanization_sliders[key].setEnabled(checked)
            if key in self.all_humanization_spinboxes:
                self.all_humanization_spinboxes[key].setEnabled(checked)
        self.invert_sway_check.setEnabled(
            individual and self.all_humanization_checks["tempo_sway"].isChecked()
        )

    def reset_to_default(self) -> None:
        self.tempo_spinbox.setValue(100)
        self.transpose_spinbox.setValue(0)
        self.pedal_style_combo.setCurrentIndex(max(0, self.pedal_style_combo.findData("hybrid")))
        self.use_88_key_check.setChecked(False)
        self.countdown_check.setChecked(True)
        self.countdown_seconds_spinbox.setValue(3)
        self.trim_check.setChecked(False)
        self.trim_auto_check.setChecked(True)
        self.trim_start_input.setText("00:00")
        self.trim_end_input.setText("00:00")
        self._update_trim_controls()
        self.performance_optimization_check.setChecked(False)
        self.debug_check.setChecked(False)
        self.humanization_mode_combo.setCurrentIndex(max(0, self.humanization_mode_combo.findData("disabled")))
        self.randomness_combo.setCurrentIndex(max(0, self.randomness_combo.findData("dynamic")))
        self.random_seed_input.clear()
        self._apply_humanization_values(self.HUMANIZATION_DEFAULTS)
        self.update_enabled_states()

    def load_config(self, config: dict) -> None:
        self.tempo_spinbox.setValue(config.get("tempo", 100.0))
        self.transpose_spinbox.setValue(config.get("transpose", 0))
        pedal_index = self.pedal_style_combo.findData(config.get("pedal_style", "hybrid"))
        self.pedal_style_combo.setCurrentIndex(max(0, pedal_index))
        self.use_88_key_check.setChecked(config.get("use_88_key_layout", False))
        self.countdown_check.setChecked(config.get("countdown", True))
        self.countdown_seconds_spinbox.setValue(
            max(1, min(10, int(config.get("countdown_seconds", 3))))
        )
        self._update_countdown_controls()
        self.trim_check.setChecked(bool(config.get("trim_enabled", False)))
        self.trim_auto_check.setChecked(bool(config.get("trim_auto", True)))
        self.trim_start_input.setText(
            self._format_time_value(float(config.get("trim_start_seconds", 0.0) or 0.0))
        )
        self.trim_end_input.setText(
            self._format_time_value(float(config.get("trim_end_seconds", 0.0) or 0.0))
        )
        self._update_trim_controls()
        self._midi_clip_invalid_data = bool(config.get("midi_clip_invalid_data", False))
        self.performance_optimization_check.setChecked(
            config_bool(config.get("performance_optimization", False))
        )
        self.debug_check.setChecked(config.get("debug_mode", False))

        any_enabled = any(bool(config.get(key, False)) for key in (
            "simulate_hands", "enable_chord_roll", "enable_vary_timing",
            "enable_vary_articulation", "enable_hand_drift", "enable_mistakes", "enable_tempo_sway",
        ))
        mode = str(config.get("humanization_mode") or ("individual" if any_enabled else "disabled"))
        seed_mode = str(config.get("humanization_seed_mode", "dynamic"))
        seed = config.get("humanization_seed")

        # Loading must preserve a stored fixed-random seed exactly. The normal
        # user-change handlers deliberately generate a new seed, so suppress
        # them while restoring a song or application configuration.
        self._loading_humanization = True
        try:
            self.humanization_mode_combo.setCurrentIndex(max(0, self.humanization_mode_combo.findData(mode)))
            self.randomness_combo.setCurrentIndex(max(0, self.randomness_combo.findData(seed_mode)))
            self.random_seed_input.setText("" if seed in (None, "") else str(seed))
            self._apply_humanization_values(config)
            if mode == "global":
                self._apply_humanization_values(self._global_humanization_config)
            if seed_mode == "fixed_random" and not self.random_seed_input.text().strip():
                self.random_seed_input.setText(str(self._new_seed()))
            elif seed_mode == "dynamic":
                self.random_seed_input.clear()
            elif seed_mode == "fixed_custom" and not self.random_seed_input.text().strip():
                self.random_seed_input.setText("1")
        finally:
            self._loading_humanization = False
        self.update_enabled_states()

    def load_song_config(self, config: dict, global_humanization: dict | None = None) -> None:
        if global_humanization is not None:
            self.set_global_humanization_config(global_humanization)
        self.load_config(config)
        if self.current_humanization_mode() == "global":
            self._apply_humanization_values(self._global_humanization_config)
            self.update_enabled_states()

    def retranslate_combo_items(self, tr) -> None:
        self._tr = tr
        self._update_countdown_controls()
        self._update_trim_controls()
        current = str(self.pedal_style_combo.currentData() or "hybrid")
        self.pedal_style_combo.blockSignals(True)
        self.pedal_style_combo.clear()
        for display, internal in self.PEDAL_MAPPING.items():
            self.pedal_style_combo.addItem(tr(display), internal)
        self.pedal_style_combo.setCurrentIndex(max(0, self.pedal_style_combo.findData(current)))
        self.pedal_style_combo.blockSignals(False)

        mode = self.current_humanization_mode()
        self.humanization_mode_combo.blockSignals(True)
        self.humanization_mode_combo.clear()
        for value, text in self.HUMANIZATION_MODES:
            self.humanization_mode_combo.addItem(tr(text), value)
        self.humanization_mode_combo.setCurrentIndex(max(0, self.humanization_mode_combo.findData(mode)))
        self.humanization_mode_combo.blockSignals(False)

        seed_mode = self.current_seed_mode()
        self.randomness_combo.blockSignals(True)
        self.randomness_combo.clear()
        for value, text in self.SEED_MODES:
            self.randomness_combo.addItem(tr(text), value)
        self.randomness_combo.setCurrentIndex(max(0, self.randomness_combo.findData(seed_mode)))
        self.randomness_combo.blockSignals(False)
        self._schedule_column_height_sync()

    def set_midi_clip_invalid_data(self, enabled: bool) -> None:
        """Remember whether the current MIDI requires Mido's clip mode."""
        self._midi_clip_invalid_data = bool(enabled)

    def gather_playback_config(self) -> dict:
        internal = str(self.pedal_style_combo.currentData() or "hybrid")
        mode = self.current_humanization_mode()
        humanization = self._current_humanization_values()
        if mode == "global":
            humanization = dict(self._global_humanization_config)
        elif mode == "disabled":
            humanization = {
                **humanization,
                "simulate_hands": False,
                "enable_chord_roll": False,
                "vary_timing": False,
                "vary_articulation": False,
                "enable_drift_correction": False,
                "enable_mistakes": False,
                "enable_tempo_sway": False,
                "invert_tempo_sway": False,
            }

        seed_mode = self.current_seed_mode()
        seed = None
        if mode != "disabled" and seed_mode in {"fixed_random", "fixed_custom"}:
            try:
                seed = int(self.random_seed_input.text())
            except (TypeError, ValueError):
                seed = self._new_seed() if seed_mode == "fixed_random" else 1
                self.random_seed_input.setText(str(seed))

        return {
            "midi_file": self.file_path_label.toolTip(),
            "midi_clip_invalid_data": bool(self._midi_clip_invalid_data),
            "tempo": self.tempo_spinbox.value(),
            "transpose": self.transpose_spinbox.value(),
            "countdown": self.countdown_check.isChecked(),
            "countdown_seconds": self.countdown_seconds_spinbox.value(),
            "trim_enabled": self.trim_check.isChecked(),
            "trim_auto": self.trim_auto_check.isChecked(),
            "trim_start_seconds": self._parse_time_value(self.trim_start_input.text()),
            "trim_end_seconds": self._parse_time_value(self.trim_end_input.text()),
            "use_88_key_layout": self.use_88_key_check.isChecked(),
            "pedal_style": internal,
            "performance_optimization": self.performance_optimization_check.isChecked(),
            "debug_mode": self.debug_check.isChecked(),
            "vary_velocity": False,
            "humanization_mode": mode,
            "humanization_seed_mode": seed_mode,
            "humanization_seed": seed,
            **humanization,
        }

    def gather_app_config(self) -> dict:
        values = self._current_humanization_values()
        return {
            "tempo": self.tempo_spinbox.value(),
            "transpose": self.transpose_spinbox.value(),
            "pedal_style": str(self.pedal_style_combo.currentData() or "hybrid"),
            "use_88_key_layout": self.use_88_key_check.isChecked(),
            "countdown": self.countdown_check.isChecked(),
            "countdown_seconds": self.countdown_seconds_spinbox.value(),
            "trim_enabled": self.trim_check.isChecked(),
            "trim_auto": self.trim_auto_check.isChecked(),
            "trim_start_seconds": self._parse_time_value(self.trim_start_input.text()),
            "trim_end_seconds": self._parse_time_value(self.trim_end_input.text()),
            "performance_optimization": self.performance_optimization_check.isChecked(),
            "debug_mode": self.debug_check.isChecked(),
            "humanization_mode": self.current_humanization_mode(),
            "humanization_seed_mode": self.current_seed_mode(),
            "humanization_seed": self.random_seed_input.text() or None,
            "select_all_humanization": self.select_all_humanization_check.isChecked(),
            "simulate_hands": values["simulate_hands"],
            "enable_chord_roll": values["enable_chord_roll"],
            "enable_vary_timing": values["vary_timing"],
            "value_timing_variance": values["timing_variance"],
            "enable_vary_articulation": values["vary_articulation"],
            "value_articulation": values["articulation"] * 100.0,
            "enable_hand_drift": values["enable_drift_correction"],
            "value_hand_drift_decay": values["drift_decay_factor"] * 100.0,
            "enable_mistakes": values["enable_mistakes"],
            "value_mistake_chance": values["mistake_chance"],
            "enable_tempo_sway": values["enable_tempo_sway"],
            "value_tempo_sway_intensity": values["tempo_sway_intensity"],
            "invert_tempo_sway": values["invert_tempo_sway"],
        }
