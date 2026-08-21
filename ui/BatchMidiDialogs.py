from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from ui.theme import ThemeManager, generate_stylesheet


class BatchImportChoiceDialog(QDialog):
    def __init__(self, count: int, parent=None, language_manager=None):
        super().__init__(parent)
        self.count = count
        self.language_manager = language_manager
        self.choice = "cancel"
        self.setStyleSheet(generate_stylesheet(ThemeManager.get_active()))
        self.setMinimumWidth(580)
        self._setup_ui()
        self.retranslate_ui()

    def _tr(self, text: str) -> str:
        return self.language_manager.tr(text) if self.language_manager else text

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)
        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)
        row = QHBoxLayout()
        row.addStretch()
        self.auto_btn = QPushButton()
        self.manual_btn = QPushButton()
        self.cancel_btn = QPushButton()
        self.auto_btn.setObjectName("save_button")
        self.auto_btn.clicked.connect(lambda: self._finish("auto"))
        self.manual_btn.clicked.connect(lambda: self._finish("manual"))
        self.cancel_btn.clicked.connect(self.reject)
        row.addWidget(self.auto_btn)
        row.addWidget(self.manual_btn)
        row.addWidget(self.cancel_btn)
        layout.addLayout(row)

    def retranslate_ui(self):
        tr = self._tr
        self.setWindowTitle(tr("Batch Import MIDI"))
        self.message_label.setText(
            tr("Importing {count} MIDI files. How should track selection and hand assignment be handled?").format(
                count=self.count
            )
        )
        self.auto_btn.setText(tr("Process All Automatically"))
        self.manual_btn.setText(tr("Let Me Choose"))
        self.cancel_btn.setText(tr("Cancel"))

    def _finish(self, choice: str):
        self.choice = choice
        self.accept()


class BatchImportSummaryDialog(QDialog):
    def __init__(self, successes: list[dict], failures: list[dict], parent=None, language_manager=None):
        super().__init__(parent)
        self.successes = successes
        self.failures = failures
        self.language_manager = language_manager
        self.choice = "cancel"
        self.setStyleSheet(generate_stylesheet(ThemeManager.get_active()))
        self.resize(720, 500)
        self._setup_ui()
        self.retranslate_ui()

    def _tr(self, text: str) -> str:
        return self.language_manager.tr(text) if self.language_manager else text

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        layout.addWidget(self.details, 1)
        row = QHBoxLayout()
        row.addStretch()
        self.add_btn = QPushButton()
        self.continue_btn = QPushButton()
        self.cancel_btn = QPushButton()
        self.add_btn.setObjectName("save_button")
        self.add_btn.clicked.connect(lambda: self._finish("add"))
        self.continue_btn.clicked.connect(lambda: self._finish("continue"))
        self.cancel_btn.clicked.connect(self.reject)
        row.addWidget(self.add_btn)
        row.addWidget(self.continue_btn)
        row.addWidget(self.cancel_btn)
        layout.addLayout(row)

    def retranslate_ui(self):
        tr = self._tr
        self.setWindowTitle(tr("Batch Import Results"))
        self.summary_label.setText(
            tr("Successfully prepared {success} MIDI file(s); {failed} file(s) were not prepared.").format(
                success=len(self.successes), failed=len(self.failures)
            )
        )
        lines = [tr("Successfully imported:")]
        if self.successes:
            lines.extend(f"  ✓ {Path(item['path']).name}" for item in self.successes)
        else:
            lines.append(f"  {tr('None')}")
        lines.append("")
        lines.append(tr("Not imported:"))
        if self.failures:
            for item in self.failures:
                lines.append(f"  ✗ {Path(item.get('path', '')).name}: {item.get('reason', '')}")
        else:
            lines.append(f"  {tr('None')}")
        self.details.setPlainText("\n".join(lines))
        self.add_btn.setText(tr("Add to Playlist"))
        self.continue_btn.setText(tr("Continue Settings"))
        self.cancel_btn.setText(tr("Cancel"))
        enabled = bool(self.successes)
        self.add_btn.setEnabled(enabled)
        self.continue_btn.setEnabled(enabled)

    def _finish(self, choice: str):
        self.choice = choice
        self.accept()
