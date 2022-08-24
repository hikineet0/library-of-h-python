from __future__ import annotations

from PySide6 import QtCore as qtc
from PySide6 import QtWidgets as qtw


class ItemsTableView(qtw.QTableView):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.horizontalHeader().setSectionResizeMode(qtw.QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setHighlightSections(False)
        self.setSelectionBehavior(qtw.QTableView.SelectionBehavior.SelectRows)
        self.setFocusPolicy(qtc.Qt.FocusPolicy.NoFocus)

    def remove_table_model(self) -> None:
        self.setModel(None)
