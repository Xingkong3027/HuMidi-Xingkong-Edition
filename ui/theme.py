"""
HuMidi theme engine.

A ThemeColors holds the 9 user-visible colour slots.  Everything else
(button backgrounds, disabled states, derived hover tints …) is computed
automatically by generate_stylesheet().

ThemeManager persists custom themes and the active-theme name to
  ~/.humidi/themes.json
"""

from __future__ import annotations
import json
from dataclasses import dataclass, asdict, field
from pathlib import Path


# ── Colour helpers ─────────────────────────────────────────────────────────

def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _mix(hex1: str, hex2: str, t: float) -> str:
    """Blend hex1 → hex2.  t=0 returns hex1, t=1 returns hex2."""
    r1, g1, b1 = _hex_to_rgb(hex1)
    r2, g2, b2 = _hex_to_rgb(hex2)
    r = max(0, min(255, int(r1 + (r2 - r1) * t)))
    g = max(0, min(255, int(g1 + (g2 - g1) * t)))
    b = max(0, min(255, int(b1 + (b2 - b1) * t)))
    return f"#{r:02x}{g:02x}{b:02x}"


# ── Data model ─────────────────────────────────────────────────────────────

@dataclass
class ThemeColors:
    name: str = "Dark"
    bg_primary:    str = "#1c1c2e"   # window / dialog background
    bg_secondary:  str = "#21213a"   # surfaces: groups, transport, headers
    bg_input:      str = "#24243e"   # inputs: spinbox, combobox, lineedit
    accent:        str = "#5b8dee"   # interactive: sliders, checkboxes, selection
    text_primary:  str = "#dcdcf0"   # main text
    text_secondary: str = "#7878a0"  # muted labels, group titles
    border:        str = "#32324a"   # all borders
    accent_play:   str = "#4ecb8d"   # play button
    accent_stop:   str = "#e05c5c"   # stop / danger
    pedal_color:   str = "#e8a020"   # sustain pedal indicator
    builtin: bool = field(default=False, repr=False)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("builtin", None)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "ThemeColors":
        d = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**d)


# ── Built-in presets ───────────────────────────────────────────────────────

BUILTIN_THEMES: dict[str, ThemeColors] = {
    "Dark": ThemeColors(
        name="Dark",
        bg_primary="#1c1c2e", bg_secondary="#21213a", bg_input="#24243e",
        accent="#5b8dee", text_primary="#dcdcf0", text_secondary="#7878a0",
        border="#32324a", accent_play="#4ecb8d", accent_stop="#e05c5c",
        pedal_color="#e8a020",
        builtin=True,
    ),
    "Light": ThemeColors(
        name="Light",
        bg_primary="#f0f0f8", bg_secondary="#ffffff", bg_input="#fafafa",
        accent="#4a7adb", text_primary="#1a1a2e", text_secondary="#6868a0",
        border="#d0d0e8", accent_play="#2a9a60", accent_stop="#cc3333",
        pedal_color="#d08010",
        builtin=True,
    ),
    "Midnight": ThemeColors(
        name="Midnight",
        bg_primary="#0d1117", bg_secondary="#161b22", bg_input="#1c2230",
        accent="#58a6ff", text_primary="#e6edf3", text_secondary="#8b949e",
        border="#30363d", accent_play="#3fb950", accent_stop="#f85149",
        pedal_color="#f0a030",
        builtin=True,
    ),
    "Mocha": ThemeColors(
        name="Mocha",
        bg_primary="#1c1614", bg_secondary="#26201e", bg_input="#302824",
        accent="#e6a050", text_primary="#ece0d0", text_secondary="#907060",
        border="#3c3028", accent_play="#7ab860", accent_stop="#e05060",
        pedal_color="#c8901a",
        builtin=True,
    ),
}


# ── Stylesheet template ────────────────────────────────────────────────────
# Uses %(key)s substitution — CSS braces do not need escaping.

_QSS = """\
QMainWindow {
    background-color: %(bg_primary)s;
}
QWidget {
    background-color: transparent;
    color: %(text_primary)s;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QWidget#main_widget, QStackedWidget {
    background-color: %(bg_primary)s;
}

/* Tabs */
QTabWidget::pane {
    border: none;
    background-color: %(bg_primary)s;
}
QTabBar::tab {
    background-color: %(tab_bg)s;
    color: %(text_secondary)s;
    padding: 7px 18px;
    border: 1px solid %(border)s;
    border-bottom: none;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected {
    background-color: %(bg_primary)s;
    color: %(text_primary)s;
    border-bottom: 2px solid %(accent)s;
}
QTabBar::tab:hover:!selected {
    background-color: %(tab_hover)s;
    color: %(text_primary)s;
}

/* Group boxes */
QGroupBox {
    background-color: %(bg_secondary)s;
    border: 1px solid %(border)s;
    border-radius: 8px;
    margin-top: 14px;
    padding: 10px 8px 8px 8px;
    font-weight: 600;
    font-size: 8pt;
    color: %(text_secondary)s;
    text-transform: uppercase;
    letter-spacing: 1px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    top: -1px;
    padding: 0 5px;
    background-color: %(bg_secondary)s;
}

/* Generic buttons */
QPushButton {
    background-color: %(btn_bg)s;
    border: 1px solid %(border)s;
    border-radius: 6px;
    padding: 5px 16px;
    color: %(text_primary)s;
    min-height: 28px;
}
QPushButton:hover {
    background-color: %(btn_hover)s;
    border-color: %(accent)s;
    color: %(text_primary)s;
}
QPushButton:pressed {
    background-color: %(btn_pressed)s;
}
QPushButton:disabled {
    color: %(dis_text)s;
    border-color: %(dis_border)s;
    background-color: %(dis_bg)s;
}

/* Play button — solid fill */
QPushButton#play_button {
    background-color: %(accent_play)s;
    border: none;
    border-radius: 6px;
    color: #ffffff;
    font-weight: bold;
    min-width: 90px;
}
QPushButton#play_button:hover {
    background-color: %(accent_play_hover)s;
    border: none;
}
QPushButton#play_button:pressed {
    background-color: %(accent_play)s;
}
QPushButton#play_button:disabled {
    background-color: %(play_dis_bg)s;
    border: none;
    color: %(play_dis_text)s;
}

/* Stop button — outlined, fills on hover */
QPushButton#stop_button {
    background-color: transparent;
    border: 1.5px solid %(accent_stop)s;
    border-radius: 6px;
    color: %(accent_stop)s;
    font-weight: bold;
    min-width: 80px;
}
QPushButton#stop_button:hover {
    background-color: %(accent_stop)s;
    border-color: %(accent_stop)s;
    color: #ffffff;
}
QPushButton#stop_button:disabled {
    background-color: transparent;
    border-color: %(stop_dis_border)s;
    color: %(stop_dis_text)s;
}

/* Save button */
QPushButton#save_button {
    background-color: %(save_bg)s;
    border-color: %(save_border)s;
    color: %(accent)s;
    min-width: 70px;
}
QPushButton#save_button:hover {
    background-color: %(save_hover)s;
    border-color: %(accent)s;
}
QPushButton#save_button:disabled {
    background-color: %(save_dis_bg)s;
    border-color: %(save_dis_border)s;
    color: %(save_dis_text)s;
}

/* Reset button */
QPushButton#reset_button {
    background-color: transparent;
    border-color: %(border)s;
    color: %(text_secondary)s;
}
QPushButton#reset_button:hover {
    border-color: %(accent_stop)s;
    color: %(accent_stop)s;
    background-color: %(stop_bg)s;
}

/* Sliders */
QSlider::groove:horizontal {
    height: 4px;
    background-color: %(bg_input)s;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background-color: %(accent)s;
    width: 14px;
    height: 14px;
    border-radius: 7px;
    margin: -5px 0;
    border: none;
}
QSlider::handle:horizontal:hover {
    background-color: %(accent_light)s;
}
QSlider::handle:horizontal:disabled {
    background-color: %(dis_border)s;
}
QSlider::sub-page:horizontal {
    background-color: %(accent)s;
    border-radius: 2px;
}
QSlider::sub-page:horizontal:disabled {
    background-color: %(dis_border)s;
}

/* Inputs */
QDoubleSpinBox, QSpinBox, QLineEdit {
    background-color: %(bg_input)s;
    border: 1px solid %(border)s;
    border-radius: 5px;
    padding: 3px 6px;
    color: %(text_primary)s;
    min-height: 24px;
    selection-background-color: %(accent)s;
}
QDoubleSpinBox:focus, QSpinBox:focus, QLineEdit:focus {
    border-color: %(accent)s;
}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
QSpinBox::up-button, QSpinBox::down-button {
    background-color: %(spinner_btn)s;
    border: none;
    width: 16px;
}
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover,
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: %(spinner_hover)s;
}

/* Checkboxes */
QCheckBox {
    spacing: 7px;
    color: %(text_primary)s;
}
QCheckBox::indicator {
    width: 15px;
    height: 15px;
    border: 1.5px solid %(border)s;
    border-radius: 4px;
    background-color: %(bg_input)s;
}
QCheckBox::indicator:hover {
    border-color: %(accent)s;
}
QCheckBox::indicator:checked {
    background-color: %(accent)s;
    border-color: %(accent)s;
}
QCheckBox::indicator:disabled {
    background-color: %(dis_bg)s;
    border-color: %(dis_border)s;
}
QCheckBox:disabled {
    color: %(dis_text)s;
}

/* Combo boxes */
QComboBox {
    background-color: %(bg_input)s;
    border: 1px solid %(border)s;
    border-radius: 5px;
    padding: 4px 8px;
    color: %(text_primary)s;
    min-height: 26px;
}
QComboBox:hover {
    border-color: %(accent)s;
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: %(bg_input)s;
    border: 1px solid %(border)s;
    color: %(text_primary)s;
    selection-background-color: %(accent)s;
    outline: none;
}

/* Text areas */
QTextEdit {
    background-color: %(text_area_bg)s;
    border: 1px solid %(border)s;
    border-radius: 6px;
    color: %(text_primary)s;
    selection-background-color: %(accent)s;
}

/* Scroll bars */
QScrollBar:horizontal {
    height: 8px;
    background: %(bg_primary)s;
    border: none;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: %(scroll_handle)s;
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background: %(accent)s; }
QScrollBar:vertical {
    width: 8px;
    background: %(bg_primary)s;
    border: none;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: %(scroll_handle)s;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: %(accent)s; }
QScrollBar::add-line, QScrollBar::sub-line,
QScrollBar::add-page, QScrollBar::sub-page {
    background: none; border: none; width: 0; height: 0;
}

/* Status bar */
QStatusBar {
    background-color: %(status_bg)s;
    border-top: 1px solid %(border)s;
    color: %(text_secondary)s;
    font-size: 8.5pt;
}

/* Tree */
QTreeWidget {
    background-color: %(bg_primary)s;
    border: 1px solid %(border)s;
    border-radius: 6px;
    color: %(text_primary)s;
    outline: none;
    alternate-background-color: %(tree_alt)s;
}
QTreeWidget::item { padding: 4px 2px; border-radius: 3px; }
QTreeWidget::item:selected { background-color: %(accent)s; color: #ffffff; }
QTreeWidget::item:hover:!selected { background-color: %(bg_input)s; }

/* Table */
QTableWidget {
    background-color: %(bg_primary)s;
    border: 1px solid %(border)s;
    border-radius: 6px;
    color: %(text_primary)s;
    gridline-color: %(grid_line)s;
    outline: none;
    alternate-background-color: %(tree_alt)s;
}
QTableWidget::item { padding: 4px 6px; }
QTableWidget::item:selected { background-color: %(accent)s; color: #ffffff; }
QTableWidget::item:hover:!selected { background-color: %(bg_input)s; }
QHeaderView::section {
    background-color: %(bg_secondary)s;
    color: %(text_secondary)s;
    border: none;
    border-right: 1px solid %(border)s;
    border-bottom: 1px solid %(border)s;
    padding: 6px 8px;
    font-weight: 600;
    font-size: 8pt;
    text-transform: uppercase;
}

/* Scroll areas */
QScrollArea {
    background-color: transparent;
    border: none;
}

/* List widgets */
QListWidget {
    background-color: %(bg_primary)s;
    border: 1px solid %(border)s;
    border-radius: 6px;
    color: %(text_primary)s;
    outline: none;
}
QListWidget::item { padding: 4px 8px; border-radius: 3px; }
QListWidget::item:selected { background-color: %(accent)s; color: #ffffff; }
QListWidget::item:hover:!selected { background-color: %(bg_input)s; }

/* Splitter */
QSplitter::handle:horizontal { background-color: %(border)s; width: 1px; }

/* Dialog button boxes */
QDialogButtonBox QPushButton {
    min-width: 70px;
}

/* Dialogs */
QDialog {
    background-color: %(bg_primary)s;
}
QMessageBox { background-color: %(bg_primary)s; }
QMessageBox QLabel { color: %(text_primary)s; }
QMessageBox QPushButton { min-width: 70px; }
QInputDialog { background-color: %(bg_primary)s; }
QInputDialog QLineEdit {
    background-color: %(bg_input)s;
    border: 1px solid %(border)s;
    border-radius: 5px;
    padding: 3px 6px;
    color: %(text_primary)s;
    min-height: 24px;
}
QInputDialog QLabel { color: %(text_primary)s; }

/* Tooltips */
QToolTip {
    background-color: %(bg_secondary)s;
    border: 1px solid %(accent)s;
    color: %(text_primary)s;
    padding: 4px 8px;
    border-radius: 4px;
}

/* Semantic label roles (set via setProperty("role", "...")) */
QLabel[role="muted"] {
    color: %(text_secondary)s;
    font-size: 9pt;
}
QLabel[role="section"] {
    color: %(text_secondary)s;
    font-size: 8pt;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
}
QLabel[role="value"] {
    color: %(text_primary)s;
    font-size: 9pt;
}
QLabel[role="success"] {
    color: %(accent_play)s;
    font-size: 9pt;
}
QLabel[role="title"] {
    color: %(text_primary)s;
    font-size: 14pt;
    font-weight: bold;
}

/* Named labels */
QLabel#time_label {
    font-size: 10pt;
    font-weight: 600;
    color: %(text_primary)s;
}
QLabel#file_path_label {
    color: %(text_secondary)s;
    font-style: italic;
    font-size: 9pt;
}

/* Transport bar */
QFrame#transport_bar {
    background-color: %(bg_secondary)s;
    border-top: 1px solid %(border)s;
}

/* Separators */
QFrame#h_sep {
    border: none;
    border-top: 1px solid %(border)s;
    background: transparent;
    max-height: 1px;
}
QFrame#v_sep {
    border: none;
    border-left: 1px solid %(border)s;
    background: transparent;
    max-width: 1px;
}

/* ── Sidebar navigation ─────────────────────────────────────── */
QFrame#sidebar {
    background-color: %(bg_secondary)s;
    border-right: 1px solid %(border)s;
    padding: 0px;
    margin: 0px;
}
QLabel#app_title {
    color: %(text_primary)s;
    font-size: 13pt;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 6px 0;
}
QFrame#nav_btn {
    background-color: transparent;
    border: none;
    border-left: 3px solid transparent;
    padding: 0px;
    margin: 0px;
}
QFrame#nav_btn[hovered="true"] {
    background-color: %(nav_hover_bg)s;
    border-left-color: %(border)s;
}
QFrame#nav_btn[active="true"] {
    border-left-color: %(accent)s;
    background-color: %(nav_active_bg)s;
}
QLabel#nav_icon {
    font-size: 16pt;
    font-family: "Segoe MDL2 Assets";
    color: %(text_secondary)s;
    background: transparent;
    border: none;
}
QLabel#nav_icon[highlighted="true"] {
    color: %(text_primary)s;
}
QLabel#nav_icon:disabled {
    color: %(dis_text)s;
}
QLabel#nav_label {
    font-size: 8pt;
    color: %(text_secondary)s;
    background: transparent;
    border: none;
}
QLabel#nav_label[highlighted="true"] {
    color: %(text_primary)s;
}
QLabel#nav_label:disabled {
    color: %(dis_text)s;
}
QFrame#nav_btn:disabled {
    background-color: transparent;
    border-left-color: transparent;
}

/* ── Section cards (replace QGroupBox) ──────────────────────── */
QFrame#section_card {
    background-color: %(bg_secondary)s;
    border: 1px solid %(border)s;
    border-radius: 10px;
}

/* ── Collapsed mini strip ────────────────────────────────────── */
QFrame#collapsed_strip {
    background-color: %(bg_secondary)s;
    border-bottom: 1px solid %(border)s;
}

/* ── Collapsed strip icon buttons ───────────────────────────── */
QPushButton#cs_save_btn {
    font-family: "Segoe MDL2 Assets";
    font-size: 12pt;
}

/* ── Transport buttons in icon mode (collapsed view) ─────────── */
QPushButton#play_button[icon_mode="true"],
QPushButton#stop_button[icon_mode="true"] {
    font-family: "Segoe MDL2 Assets";
    font-size: 14pt;
    min-width: 0;
}
QPushButton#save_button[icon_mode="true"],
QPushButton#reset_button[icon_mode="true"] {
    font-family: "Segoe MDL2 Assets";
    font-size: 14pt;
    min-width: 60px;
    max-width: 60px;
}

/* ── Collapse toggle button ──────────────────────────────────── */
QPushButton#collapse_btn {
    background: transparent;
    border: 1px solid %(border)s;
    border-radius: 4px;
    color: %(text_secondary)s;
}
QPushButton#collapse_btn:hover {
    background-color: %(nav_hover_bg)s;
    color: %(text_primary)s;
}
QPushButton#collapse_btn[strip_mode="true"] {
    font-size: 9pt;
    padding: 5px 16px;
    color: %(text_primary)s;
}
"""


def generate_stylesheet(c: ThemeColors) -> str:
    """Generate a complete QSS string from a ThemeColors instance."""
    # Tinted button backgrounds
    play_bg       = _mix(c.bg_primary, c.accent_play, 0.15)
    play_hover    = _mix(c.bg_primary, c.accent_play, 0.28)
    play_border   = _mix(c.accent_play, c.bg_secondary, 0.40)
    play_dis_bg   = _mix(play_bg, c.bg_primary, 0.55)
    play_dis_text = _mix(c.accent_play, c.bg_primary, 0.65)
    play_dis_bdr  = _mix(play_border, c.bg_primary, 0.65)

    stop_bg       = _mix(c.bg_primary, c.accent_stop, 0.15)
    stop_hover    = _mix(c.bg_primary, c.accent_stop, 0.28)
    stop_border   = _mix(c.accent_stop, c.bg_secondary, 0.40)
    stop_dis_bg   = _mix(stop_bg, c.bg_primary, 0.55)
    stop_dis_text = _mix(c.accent_stop, c.bg_primary, 0.65)
    stop_dis_bdr  = _mix(stop_border, c.bg_primary, 0.65)

    save_bg       = _mix(c.bg_primary, c.accent, 0.15)
    save_hover    = _mix(c.bg_primary, c.accent, 0.28)
    save_border   = _mix(c.accent, c.bg_secondary, 0.40)
    save_dis_bg   = _mix(save_bg, c.bg_primary, 0.55)
    save_dis_text = _mix(c.accent, c.bg_primary, 0.65)
    save_dis_bdr  = _mix(save_border, c.bg_primary, 0.65)

    # Generic button
    btn_bg      = _mix(c.bg_primary, c.bg_secondary, 0.55)
    btn_hover   = _mix(c.bg_secondary, c.accent, 0.16)
    btn_pressed = _mix(c.bg_primary, "#000000", 0.06)

    # Disabled generic
    dis_text   = _mix(c.text_primary, c.bg_primary, 0.65)
    dis_bg     = _mix(c.bg_secondary, c.bg_primary, 0.55)
    dis_border = _mix(c.border, c.bg_primary, 0.50)

    # Misc derived
    accent_light      = _mix(c.accent, "#ffffff", 0.25)
    accent_play_hover = _mix(c.accent_play, "#ffffff", 0.15)
    text_area_bg  = _mix(c.bg_input, c.bg_primary, 0.45)
    scroll_handle = _mix(c.border, c.accent, 0.45)
    tab_bg        = c.bg_secondary
    tab_hover     = _mix(c.bg_secondary, c.accent, 0.10)
    status_bg     = _mix(c.bg_primary, "#000000", 0.06)
    tree_alt      = _mix(c.bg_primary, c.bg_secondary, 0.20)
    grid_line     = _mix(c.bg_input, c.bg_primary, 0.50)
    spinner_btn   = _mix(c.bg_input, c.bg_secondary, 0.50)
    spinner_hover = _mix(spinner_btn, c.accent, 0.15)
    nav_active_bg = _mix(c.bg_secondary, c.accent, 0.10)
    nav_hover_bg  = _mix(c.bg_secondary, c.accent, 0.05)

    d = dict(
        bg_primary=c.bg_primary, bg_secondary=c.bg_secondary, bg_input=c.bg_input,
        accent=c.accent, accent_play=c.accent_play, accent_stop=c.accent_stop,
        text_primary=c.text_primary, text_secondary=c.text_secondary, border=c.border,
        accent_light=accent_light,
        play_bg=play_bg, play_hover=play_hover, play_border=play_border,
        play_dis_bg=play_dis_bg, play_dis_text=play_dis_text, play_dis_border=play_dis_bdr,
        stop_bg=stop_bg, stop_hover=stop_hover, stop_border=stop_border,
        stop_dis_bg=stop_dis_bg, stop_dis_text=stop_dis_text, stop_dis_border=stop_dis_bdr,
        save_bg=save_bg, save_hover=save_hover, save_border=save_border,
        save_dis_bg=save_dis_bg, save_dis_text=save_dis_text, save_dis_border=save_dis_bdr,
        btn_bg=btn_bg, btn_hover=btn_hover, btn_pressed=btn_pressed,
        dis_text=dis_text, dis_bg=dis_bg, dis_border=dis_border,
        text_area_bg=text_area_bg, scroll_handle=scroll_handle,
        tab_bg=tab_bg, tab_hover=tab_hover, status_bg=status_bg,
        tree_alt=tree_alt, grid_line=grid_line,
        spinner_btn=spinner_btn, spinner_hover=spinner_hover,
        accent_play_hover=accent_play_hover,
        nav_active_bg=nav_active_bg, nav_hover_bg=nav_hover_bg,
    )
    return _QSS % d


# ── Theme manager ──────────────────────────────────────────────────────────

class ThemeManager:
    """Loads/saves custom themes and the active theme name from disk."""

    _themes_dir = Path.home() / ".humidi"
    _themes_file = Path.home() / ".humidi" / "themes.json"

    # ── Disk I/O ──────────────────────────────────────────────────────

    @classmethod
    def _load_raw(cls) -> dict:
        try:
            return json.loads(cls._themes_file.read_text(encoding="utf-8"))
        except Exception:
            return {}

    @classmethod
    def _save_raw(cls, data: dict) -> None:
        cls._themes_dir.mkdir(parents=True, exist_ok=True)
        cls._themes_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # ── Public API ────────────────────────────────────────────────────

    @classmethod
    def all_themes(cls) -> dict[str, ThemeColors]:
        """Returns an ordered dict: built-ins first, then custom."""
        themes: dict[str, ThemeColors] = dict(BUILTIN_THEMES)
        raw = cls._load_raw()
        for d in raw.get("custom", []):
            try:
                t = ThemeColors.from_dict(d)
                t.builtin = False
                themes[t.name] = t
            except Exception:
                pass
        return themes

    @classmethod
    def get_active_name(cls) -> str:
        return cls._load_raw().get("active", "Midnight")

    @classmethod
    def set_active_name(cls, name: str) -> None:
        raw = cls._load_raw()
        raw["active"] = name
        cls._save_raw(raw)

    @classmethod
    def get_active(cls) -> ThemeColors:
        name = cls.get_active_name()
        return cls.all_themes().get(name, BUILTIN_THEMES["Dark"])

    @classmethod
    def save_custom(cls, theme: ThemeColors) -> None:
        """Insert or replace a custom theme by name."""
        raw = cls._load_raw()
        customs = raw.get("custom", [])
        customs = [d for d in customs if d.get("name") != theme.name]
        customs.append(theme.to_dict())
        raw["custom"] = customs
        cls._save_raw(raw)

    @classmethod
    def delete_custom(cls, name: str) -> None:
        raw = cls._load_raw()
        raw["custom"] = [d for d in raw.get("custom", []) if d.get("name") != name]
        if raw.get("active") == name:
            raw["active"] = "Dark"
        cls._save_raw(raw)
