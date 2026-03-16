from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QTextEdit, QApplication)
from PyQt6.QtGui import QFont


class DebugTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont("Courier New", 9))
        layout.addWidget(self.log_output)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self.log_clear_btn = QPushButton("Clear")
        self.log_clear_btn.setToolTip("Clear all log entries")
        self.log_copy_btn = QPushButton("Copy Log")
        self.log_copy_btn.setToolTip("Copy the full log to clipboard")
        self.log_clear_btn.clicked.connect(self.log_output.clear)
        self.log_copy_btn.clicked.connect(self._copy_to_clipboard)
        btn_row.addWidget(self.log_clear_btn)
        btn_row.addWidget(self.log_copy_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _copy_to_clipboard(self) -> None:
        QApplication.clipboard().setText(self.log_output.toPlainText())
