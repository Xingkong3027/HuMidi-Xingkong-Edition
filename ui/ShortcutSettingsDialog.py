from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ui.theme import ThemeManager, generate_stylesheet


class ShortcutSettingsDialog(QDialog):
    ACTIONS = (
        ("play_pause", "Play / Pause"),
        ("stop", "Stop"),
        ("next", "Next Song"),
        ("previous", "Previous Song"),
    )

    def __init__(self, hotkey_manager, parent=None, language_manager=None):
        super().__init__(parent)
        self.hotkey_manager = hotkey_manager
        self.language_manager = language_manager
        self._snapshot = hotkey_manager.snapshot()
        self._active_target: tuple[str, int] | None = None
        self._slot_buttons: dict[tuple[str, int], QPushButton] = {}
        self.setStyleSheet(generate_stylesheet(ThemeManager.get_active()))
        self.resize(680, 360)
        self._setup_ui()
        self.hotkey_manager.binding_captured.connect(self._on_binding_captured)
        self.hotkey_manager.bindings_changed.connect(self.refresh_bindings)
        self.retranslate_ui()
        self.refresh_bindings()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(12)

        self.info_label = QLabel(
            "Each action can use up to two shortcuts. Media Play/Pause, Media Previous, "
            "Media Next, function keys, letters, numbers, and other keyboard keys are supported."
        )
        self.info_label.setWordWrap(True)
        self.info_label.setProperty("role", "muted")
        outer.addWidget(self.info_label)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        self.action_header = QLabel("Action")
        self.shortcut1_header = QLabel("Shortcut 1")
        self.shortcut2_header = QLabel("Shortcut 2")
        grid.addWidget(self.action_header, 0, 0)
        grid.addWidget(self.shortcut1_header, 0, 1)
        grid.addWidget(self.shortcut2_header, 0, 2)

        self.action_labels: dict[str, QLabel] = {}
        for row, (action, label) in enumerate(self.ACTIONS, start=1):
            action_label = QLabel(label)
            self.action_labels[action] = action_label
            grid.addWidget(action_label, row, 0)
            for slot in (0, 1):
                holder = QWidget()
                holder_layout = QHBoxLayout(holder)
                holder_layout.setContentsMargins(0, 0, 0, 0)
                holder_layout.setSpacing(4)
                bind_btn = QPushButton()
                bind_btn.setMinimumWidth(150)
                bind_btn.clicked.connect(
                    lambda _checked=False, a=action, s=slot: self._begin_capture(a, s)
                )
                clear_btn = QToolButton()
                clear_btn.setText("×")
                clear_btn.setToolTip("Clear this shortcut")
                clear_btn.clicked.connect(
                    lambda _checked=False, a=action, s=slot: self._clear_binding(a, s)
                )
                holder_layout.addWidget(bind_btn, 1)
                holder_layout.addWidget(clear_btn)
                grid.addWidget(holder, row, slot + 1)
                self._slot_buttons[(action, slot)] = bind_btn
        outer.addLayout(grid)

        self.capture_hint = QLabel("")
        self.capture_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.capture_hint.setProperty("role", "accent")
        outer.addWidget(self.capture_hint)
        outer.addStretch()

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        outer.addWidget(self.buttons)

    def _tr(self, text: str) -> str:
        return self.language_manager.tr(text) if self.language_manager else text

    def retranslate_ui(self):
        tr = self._tr
        self.setWindowTitle(tr("Keyboard Shortcuts"))
        self.info_label.setText(tr(
            "Each action can use up to two shortcuts. Media Play/Pause, Media Previous, "
            "Media Next, function keys, letters, numbers, and other keyboard keys are supported."
        ))
        self.action_header.setText(tr("Action"))
        self.shortcut1_header.setText(tr("Shortcut 1"))
        self.shortcut2_header.setText(tr("Shortcut 2"))
        for action, label in self.ACTIONS:
            self.action_labels[action].setText(tr(label))
        ok_btn = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        cancel_btn = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if ok_btn:
            ok_btn.setText(tr("OK"))
        if cancel_btn:
            cancel_btn.setText(tr("Cancel"))
        self.refresh_bindings()

    def refresh_bindings(self):
        for (action, slot), button in self._slot_buttons.items():
            if self._active_target == (action, slot):
                button.setText(self._tr("Press a key…"))
            else:
                display = self.hotkey_manager.display_for(action, slot)
                button.setText(self._tr(display))

    def _begin_capture(self, action: str, slot: int):
        self._active_target = (action, slot)
        self.capture_hint.setText(self._tr("Press the key you want to use. Press Esc to bind Esc."))
        self.hotkey_manager.start_binding(action, slot)
        self.refresh_bindings()

    def _on_binding_captured(self, action: str, slot: int, _display: str):
        if self._active_target == (action, slot):
            self._active_target = None
            self.capture_hint.setText(self._tr("Shortcut captured."))
        self.refresh_bindings()

    def _clear_binding(self, action: str, slot: int):
        if self._active_target == (action, slot):
            self.hotkey_manager.cancel_binding()
            self._active_target = None
        self.hotkey_manager.clear_binding(action, slot)
        self.capture_hint.setText("")
        self.refresh_bindings()

    def keyPressEvent(self, event):
        # While the global listener is capturing a binding, prevent QDialog's
        # local Esc/Enter handling from closing or accepting the dialog first.
        if self.hotkey_manager.listening_for_bind:
            event.accept()
            return
        super().keyPressEvent(event)

    def accept(self):
        self.hotkey_manager.cancel_binding()
        self._active_target = None
        super().accept()

    def reject(self):
        self.hotkey_manager.cancel_binding()
        self._active_target = None
        self.hotkey_manager.restore_bindings(self._snapshot, reset=True)
        super().reject()

    def closeEvent(self, event):
        if self.result() != QDialog.DialogCode.Accepted:
            self.hotkey_manager.cancel_binding()
            self.hotkey_manager.restore_bindings(self._snapshot, reset=True)
        super().closeEvent(event)
