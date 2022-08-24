from __future__ import annotations

from PySide6 import QtCore as qtc
from PySide6 import QtGui as qtg
from PySide6 import QtWidgets as qtw

from library_of_h.explorer.constants import (DESCRIPTION_OBJECT_ROLE,
                                             SELECTION_TINT_WIDTH,
                                             THUMBNAIL_SIZE)
from library_of_h.explorer.custom_sub_classes.items_delegate import \
    ItemsDelegate
from library_of_h.explorer.custom_sub_classes.list_model import ListModel
from library_of_h.signals_hub.signals_hub import browser_signals


class ListView(qtw.QListView):

    context_menu_move_to_trash_signal = qtc.Signal()
    selection_changed_signal = qtc.Signal()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.setItemDelegate(ItemsDelegate(self))
        self.setModel(ListModel(parent=self))
        self.setSelectionMode(qtw.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setVerticalScrollMode(qtw.QListView.ScrollMode.ScrollPerPixel)

    def selectionChanged(
        self, selected: qtc.QItemSelection, deselected: qtc.QItemSelection
    ):
        self.selection_changed_signal.emit()
        super().selectionChanged(selected, deselected)

    def mouseDoubleClickEvent(self, event: qtg.QMouseEvent):
        event_pos = event.position().toPoint()
        index = self.indexAt(event_pos)
        if not index.isValid():
            super().mouseDoubleClickEvent(event)

        if event_pos.x() <= THUMBNAIL_SIZE[0] + SELECTION_TINT_WIDTH:
            browser_signals.view_new_item_signal.emit(
                index.data(DESCRIPTION_OBJECT_ROLE).location
            )
        else:
            super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event: qtg.QContextMenuEvent):
        menu = qtw.QMenu(self)

        menu.addAction(
            "Move to &Trash",
            self.context_menu_move_to_trash_signal.emit,
        )

        if len(self.selectionModel().selectedIndexes()) == 1:
            menu.addAction(
                qtg.QIcon.fromTheme("edit-copy", qtg.QPixmap("assets:/clipboard.svg")),
                "&Copy Location",
                self._action_copy_location_slot,
            )

        menu.popup(event.globalPos())

    def _action_copy_location_slot(self):
        location = (
            self.selectionModel()
            .selectedIndexes()[0]
            .data(DESCRIPTION_OBJECT_ROLE)
            .location
        )
        qtg.QGuiApplication.clipboard().setText(location)
