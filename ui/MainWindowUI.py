from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider, QLabel,
    QStackedWidget, QFrame, QSizePolicy, QComboBox, QListWidget,
    QListWidgetItem, QAbstractItemView,
)
from PyQt6.QtCore import Qt, QObject, QSize
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap

from ui.widgets import NavButton
from ui.PlaybackTab import PlaybackTab
from ui.PlaylistTab import PlaylistTab
from ui.SettingsTab import SettingsTab
from ui.TranslatorTab import TranslatorTab
from ui.VisualizerTab import VisualizerTab
from ui.DebugTab import DebugTab
from ui.LicenseTab import LicenseTab
from ui.theme import ThemeManager, generate_stylesheet


def _make_mdl2_icon(glyph: str, color: QColor, pixel_size: int = 14) -> QIcon:
    """Render a Segoe MDL2 Assets glyph into a QIcon at the given pixel size."""
    pix = QPixmap(pixel_size, pixel_size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    f = QFont("Segoe MDL2 Assets")
    f.setPixelSize(pixel_size)
    p.setFont(f)
    p.setPen(color)
    p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, glyph)
    p.end()
    return QIcon(pix)


class ElidingLabel(QLabel):
    """QLabel that truncates text with '...' when it doesn't fit."""
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._full_text = text
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        if text:
            self._update_elided()

    def setText(self, text):
        self._full_text = text
        self._update_elided()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elided()

    def _update_elided(self):
        width = self.contentsRect().width()
        if width <= 0:
            return
        elided = self.fontMetrics().elidedText(
            self._full_text, Qt.TextElideMode.ElideRight, width
        )
        super().setText(elided)


class MainWindowUI(QObject):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setup_ui()

    def setup_ui(self):
        main_widget = QWidget()
        main_widget.setObjectName("main_widget")
        self.main_window.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._is_collapsed = False

        # ── Collapsed mini player ──────────────────────────────────────
        self._collapsed_strip = QFrame()
        self._collapsed_strip.setObjectName("collapsed_strip")
        self._collapsed_strip.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._collapsed_strip.setVisible(False)
        cs_layout = QVBoxLayout(self._collapsed_strip)
        cs_layout.setContentsMargins(12, 8, 12, 8)
        cs_layout.setSpacing(6)

        self._collapsed_file_label = ElidingLabel("No file selected.")
        self._collapsed_file_label.setObjectName("file_path_label")
        self._collapsed_file_label.setProperty("i18n_dynamic", True)
        cs_layout.addWidget(self._collapsed_file_label)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(6)
        self._collapsed_mode_label = QLabel("Playback Mode")
        self._collapsed_mode_combo = QComboBox()
        for value, text in PlaylistTab.MODES:
            self._collapsed_mode_combo.addItem(text, value)
        mode_row.addWidget(self._collapsed_mode_label)
        mode_row.addWidget(self._collapsed_mode_combo, 1)
        cs_layout.addLayout(mode_row)

        navigation_row = QHBoxLayout()
        navigation_row.setSpacing(6)
        self._collapsed_previous_btn = QPushButton("Previous")
        self._collapsed_previous_btn.setToolTip("Play the previous playlist item")
        self._collapsed_next_btn = QPushButton("Next")
        self._collapsed_next_btn.setToolTip("Play the next playlist item")
        navigation_row.addWidget(self._collapsed_previous_btn, 1)
        navigation_row.addWidget(self._collapsed_next_btn, 1)
        cs_layout.addLayout(navigation_row)

        self._collapsed_playlist_label = QLabel("Playlist")
        self._collapsed_playlist_label.setProperty("role", "section")
        cs_layout.addWidget(self._collapsed_playlist_label)
        self._collapsed_playlist_list = QListWidget()
        self._collapsed_playlist_list.setObjectName("collapsed_playlist_list")
        self._collapsed_playlist_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._collapsed_playlist_list.setMinimumHeight(135)
        cs_layout.addWidget(self._collapsed_playlist_list, 1)

        self._cs_scrubber_row = QWidget()
        self._cs_scrubber_layout = QVBoxLayout(self._cs_scrubber_row)
        self._cs_scrubber_layout.setContentsMargins(0, 0, 0, 0)
        self._cs_scrubber_layout.setSpacing(2)
        cs_layout.addWidget(self._cs_scrubber_row)

        self._cs_playback_row = QWidget()
        self._cs_playback_layout = QHBoxLayout(self._cs_playback_row)
        self._cs_playback_layout.setContentsMargins(0, 0, 0, 0)
        self._cs_playback_layout.setSpacing(5)
        cs_layout.addWidget(self._cs_playback_row)

        self._cs_expand_row = QWidget()
        self._cs_expand_layout = QHBoxLayout(self._cs_expand_row)
        self._cs_expand_layout.setContentsMargins(0, 0, 0, 0)
        self._cs_expand_layout.setSpacing(0)
        cs_layout.addWidget(self._cs_expand_row)

        self._cs_layout = cs_layout
        main_layout.addWidget(self._collapsed_strip, 1)

        # ── Body: sidebar + page stack ─────────────────────────────────
        self._body = QWidget()
        body_layout = QHBoxLayout(self._body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(120)
        sidebar.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
        )
        sidebar_vbox = QVBoxLayout(sidebar)
        sidebar_vbox.setContentsMargins(0, 0, 0, 0)
        sidebar_vbox.setSpacing(0)


        self.tabs = QStackedWidget()
        self.tabs.currentChanged.connect(self._on_page_changed)

        _NAV_ITEMS = [
            ("\uE768", "Playback"),
            ("\uE8D5", "Playlist"),
            ("\uE8D6", "Visualizer"),
            ("\uE8B1", "Translator"),
            ("\uE713", "Settings"),
            ("\uEBE8", "Debug"),
            ("\uE946", "License"),
        ]
        self._nav_btns: list[NavButton] = []
        for i, (icon, label) in enumerate(_NAV_ITEMS):
            btn = NavButton(icon, label)
            btn.clicked.connect(lambda idx=i: self._switch_page(idx))
            sidebar_vbox.addWidget(btn)
            self._nav_btns.append(btn)

        sidebar_vbox.addStretch()
        body_layout.addWidget(sidebar)
        body_layout.addWidget(self.tabs, 1)
        main_layout.addWidget(self._body, 1)

        # ── Pages ──────────────────────────────────────────────────────
        self.playback_tab   = PlaybackTab()
        self.playlist_tab   = PlaylistTab()
        self.visualizer_tab = VisualizerTab()
        self.translator_tab = TranslatorTab()
        self.settings_tab   = SettingsTab()
        self.debug_tab      = DebugTab()
        self.license_tab    = LicenseTab()

        self.tabs.addWidget(self.playback_tab)    # 0
        self.tabs.addWidget(self.playlist_tab)    # 1
        self.tabs.addWidget(self.visualizer_tab)  # 2
        self.tabs.addWidget(self.translator_tab)  # 3
        self.tabs.addWidget(self.settings_tab)    # 4
        self.tabs.addWidget(self.debug_tab)       # 5
        self.tabs.addWidget(self.license_tab)     # 6

        # ── Convenience aliases for frequently accessed sub-widgets ────
        self.log_output      = self.debug_tab.log_output
        self.save_button     = self.playback_tab.save_button
        self.reset_button    = self.playback_tab.reset_button
        self.timeline_widget = self.visualizer_tab.timeline_widget
        self.piano_widget    = self.visualizer_tab.piano_widget
        self.scroll_area     = self.visualizer_tab.scroll_area

        # ── Transport bar ─────────────────────────────────────────────
        transport_bar = QFrame()
        transport_bar.setObjectName("transport_bar")
        transport_layout = QVBoxLayout(transport_bar)
        transport_layout.setContentsMargins(16, 10, 16, 10)
        transport_layout.setSpacing(6)

        self.scrubber_slider = QSlider(Qt.Orientation.Horizontal)
        self.scrubber_slider.setObjectName("scrubber_slider")
        self.scrubber_slider.setRange(0, 10000)
        self.scrubber_slider.sliderPressed.connect(self._on_scrubber_pressed)
        self.scrubber_slider.sliderMoved.connect(self._on_scrubber_moved)
        self.scrubber_slider.sliderReleased.connect(self._on_scrubber_released)
        self._scrubber_dragging = False
        transport_layout.addWidget(self.scrubber_slider)

        self._btn_row_widget = QWidget()
        btn_row = QHBoxLayout(self._btn_row_widget)
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(5)

        self.play_button = QPushButton("▶  Play")
        self.play_button.setObjectName("play_button")
        self.play_button.setProperty("i18n_dynamic", True)
        self.play_button.setToolTip("Start, pause, or resume playback")

        self.stop_button = QPushButton("■  Stop")
        self.stop_button.setObjectName("stop_button")
        self.stop_button.setProperty("i18n_dynamic", True)
        self.stop_button.setToolTip("Stop playback and reset to the beginning")

        self._playback_info_widget = QWidget()
        self._playback_info_widget.setObjectName("playback_info_widget")
        self._playback_info_widget.setMinimumWidth(320)
        playback_info_layout = QVBoxLayout(self._playback_info_widget)
        playback_info_layout.setContentsMargins(4, 0, 4, 0)
        playback_info_layout.setSpacing(1)

        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setObjectName("time_label")
        self.time_label.setProperty("i18n_dynamic", True)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._time_display_current = 0.0
        self._time_display_total = 0.0
        self._countdown_remaining = 0

        self.now_playing_label = ElidingLabel("Now Playing: —")
        self.now_playing_label.setObjectName("now_playing_label")
        self.now_playing_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.playback_source_label = ElidingLabel("Source: —")
        self.playback_source_label.setObjectName("playback_source_label")
        self.playback_source_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        playback_info_layout.addWidget(self.time_label)
        playback_info_layout.addWidget(self.now_playing_label)
        playback_info_layout.addWidget(self.playback_source_label)

        btn_row.addWidget(self.play_button)
        btn_row.addWidget(self.stop_button)
        btn_row.addStretch()
        btn_row.addWidget(self._playback_info_widget, 1)
        btn_row.addStretch()

        self.previous_button = QPushButton("Previous")
        self.previous_button.setObjectName("previous_button")
        self.previous_button.setToolTip("Play the previous playlist item")
        self.next_button = QPushButton("Next")
        self.next_button.setObjectName("next_button")
        self.next_button.setToolTip("Play the next playlist item")
        btn_row.addWidget(self.previous_button)
        btn_row.addWidget(self.next_button)

        self.collapse_btn = QPushButton("▲  Collapse")
        self.collapse_btn.setObjectName("collapse_btn")
        self.collapse_btn.setProperty("i18n_dynamic", True)
        self.collapse_btn.setToolTip("Collapse to mini mode")
        self.collapse_btn.clicked.connect(self._toggle_collapsed)
        btn_row.addWidget(self.collapse_btn)

        transport_layout.addWidget(self._btn_row_widget)
        main_layout.addWidget(transport_bar)
        self._transport_bar = transport_bar
        self._transport_layout = transport_layout

        self.play_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.previous_button.setEnabled(False)
        self.next_button.setEnabled(False)
        self._collapsed_previous_btn.setEnabled(False)
        self._collapsed_next_btn.setEnabled(False)
        self.scrubber_slider.setEnabled(False)

        # ── Cross-cutting connections ──────────────────────────────────
        self.settings_tab.timeline_vis_check.toggled.connect(self._on_timeline_toggle)
        self.settings_tab.piano_vis_check.toggled.connect(self._on_piano_toggle)
        self.settings_tab.theme_combo.currentTextChanged.connect(self.apply_theme)
        self.settings_tab.theme_customize_btn.clicked.connect(self._open_theme_dialog)

        self._collapsed_mode_combo.currentIndexChanged.connect(
            self._on_collapsed_mode_changed
        )
        self.playlist_tab.mode_combo.currentIndexChanged.connect(
            self._sync_collapsed_mode
        )
        self._collapsed_playlist_list.currentItemChanged.connect(
            self._on_collapsed_playlist_selection_changed
        )
        self._collapsed_playlist_list.itemDoubleClicked.connect(
            self._on_collapsed_playlist_activated
        )

        self._switch_page(0)
        self.apply_theme(ThemeManager.get_active_name())

    # ── Navigation ─────────────────────────────────────────────────────

    def _switch_page(self, index: int) -> None:
        self.tabs.setCurrentIndex(index)

    def _on_page_changed(self, index: int) -> None:
        for i, btn in enumerate(self._nav_btns):
            btn.set_active(i == index)

    # ── Theme ──────────────────────────────────────────────────────────

    def apply_theme(self, name: str) -> None:
        themes = ThemeManager.all_themes()
        theme = themes.get(name)
        if theme is None:
            return
        ThemeManager.set_active_name(name)
        self.main_window.setStyleSheet(generate_stylesheet(theme))
        self.timeline_widget.left_hand_color.setNamedColor(theme.accent)
        self.timeline_widget.left_hand_color.setAlpha(210)
        self.timeline_widget.right_hand_color.setNamedColor(theme.accent_play)
        self.timeline_widget.right_hand_color.setAlpha(210)
        self.timeline_widget.bg_color.setNamedColor(theme.bg_primary)
        pedal_q = QColor(theme.pedal_color)
        pedal_q.setAlpha(180)
        self.timeline_widget.pedal_color = pedal_q
        self.timeline_widget.cached_background = None
        self.timeline_widget.update()
        piano_pedal_q = QColor(theme.pedal_color)
        self.piano_widget.pedal_color = piano_pedal_q
        self.piano_widget.update()

    def _open_theme_dialog(self) -> None:
        from ui.ThemeDialog import ThemeDialog
        dlg = ThemeDialog(self.main_window, self.main_window)
        dlg.theme_applied.connect(self._on_theme_dialog_accepted)
        dlg.exec()

    def _on_theme_dialog_accepted(self, name: str) -> None:
        self.settings_tab.refresh_theme_combo()
        self.apply_theme(name)

    # ── Visualizer helpers ─────────────────────────────────────────────

    def _on_timeline_toggle(self, checked: bool) -> None:
        self.scroll_area.setVisible(checked)
        self._update_visualizer_availability()

    def _on_piano_toggle(self, checked: bool) -> None:
        self.piano_widget.setVisible(checked)
        self.timeline_widget.set_show_pedal(checked)
        self._update_visualizer_availability()

    def _update_visualizer_availability(self) -> None:
        both_off = (not self.settings_tab.timeline_vis_check.isChecked() and
                    not self.settings_tab.piano_vis_check.isChecked())
        self._nav_btns[2].setEnabled(not both_off)
        if both_off and self.tabs.currentIndex() == 2:
            self._switch_page(0)

    def update_progress(self, current_time, total_duration):
        if self.scroll_area.isVisible() and not self.timeline_widget.is_dragging:
            self.timeline_widget.set_position(current_time)
            if total_duration > 0:
                ratio = current_time / total_duration
                cursor_x = ratio * self.timeline_widget.width()
                target_scroll = cursor_x - (self.scroll_area.width() / 2)
                self.scroll_area.horizontalScrollBar().setValue(int(target_scroll))

        if not self._scrubber_dragging and not self.timeline_widget.is_dragging:
            self.scrubber_slider.blockSignals(True)
            if total_duration > 0:
                self.scrubber_slider.setValue(int(current_time / total_duration * 10000))
            self.scrubber_slider.blockSignals(False)

        self.update_time_label(current_time, total_duration)

    def reset_timeline_position(self) -> None:
        self.timeline_widget.current_time = 0.0
        self.scrubber_slider.blockSignals(True)
        self.scrubber_slider.setValue(0)
        self.scrubber_slider.blockSignals(False)

    def update_time_label(self, current, total) -> None:
        def fmt(s):
            m, sec = int(s // 60), int(s % 60)
            return f"{m:02d}:{sec:02d}"

        self._time_display_current = max(0.0, float(current or 0.0))
        self._time_display_total = max(0.0, float(total or 0.0))
        text = f"{fmt(self._time_display_current)} / {fmt(self._time_display_total)}"
        if self._countdown_remaining > 0:
            suffix = self.main_window._t("Countdown {seconds} seconds").format(
                seconds=self._countdown_remaining
            )
            text += f" ({suffix})"
        self.time_label.setText(text)

    def set_countdown_remaining(self, seconds: int) -> None:
        """Show or clear the pre-playback countdown beside the time display."""
        self._countdown_remaining = max(0, int(seconds))
        self.update_time_label(self._time_display_current, self._time_display_total)

    # ── Scrubber ───────────────────────────────────────────────────────

    def _on_scrubber_pressed(self):
        self._scrubber_dragging = True

    def _on_scrubber_moved(self, value):
        if self.timeline_widget.total_duration > 0:
            t = (value / 10000.0) * self.timeline_widget.total_duration
            self.timeline_widget.current_time = t
            self.timeline_widget.scrub_position_changed.emit(t)
            self.update_time_label(t, self.timeline_widget.total_duration)

    def _on_scrubber_released(self):
        self._scrubber_dragging = False
        self.timeline_widget.seek_requested.emit(self.timeline_widget.current_time)

    # ── Collapse ───────────────────────────────────────────────────────

    def _toggle_collapsed(self) -> None:
        self._is_collapsed = not self._is_collapsed
        if self._is_collapsed:
            self._expanded_size = self.main_window.size()
            self._expanded_minimum_size = self.main_window.minimumSize()
            self._body.setVisible(False)
            self._collapsed_strip.setVisible(True)
            self.collapse_btn.setText(self.main_window._t("▼  Expand"))
            self.collapse_btn.setToolTip(self.main_window._t("Restore full window"))
            self.collapse_btn.setMinimumWidth(0)
            self.collapse_btn.setMaximumWidth(16777215)
            self.collapse_btn.setProperty("strip_mode", True)
            self.collapse_btn.style().unpolish(self.collapse_btn)
            self.collapse_btn.style().polish(self.collapse_btn)
            # Row 4: scrubber followed by time, current song, and source.
            self._cs_scrubber_layout.addWidget(self.scrubber_slider)
            self._playback_info_widget.setMinimumWidth(0)
            self._cs_scrubber_layout.addWidget(self._playback_info_widget)
            # Row 5: play + stop equal width
            self._cs_playback_layout.addWidget(self.play_button, 1)
            self._cs_playback_layout.addWidget(self.stop_button, 1)
            # Row 6: expand button full width
            self._cs_expand_layout.addWidget(self.collapse_btn)
            for btn, glyph in [
                (self.play_button, "\uE768"),
                (self.stop_button, "\uE71A"),
            ]:
                btn.setMinimumWidth(0)
                btn.setMaximumWidth(16777215)
                btn.setText(glyph)
                btn.setProperty("icon_mode", True)
                btn.style().unpolish(btn)
                btn.style().polish(btn)
            self._transport_bar.setVisible(False)
            self.main_window.setMinimumSize(340, 430)
            self.main_window.resize(380, 500)
        else:
            self._body.setVisible(True)
            self._collapsed_strip.setVisible(False)
            self.collapse_btn.setText(self.main_window._t("▲  Collapse"))
            self.collapse_btn.setToolTip(self.main_window._t("Collapse to mini mode"))
            self.collapse_btn.setProperty("strip_mode", False)
            self.collapse_btn.style().unpolish(self.collapse_btn)
            self.collapse_btn.style().polish(self.collapse_btn)
            # Restore all reparented widgets back into the transport bar
            self._transport_layout.insertWidget(0, self.scrubber_slider)
            btn_row_layout = self._btn_row_widget.layout()
            btn_row_layout.insertWidget(0, self.play_button)
            btn_row_layout.insertWidget(1, self.stop_button)
            self._playback_info_widget.setMinimumWidth(320)
            btn_row_layout.insertWidget(3, self._playback_info_widget, 1)
            btn_row_layout.addWidget(self.collapse_btn)
            for btn in (self.play_button, self.stop_button):
                btn.setMinimumWidth(0)
                btn.setMaximumWidth(16777215)
                btn.setProperty("icon_mode", False)
                btn.style().unpolish(btn)
                btn.style().polish(btn)
            self.stop_button.setText(self.main_window._t("■  Stop"))
            self._transport_bar.setVisible(True)
            # play_button text restored by _sync_play_button (connected to collapse_btn.clicked)
            self.main_window.setMinimumSize(self._expanded_minimum_size)
            self.main_window.resize(self._expanded_size)

    # ── Collapsed player synchronization ──────────────────────────────

    def _on_collapsed_mode_changed(self, _index: int) -> None:
        mode = str(self._collapsed_mode_combo.currentData() or "single")
        self.playlist_tab.set_mode(mode)

    def _sync_collapsed_mode(self, *_args) -> None:
        mode = self.playlist_tab.current_mode()
        self._collapsed_mode_combo.blockSignals(True)
        self._collapsed_mode_combo.setCurrentIndex(
            max(0, self._collapsed_mode_combo.findData(mode))
        )
        self._collapsed_mode_combo.blockSignals(False)

    def _on_collapsed_playlist_selection_changed(self, current, _previous) -> None:
        if current is None:
            return
        item_id = current.data(Qt.ItemDataRole.UserRole)
        if item_id:
            self.playlist_tab.select_id(str(item_id))

    def _on_collapsed_playlist_activated(self, item) -> None:
        item_id = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        if item_id:
            self.playlist_tab.play_requested.emit(str(item_id))

    def collapsed_selected_playlist_id(self) -> str | None:
        item = self._collapsed_playlist_list.currentItem()
        if item is None:
            return None
        item_id = item.data(Qt.ItemDataRole.UserRole)
        return str(item_id) if item_id else None

    def refresh_collapsed_playlist(
        self, items: list[dict], selected_id: str | None = None
    ) -> None:
        current_id = selected_id
        if not current_id:
            current = self._collapsed_playlist_list.currentItem()
            if current is not None:
                current_id = str(current.data(Qt.ItemDataRole.UserRole) or "")
        self._collapsed_playlist_list.blockSignals(True)
        self._collapsed_playlist_list.clear()
        selected_item = None
        for data in items:
            item = QListWidgetItem(str(data.get("name") or ""))
            item.setData(Qt.ItemDataRole.UserRole, str(data.get("id") or ""))
            source_type = str(data.get("source_type") or "midi")
            item.setToolTip(
                self.main_window._t("Text Sheet")
                if source_type == "sheet"
                else str(data.get("source_label") or data.get("source_midi_filename") or "")
            )
            self._collapsed_playlist_list.addItem(item)
            if current_id and str(data.get("id")) == current_id:
                selected_item = item
        if selected_item is not None:
            self._collapsed_playlist_list.setCurrentItem(selected_item)
            self._collapsed_playlist_list.scrollToItem(selected_item)
        elif self._collapsed_playlist_list.count() > 0:
            self._collapsed_playlist_list.setCurrentRow(0)
        self._collapsed_playlist_list.blockSignals(False)
        has_items = self._collapsed_playlist_list.count() > 0
        self._collapsed_previous_btn.setEnabled(has_items)
        self._collapsed_next_btn.setEnabled(has_items)
        self.previous_button.setEnabled(has_items)
        self.next_button.setEnabled(has_items)

    def apply_language(self, language_manager) -> None:
        language_manager.translate_widget_tree(self.main_window)
        self.playback_tab.retranslate_combo_items(language_manager.tr)
        self.playlist_tab.retranslate_mode_items(language_manager.tr)
        self.settings_tab.retranslate_language_items(language_manager)
        self.settings_tab.update_global_humanization_summary(language_manager.tr)
        self.translator_tab.retranslate(language_manager)
        self.license_tab.retranslate_combo_items(language_manager.tr)
        current_mode = self.playlist_tab.current_mode()
        self._collapsed_mode_combo.blockSignals(True)
        self._collapsed_mode_combo.clear()
        for value, text in PlaylistTab.MODES:
            self._collapsed_mode_combo.addItem(language_manager.tr(text), value)
        self._collapsed_mode_combo.setCurrentIndex(
            max(0, self._collapsed_mode_combo.findData(current_mode))
        )
        self._collapsed_mode_combo.blockSignals(False)
        self._collapsed_mode_label.setText(language_manager.tr("Playback Mode"))
        self._collapsed_playlist_label.setText(language_manager.tr("Playlist"))
        self._collapsed_previous_btn.setText(language_manager.tr("Previous"))
        self._collapsed_next_btn.setText(language_manager.tr("Next"))
        self.previous_button.setText(language_manager.tr("Previous"))
        self.next_button.setText(language_manager.tr("Next"))

        # Transport labels are stateful and may have changed after the original
        # English strings were cached by the generic translator.
        if not self._is_collapsed:
            self.stop_button.setText(language_manager.tr("■  Stop"))
            self.save_button.setText(language_manager.tr("Save Playback"))
            self.reset_button.setText(language_manager.tr("Reset"))
            self.collapse_btn.setText(language_manager.tr("▲  Collapse"))
        self.update_time_label(self._time_display_current, self._time_display_total)

    # ── Public API ─────────────────────────────────────────────────────

    def update_file_label(self, text: str, tooltip: str = "") -> None:
        self.playback_tab.update_file_label(text, tooltip)
        self._collapsed_file_label.setText(text)

    def update_playback_info(self, title_text: str, source_text: str) -> None:
        self.now_playing_label.setText(title_text)
        self.now_playing_label.setToolTip(title_text)
        self.playback_source_label.setText(source_text)
        self.playback_source_label.setToolTip(source_text)

    def set_controls_enabled(self, enabled: bool, ignore_if_loaded: bool = False) -> None:
        self.playback_tab.set_groups_enabled(
            enabled,
            skip_playback_humanization=(ignore_if_loaded and enabled)
        )

    def _set_save_enabled(self, val: bool) -> None:
        self.save_button.setEnabled(val)

    def reset_controls_to_default(self) -> None:
        self.playback_tab.reset_to_default()
        self.settings_tab.use_ai_pedal_check.setChecked(False)

    def load_config_to_ui(self, config: dict, save_dir: str) -> None:
        self.settings_tab.load_config(config, save_dir)
        self.playback_tab.set_global_humanization_config(
            self.settings_tab.global_humanization_config()
        )
        self.playback_tab.load_config(config)

    def gather_playback_config(self) -> dict:
        self.playback_tab.set_global_humanization_config(
            self.settings_tab.global_humanization_config()
        )
        cfg = self.playback_tab.gather_playback_config()
        cfg['use_ai_pedal'] = self.settings_tab.use_ai_pedal_check.isChecked()
        return cfg

    def gather_app_config(self) -> dict:
        return {
            **self.playback_tab.gather_app_config(),
            **self.settings_tab.gather_config(),
            "playlist_mode": self.playlist_tab.current_mode(),
        }

    def update_enabled_states(self) -> None:
        self.playback_tab.update_enabled_states()
