from __future__ import annotations

import os
from ctypes import wintypes

from PyQt6.QtCore import (
    QByteArray, QMimeData, Qt, QPoint, QItemSelectionModel, QTimer, QEvent,
    QAbstractNativeEventFilter,
    pyqtSignal as Signal,
)
from PyQt6.QtGui import QCursor, QDrag, QPainter, QPen
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.playlist_order import build_reordered_ids
from core.windows_events import wheel_delta_from_wparam
from ui.widgets import make_card


class _WindowsDragWheelFilter(QAbstractNativeEventFilter):
    """Capture WM_MOUSEWHEEL while Qt is inside the native drag loop.

    On Windows, ``QDrag.exec()`` enters the platform drag-and-drop loop. Mouse
    wheel messages are consumed before Qt can turn them into ``QWheelEvent``
    objects, so neither ``wheelEvent`` nor a normal QObject event filter sees
    them. A native event filter is therefore installed only for the lifetime of
    a playlist drag and forwards the wheel delta to the table's scroll bar.
    """

    WM_MOUSEWHEEL = 0x020A

    def __init__(self, owner: "PlaylistTableWidget"):
        super().__init__()
        self._owner = owner

    def nativeEventFilter(self, _event_type, message):
        if os.name != "nt" or not self._owner._dragging_ids:
            return False, 0
        try:
            address = int(message)
            if address <= 0:
                return False, 0
            native_message = wintypes.MSG.from_address(address)
        except (TypeError, ValueError, OSError, OverflowError):
            return False, 0
        if int(native_message.message) != self.WM_MOUSEWHEEL:
            return False, 0

        wheel_delta = wheel_delta_from_wparam(native_message.wParam)
        if not wheel_delta:
            return False, 0

        self._owner._scroll_drag_by_delta(wheel_delta, refresh_pointer=True)
        # Consume the native message so the drag target cannot also react to it.
        return True, 0


class PlaylistTableWidget(QTableWidget):
    """Multi-row table with stable drag reordering and a white insert line.

    QTableWidget's built-in ``InternalMove`` performs its own source-row cleanup
    after a successful drop.  The playlist already persists and redraws the
    requested order itself, so letting Qt do that second move clears cells from
    the freshly redrawn table.  A private QDrag is used instead: it carries no
    table items and therefore cannot delete or blank source rows.
    """

    order_changed = Signal(object)
    MIME_TYPE = "application/x-humidi-playlist-reorder"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drop_row = -1
        self._drag_all_ids: list[str] = []
        self._dragging_ids: list[str] = []
        self._drag_pointer = QPoint()
        self._ctrl_selecting = False
        self._ctrl_anchor_row = -1
        self._ctrl_base_rows: set[int] = set()
        self._ctrl_start_was_selected = False
        self._ctrl_drag_moved = False
        self._ctrl_press_position = QPoint()
        self._auto_scroll_timer = QTimer(self)
        self._auto_scroll_timer.setInterval(45)
        self._auto_scroll_timer.timeout.connect(self._auto_scroll_step)
        self._native_wheel_filter = (
            _WindowsDragWheelFilter(self) if os.name == "nt" else None
        )
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(False)
        # Do not use InternalMove here.  We only use Qt for pointer tracking;
        # PlaylistManager owns the actual order mutation.
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDragDropOverwriteMode(False)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setAutoScroll(False)

    def selected_rows(self) -> list[int]:
        model = self.selectionModel()
        if model is None:
            return []
        return sorted({index.row() for index in model.selectedRows(0)})

    def _current_order_ids(self) -> list[str]:
        ids: list[str] = []
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            item_id = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
            if item_id is None or not str(item_id):
                return []
            ids.append(str(item_id))
        return ids if len(set(ids)) == len(ids) else []

    def startDrag(self, _supported_actions):
        # Holding Ctrl is reserved for paint-style multi-selection. Reordering
        # only starts from a new drag after Ctrl has been released.
        if QApplication.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier:
            return
        selected_rows = self.selected_rows()
        all_ids = self._current_order_ids()
        if not selected_rows or not all_ids:
            return

        moving_ids = [all_ids[row] for row in selected_rows if 0 <= row < len(all_ids)]
        if not moving_ids:
            return

        self._drag_all_ids = all_ids
        self._dragging_ids = moving_ids
        mime_data = QMimeData()
        mime_data.setData(self.MIME_TYPE, QByteArray(b"humidi-playlist-reorder"))
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
            if self._native_wheel_filter is not None:
                app.installNativeEventFilter(self._native_wheel_filter)
        try:
            # Because this QDrag is created directly (instead of calling the
            # QAbstractItemView implementation), MoveAction does not trigger
            # QTableWidget's destructive source-row cleanup.
            drag.exec(Qt.DropAction.MoveAction, Qt.DropAction.MoveAction)
        finally:
            if app is not None:
                if self._native_wheel_filter is not None:
                    app.removeNativeEventFilter(self._native_wheel_filter)
                app.removeEventFilter(self)
            self._auto_scroll_timer.stop()
            self._drag_all_ids = []
            self._dragging_ids = []
            self._drop_row = -1
            self.viewport().update()

    def _is_our_drag(self, event) -> bool:
        return (
            event.source() is self
            and event.mimeData() is not None
            and event.mimeData().hasFormat(self.MIME_TYPE)
            and bool(self._drag_all_ids)
            and bool(self._dragging_ids)
        )

    def _target_row(self, point: QPoint) -> int:
        row = self.rowAt(point.y())
        if row < 0:
            return self.rowCount()
        rect = self.visualRect(self.model().index(row, 0))
        return row + (1 if point.y() >= rect.center().y() else 0)

    def dragEnterEvent(self, event):
        if self._is_our_drag(event):
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
            return
        event.ignore()

    def dragMoveEvent(self, event):
        if self._is_our_drag(event):
            self._drag_pointer = event.position().toPoint()
            self._drop_row = self._target_row(self._drag_pointer)
            if not self._auto_scroll_timer.isActive():
                self._auto_scroll_timer.start()
            self.viewport().update()
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
            return
        event.ignore()

    def dragLeaveEvent(self, event):
        self._auto_scroll_timer.stop()
        self._drop_row = -1
        self.viewport().update()
        event.accept()

    def dropEvent(self, event):
        self._auto_scroll_timer.stop()
        if not self._is_our_drag(event):
            self._drop_row = -1
            self.viewport().update()
            event.ignore()
            return

        target = self._drop_row if self._drop_row >= 0 else self._target_row(event.position().toPoint())
        all_ids = list(self._drag_all_ids)
        moving_ids = list(self._dragging_ids)
        try:
            new_order = build_reordered_ids(all_ids, moving_ids, target)
        except ValueError:
            self._drop_row = -1
            self.viewport().update()
            event.ignore()
            return

        self._drop_row = -1
        self.viewport().update()
        event.setDropAction(Qt.DropAction.MoveAction)
        event.accept()
        if new_order != all_ids:
            self.order_changed.emit(new_order)

    def mousePressEvent(self, event):
        if (event.button() == Qt.MouseButton.LeftButton and
                event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            row = self.rowAt(event.position().toPoint().y())
            if row >= 0:
                self._ctrl_selecting = True
                self._ctrl_anchor_row = row
                self._ctrl_base_rows = set(self.selected_rows())
                self._ctrl_start_was_selected = row in self._ctrl_base_rows
                self._ctrl_drag_moved = False
                self._ctrl_press_position = event.position().toPoint()
                if not self._ctrl_start_was_selected:
                    self._apply_ctrl_selection(row)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._ctrl_selecting and event.buttons() & Qt.MouseButton.LeftButton:
            point = event.position().toPoint()
            if (point - self._ctrl_press_position).manhattanLength() >= QApplication.startDragDistance():
                self._ctrl_drag_moved = True
            row = self.rowAt(point.y())
            if self.rowCount() > 0:
                if row < 0:
                    row = 0 if event.position().y() < 0 else self.rowCount() - 1
                if self._ctrl_drag_moved:
                    self._apply_ctrl_selection(row)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._ctrl_selecting and event.button() == Qt.MouseButton.LeftButton:
            if not self._ctrl_drag_moved and self._ctrl_start_was_selected:
                model = self.selectionModel()
                if model is not None and 0 <= self._ctrl_anchor_row < self.rowCount():
                    model.select(
                        self.model().index(self._ctrl_anchor_row, 0),
                        QItemSelectionModel.SelectionFlag.Deselect
                        | QItemSelectionModel.SelectionFlag.Rows,
                    )
            self._ctrl_selecting = False
            self._ctrl_anchor_row = -1
            self._ctrl_base_rows.clear()
            self._ctrl_start_was_selected = False
            self._ctrl_drag_moved = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _apply_ctrl_selection(self, current_row: int) -> None:
        model = self.selectionModel()
        if model is None or self._ctrl_anchor_row < 0:
            return
        rows = set(self._ctrl_base_rows)
        low, high = sorted((self._ctrl_anchor_row, current_row))
        rows.update(range(low, high + 1))
        model.clearSelection()
        for row in sorted(rows):
            if 0 <= row < self.rowCount():
                model.select(
                    self.model().index(row, 0),
                    QItemSelectionModel.SelectionFlag.Select
                    | QItemSelectionModel.SelectionFlag.Rows,
                )
        if 0 <= current_row < self.rowCount():
            self.setCurrentCell(
                current_row, 0, QItemSelectionModel.SelectionFlag.NoUpdate
            )

    def _scroll_drag_by_delta(self, delta: int, refresh_pointer: bool = False) -> None:
        if not delta:
            return
        if refresh_pointer:
            # Native wheel messages do not carry a Qt-local position. Refresh
            # it from the real cursor so the white insertion line stays aligned
            # after the viewport scrolls during a native QDrag.
            local = self.viewport().mapFromGlobal(QCursor.pos())
            if self.viewport().rect().adjusted(-48, -48, 48, 48).contains(local):
                self._drag_pointer = local

        bar = self.verticalScrollBar()
        steps = max(1, abs(delta) // 120)
        direction = -1 if delta > 0 else 1
        before = bar.value()
        bar.setValue(
            before + direction * steps * max(18, bar.singleStep() * 3)
        )
        if bar.value() != before:
            self._drop_row = self._target_row(self._drag_pointer)
            self.viewport().update()

    def _scroll_drag_by_wheel(self, event) -> None:
        self._scroll_drag_by_delta(event.angleDelta().y(), refresh_pointer=True)

    def eventFilter(self, watched, event):
        if self._dragging_ids and event.type() == QEvent.Type.Wheel:
            self._scroll_drag_by_wheel(event)
            event.accept()
            return True
        return super().eventFilter(watched, event)

    def wheelEvent(self, event):
        if self._dragging_ids:
            self._scroll_drag_by_wheel(event)
            event.accept()
            return
        super().wheelEvent(event)

    def _auto_scroll_step(self) -> None:
        if not self._dragging_ids:
            self._auto_scroll_timer.stop()
            return
        threshold = 34
        y = self._drag_pointer.y()
        direction = -1 if y < threshold else (1 if y > self.viewport().height() - threshold else 0)
        if not direction:
            return
        bar = self.verticalScrollBar()
        before = bar.value()
        bar.setValue(before + direction * max(12, bar.singleStep() * 2))
        if bar.value() != before:
            self._drop_row = self._target_row(self._drag_pointer)
            self.viewport().update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._drop_row < 0:
            return
        if self._drop_row <= 0:
            y = 1
        elif self._drop_row >= self.rowCount():
            if self.rowCount() <= 0:
                y = 1
            else:
                rect = self.visualRect(self.model().index(self.rowCount() - 1, 0))
                y = rect.bottom()
        else:
            rect = self.visualRect(self.model().index(self._drop_row, 0))
            y = rect.top()
        painter = QPainter(self.viewport())
        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        painter.drawLine(0, y, self.viewport().width(), y)
        painter.end()


class PlaylistTab(QWidget):
    play_requested = Signal(str)
    previous_requested = Signal()
    next_requested = Signal()
    import_requested = Signal()
    export_requested = Signal()
    delete_requested = Signal(str)
    delete_many_requested = Signal(object)
    clear_requested = Signal()
    edit_requested = Signal(str)
    batch_edit_requested = Signal(object)
    save_midi_as_requested = Signal(str)
    batch_save_midi_as_requested = Signal(object)
    reorder_requested = Signal(object)
    mode_changed = Signal(str)

    MODES = [
        ("single", "Single Play"),
        ("single_repeat", "Single Repeat"),
        ("repeat_all", "Repeat All"),
        ("sequential", "Sequential"),
        ("shuffle", "Shuffle"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[dict] = []
        self._tr = lambda text: text
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(10)

        card, content = make_card("My Playlist")

        mode_row = QHBoxLayout()
        self.mode_label = QLabel("Playback Mode")
        self.mode_combo = QComboBox()
        for value, text in self.MODES:
            self.mode_combo.addItem(text, value)
        self.mode_combo.currentIndexChanged.connect(
            lambda _index: self.mode_changed.emit(self.current_mode())
        )
        mode_row.addWidget(self.mode_label)
        mode_row.addWidget(self.mode_combo, 1)
        content.addLayout(mode_row)

        self.table = PlaylistTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Name", "Source", "Duration"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.doubleClicked.connect(self._emit_play)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.order_changed.connect(self.reorder_requested.emit)
        content.addWidget(self.table, 1)

        transport = QHBoxLayout()
        self.previous_btn = QPushButton("Previous")
        self.previous_btn.setToolTip("Play the previous playlist item")
        self.play_btn = QPushButton("Play")
        self.play_btn.setToolTip("Play the selected playlist item")
        self.next_btn = QPushButton("Next")
        self.next_btn.setToolTip("Play the next playlist item")
        transport.addWidget(self.previous_btn)
        transport.addWidget(self.play_btn, 1)
        transport.addWidget(self.next_btn)
        content.addLayout(transport)

        actions = QHBoxLayout()
        self.import_btn = QPushButton("Import")
        self.import_btn.setToolTip("Import a HuMidi playlist file")
        self.export_btn = QPushButton("Export")
        self.export_btn.setToolTip("Export the playlist with visible progress")
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setToolTip("Delete the selected song or songs from the playlist")
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setToolTip("Remove every song from the playlist")
        for button in (self.import_btn, self.export_btn, self.delete_btn, self.clear_btn):
            actions.addWidget(button)
        content.addLayout(actions)

        outer.addWidget(card, 1)

        self.previous_btn.clicked.connect(lambda _checked=False: self.previous_requested.emit())
        self.play_btn.clicked.connect(self._emit_play)
        self.next_btn.clicked.connect(lambda _checked=False: self.next_requested.emit())
        self.import_btn.clicked.connect(lambda _checked=False: self.import_requested.emit())
        self.export_btn.clicked.connect(lambda _checked=False: self.export_requested.emit())
        self.delete_btn.clicked.connect(self._emit_delete)
        self.clear_btn.clicked.connect(lambda _checked=False: self.clear_requested.emit())
        self.table.itemSelectionChanged.connect(self._update_actions)
        self._update_actions()

    def refresh(self, items: list[dict], selected_id: str | None = None, selected_ids: list[str] | None = None):
        restore_ids = set(selected_ids or ([] if selected_id is None else [selected_id]))
        if not restore_ids:
            restore_ids = set(self.selected_ids())
        self._items = list(items)
        self.table.setRowCount(len(self._items))
        for row, item in enumerate(self._items):
            name_item = QTableWidgetItem(str(item.get("name", "")))
            name_item.setData(Qt.ItemDataRole.UserRole, item.get("id"))
            if str(item.get("source_type") or "midi") == "sheet":
                format_name = self._tr(str(item.get("source_label") or "Virtual Piano"))
                source_text = self._tr("Text Sheet ({format_name})").format(
                    format_name=format_name
                )
            else:
                source_text = str(item.get("source_label") or item.get("source_midi_filename", ""))
            source_item = QTableWidgetItem(source_text)
            duration_item = QTableWidgetItem(self._format_duration(float(item.get("duration", 0.0))))
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, source_item)
            self.table.setItem(row, 2, duration_item)

        self.table.clearSelection()
        first_selected = None
        selection_model = self.table.selectionModel()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and str(item.data(Qt.ItemDataRole.UserRole)) in restore_ids:
                if selection_model is not None:
                    index = self.table.model().index(row, 0)
                    selection_model.select(
                        index,
                        QItemSelectionModel.SelectionFlag.Select
                        | QItemSelectionModel.SelectionFlag.Rows,
                    )
                if first_selected is None:
                    first_selected = item
        if first_selected is not None:
            self.table.setCurrentItem(first_selected, QItemSelectionModel.SelectionFlag.NoUpdate)
            self.table.scrollToItem(first_selected)
        elif self._items:
            self.table.selectRow(0)
        self._update_actions()

    def selected_ids(self) -> list[str]:
        ids = []
        for row in self.table.selected_rows():
            item = self.table.item(row, 0)
            if item:
                item_id = item.data(Qt.ItemDataRole.UserRole)
                if item_id is not None:
                    ids.append(str(item_id))
        return ids

    def selected_id(self) -> str | None:
        ids = self.selected_ids()
        if ids:
            current_row = self.table.currentRow()
            current_item = self.table.item(current_row, 0) if current_row >= 0 else None
            current_id = str(current_item.data(Qt.ItemDataRole.UserRole)) if current_item else None
            return current_id if current_id in ids else ids[0]
        return None

    def select_id(self, item_id: str) -> bool:
        self.table.clearSelection()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and str(item.data(Qt.ItemDataRole.UserRole)) == item_id:
                self.table.setCurrentCell(row, 0)
                self.table.selectRow(row)
                self.table.scrollToItem(item)
                return True
        return False

    def current_mode(self) -> str:
        return str(self.mode_combo.currentData() or "single")

    def set_mode(self, mode: str):
        index = self.mode_combo.findData(mode)
        if index < 0:
            index = 0
        self.mode_combo.setCurrentIndex(index)

    def retranslate_mode_items(self, tr):
        self._tr = tr
        current = self.current_mode()
        self.mode_combo.blockSignals(True)
        self.mode_combo.clear()
        for value, text in self.MODES:
            self.mode_combo.addItem(tr(text), value)
        self.mode_combo.setCurrentIndex(max(0, self.mode_combo.findData(current)))
        self.mode_combo.blockSignals(False)
        self.table.setHorizontalHeaderLabels([tr("Name"), tr("Source"), tr("Duration")])
        if self._items:
            self.refresh(self._items, selected_ids=self.selected_ids())

    def _emit_play(self, *_args):
        ids = self.selected_ids()
        if len(ids) == 1:
            self.play_requested.emit(ids[0])

    def _emit_delete(self, *_args):
        ids = self.selected_ids()
        if len(ids) == 1:
            self.delete_requested.emit(ids[0])
        elif ids:
            self.delete_many_requested.emit(ids)

    def _show_context_menu(self, position: QPoint):
        clicked_item = self.table.itemAt(position)
        if clicked_item is not None and clicked_item.row() not in self.table.selected_rows():
            self.table.clearSelection()
            self.table.selectRow(clicked_item.row())
            self.table.setCurrentCell(clicked_item.row(), 0)
        ids = self.selected_ids()
        if not ids:
            return

        selected_items = [
            item for item in self._items
            if str(item.get("id")) in set(ids)
        ]
        midi_items = [
            item for item in selected_items
            if str(item.get("source_type") or "midi") == "midi"
        ]
        sheet_items = [
            item for item in selected_items
            if str(item.get("source_type") or "midi") == "sheet"
        ]

        menu = QMenu(self)
        if len(ids) > 1:
            # An all-sheet selection only supports deletion. In a mixed selection
            # the MIDI-only operations remain visible; the main window explains
            # that sheets will be skipped before carrying out the operation.
            edit_action = save_action = None
            if midi_items:
                edit_action = menu.addAction(self._tr("Batch Modify Songs"))
                save_action = menu.addAction(self._tr("Batch Save MIDI As…"))
                if sheet_items:
                    menu.addSeparator()
            delete_action = menu.addAction(self._tr("Batch Delete"))
            selected = menu.exec(self.table.viewport().mapToGlobal(position))
            if edit_action is not None and selected == edit_action:
                self.batch_edit_requested.emit(ids)
            elif save_action is not None and selected == save_action:
                self.batch_save_midi_as_requested.emit(ids)
            elif selected == delete_action:
                self.delete_many_requested.emit(ids)
            return

        item_id = ids[0]
        current = next((item for item in self._items if str(item.get("id")) == item_id), {})
        source_type = str(current.get("source_type") or "midi")
        play_action = menu.addAction(self._tr("Play"))
        edit_action = menu.addAction(self._tr("Modify Song"))
        save_midi_action = None
        if source_type == "midi":
            save_midi_action = menu.addAction(self._tr("Save MIDI As…"))
            midi_available = bool(current.get("midi_available", False))
            edit_action.setEnabled(midi_available)
            save_midi_action.setEnabled(midi_available)
        else:
            edit_action.setEnabled(bool(current.get("sheet_available", True)))
        menu.addSeparator()
        delete_action = menu.addAction(self._tr("Delete"))
        selected = menu.exec(self.table.viewport().mapToGlobal(position))
        if selected == play_action:
            self.play_requested.emit(item_id)
        elif selected == edit_action:
            self.edit_requested.emit(item_id)
        elif save_midi_action is not None and selected == save_midi_action:
            self.save_midi_as_requested.emit(item_id)
        elif selected == delete_action:
            self.delete_requested.emit(item_id)

    def _update_actions(self):
        has_items = bool(self._items)
        count = len(self.selected_ids())
        self.play_btn.setEnabled(count == 1)
        self.delete_btn.setEnabled(count > 0)
        self.previous_btn.setEnabled(has_items)
        self.next_btn.setEnabled(has_items)
        self.export_btn.setEnabled(has_items)
        self.clear_btn.setEnabled(has_items)

    @staticmethod
    def _format_duration(seconds: float) -> str:
        total = max(0, int(round(seconds)))
        return f"{total // 60:02d}:{total % 60:02d}"
