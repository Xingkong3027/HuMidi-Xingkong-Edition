from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QEvent, pyqtSignal as Signal


class NavButton(QFrame):
    """Sidebar nav item: large icon glyph stacked above a small label."""

    clicked = Signal()

    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(parent)
        self.setObjectName("nav_btn")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(70)
        self.setProperty("active",  "false")
        self.setProperty("hovered", "false")

        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 14, 0, 14)
        vbox.setSpacing(2)
        vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._icon_lbl = QLabel(icon)
        self._icon_lbl.setObjectName("nav_icon")
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_lbl.setProperty("highlighted", "false")
        self._icon_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._text_lbl = QLabel(label)
        self._text_lbl.setObjectName("nav_label")
        self._text_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._text_lbl.setProperty("highlighted", "false")
        self._text_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        vbox.addWidget(self._icon_lbl)
        vbox.addWidget(self._text_lbl)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self._update("hovered", True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._update("hovered", False)
        super().leaveEvent(event)

    def set_active(self, active: bool) -> None:
        self._update("active", active)

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.EnabledChange and not self.isEnabled():
            self.setProperty("active",  "false")
            self.setProperty("hovered", "false")
            for lbl in (self._icon_lbl, self._text_lbl):
                lbl.setProperty("highlighted", "false")
                lbl.style().unpolish(lbl)
                lbl.style().polish(lbl)
            self.style().unpolish(self)
            self.style().polish(self)
            self.update()
        super().changeEvent(event)

    def _update(self, key: str, value: bool) -> None:
        self.setProperty(key, "true" if value else "false")
        active  = self.property("active")  == "true"
        hovered = self.property("hovered") == "true"
        hi = "true" if (active or hovered) else "false"
        for lbl in (self._icon_lbl, self._text_lbl):
            lbl.setProperty("highlighted", hi)
            lbl.style().unpolish(lbl)
            lbl.style().polish(lbl)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


def make_card(title: str) -> tuple:
    """Return a styled section card (QFrame) and its content QVBoxLayout."""
    card = QFrame()
    card.setObjectName("section_card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(14, 12, 14, 14)
    layout.setSpacing(8)
    if title:
        lbl = QLabel(title)
        lbl.setProperty("role", "section")
        layout.addWidget(lbl)
    return card, layout
