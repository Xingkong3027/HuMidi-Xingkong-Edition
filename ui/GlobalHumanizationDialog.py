from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QGridLayout,
    QLabel,
    QVBoxLayout,
)

from ui.theme import ThemeManager, generate_stylesheet


class GlobalHumanizationDialog(QDialog):
    """Editor for the global human-like performance preset."""

    def __init__(self, config: dict, parent=None, language_manager=None):
        super().__init__(parent)
        self.language_manager = language_manager
        self._setup_ui()
        self.load_config(config)
        self.retranslate_ui()

    def _setup_ui(self):
        self.resize(560, 420)
        self.setStyleSheet(generate_stylesheet(ThemeManager.get_active()))
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        self.info_label = QLabel(
            "Songs set to 'Enabled (Use Global Settings)' use these options. "
            "Changing this preset affects their next compilation."
        )
        self.info_label.setWordWrap(True)
        self.info_label.setProperty("role", "muted")
        outer.addWidget(self.info_label)

        grid = QGridLayout()
        grid.setSpacing(9)
        self.simulate_hands = QCheckBox("Simulate Hands")
        self.chord_roll = QCheckBox("Chord Roll")
        grid.addWidget(self.simulate_hands, 0, 0, 1, 2)
        grid.addWidget(self.chord_roll, 1, 0, 1, 2)

        self.vary_timing = QCheckBox("Vary Timing")
        self.timing = self._spin(0.0, 0.1, 0.01, 4, " s")
        self.vary_articulation = QCheckBox("Vary Articulation")
        self.articulation = self._spin(50.0, 100.0, 95.0, 1, "%")
        self.hand_drift = QCheckBox("Hand Drift")
        self.drift = self._spin(0.0, 100.0, 25.0, 1, "%")
        self.mistakes = QCheckBox("Mistakes")
        self.mistake_chance = self._spin(0.0, 10.0, 0.5, 1, "%")
        self.tempo_sway = QCheckBox("Tempo Sway")
        self.sway = self._spin(0.0, 0.1, 0.015, 4, " s")
        self.invert_sway = QCheckBox("Invert Sway")

        rows = [
            (self.vary_timing, self.timing),
            (self.vary_articulation, self.articulation),
            (self.hand_drift, self.drift),
            (self.mistakes, self.mistake_chance),
            (self.tempo_sway, self.sway),
        ]
        for row, (check, spin) in enumerate(rows, start=2):
            grid.addWidget(check, row, 0)
            grid.addWidget(spin, row, 1)
            check.toggled.connect(spin.setEnabled)
        grid.addWidget(self.invert_sway, 7, 0, 1, 2)
        self.tempo_sway.toggled.connect(self.invert_sway.setEnabled)
        outer.addLayout(grid)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        outer.addWidget(self.buttons)

    @staticmethod
    def _spin(minimum, maximum, value, decimals, suffix):
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setDecimals(decimals)
        spin.setValue(value)
        spin.setSuffix(suffix)
        spin.setAlignment(Qt.AlignmentFlag.AlignRight)
        return spin

    def load_config(self, config: dict):
        self.simulate_hands.setChecked(bool(config.get("simulate_hands", False)))
        self.chord_roll.setChecked(bool(config.get("enable_chord_roll", False)))
        self.vary_timing.setChecked(bool(config.get("vary_timing", False)))
        self.timing.setValue(float(config.get("timing_variance", 0.010)))
        self.vary_articulation.setChecked(bool(config.get("vary_articulation", False)))
        self.articulation.setValue(float(config.get("articulation", 0.95)) * 100.0)
        self.hand_drift.setChecked(bool(config.get("enable_drift_correction", False)))
        self.drift.setValue(float(config.get("drift_decay_factor", 0.25)) * 100.0)
        self.mistakes.setChecked(bool(config.get("enable_mistakes", False)))
        self.mistake_chance.setValue(float(config.get("mistake_chance", 0.5)))
        self.tempo_sway.setChecked(bool(config.get("enable_tempo_sway", False)))
        self.sway.setValue(float(config.get("tempo_sway_intensity", 0.015)))
        self.invert_sway.setChecked(bool(config.get("invert_tempo_sway", False)))
        self._sync_enabled()

    def _sync_enabled(self):
        self.timing.setEnabled(self.vary_timing.isChecked())
        self.articulation.setEnabled(self.vary_articulation.isChecked())
        self.drift.setEnabled(self.hand_drift.isChecked())
        self.mistake_chance.setEnabled(self.mistakes.isChecked())
        self.sway.setEnabled(self.tempo_sway.isChecked())
        self.invert_sway.setEnabled(self.tempo_sway.isChecked())

    def get_config(self) -> dict:
        return {
            "simulate_hands": self.simulate_hands.isChecked(),
            "enable_chord_roll": self.chord_roll.isChecked(),
            "vary_timing": self.vary_timing.isChecked(),
            "timing_variance": self.timing.value(),
            "vary_articulation": self.vary_articulation.isChecked(),
            "articulation": self.articulation.value() / 100.0,
            "enable_drift_correction": self.hand_drift.isChecked(),
            "drift_decay_factor": self.drift.value() / 100.0,
            "enable_mistakes": self.mistakes.isChecked(),
            "mistake_chance": self.mistake_chance.value(),
            "enable_tempo_sway": self.tempo_sway.isChecked(),
            "tempo_sway_intensity": self.sway.value(),
            "invert_tempo_sway": self.invert_sway.isChecked(),
        }

    def retranslate_ui(self):
        tr = self.language_manager.tr if self.language_manager else (lambda text: text)
        self.setWindowTitle(tr("Global Human-like Performance Settings"))
        self.info_label.setText(tr(
            "Songs set to 'Enabled (Use Global Settings)' use these options. Changing this preset affects their next compilation."
        ))
        for widget in (
            self.simulate_hands, self.chord_roll, self.vary_timing, self.vary_articulation,
            self.hand_drift, self.mistakes, self.tempo_sway, self.invert_sway,
        ):
            widget.setText(tr(widget.text()))
        ok = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        cancel = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if ok:
            ok.setText(tr("OK"))
        if cancel:
            cancel.setText(tr("Cancel"))
