"""
ThemeDialog — select from built-in presets, create / edit / delete custom themes.

Live-preview: clicking any theme in the list immediately applies it to the
parent window so you can see it in context.  Clicking Cancel reverts to
whatever was active when the dialog was opened.
"""

from __future__ import annotations
from dataclasses import replace

from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QLineEdit, QPushButton, QScrollArea, QWidget,
    QDialogButtonBox, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal as Signal
from PyQt6.QtGui import QColor

from ui.theme import ThemeColors, ThemeManager, generate_stylesheet, BUILTIN_THEMES


# ── Colour labels (order matters — shown in the editor) ───────────────────

_COLOR_FIELDS = [
    ("bg_primary",    "Background"),
    ("bg_secondary",  "Surface"),
    ("bg_input",      "Input Fields"),
    ("accent",        "Accent"),
    ("text_primary",  "Text"),
    ("text_secondary","Muted Text"),
    ("border",        "Borders"),
    ("accent_play",   "Play Color"),
    ("accent_stop",   "Stop / Danger"),
    ("pedal_color",   "Pedal Color"),
]


# ── Color swatch widget ────────────────────────────────────────────────────

class _ColorSwatch(QWidget):
    """A coloured square button + hex text field, kept in sync."""

    colorChanged = Signal(str)   # emits lowercase hex like "#aabbcc"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._color = "#000000"
        self._editable = True

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._swatch = QPushButton()
        self._swatch.setFixedSize(24, 24)
        self._swatch.setCursor(Qt.CursorShape.PointingHandCursor)
        self._swatch.clicked.connect(self._pick_color)

        self._hex = QLineEdit()
        self._hex.setMaxLength(7)
        self._hex.setPlaceholderText("#rrggbb")
        self._hex.textEdited.connect(self._on_hex_edited)

        layout.addWidget(self._swatch)
        layout.addWidget(self._hex)

    # ── Public ────────────────────────────────────────────────────────

    def set_color(self, hex_color: str, emit: bool = False) -> None:
        self._color = hex_color.lower()
        self._hex.blockSignals(True)
        self._hex.setText(hex_color)
        self._hex.blockSignals(False)
        self._refresh_swatch()
        if emit:
            self.colorChanged.emit(self._color)

    def color(self) -> str:
        return self._color

    def set_editable(self, editable: bool) -> None:
        self._editable = editable
        self._swatch.setEnabled(editable)
        self._hex.setReadOnly(not editable)

    # ── Internals ─────────────────────────────────────────────────────

    def _pick_color(self) -> None:
        if not self._editable:
            return
        from PyQt6.QtWidgets import QColorDialog
        initial = QColor(self._color)
        color = QColorDialog.getColor(initial, self, "Choose colour")
        if color.isValid():
            self.set_color(color.name(), emit=True)

    def _on_hex_edited(self, text: str) -> None:
        text = text.strip()
        if not text.startswith("#"):
            text = "#" + text
        if len(text) == 7:
            try:
                QColor(text)          # validates hex
                self._color = text.lower()
                self._refresh_swatch()
                self.colorChanged.emit(self._color)
            except Exception:
                pass

    def _refresh_swatch(self) -> None:
        c = self._color
        r, g, b = int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        border = "#555555" if lum > 127 else "#aaaaaa"
        self._swatch.setStyleSheet(
            f"QPushButton {{ background-color: {c}; border: 1px solid {border}; "
            f"border-radius: 12px; "
            f"min-width: 24px; max-width: 24px; min-height: 24px; max-height: 24px; padding: 0; }}"
            f"QPushButton:hover {{ border: 2px solid {border}; }}"
        )


# ── Theme dialog ───────────────────────────────────────────────────────────

class ThemeDialog(QDialog):
    """
    Lets the user pick a built-in theme or create / edit / delete custom ones.

    The parent window's stylesheet is updated live as themes are selected.
    Cancelling the dialog reverts the stylesheet to what it was on open.
    """

    theme_applied = Signal(str)   # emits name when user accepts

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self._previous_name = ThemeManager.get_active_name()
        self._current_theme: ThemeColors | None = None
        self._pending_save = False      # True when unsaved edits exist

        self.setWindowTitle("Theme Manager")
        self.setMinimumSize(520, 520)
        self._apply_own_stylesheet()
        self._build_ui()
        self._populate_list()

    # ── Layout ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(10)

        body = QHBoxLayout()
        body.setSpacing(12)

        # ── Left: theme list ──────────────────────────────────────────
        left = QWidget()
        left.setFixedWidth(176)
        left_vbox = QVBoxLayout(left)
        left_vbox.setContentsMargins(0, 0, 0, 0)
        left_vbox.setSpacing(6)

        list_label = QLabel("Themes")
        list_label.setProperty("role", "section")
        left_vbox.addWidget(list_label)

        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_row_changed)
        left_vbox.addWidget(self._list)

        list_btns = QHBoxLayout()
        list_btns.setSpacing(4)
        self._new_btn = QPushButton("New")
        self._new_btn.setToolTip("Duplicate the selected theme as a new custom preset")
        self._new_btn.clicked.connect(self._on_new)
        self._del_btn = QPushButton("Delete")
        self._del_btn.setObjectName("reset_button")
        self._del_btn.setToolTip("Delete this custom theme (built-in themes cannot be deleted)")
        self._del_btn.setEnabled(False)
        self._del_btn.clicked.connect(self._on_delete)
        list_btns.addWidget(self._new_btn)
        list_btns.addWidget(self._del_btn)
        left_vbox.addLayout(list_btns)

        body.addWidget(left)

        # Thin vertical separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setObjectName("v_sep")
        body.addWidget(sep)

        # ── Right: editor ─────────────────────────────────────────────
        right = QWidget()
        right_vbox = QVBoxLayout(right)
        right_vbox.setContentsMargins(4, 0, 4, 0)
        right_vbox.setSpacing(8)

        # Name row
        name_row = QHBoxLayout()
        name_lbl = QLabel("Name")
        name_lbl.setFixedWidth(110)
        name_lbl.setProperty("role", "muted")
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Custom theme name…")
        self._name_edit.textEdited.connect(self._mark_dirty)
        name_row.addWidget(name_lbl)
        name_row.addWidget(self._name_edit)
        right_vbox.addLayout(name_row)

        # Builtin badge
        self._builtin_label = QLabel("Built-in — read only")
        self._builtin_label.setProperty("role", "muted")
        self._builtin_label.setStyleSheet("font-style: italic;")
        self._builtin_label.setVisible(False)
        right_vbox.addWidget(self._builtin_label)

        # Scroll area for colour swatches
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        swatch_container = QWidget()
        swatch_vbox = QVBoxLayout(swatch_container)
        swatch_vbox.setContentsMargins(4, 6, 4, 6)
        swatch_vbox.setSpacing(10)

        self._swatches: dict[str, _ColorSwatch] = {}
        for key, label in _COLOR_FIELDS:
            sw = _ColorSwatch()
            sw.colorChanged.connect(lambda _hex, k=key: self._on_color_changed(k, _hex))
            row = QHBoxLayout()
            row.setSpacing(8)
            row_label = QLabel(label)
            row_label.setFixedWidth(110)
            row_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(row_label)
            row.addWidget(sw, 1)
            swatch_vbox.addLayout(row)
            self._swatches[key] = sw

        swatch_vbox.addStretch()
        scroll.setWidget(swatch_container)
        right_vbox.addWidget(scroll)

        # Save/revert row
        action_row = QHBoxLayout()
        self._save_btn = QPushButton("Save Changes")
        self._save_btn.setObjectName("save_button")
        self._save_btn.setEnabled(False)
        self._save_btn.setToolTip("Persist edits to this custom theme")
        self._save_btn.clicked.connect(self._on_save)
        self._revert_btn = QPushButton("Revert")
        self._revert_btn.setEnabled(False)
        self._revert_btn.setToolTip("Discard unsaved edits")
        self._revert_btn.clicked.connect(self._on_revert)
        action_row.addWidget(self._save_btn)
        action_row.addWidget(self._revert_btn)
        action_row.addStretch()
        right_vbox.addLayout(action_row)

        body.addWidget(right)
        outer.addLayout(body)

        # ── Bottom button box ─────────────────────────────────────────
        h_sep = QFrame()
        h_sep.setObjectName("h_sep")
        h_sep.setFrameShape(QFrame.Shape.HLine)
        outer.addWidget(h_sep)

        bbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_btn = bbox.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setObjectName("save_button")
        bbox.accepted.connect(self._on_accept)
        bbox.rejected.connect(self._on_cancel)
        outer.addWidget(bbox)

    # ── Population ────────────────────────────────────────────────────

    def _populate_list(self, select_name: str | None = None) -> None:
        self._list.blockSignals(True)
        self._list.clear()
        themes = ThemeManager.all_themes()
        active = ThemeManager.get_active_name()
        target_row = 0
        for i, (name, t) in enumerate(themes.items()):
            item = QListWidgetItem(name)
            if t.builtin:
                item.setForeground(QColor(ThemeManager.get_active().text_secondary))
            self._list.addItem(item)
            if name == (select_name or active):
                target_row = i
        self._list.blockSignals(False)
        self._list.setCurrentRow(target_row)

    # ── Slots ─────────────────────────────────────────────────────────

    def _on_row_changed(self, row: int) -> None:
        if row < 0:
            return
        name = self._list.item(row).text()
        themes = ThemeManager.all_themes()
        theme = themes.get(name)
        if theme is None:
            return
        self._current_theme = theme
        self._pending_save = False

        # Populate editor
        self._name_edit.setText(theme.name)
        self._name_edit.setReadOnly(theme.builtin)
        self._builtin_label.setVisible(theme.builtin)
        for key, _lbl in _COLOR_FIELDS:
            self._swatches[key].set_color(getattr(theme, key))
            self._swatches[key].set_editable(not theme.builtin)

        self._del_btn.setEnabled(not theme.builtin)
        self._save_btn.setEnabled(False)
        self._revert_btn.setEnabled(False)

        # Live preview
        self._preview(theme)

    def _on_color_changed(self, field: str, value: str) -> None:
        if self._current_theme is None:
            return
        self._current_theme = replace(self._current_theme, **{field: value})
        self._mark_dirty()
        self._preview(self._current_theme)

    def _mark_dirty(self, *_) -> None:
        self._pending_save = True
        self._save_btn.setEnabled(True)
        self._revert_btn.setEnabled(True)

    def _on_new(self) -> None:
        """Duplicate the selected theme as a new custom theme."""
        base = self._current_theme or list(BUILTIN_THEMES.values())[0]
        # Find a unique name
        existing = set(ThemeManager.all_themes().keys())
        candidate = f"{base.name} Copy"
        n = 2
        while candidate in existing:
            candidate = f"{base.name} Copy {n}"
            n += 1
        new_theme = replace(base, name=candidate, builtin=False)
        ThemeManager.save_custom(new_theme)
        self._populate_list(select_name=candidate)

    def _on_delete(self) -> None:
        if self._current_theme is None or self._current_theme.builtin:
            return
        name = self._current_theme.name
        reply = QMessageBox.question(
            self, "Delete Theme",
            f'Delete custom theme "{name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            ThemeManager.delete_custom(name)
            # Revert preview to first available theme
            active = ThemeManager.get_active_name()
            if active == name:
                ThemeManager.set_active_name("Dark")
                self._preview(BUILTIN_THEMES["Dark"])
            self._populate_list()

    def _on_save(self) -> None:
        if self._current_theme is None or self._current_theme.builtin:
            return
        new_name = self._name_edit.text().strip()
        if not new_name:
            QMessageBox.warning(self, "Name required", "Please enter a theme name.")
            return
        old_name = self._current_theme.name
        updated = replace(self._current_theme, name=new_name, builtin=False)
        # If renamed, delete old entry first
        if old_name != new_name:
            ThemeManager.delete_custom(old_name)
            if ThemeManager.get_active_name() == old_name:
                ThemeManager.set_active_name(new_name)
        ThemeManager.save_custom(updated)
        self._current_theme = updated
        self._pending_save = False
        self._save_btn.setEnabled(False)
        self._revert_btn.setEnabled(False)
        self._populate_list(select_name=new_name)

    def _on_revert(self) -> None:
        if self._current_theme is None:
            return
        # Re-load from disk
        themes = ThemeManager.all_themes()
        original = themes.get(self._current_theme.name)
        if original:
            self._current_theme = original
            for key, _lbl in _COLOR_FIELDS:
                self._swatches[key].set_color(getattr(original, key))
            self._preview(original)
        self._pending_save = False
        self._save_btn.setEnabled(False)
        self._revert_btn.setEnabled(False)

    def _on_accept(self) -> None:
        if self._pending_save:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved edits. Save them before applying?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Cancel:
                return
            if reply == QMessageBox.StandardButton.Save:
                self._on_save()

        if self._current_theme:
            ThemeManager.set_active_name(self._current_theme.name)
            self.theme_applied.emit(self._current_theme.name)
        self.accept()

    def _on_cancel(self) -> None:
        # Revert live preview to what was active before we opened
        prev = ThemeManager.all_themes().get(self._previous_name,
                                              BUILTIN_THEMES["Dark"])
        self._preview(prev)
        self.reject()

    # ── Helpers ───────────────────────────────────────────────────────

    def _preview(self, theme: ThemeColors) -> None:
        """Apply theme stylesheet to the main window immediately."""
        ss = generate_stylesheet(theme)
        self.main_window.setStyleSheet(ss)
        # Re-apply to ourselves too so the dialog stays consistent
        self.setStyleSheet(ss)

    def _apply_own_stylesheet(self) -> None:
        active = ThemeManager.get_active()
        self.setStyleSheet(generate_stylesheet(active))
