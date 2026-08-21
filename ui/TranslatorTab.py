from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QTabWidget, QTextEdit, QSpinBox, QCheckBox, QPushButton, QFrame,
    QLineEdit,
)
from PyQt6.QtCore import pyqtSignal as Signal
from PyQt6.QtGui import QFont

from core.translator import FormatRegistry


class TranslatorTab(QWidget):
    # (text, canonical_format_name, bpm, simulate_human_performance)
    play_sheet_requested = Signal(str, str, int, bool)
    # (text, canonical_format_name, bpm, simulate_human_performance, display_name)
    add_to_playlist_requested = Signal(str, str, int, bool, str)
    # (canonical_format_name)
    export_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tr = lambda text: text
        self._playlist_editing = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        fmt_row = QHBoxLayout()
        self.format_label = QLabel("Format")
        self.format_label.setProperty("role", "section")
        self.format_combo = QComboBox()
        for name in FormatRegistry.names():
            self.format_combo.addItem(name, name)
        self.format_combo.setToolTip("Select the Roblox piano sheet format")
        fmt_row.addWidget(self.format_label)
        fmt_row.addWidget(self.format_combo, 1)
        layout.addLayout(fmt_row)

        self.sub_tabs = QTabWidget()
        self.import_tab = self._build_import_tab()
        self.export_tab = self._build_export_tab()
        self.sub_tabs.addTab(self.import_tab, "Import")
        self.sub_tabs.addTab(self.export_tab, "Export")
        layout.addWidget(self.sub_tabs)

    def _build_import_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.name_label = QLabel("Song Name")
        self.name_label.setProperty("role", "muted")
        layout.addWidget(self.name_label)
        self.song_name_input = QLineEdit()
        self.song_name_input.setPlaceholderText("Optional; defaults to Text Sheet")
        layout.addWidget(self.song_name_input)

        self.import_hint = QLabel("Paste sheet text:")
        self.import_hint.setProperty("role", "muted")
        layout.addWidget(self.import_hint)

        self.import_text = QTextEdit()
        self.import_text.setFont(QFont("Courier New", 9))
        self.import_text.setPlaceholderText(
            "e.g.\ne e e [6t] e\ne y 9 y t [wy] t\ne w [6e] e e t"
        )
        layout.addWidget(self.import_text)

        options_row = QHBoxLayout()
        options_row.setSpacing(12)
        self.bpm_label = QLabel("BPM")
        self.bpm_label.setProperty("role", "muted")
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
        options_row.addWidget(self.bpm_label)
        options_row.addWidget(self.bpm_spinbox)
        options_row.addWidget(self.humanize_check)
        options_row.addStretch()
        layout.addLayout(options_row)

        button_row = QHBoxLayout()
        self.import_play_btn = QPushButton("▶  Play Sheet")
        self.import_play_btn.setToolTip(
            "Convert the pasted sheet to keystrokes and begin playback"
        )
        self.import_play_btn.clicked.connect(self._on_play_clicked)
        self.add_to_playlist_btn = QPushButton("Add to Playlist")
        self.add_to_playlist_btn.setProperty("i18n_dynamic", True)
        self.add_to_playlist_btn.setToolTip(
            "Add the pasted text sheet and its settings to the playlist"
        )
        self.add_to_playlist_btn.clicked.connect(self._on_add_clicked)
        button_row.addWidget(self.import_play_btn, 1)
        button_row.addWidget(self.add_to_playlist_btn, 1)
        layout.addLayout(button_row)
        return tab

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

        self.output_label = QLabel("Output")
        self.output_label.setProperty("role", "muted")
        layout.addWidget(self.output_label)

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

    def current_format_name(self) -> str:
        return str(self.format_combo.currentData() or self.format_combo.currentText())

    def _payload(self) -> tuple[str, str, int, bool, str]:
        return (
            self.import_text.toPlainText().strip(),
            self.current_format_name(),
            self.bpm_spinbox.value(),
            self.humanize_check.isChecked(),
            self.song_name_input.text().strip(),
        )

    def has_playable_input(self) -> bool:
        return (
            self.sub_tabs.currentWidget() is self.import_tab
            and bool(self.import_text.toPlainText().strip())
        )

    def request_current_playback(self) -> None:
        self._on_play_clicked()

    def _on_play_clicked(self):
        text, format_name, bpm, humanize, _name = self._payload()
        if text:
            self.play_sheet_requested.emit(text, format_name, bpm, humanize)

    def _on_add_clicked(self):
        text, format_name, bpm, humanize, name = self._payload()
        if text:
            self.add_to_playlist_requested.emit(text, format_name, bpm, humanize, name)

    def _on_export_clicked(self):
        self.export_requested.emit(self.current_format_name())

    def _on_copy_clicked(self):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.export_text.toPlainText())

    def set_export_text(self, text: str):
        self.export_text.setPlainText(text)
        note_count = sum(
            1 for line in text.splitlines() if line.strip() and not line.startswith('#')
        )
        self.export_status_label.setText(
            self._tr("Generated {count} line(s).").format(count=note_count)
        )
        self.export_status_label.setStyleSheet("")
        self.export_status_label.setProperty("role", "success")
        self.export_status_label.style().unpolish(self.export_status_label)
        self.export_status_label.style().polish(self.export_status_label)

    def load_sheet(
        self,
        text: str,
        format_name: str,
        bpm: int,
        humanize: bool,
        name: str = "",
    ) -> None:
        index = self.format_combo.findData(format_name)
        if index >= 0:
            self.format_combo.setCurrentIndex(index)
        self.import_text.setPlainText(text)
        self.bpm_spinbox.setValue(max(20, min(400, int(bpm))))
        self.humanize_check.setChecked(bool(humanize))
        self.song_name_input.setText(str(name or ""))
        self.sub_tabs.setCurrentWidget(self.import_tab)

    def reset_sheet_editor(self) -> None:
        self.import_text.clear()
        self.song_name_input.clear()
        self.bpm_spinbox.setValue(120)
        self.humanize_check.setChecked(False)
        self.set_playlist_editing(False, self._tr)

    def set_playlist_editing(self, editing: bool, tr=lambda text: text) -> None:
        self._playlist_editing = bool(editing)
        self.add_to_playlist_btn.setText(
            tr("Complete Modification") if editing else tr("Add to Playlist")
        )
        self.add_to_playlist_btn.setToolTip(
            tr("Save the modified text sheet back to this playlist song")
            if editing else
            tr("Add the pasted text sheet and its settings to the playlist")
        )

    def retranslate(self, language_manager) -> None:
        self._tr = language_manager.tr
        current = self.current_format_name()
        self.format_combo.blockSignals(True)
        self.format_combo.clear()
        for name in FormatRegistry.names():
            self.format_combo.addItem(language_manager.tr(name), name)
        index = self.format_combo.findData(current)
        self.format_combo.setCurrentIndex(max(0, index))
        self.format_combo.blockSignals(False)

        self.sub_tabs.setTabText(self.sub_tabs.indexOf(self.import_tab), language_manager.tr("Import"))
        self.sub_tabs.setTabText(self.sub_tabs.indexOf(self.export_tab), language_manager.tr("Export"))
        self.export_text.setPlaceholderText(language_manager.tr("Generated sheet will appear here…"))
        self.song_name_input.setPlaceholderText(language_manager.tr("Optional; defaults to Text Sheet"))
        self.set_playlist_editing(self._playlist_editing, language_manager.tr)
