from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox, QSlider,
    QLabel, QComboBox, QLineEdit, QGridLayout)
from PyQt6.QtCore import Qt

from ui.widgets import make_card
from ui.theme import ThemeManager


class SettingsTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(12)

        # ── Save Path card (full width) ────────────────────────────────
        save_card, save_content = make_card("Save Path")
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

        # ── Two-column body ────────────────────────────────────────────
        body = QHBoxLayout()
        body.setSpacing(12)

        left_col = QVBoxLayout()
        left_col.setSpacing(10)
        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        # Hotkey card
        hk_card, hk_content = make_card("Hotkey")
        hk_row = QHBoxLayout()
        hk_row.setSpacing(8)
        self.hk_label = QLabel("Hotkey: ")
        self.hk_btn = QPushButton("Change")
        self.hk_btn.setToolTip("Click to bind a new hotkey for toggling playback")
        hk_row.addWidget(self.hk_label, 1)
        hk_row.addWidget(self.hk_btn)
        hk_content.addLayout(hk_row)
        left_col.addWidget(hk_card)

        # Overlay card
        ov_card, ov_content = make_card("Overlay")
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
        ov_grid.addWidget(opacity_label,         1, 0)
        ov_grid.addWidget(self.opacity_slider,   1, 1)
        ov_content.addLayout(ov_grid)
        left_col.addWidget(ov_card)

        self.check_update_btn = QPushButton("Check for updates")
        self.check_update_btn.setToolTip("Check GitHub for a newer version of HuMidi")
        left_col.addWidget(self.check_update_btn)
        left_col.addStretch()

        # Visualizer card
        vis_card, vis_content = make_card("Visualizer")
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

        # Theme card
        theme_card, theme_content = make_card("Theme")
        theme_row = QHBoxLayout()
        theme_row.setSpacing(8)
        self.theme_combo = QComboBox()
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
        outer.addLayout(body, 1)

    def _populate_theme_combo(self) -> None:
        active = ThemeManager.get_active_name()
        for name in ThemeManager.all_themes():
            self.theme_combo.addItem(name)
        idx = self.theme_combo.findText(active)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)

    # ── Public API ─────────────────────────────────────────────────────

    def refresh_theme_combo(self) -> None:
        self.theme_combo.blockSignals(True)
        self.theme_combo.clear()
        self._populate_theme_combo()
        self.theme_combo.blockSignals(False)

    def load_config(self, config: dict, save_dir: str) -> None:
        self.always_top_check.setChecked(config.get('always_on_top', False))
        self.opacity_slider.setValue(config.get('opacity', 100))
        self.timeline_vis_check.setChecked(config.get('show_timeline_visualizer', True))
        self.piano_vis_check.setChecked(config.get('show_piano_visualizer', True))
        self.save_path_input.setText(save_dir)

    def gather_config(self) -> dict:
        return {
            'always_on_top':             self.always_top_check.isChecked(),
            'opacity':                   self.opacity_slider.value(),
            'show_timeline_visualizer':  self.timeline_vis_check.isChecked(),
            'show_piano_visualizer':     self.piano_vis_check.isChecked(),
        }
