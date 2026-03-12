from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QTabWidget, QTextEdit, QSpinBox, QCheckBox, QPushButton, QFrame
)
from PyQt6.QtCore import pyqtSignal as Signal
from PyQt6.QtGui import QFont

from core.translator import FormatRegistry


class TranslatorTab(QWidget):
    # Emitted when the user wants to play an imported sheet
    # (text, format_name, bpm, humanize)
    play_sheet_requested = Signal(str, str, int, bool)

    # Emitted when the user wants to export the current MIDI as a sheet
    # (format_name)
    export_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Format selector row
        fmt_row = QHBoxLayout()
        fmt_label = QLabel("Format")
        fmt_label.setProperty("role", "section")
        self.format_combo = QComboBox()
        self.format_combo.addItems(FormatRegistry.names())
        self.format_combo.setToolTip("Select the Roblox piano sheet format")
        fmt_row.addWidget(fmt_label)
        fmt_row.addWidget(self.format_combo, 1)
        layout.addLayout(fmt_row)

        # Sub-tabs
        self.sub_tabs = QTabWidget()
        self.sub_tabs.addTab(self._build_import_tab(), "Import")
        self.sub_tabs.addTab(self._build_export_tab(), "Export")
        layout.addWidget(self.sub_tabs)

    # ── Import tab ────────────────────────────────────────────────────

    def _build_import_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        hint = QLabel("Paste sheet text:")
        hint.setProperty("role", "muted")
        layout.addWidget(hint)

        self.import_text = QTextEdit()
        self.import_text.setFont(QFont("Courier New", 9))
        self.import_text.setPlaceholderText(
            "e.g.\ne e e [6t] e\ne y 9 y t [wy] t\ne w [6e] e e t"
        )
        layout.addWidget(self.import_text)

        # Options row
        options_row = QHBoxLayout()
        options_row.setSpacing(12)
        bpm_label = QLabel("BPM")
        bpm_label.setProperty("role", "muted")
        self.bpm_spinbox = QSpinBox()
        self.bpm_spinbox.setRange(20, 400)
        self.bpm_spinbox.setValue(120)
        self.bpm_spinbox.setFixedWidth(70)
        self.bpm_spinbox.setToolTip("Tempo used to calculate note durations from the sheet")
        self.humanize_check = QCheckBox("Humanize")
        self.humanize_check.setToolTip(
            "Apply current humanization settings during playback.\n"
            "When unchecked, the sheet plays back exactly as written."
        )
        options_row.addWidget(bpm_label)
        options_row.addWidget(self.bpm_spinbox)
        options_row.addWidget(self.humanize_check)
        options_row.addStretch()
        layout.addLayout(options_row)

        self.import_play_btn = QPushButton("▶  Play Sheet")
        self.import_play_btn.setToolTip(
            "Convert the pasted sheet to keystrokes and begin playback"
        )
        self.import_play_btn.clicked.connect(self._on_play_clicked)
        layout.addWidget(self.import_play_btn)

        return tab

    # ── Export tab ────────────────────────────────────────────────────

    def _build_export_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.export_status_label = QLabel(
            "Load a MIDI file on the Playback tab, then click Generate."
        )
        self.export_status_label.setProperty("role", "muted")
        self.export_status_label.setStyleSheet("font-style: italic;")
        layout.addWidget(self.export_status_label)

        self.export_generate_btn = QPushButton("Generate Sheet")
        self.export_generate_btn.setToolTip(
            "Convert the currently loaded MIDI notes to sheet text in the selected format"
        )
        self.export_generate_btn.clicked.connect(self._on_export_clicked)
        layout.addWidget(self.export_generate_btn)

        sep = QFrame()
        sep.setObjectName("h_sep")
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        out_label = QLabel("Output")
        out_label.setProperty("role", "muted")
        layout.addWidget(out_label)

        self.export_text = QTextEdit()
        self.export_text.setReadOnly(True)
        self.export_text.setFont(QFont("Courier New", 9))
        self.export_text.setPlaceholderText("Generated sheet will appear here…")
        layout.addWidget(self.export_text)

        self.copy_btn = QPushButton("Copy to Clipboard")
        self.copy_btn.setToolTip("Copy the generated sheet to the clipboard")
        self.copy_btn.clicked.connect(self._on_copy_clicked)
        layout.addWidget(self.copy_btn)

        return tab

    # ── Slots ─────────────────────────────────────────────────────────

    def _on_play_clicked(self):
        text = self.import_text.toPlainText().strip()
        if not text:
            return
        self.play_sheet_requested.emit(
            text,
            self.format_combo.currentText(),
            self.bpm_spinbox.value(),
            self.humanize_check.isChecked(),
        )

    def _on_export_clicked(self):
        self.export_requested.emit(self.format_combo.currentText())

    def _on_copy_clicked(self):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.export_text.toPlainText())

    # ── Public API ────────────────────────────────────────────────────

    def set_export_text(self, text: str):
        self.export_text.setPlainText(text)
        note_count = sum(
            1 for line in text.splitlines() if line.strip() and not line.startswith('#')
        )
        self.export_status_label.setText(f"Generated {note_count} line(s).")
        self.export_status_label.setStyleSheet("")
        self.export_status_label.setProperty("role", "success")
        self.export_status_label.style().unpolish(self.export_status_label)
        self.export_status_label.style().polish(self.export_status_label)
