from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QCheckBox, QSlider, QLabel,
                             QTextEdit, QComboBox, QDoubleSpinBox, QGridLayout,
                             QScrollArea, QStackedWidget, QLineEdit,
                             QApplication, QFrame)
from PyQt6.QtCore import Qt, QObject, QEvent, pyqtSignal as Signal
from PyQt6.QtGui import QFont


class _NavButton(QFrame):
    """Sidebar nav item: large icon glyph stacked above a small label."""

    clicked = Signal()

    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(parent)
        self.setObjectName("nav_btn")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("active",    "false")
        self.setProperty("hovered",   "false")

        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 14, 0, 14)
        vbox.setSpacing(2)
        vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._icon_lbl = QLabel(icon)
        self._icon_lbl.setObjectName("nav_icon")
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_lbl.setProperty("highlighted", "false")
        self._icon_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._text_lbl = QLabel(label)
        self._text_lbl.setObjectName("nav_label")
        self._text_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._text_lbl.setProperty("highlighted", "false")
        self._text_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        vbox.addWidget(self._icon_lbl)
        vbox.addWidget(self._text_lbl)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self._update("hovered", True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._update("hovered", False)
        super().leaveEvent(event)

    def set_active(self, active: bool) -> None:
        self._update("active", active)

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.EnabledChange and not self.isEnabled():
            self.setProperty("active",  "false")
            self.setProperty("hovered", "false")
            for lbl in (self._icon_lbl, self._text_lbl):
                lbl.setProperty("highlighted", "false")
                lbl.style().unpolish(lbl)
                lbl.style().polish(lbl)
            self.style().unpolish(self)
            self.style().polish(self)
            self.update()
        super().changeEvent(event)

    def _update(self, key: str, value: bool) -> None:
        self.setProperty(key, "true" if value else "false")
        active   = self.property("active")   == "true"
        hovered  = self.property("hovered")  == "true"
        hi = "true" if (active or hovered) else "false"
        for lbl in (self._icon_lbl, self._text_lbl):
            lbl.setProperty("highlighted", hi)
            lbl.style().unpolish(lbl)
            lbl.style().polish(lbl)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

from ui.visualizer import PianoWidget, TimelineWidget
from ui.TranslatorTab import TranslatorTab
from ui.theme import ThemeManager, generate_stylesheet


_LICENSE_TEXTS: dict[str, str] = {
    "MIT License — HuMidi": """\
MIT License

Copyright (c) 2024 HuMidi Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
""",

    "Dataset Credits": """\
The following datasets were used to train the BiLSTM AI pedal timing
model bundled with HuMidi.

────────────────────────────────────────────────────────────────────────
POP909
────────────────────────────────────────────────────────────────────────
A piano MIDI dataset of 909 popular songs with performance annotations.

Citation:
  Wang, Z., Chen, K., Jiang, J., Zhang, Y., Xu, M., Dai, S., Xia, G.,
  & Fazekas, G. (2020). POP909: A Pop-song Dataset for Music Arrangement
  Generation. Proceedings of ISMIR 2020.

License : MIT
URL     : https://github.com/music-x-lab/POP909-Dataset

────────────────────────────────────────────────────────────────────────
GiantMIDI-Piano
────────────────────────────────────────────────────────────────────────
A large-scale MIDI dataset of classical piano music transcribed from
audio recordings.

Citation:
  Kong, Q., Li, B., Chen, J., & Wang, Y. (2020). GiantMIDI-Piano: A
  large-scale MIDI dataset for classical piano music. arXiv:2010.07061.

License : Creative Commons Attribution 4.0 International (CC BY 4.0)

  You are free to share and adapt the material for any purpose, provided
  appropriate credit is given.

URL     : https://github.com/bytedance/GiantMIDI-Piano
""",

    "Third-Party Libraries": """\
PyQt6
  License : GPL v3 / Commercial (Riverbank Computing)
  URL     : https://riverbankcomputing.com/software/pyqt/

mido
  License : MIT
  URL     : https://github.com/mido/mido

pynput
  License : LGPL v3
  URL     : https://github.com/moses-palmer/pynput

onnxruntime
  License : MIT
  URL     : https://github.com/microsoft/onnxruntime

numpy
  License : BSD 3-Clause
  URL     : https://numpy.org/
""",
}


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
        main_widget.setObjectName("main_widget")
        self.main_window.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._is_collapsed = False

        # ── Collapsed mini strip (hidden by default) ───────────────────
        self._collapsed_strip = QFrame()
        self._collapsed_strip.setObjectName("collapsed_strip")
        self._collapsed_strip.setVisible(False)
        cs_layout = QHBoxLayout(self._collapsed_strip)
        cs_layout.setContentsMargins(12, 6, 12, 6)
        cs_layout.setSpacing(8)

        self._collapsed_file_label = QLabel("No file selected.")
        self._collapsed_file_label.setObjectName("file_path_label")
        self._collapsed_humanize_check = QCheckBox("Humanize")
        self._collapsed_humanize_check.setToolTip("Enable or disable all humanization at once")
        self._collapsed_load_btn = QPushButton("Browse…")
        self._collapsed_load_btn.setToolTip("Open a MIDI file to play")
        self._collapsed_load_saved_btn = QPushButton("Load Save")
        self._collapsed_load_saved_btn.setToolTip("Load a previously saved humanized performance")
        self._collapsed_save_btn = QPushButton("Save")
        self._collapsed_save_btn.setToolTip("Save the current humanized performance")
        self._collapsed_save_btn.setEnabled(False)

        cs_layout.addWidget(self._collapsed_file_label, 1)
        cs_layout.addWidget(self._collapsed_humanize_check)
        cs_layout.addWidget(self._collapsed_load_btn)
        cs_layout.addWidget(self._collapsed_load_saved_btn)
        cs_layout.addWidget(self._collapsed_save_btn)
        main_layout.addWidget(self._collapsed_strip)

        # ── Body: sidebar + page stack ─────────────────────────────────
        self._body = QWidget()
        body_layout = QHBoxLayout(self._body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(120)
        sidebar_vbox = QVBoxLayout(sidebar)
        sidebar_vbox.setContentsMargins(0, 16, 0, 12)
        sidebar_vbox.setSpacing(0)

        app_title = QLabel("HuMidi")
        app_title.setObjectName("app_title")
        app_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_vbox.addWidget(app_title)
        sidebar_vbox.addSpacing(20)

        # Page stack — self.tabs preserves the setCurrentIndex API used by main.py
        self.tabs = QStackedWidget()
        self.tabs.currentChanged.connect(self._on_page_changed)

        # Icons use Segoe MDL2 Assets (built into Windows 10/11)
        _NAV_ITEMS = [
            ("\uE768", "Playback"),    # Play
            ("\uE8D6", "Visualizer"),  # Music / audio
            ("\uE8B1", "Translator"),  # Globe / language
            ("\uE713", "Settings"),    # Gear
            ("\uEBE8", "Debug"),       # Bug
            ("\uE946", "License"),     # Info / about
        ]
        self._nav_btns: list[_NavButton] = []
        for i, (icon, label) in enumerate(_NAV_ITEMS):
            btn = _NavButton(icon, label)
            btn.clicked.connect(lambda idx=i: self._switch_page(idx))
            sidebar_vbox.addWidget(btn)
            self._nav_btns.append(btn)

        sidebar_vbox.addStretch()
        body_layout.addWidget(sidebar)
        body_layout.addWidget(self.tabs, 1)
        main_layout.addWidget(self._body, 1)

        # ── Pages ──────────────────────────────────────────────────────
        controls_page = QWidget()
        visual_page   = QWidget()
        settings_page = QWidget()
        log_page      = QWidget()
        self.translator_tab = TranslatorTab()

        self.tabs.addWidget(controls_page)        # 0 — Playback
        self.tabs.addWidget(visual_page)          # 1 — Visualizer
        self.tabs.addWidget(self.translator_tab)  # 2 — Translator
        self.tabs.addWidget(settings_page)        # 3 — Settings
        self.tabs.addWidget(log_page)             # 4 — Debug
        self.tabs.addWidget(self._create_license_page())  # 5 — License

        # ── Visualizer page ───────────────────────────────────────────
        vis_layout = QVBoxLayout(visual_page)
        vis_layout.setContentsMargins(6, 6, 6, 6)
        vis_layout.setSpacing(6)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.timeline_widget = TimelineWidget()
        self.scroll_area.setWidget(self.timeline_widget)
        vis_layout.addWidget(self.scroll_area)

        self.piano_widget = PianoWidget()
        vis_layout.addWidget(self.piano_widget)

        # ── Controls page (2-column landscape) ────────────────────────
        controls_outer = QHBoxLayout(controls_page)
        controls_outer.setContentsMargins(12, 12, 12, 12)
        controls_outer.setSpacing(12)

        left_col = QVBoxLayout()
        left_col.setSpacing(10)
        self.file_group = self._create_file_group()
        left_col.addWidget(self.file_group)
        self.playback_group = self._create_playback_group()
        left_col.addWidget(self.playback_group)
        left_col.addStretch()

        right_col = QVBoxLayout()
        right_col.setSpacing(10)
        self.humanization_group = self._create_humanization_group()
        right_col.addWidget(self.humanization_group)
        right_col.addStretch()

        controls_outer.addLayout(left_col, 1)
        controls_outer.addLayout(right_col, 1)

        # ── Settings page (2-column landscape) ────────────────────────
        settings_outer = QHBoxLayout(settings_page)
        settings_outer.setContentsMargins(12, 12, 12, 12)
        settings_outer.setSpacing(12)

        settings_left = QVBoxLayout()
        settings_left.setSpacing(10)
        settings_right = QVBoxLayout()
        settings_right.setSpacing(10)

        # Hotkey card
        hk_card, hk_content = self._make_card("Hotkey")
        hk_row = QHBoxLayout()
        hk_row.setSpacing(8)
        self.hk_label = QLabel("Hotkey: ")
        self.hk_btn = QPushButton("Change")
        self.hk_btn.setToolTip("Click to bind a new hotkey for toggling playback")
        hk_row.addWidget(self.hk_label)
        hk_row.addWidget(self.hk_btn)
        hk_content.addLayout(hk_row)
        settings_left.addWidget(hk_card)

        # Overlay card
        ov_card, ov_content = self._make_card("Overlay")
        ov_grid = QGridLayout()
        ov_grid.setSpacing(8)
        self.always_top_check = QCheckBox("Always on Top")
        self.always_top_check.setToolTip("Keep this window above all other windows")
        opacity_label = QLabel("Opacity")
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(20, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setToolTip("Adjust window transparency (20–100%)")
        ov_grid.addWidget(self.always_top_check, 0, 0, 1, 2)
        ov_grid.addWidget(opacity_label, 1, 0)
        ov_grid.addWidget(self.opacity_slider, 1, 1)
        ov_content.addLayout(ov_grid)
        settings_left.addWidget(ov_card)
        settings_left.addStretch()

        # Save Path card
        save_card, save_content = self._make_card("Save Path")
        save_row = QHBoxLayout()
        save_row.setSpacing(8)
        self.save_path_input = QLineEdit()
        self.save_path_input.setReadOnly(True)
        self.save_path_input.setToolTip("Directory where humanized performance saves are stored")
        self.save_browse_btn = QPushButton("Browse")
        self.save_browse_btn.setToolTip("Choose where to save humanized performance files")
        save_row.addWidget(self.save_path_input)
        save_row.addWidget(self.save_browse_btn)
        save_content.addLayout(save_row)
        settings_right.addWidget(save_card)

        # Visualizer settings card
        vis_card, vis_content = self._make_card("Visualizer")
        self.timeline_vis_check = QCheckBox("Timeline")
        self.timeline_vis_check.setChecked(True)
        self.timeline_vis_check.setToolTip(
            "Show the piano-roll timeline in the Visualizer tab (disable for a simple seek slider)"
        )
        self.piano_vis_check = QCheckBox("Piano Keys")
        self.piano_vis_check.setChecked(True)
        self.piano_vis_check.setToolTip("Show the piano key visualizer in the Visualizer tab")
        vis_content.addWidget(self.timeline_vis_check)
        vis_content.addWidget(self.piano_vis_check)
        settings_right.addWidget(vis_card)
        self.timeline_vis_check.toggled.connect(self._on_timeline_toggle)
        self.piano_vis_check.toggled.connect(self._on_piano_toggle)

        # AI Model card
        ai_card, ai_content = self._make_card("AI Model")
        self.use_ai_pedal_check = QCheckBox("Enable AI Pedal")
        self.use_ai_pedal_check.setChecked(True)
        self.use_ai_pedal_check.setToolTip(
            "Use the ONNX BiLSTM model for pedal timing when 'Auto (Default)' is selected.\n"
            "Falls back to the algorithmic driver if the model file is missing.\n"
            "Disable to always use the algorithmic driver."
        )
        ai_content.addWidget(self.use_ai_pedal_check)
        settings_right.addWidget(ai_card)

        # Theme card
        theme_card, theme_content = self._make_card("Theme")
        theme_row = QHBoxLayout()
        theme_row.setSpacing(8)
        self.theme_combo = QComboBox()
        self.theme_combo.setToolTip("Switch the application colour theme")
        self._refresh_theme_combo()
        self.theme_combo.currentTextChanged.connect(self.apply_theme)
        self.theme_customize_btn = QPushButton("Customize…")
        self.theme_customize_btn.setToolTip("Open the theme editor to create or modify colour presets")
        self.theme_customize_btn.clicked.connect(self._open_theme_dialog)
        theme_row.addWidget(self.theme_combo, 1)
        theme_row.addWidget(self.theme_customize_btn)
        theme_content.addLayout(theme_row)
        settings_right.addWidget(theme_card)
        settings_right.addStretch()

        settings_outer.addLayout(settings_left, 1)
        settings_outer.addLayout(settings_right, 1)

        # ── Debug / Log page ──────────────────────────────────────────
        log_layout = QVBoxLayout(log_page)
        log_layout.setContentsMargins(12, 12, 12, 12)
        log_layout.setSpacing(6)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont("Courier New", 9))
        log_layout.addWidget(self.log_output)

        log_btn_layout = QHBoxLayout()
        log_btn_layout.setSpacing(6)
        self.log_clear_btn = QPushButton("Clear")
        self.log_clear_btn.setToolTip("Clear all log entries")
        self.log_copy_btn = QPushButton("Copy Log")
        self.log_copy_btn.setToolTip("Copy the full log to clipboard")
        self.log_clear_btn.clicked.connect(self.log_output.clear)
        self.log_copy_btn.clicked.connect(self.copy_log_to_clipboard)
        log_btn_layout.addWidget(self.log_clear_btn)
        log_btn_layout.addWidget(self.log_copy_btn)
        log_btn_layout.addStretch()
        log_layout.addLayout(log_btn_layout)

        # ── Transport bar ─────────────────────────────────────────────
        transport_bar = QFrame()
        transport_bar.setObjectName("transport_bar")
        transport_layout = QVBoxLayout(transport_bar)
        transport_layout.setContentsMargins(16, 10, 16, 10)
        transport_layout.setSpacing(6)

        # Row 1: scrubber (always visible)
        self.scrubber_slider = QSlider(Qt.Orientation.Horizontal)
        self.scrubber_slider.setObjectName("scrubber_slider")
        self.scrubber_slider.setRange(0, 10000)
        self.scrubber_slider.sliderPressed.connect(self._on_scrubber_pressed)
        self.scrubber_slider.sliderMoved.connect(self._on_scrubber_moved)
        self.scrubber_slider.sliderReleased.connect(self._on_scrubber_released)
        self._scrubber_dragging = False
        transport_layout.addWidget(self.scrubber_slider)

        # Row 2: buttons + time
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.play_button = QPushButton("▶  Play")
        self.play_button.setObjectName("play_button")
        self.play_button.setToolTip("Start, pause, or resume playback")

        self.stop_button = QPushButton("■  Stop")
        self.stop_button.setObjectName("stop_button")
        self.stop_button.setToolTip("Stop playback and reset to the beginning")

        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setObjectName("time_label")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.save_button = QPushButton("Save")
        self.save_button.setObjectName("save_button")
        self.save_button.setToolTip("Save the current humanized performance to a file for later replay")

        self.reset_button = QPushButton("Reset")
        self.reset_button.setObjectName("reset_button")
        self.reset_button.setToolTip("Reset all settings to their default values")

        btn_row.addWidget(self.play_button)
        btn_row.addWidget(self.stop_button)
        btn_row.addStretch()
        btn_row.addWidget(self.time_label)
        btn_row.addStretch()
        btn_row.addWidget(self.save_button)
        btn_row.addWidget(self.reset_button)

        self.collapse_btn = QPushButton("▲")
        self.collapse_btn.setObjectName("collapse_btn")
        self.collapse_btn.setFixedWidth(28)
        self.collapse_btn.setToolTip("Collapse to mini mode")
        self.collapse_btn.clicked.connect(self._toggle_collapsed)
        btn_row.addWidget(self.collapse_btn)

        transport_layout.addLayout(btn_row)

        main_layout.addWidget(transport_bar)

        self.play_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.save_button.setEnabled(False)

        # Sync collapsed humanize toggle with the main "All" checkbox
        self._collapsed_humanize_check.toggled.connect(self._on_collapsed_humanize_toggled)
        self.select_all_humanization_check.toggled.connect(self._sync_collapsed_humanize)

        # Set initial page and apply theme (all widgets must exist first)
        self._switch_page(0)
        self.apply_theme(ThemeManager.get_active_name())

    # ── Card + nav helpers ─────────────────────────────────────────────

    def _make_card(self, title: str) -> tuple:
        """Return a styled section card (QFrame) and its content QVBoxLayout."""
        card = QFrame()
        card.setObjectName("section_card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(8)
        if title:
            lbl = QLabel(title)
            lbl.setProperty("role", "section")
            layout.addWidget(lbl)
        return card, layout

    def _switch_page(self, index: int) -> None:
        self.tabs.setCurrentIndex(index)

    def _on_page_changed(self, index: int) -> None:
        for i, btn in enumerate(self._nav_btns):
            btn.set_active(i == index)

    # ── Group creators ─────────────────────────────────────────────────

    def _create_slider_and_spinbox(self, min_val, max_val, default_val,
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

    def _create_file_group(self):
        card, layout = self._make_card("MIDI File")

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
        card, layout = self._make_card("Playback")
        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setColumnMinimumWidth(1, 8)
        grid.setColumnStretch(2, 1)

        tempo_label = QLabel("Tempo")
        self.tempo_slider, self.tempo_spinbox = self._create_slider_and_spinbox(
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
        self.pedal_style_combo.addItems(list(self.pedal_mapping.keys()))
        self.pedal_style_combo.setToolTip(
            "Auto (Default): AI-driven pedal using a hybrid of rhythmic and harmonic analysis\n"
            "Harmonic: Hold pedal through harmonic regions, releasing at chord/bass changes\n"
            "Rhythmic: Release pedal on beat boundaries only\n"
            "None: No sustain pedal"
        )
        grid.addWidget(pedal_label, 1, 0)
        grid.addWidget(self.pedal_style_combo, 1, 2, 1, 2)

        toggles_row = QHBoxLayout()
        toggles_row.setSpacing(16)
        self.use_88_key_check = QCheckBox("88-Key Layout")
        self.use_88_key_check.setToolTip(
            "Map notes to the full 88-key piano layout instead of a compressed keyboard layout"
        )
        self.countdown_check = QCheckBox("Countdown")
        self.countdown_check.setToolTip("Show a 3-second countdown before playback begins")
        self.debug_check = QCheckBox("Debug Output")
        self.debug_check.setToolTip("Print verbose event logs to the Debug tab during playback")
        toggles_row.addWidget(self.use_88_key_check)
        toggles_row.addWidget(self.countdown_check)
        toggles_row.addWidget(self.debug_check)
        toggles_row.addStretch()

        toggles_widget = QWidget()
        toggles_widget.setLayout(toggles_row)
        grid.addWidget(toggles_widget, 2, 0, 1, 4)

        layout.addLayout(grid)
        return card

    def _create_humanization_group(self):
        card, main_v_layout = self._make_card("Humanization")

        # Master toggle + simple toggles in one row
        top_row = QHBoxLayout()
        top_row.setSpacing(16)
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

        top_row.addWidget(self.select_all_humanization_check)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setObjectName("v_sep")
        top_row.addWidget(sep)

        top_row.addWidget(self.all_humanization_checks['simulate_hands'])
        top_row.addWidget(self.all_humanization_checks['enable_chord_roll'])
        top_row.addStretch()
        main_v_layout.addLayout(top_row)

        h_sep = QFrame()
        h_sep.setObjectName("h_sep")
        h_sep.setFrameShape(QFrame.Shape.HLine)
        main_v_layout.addWidget(h_sep)

        detailed_layout = QGridLayout()
        detailed_layout.setSpacing(6)
        detailed_layout.setColumnStretch(2, 1)
        detailed_layout.setColumnMinimumWidth(1, 4)

        def add_detailed_row(row_idx, name, key, min_val, max_val, def_val,
                             suffix, factor=1.0, decimals=3, tooltip=""):
            check = QCheckBox(name)
            slider, spinbox = self._create_slider_and_spinbox(
                min_val, max_val, def_val, suffix, factor=factor, decimals=decimals
            )
            spinbox.setFixedWidth(80)
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

        add_detailed_row(0, "Vary Timing", "vary_timing", 0, 0.1, 0.01, " s",
                         factor=10000.0,
                         tooltip="Add random timing offsets to note events (in seconds)")
        add_detailed_row(1, "Vary Articulation", "vary_articulation", 50, 100, 95, "%",
                         factor=100.0, decimals=1,
                         tooltip="Randomize note hold duration — lower values create a more staccato feel")
        add_detailed_row(2, "Hand Drift", "hand_drift", 0, 100, 25, "%",
                         factor=100.0, decimals=1,
                         tooltip="Simulate gradual timing drift between the left and right hands")
        add_detailed_row(3, "Mistakes", "mistake_chance", 0, 10, 0, "%",
                         factor=100.0, decimals=1,
                         tooltip="Randomly skip notes to simulate human errors")
        add_detailed_row(4, "Tempo Sway", "tempo_sway", 0, 0.1, 0, " s",
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

        self.all_humanization_checks['vary_velocity'] = QCheckBox()  # dummy for logic compat
        self.select_all_humanization_check.toggled.connect(self._toggle_all_humanization)
        for check in self.all_humanization_checks.values():
            if check.text():
                check.toggled.connect(self._update_select_all_state)

        return card

    # ── Theme helpers ─────────────────────────────────────────────────

    def apply_theme(self, name: str) -> None:
        """Generate and apply the stylesheet for the named theme."""
        themes = ThemeManager.all_themes()
        theme = themes.get(name)
        if theme is None:
            return
        ThemeManager.set_active_name(name)
        ss = generate_stylesheet(theme)
        self.main_window.setStyleSheet(ss)
        # Keep visualizer colours in sync
        self.timeline_widget.left_hand_color.setNamedColor(theme.accent)
        self.timeline_widget.left_hand_color.setAlpha(210)
        self.timeline_widget.right_hand_color.setNamedColor(theme.accent_play)
        self.timeline_widget.right_hand_color.setAlpha(210)
        self.timeline_widget.bg_color.setNamedColor(theme.bg_primary)
        self.timeline_widget.cached_background = None
        self.timeline_widget.update()

    def _refresh_theme_combo(self) -> None:
        """Populate the theme dropdown from ThemeManager (blocking signals)."""
        self.theme_combo.blockSignals(True)
        self.theme_combo.clear()
        active = ThemeManager.get_active_name()
        for name in ThemeManager.all_themes():
            self.theme_combo.addItem(name)
        idx = self.theme_combo.findText(active)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        self.theme_combo.blockSignals(False)

    def _open_theme_dialog(self) -> None:
        from ui.ThemeDialog import ThemeDialog
        dlg = ThemeDialog(self.main_window, self.main_window)
        dlg.theme_applied.connect(self._on_theme_dialog_accepted)
        dlg.exec()

    def _on_theme_dialog_accepted(self, name: str) -> None:
        self._refresh_theme_combo()
        self.apply_theme(name)

    # ── Public API ────────────────────────────────────────────────────

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
            if check.text():
                check.setChecked(False)
        self.update_enabled_states()

    def _toggle_all_humanization(self, checked):
        for check in self.all_humanization_checks.values():
            if check.text():
                check.setChecked(checked)

    def _update_select_all_state(self):
        checks = [c for c in self.all_humanization_checks.values() if c.text()]
        is_all_checked = all(c.isChecked() for c in checks)
        self.select_all_humanization_check.blockSignals(True)
        self.select_all_humanization_check.setChecked(is_all_checked)
        self.select_all_humanization_check.blockSignals(False)

    def set_controls_enabled(self, enabled, ignore_if_loaded=False):
        groups_to_toggle = [self.file_group, self.playback_group, self.humanization_group]
        for group in groups_to_toggle:
            if group in (self.playback_group, self.humanization_group) \
                    and ignore_if_loaded and enabled:
                continue
            group.setEnabled(enabled)

    def _set_save_enabled(self, val: bool) -> None:
        self.save_button.setEnabled(val)
        self._collapsed_save_btn.setEnabled(val)

    def update_file_label(self, text: str, tooltip: str = "") -> None:
        self.file_path_label.setText(text)
        self.file_path_label.setToolTip(tooltip)
        self._collapsed_file_label.setText(text)

    def _toggle_collapsed(self) -> None:
        self._is_collapsed = not self._is_collapsed
        if self._is_collapsed:
            self._expanded_size = self.main_window.size()
            self._body.setVisible(False)
            self._collapsed_strip.setVisible(True)
            self.collapse_btn.setText("▼")
            self.collapse_btn.setToolTip("Restore full window")
            self.main_window.setMinimumHeight(0)
            self.main_window.adjustSize()
        else:
            self._body.setVisible(True)
            self._collapsed_strip.setVisible(False)
            self.collapse_btn.setText("▲")
            self.collapse_btn.setToolTip("Collapse to mini mode")
            self.main_window.setMinimumHeight(520)
            self.main_window.resize(self._expanded_size)

    def _on_collapsed_humanize_toggled(self, checked: bool) -> None:
        """Propagate collapsed checkbox → main 'All' checkbox without feedback loop."""
        self.select_all_humanization_check.blockSignals(True)
        self.select_all_humanization_check.setChecked(checked)
        self.select_all_humanization_check.blockSignals(False)
        self._toggle_all_humanization(checked)

    def _sync_collapsed_humanize(self, checked: bool) -> None:
        """Propagate main 'All' checkbox → collapsed checkbox without feedback loop."""
        self._collapsed_humanize_check.blockSignals(True)
        self._collapsed_humanize_check.setChecked(checked)
        self._collapsed_humanize_check.blockSignals(False)

    def update_enabled_states(self):
        for key, check in self.all_humanization_checks.items():
            if not check.text():
                continue
            is_checked = check.isChecked()
            if key in self.all_humanization_sliders:
                self.all_humanization_sliders[key].setEnabled(is_checked)
            if key in self.all_humanization_spinboxes:
                self.all_humanization_spinboxes[key].setEnabled(is_checked)
        self.invert_sway_check.setEnabled(
            self.all_humanization_checks['tempo_sway'].isChecked()
        )

    def copy_log_to_clipboard(self):
        QApplication.clipboard().setText(self.log_output.toPlainText())

    # ── Visualizer / progress helpers ─────────────────────────────────

    def update_progress(self, current_time, total_duration):
        if self.scroll_area.isVisible() and not self.timeline_widget.is_dragging:
            self.timeline_widget.set_position(current_time)
            timeline_width = self.timeline_widget.width()
            scroll_width = self.scroll_area.width()
            if total_duration > 0:
                ratio = current_time / total_duration
                cursor_x = ratio * timeline_width
                target_scroll = cursor_x - (scroll_width / 2)
                self.scroll_area.horizontalScrollBar().setValue(int(target_scroll))

        if not self._scrubber_dragging and not self.timeline_widget.is_dragging:
            self.scrubber_slider.blockSignals(True)
            if total_duration > 0:
                self.scrubber_slider.setValue(int(current_time / total_duration * 10000))
            self.scrubber_slider.blockSignals(False)

        self.update_time_label(current_time, total_duration)

    def reset_timeline_position(self):
        self.timeline_widget.current_time = 0.0
        self.scrubber_slider.blockSignals(True)
        self.scrubber_slider.setValue(0)
        self.scrubber_slider.blockSignals(False)

    def _on_timeline_toggle(self, checked):
        self.scroll_area.setVisible(checked)
        self._update_visualizer_availability()

    def _on_piano_toggle(self, checked):
        self.piano_widget.setVisible(checked)
        self._update_visualizer_availability()

    def _update_visualizer_availability(self) -> None:
        both_off = (not self.timeline_vis_check.isChecked() and
                    not self.piano_vis_check.isChecked())
        vis_btn = self._nav_btns[1]
        vis_btn.setEnabled(not both_off)
        if both_off and self.tabs.currentIndex() == 1:
            self._switch_page(0)

    def _on_scrubber_pressed(self):
        self._scrubber_dragging = True

    def _on_scrubber_moved(self, value):
        if self.timeline_widget.total_duration > 0:
            t = (value / 10000.0) * self.timeline_widget.total_duration
            self.timeline_widget.current_time = t
            self.timeline_widget.scrub_position_changed.emit(t)
            self.update_time_label(t, self.timeline_widget.total_duration)

    def _on_scrubber_released(self):
        self._scrubber_dragging = False
        self.timeline_widget.seek_requested.emit(self.timeline_widget.current_time)

    def _create_license_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header = QLabel("Licenses & Credits")
        header.setProperty("role", "title")
        layout.addWidget(header)

        selector_row = QHBoxLayout()
        selector_row.setSpacing(8)
        sel_lbl = QLabel("View:")
        sel_lbl.setProperty("role", "muted")
        sel_lbl.setFixedWidth(34)
        self._license_combo = QComboBox()
        for name in _LICENSE_TEXTS:
            self._license_combo.addItem(name)
        self._license_combo.currentTextChanged.connect(self._on_license_changed)
        selector_row.addWidget(sel_lbl)
        selector_row.addWidget(self._license_combo, 1)
        layout.addLayout(selector_row)

        self._license_text = QTextEdit()
        self._license_text.setReadOnly(True)
        self._license_text.setFont(QFont("Courier New", 9))
        first = self._license_combo.currentText()
        self._license_text.setPlainText(_LICENSE_TEXTS.get(first, ""))
        layout.addWidget(self._license_text)
        return page

    def _on_license_changed(self, name: str) -> None:
        self._license_text.setPlainText(_LICENSE_TEXTS.get(name, ""))

    def update_time_label(self, current, total):
        def fmt(s):
            m = int(s // 60)
            sec = int(s % 60)
            return f"{m:02d}:{sec:02d}"
        self.time_label.setText(f"{fmt(current)} / {fmt(total)}")

    # ── Config bridge ─────────────────────────────────────────────────

    def load_config_to_ui(self, config, save_dir):
        self.tempo_spinbox.setValue(config.get('tempo', 100.0))
        internal_style = config.get('pedal_style', 'hybrid')
        display_text = self.pedal_mapping_inv.get(internal_style, "Auto (Default)")
        self.pedal_style_combo.setCurrentText(display_text)
        self.use_88_key_check.setChecked(config.get('use_88_key_layout', False))
        self.countdown_check.setChecked(config.get('countdown', True))
        self.debug_check.setChecked(config.get('debug_mode', False))
        self.select_all_humanization_check.setChecked(
            config.get('select_all_humanization', False)
        )
        self.all_humanization_checks['simulate_hands'].setChecked(
            config.get('simulate_hands', False)
        )
        self.all_humanization_checks['enable_chord_roll'].setChecked(
            config.get('enable_chord_roll', False)
        )
        self.all_humanization_checks['vary_timing'].setChecked(
            config.get('enable_vary_timing', False)
        )
        self.all_humanization_spinboxes['vary_timing'].setValue(
            config.get('value_timing_variance', 0.010)
        )
        self.all_humanization_checks['vary_articulation'].setChecked(
            config.get('enable_vary_articulation', False)
        )
        self.all_humanization_spinboxes['vary_articulation'].setValue(
            config.get('value_articulation', 95.0)
        )
        self.all_humanization_checks['hand_drift'].setChecked(
            config.get('enable_hand_drift', False)
        )
        self.all_humanization_spinboxes['hand_drift'].setValue(
            config.get('value_hand_drift_decay', 25.0)
        )
        self.all_humanization_checks['mistake_chance'].setChecked(
            config.get('enable_mistakes', False)
        )
        self.all_humanization_spinboxes['mistake_chance'].setValue(
            config.get('value_mistake_chance', 0.5)
        )
        self.all_humanization_checks['tempo_sway'].setChecked(
            config.get('enable_tempo_sway', False)
        )
        self.all_humanization_spinboxes['tempo_sway'].setValue(
            config.get('value_tempo_sway_intensity', 0.015)
        )
        self.all_humanization_checks['invert_tempo_sway'].setChecked(
            config.get('invert_tempo_sway', False)
        )
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
