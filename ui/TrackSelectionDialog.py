from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ui.theme import ThemeManager, generate_stylesheet


class TrackSelectionDialog(QDialog):
    """Track and hand-assignment chooser.

    ``mode='auto_failure'`` is used by batch import when automatic selection
    could not find a playable non-drum track.  It exposes Ignore, Ignore All,
    and Confirm and Continue outcomes.
    """

    def __init__(
        self,
        tracks,
        parent=None,
        language_manager=None,
        *,
        mode: str = "normal",
        midi_name: str = "",
    ):
        super().__init__(parent)
        self.resize(760, 430)
        self.setStyleSheet(generate_stylesheet(ThemeManager.get_active()))
        self.tracks = tracks
        self.language_manager = language_manager
        self.mode = mode
        self.midi_name = midi_name
        self.result_action = "cancel"
        self._setup_ui()
        self.retranslate_ui()

    def _tr(self, text: str) -> str:
        return self.language_manager.tr(text) if self.language_manager else text

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setProperty("role", "muted")
        layout.addWidget(self.info_label)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        layout.addWidget(self.table)

        self.table.setRowCount(len(self.tracks))
        self.table.verticalHeader().setMinimumSectionSize(36)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.checkboxes = []
        self.role_combos = []

        for i, track in enumerate(self.tracks):
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            check_item.setCheckState(
                Qt.CheckState.Unchecked if track.is_drum else Qt.CheckState.Checked
            )
            self.table.setItem(i, 0, check_item)
            self.checkboxes.append(check_item)

            name_item = QTableWidgetItem(str(track.name))
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 1, name_item)

            inst_item = QTableWidgetItem(str(track.instrument_name))
            inst_item.setFlags(inst_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 2, inst_item)

            notes_item = QTableWidgetItem(str(track.note_count))
            notes_item.setFlags(notes_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            notes_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 3, notes_item)

            combo = QComboBox()
            combo.setStyleSheet("QComboBox { min-height: 0px; padding: 2px 8px; }")
            combo.setFixedHeight(28)
            for text, value in (
                ("Auto-Detect", "Auto-Detect"),
                ("Left Hand", "Left Hand"),
                ("Right Hand", "Right Hand"),
            ):
                combo.addItem(text, value)
            self.table.setCellWidget(i, 4, combo)
            self.role_combos.append(combo)

        self.table.resizeColumnToContents(0)
        self.table.resizeColumnToContents(3)
        self.table.resizeColumnToContents(4)

        if self.mode == "auto_failure":
            self.buttons = None
            button_row = QHBoxLayout()
            button_row.addStretch()
            self.ignore_btn = QPushButton("Ignore")
            self.ignore_all_btn = QPushButton("Ignore All")
            self.continue_btn = QPushButton("Confirm and Continue")
            self.continue_btn.setObjectName("save_button")
            self.ignore_btn.clicked.connect(self._ignore)
            self.ignore_all_btn.clicked.connect(self._ignore_all)
            self.continue_btn.clicked.connect(self._accept_with_validation)
            button_row.addWidget(self.ignore_btn)
            button_row.addWidget(self.ignore_all_btn)
            button_row.addWidget(self.continue_btn)
            layout.addLayout(button_row)
        else:
            self.buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
            )
            ok_btn = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
            if ok_btn:
                ok_btn.setObjectName("save_button")
            self.buttons.accepted.connect(self._accept_with_validation)
            self.buttons.rejected.connect(self.reject)
            layout.addWidget(self.buttons)

    def retranslate_ui(self):
        tr = self._tr
        self.setWindowTitle(tr("Select Tracks"))
        if self.mode == "auto_failure":
            self.info_label.setText(
                tr("This MIDI could not be selected automatically. Please choose at least one track to continue.")
                + (f"\n{self.midi_name}" if self.midi_name else "")
            )
        else:
            self.info_label.setText(tr(
                "Select the tracks to include in playback. Optionally override the hand assignment for each track."
            ) + (f"\n{self.midi_name}" if self.midi_name else ""))
        self.table.setHorizontalHeaderLabels([
            tr("Play"), tr("Track Name"), tr("Instrument"), tr("Notes"), tr("Hand Assignment")
        ])
        for combo in self.role_combos:
            current = str(combo.currentData() or "Auto-Detect")
            combo.blockSignals(True)
            combo.clear()
            for text, value in (
                ("Auto-Detect", "Auto-Detect"),
                ("Left Hand", "Left Hand"),
                ("Right Hand", "Right Hand"),
            ):
                combo.addItem(tr(text), value)
            combo.setCurrentIndex(max(0, combo.findData(current)))
            combo.blockSignals(False)
        if self.mode == "auto_failure":
            self.ignore_btn.setText(tr("Ignore"))
            self.ignore_all_btn.setText(tr("Ignore All"))
            self.continue_btn.setText(tr("Confirm and Continue"))
        elif self.buttons is not None:
            ok_btn = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
            cancel_btn = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
            if ok_btn:
                ok_btn.setText(tr("OK"))
            if cancel_btn:
                cancel_btn.setText(tr("Cancel"))

    def _accept_with_validation(self):
        if not self.get_selection():
            QMessageBox.warning(
                self,
                self._tr("No Tracks"),
                self._tr("Please select at least one track."),
            )
            return
        self.result_action = "accepted"
        self.accept()

    def _ignore(self):
        self.result_action = "ignore"
        self.reject()

    def _ignore_all(self):
        self.result_action = "ignore_all"
        self.reject()

    def reject(self):
        if self.result_action not in {"ignore", "ignore_all"}:
            self.result_action = "cancel"
        super().reject()

    def get_selection(self):
        result = []
        for i, track in enumerate(self.tracks):
            if self.checkboxes[i].checkState() == Qt.CheckState.Checked:
                role = str(self.role_combos[i].currentData() or "Auto-Detect")
                result.append((track, role))
        return result
