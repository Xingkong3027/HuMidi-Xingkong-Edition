from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox, QSlider,
    QLabel, QComboBox, QLineEdit, QGridLayout, QScrollArea, QFrame,
    QSizePolicy,
)
from PyQt6.QtCore import Qt

from ui.widgets import make_card, NoWheelSlider, NoWheelComboBox
from ui.theme import ThemeManager


class SettingsTab(QWidget):

    GLOBAL_HUMANIZATION_DEFAULTS = {
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
        self._global_humanization_config = dict(self.GLOBAL_HUMANIZATION_DEFAULTS)
        self._setup_ui()

    @staticmethod
    def _keep_card_size(card: QWidget) -> None:
        """Let the settings page scroll instead of vertically crushing cards."""
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _setup_ui(self):
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("settings_scroll_area")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        scroll_content = QWidget()
        scroll_content.setObjectName("settings_scroll_content")
        # At the application's minimum width this fits without a horizontal bar,
        # while the vertical size remains the natural size of all option cards.
        scroll_content.setMinimumWidth(680)
        outer = QVBoxLayout(scroll_content)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(12)

        # ── Save Path card (full width) ────────────────────────────────
        save_card, save_content = make_card("Save Path")
        self._keep_card_size(save_card)
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
        outer.addWidget(save_card)

        # ── Language card ───────────────────────────────────────────────
        language_card, language_content = make_card("Language")
        self._keep_card_size(language_card)
        language_row = QHBoxLayout()
        language_row.setSpacing(8)
        self.language_combo = NoWheelComboBox()
        self.language_combo.addItem("Automatic (English)", "auto")
        self.language_combo.addItem("Simplified Chinese", "zh_CN")
        self.language_combo.addItem("English", "en_US")
        language_row.addWidget(self.language_combo, 1)
        language_content.addLayout(language_row)
        outer.addWidget(language_card)

        # ── Two-column body ────────────────────────────────────────────
        body = QHBoxLayout()
        body.setSpacing(12)

        left_col = QVBoxLayout()
        left_col.setSpacing(10)
        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        # Keyboard shortcuts card
        hk_card, hk_content = make_card("Keyboard Shortcuts")
        self._keep_card_size(hk_card)
        hk_row = QHBoxLayout()
        hk_row.setSpacing(8)
        self.hk_label = QLabel("Configure play, stop, previous, and next shortcuts")
        self.hk_label.setWordWrap(True)
        self.hk_label.setProperty("i18n_dynamic", True)
        self.hk_btn = QPushButton("Configure…")
        self.hk_btn.setToolTip("Configure up to two keyboard shortcuts for each playback action")
        hk_row.addWidget(self.hk_label, 1)
        hk_row.addWidget(self.hk_btn)
        hk_content.addLayout(hk_row)
        left_col.addWidget(hk_card)

        # Overlay card
        ov_card, ov_content = make_card("Overlay")
        self._keep_card_size(ov_card)
        ov_grid = QGridLayout()
        ov_grid.setSpacing(8)
        self.always_top_check = QCheckBox("Always on Top")
        self.always_top_check.setToolTip("Keep this window above all other windows")
        opacity_label = QLabel("Opacity")
        self.opacity_slider = NoWheelSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(20, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setToolTip("Adjust window transparency (20–100%)")
        ov_grid.addWidget(self.always_top_check, 0, 0, 1, 2)
        ov_grid.addWidget(opacity_label,         1, 0)
        ov_grid.addWidget(self.opacity_slider,   1, 1)
        ov_content.addLayout(ov_grid)
        left_col.addWidget(ov_card)

        self.check_update_btn = QPushButton("Check for updates")
        self.check_update_btn.setToolTip(
            "Check GitHub for a newer version of HuMidi Xingkong Edition"
        )
        self.check_update_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        left_col.addWidget(self.check_update_btn)
        left_col.addStretch()

        # Visualizer card
        vis_card, vis_content = make_card("Visualizer")
        self._keep_card_size(vis_card)
        self.timeline_vis_check = QCheckBox("Timeline")
        self.timeline_vis_check.setChecked(True)
        self.timeline_vis_check.setToolTip(
            "Show the piano-roll timeline in the Visualizer tab "
            "(disable for a simple seek slider)"
        )
        self.piano_vis_check = QCheckBox("Piano Keys")
        self.piano_vis_check.setChecked(True)
        self.piano_vis_check.setToolTip("Show the piano key visualizer in the Visualizer tab")
        vis_content.addWidget(self.timeline_vis_check)
        vis_content.addWidget(self.piano_vis_check)
        right_col.addWidget(vis_card)

        # Global human-like performance preset
        human_card, human_content = make_card("Global Human-like Performance")
        self._keep_card_size(human_card)
        self.global_humanization_summary = QLabel("No simulated-performance options enabled")
        self.global_humanization_summary.setWordWrap(True)
        self.global_humanization_summary.setProperty("i18n_dynamic", True)
        self.global_humanization_btn = QPushButton("Configure…")
        self.global_humanization_btn.setToolTip(
            "Configure the preset used by songs set to Enabled (Use Global Settings)"
        )
        human_content.addWidget(self.global_humanization_summary)
        human_content.addWidget(self.global_humanization_btn)
        right_col.addWidget(human_card)

        # AI Model card
        ai_card, ai_content = make_card("AI Model")
        self._keep_card_size(ai_card)
        self.use_ai_pedal_check = QCheckBox("Enable AI Pedal")
        self.use_ai_pedal_check.setChecked(False)
        self.use_ai_pedal_check.setEnabled(False)
        self.use_ai_pedal_check.setToolTip("Sorry, still in development!")
        ai_wip_label = QLabel("Sorry, still in development!")
        ai_wip_label.setEnabled(False)
        ai_content.addWidget(self.use_ai_pedal_check)
        ai_content.addWidget(ai_wip_label)
        right_col.addWidget(ai_card)

        # Theme card
        theme_card, theme_content = make_card("Theme")
        self._keep_card_size(theme_card)
        theme_row = QHBoxLayout()
        theme_row.setSpacing(8)
        self.theme_combo = NoWheelComboBox()
        self.theme_combo.setToolTip("Switch the application colour theme")
        self._populate_theme_combo()
        self.theme_customize_btn = QPushButton("Customize…")
        self.theme_customize_btn.setToolTip(
            "Open the theme editor to create or modify colour presets"
        )
        theme_row.addWidget(self.theme_combo, 1)
        theme_row.addWidget(self.theme_customize_btn)
        theme_content.addLayout(theme_row)
        right_col.addWidget(theme_card)
        right_col.addStretch()

        body.addLayout(left_col, 1)
        body.addLayout(right_col, 1)
        outer.addLayout(body)
        outer.addStretch()

        self.scroll_area.setWidget(scroll_content)
        page_layout.addWidget(self.scroll_area)

    def update_shortcut_summary(self, hotkey_manager, tr=lambda text: text) -> None:
        parts = []
        for action, label in ((
            "play_pause", "Play / Pause"
        ), (
            "stop", "Stop"
        ), (
            "next", "Next Song"
        ), (
            "previous", "Previous Song"
        )):
            displays = [
                hotkey_manager.display_for(action, slot)
                for slot in (0, 1)
                if hotkey_manager.display_for(action, slot) != "Not Set"
            ]
            binding = " / ".join(tr(display) for display in displays) or tr("Not Set")
            parts.append(f"{tr(label)}: {binding}")
        self.hk_label.setText("\n".join(parts))

    def _populate_theme_combo(self) -> None:
        active = ThemeManager.get_active_name()
        for name in ThemeManager.all_themes():
            self.theme_combo.addItem(name)
        idx = self.theme_combo.findText(active)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)

    def retranslate_language_items(self, language_manager) -> None:
        current = str(self.language_combo.currentData() or "auto")
        self.language_combo.blockSignals(True)
        self.language_combo.clear()
        for option in ("auto", "zh_CN", "en_US"):
            self.language_combo.addItem(language_manager.language_option_text(option), option)
        self.language_combo.setCurrentIndex(max(0, self.language_combo.findData(current)))
        self.language_combo.blockSignals(False)

    # ── Public API ─────────────────────────────────────────────────────

    def refresh_theme_combo(self) -> None:
        self.theme_combo.blockSignals(True)
        self.theme_combo.clear()
        self._populate_theme_combo()
        self.theme_combo.blockSignals(False)

    def load_config(self, config: dict, save_dir: str) -> None:
        self.use_ai_pedal_check.setChecked(config.get('use_ai_pedal', False))
        self.always_top_check.setChecked(config.get('always_on_top', False))
        self.opacity_slider.setValue(config.get('opacity', 100))
        self.timeline_vis_check.setChecked(config.get('show_timeline_visualizer', True))
        self.piano_vis_check.setChecked(config.get('show_piano_visualizer', True))
        self._global_humanization_config = {
            "simulate_hands": bool(config.get("global_simulate_hands", False)),
            "enable_chord_roll": bool(config.get("global_enable_chord_roll", False)),
            "vary_timing": bool(config.get("global_vary_timing", False)),
            "timing_variance": float(config.get("global_timing_variance", 0.010)),
            "vary_articulation": bool(config.get("global_vary_articulation", False)),
            "articulation": float(config.get("global_articulation", 0.95)),
            "enable_drift_correction": bool(config.get("global_enable_drift_correction", False)),
            "drift_decay_factor": float(config.get("global_drift_decay_factor", 0.25)),
            "enable_mistakes": bool(config.get("global_enable_mistakes", False)),
            "mistake_chance": float(config.get("global_mistake_chance", 0.5)),
            "enable_tempo_sway": bool(config.get("global_enable_tempo_sway", False)),
            "tempo_sway_intensity": float(config.get("global_tempo_sway_intensity", 0.015)),
            "invert_tempo_sway": bool(config.get("global_invert_tempo_sway", False)),
        }
        self.save_path_input.setText(save_dir)
        lang = str(config.get("language_selection", "auto"))
        idx = self.language_combo.findData(lang)
        self.language_combo.setCurrentIndex(idx if idx >= 0 else 0)

    def gather_config(self) -> dict:
        global_cfg = self._global_humanization_config
        return {
            'use_ai_pedal': self.use_ai_pedal_check.isChecked(),
            'always_on_top': self.always_top_check.isChecked(),
            'opacity': self.opacity_slider.value(),
            'show_timeline_visualizer': self.timeline_vis_check.isChecked(),
            'show_piano_visualizer': self.piano_vis_check.isChecked(),
            'language_selection': str(self.language_combo.currentData() or 'auto'),
            'global_simulate_hands': bool(global_cfg.get('simulate_hands', False)),
            'global_enable_chord_roll': bool(global_cfg.get('enable_chord_roll', False)),
            'global_vary_timing': bool(global_cfg.get('vary_timing', False)),
            'global_timing_variance': float(global_cfg.get('timing_variance', 0.010)),
            'global_vary_articulation': bool(global_cfg.get('vary_articulation', False)),
            'global_articulation': float(global_cfg.get('articulation', 0.95)),
            'global_enable_drift_correction': bool(global_cfg.get('enable_drift_correction', False)),
            'global_drift_decay_factor': float(global_cfg.get('drift_decay_factor', 0.25)),
            'global_enable_mistakes': bool(global_cfg.get('enable_mistakes', False)),
            'global_mistake_chance': float(global_cfg.get('mistake_chance', 0.5)),
            'global_enable_tempo_sway': bool(global_cfg.get('enable_tempo_sway', False)),
            'global_tempo_sway_intensity': float(global_cfg.get('tempo_sway_intensity', 0.015)),
            'global_invert_tempo_sway': bool(global_cfg.get('invert_tempo_sway', False)),
        }

    def global_humanization_config(self) -> dict:
        return dict(self._global_humanization_config)

    def set_global_humanization_config(self, config: dict) -> None:
        merged = dict(self.GLOBAL_HUMANIZATION_DEFAULTS)
        merged.update({key: config[key] for key in merged if key in config})
        self._global_humanization_config = merged

    def update_global_humanization_summary(self, tr=lambda text: text) -> None:
        cfg = self._global_humanization_config
        labels = []
        for key, text in (
            ("simulate_hands", "Simulate Hands"),
            ("enable_chord_roll", "Chord Roll"),
            ("vary_timing", "Vary Timing"),
            ("vary_articulation", "Vary Articulation"),
            ("enable_drift_correction", "Hand Drift"),
            ("enable_mistakes", "Mistakes"),
            ("enable_tempo_sway", "Tempo Sway"),
        ):
            if cfg.get(key):
                labels.append(tr(text))
        self.global_humanization_summary.setText(
            ", ".join(labels) if labels else tr("No simulated-performance options enabled")
        )
