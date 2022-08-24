from typing import NamedTuple, Optional, Union

from PySide6 import QtCore as qtc
from PySide6 import QtGui as qtg

from library_of_h.explorer.constants import (BROWSER_IMAGES_LIMIT,
                                             DESCRIPTION_HTML_TEMPLATE,
                                             DESCRIPTION_OBJECT_ROLE)


class Description(NamedTuple):
    title: str
    jtitle: str
    gallery: int
    artist: list[str]
    character: list[str]
    group: list[str]
    series: list[str]
    tag: list[str]
    language: str
    location: str
    pages: int
    source: str
    type: str
    udate: str
    size_in_bytes: str

    def to_html(self):
        return DESCRIPTION_HTML_TEMPLATE.format(**self._asdict())


class RowData(NamedTuple):
    thumbnail: qtg.QImage
    description: Description


class ListData(NamedTuple):
    thumbnails: list[qtg.QImage]
    descriptions: list[Description]


class ListModel(qtc.QAbstractListModel):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._data = ListData(
            [None for _ in range(BROWSER_IMAGES_LIMIT)],
            [None for _ in range(BROWSER_IMAGES_LIMIT)],
        )

    def data(
        self, index: qtc.QModelIndex, role: qtc.Qt.ItemDataRole
    ) -> Union[int, None]:
        if not index.isValid():
            return None

        if role == qtc.Qt.ItemDataRole.DisplayRole:
            if self._data.descriptions[index.row()] is not None:
                return self._data.descriptions[index.row()].to_html()
        elif role == qtc.Qt.ItemDataRole.DecorationRole:
            return self._data.thumbnails[index.row()]
        elif role == DESCRIPTION_OBJECT_ROLE:
            return self._data.descriptions[index.row()]

        return None

    def flags(self, index) -> qtc.Qt.ItemFlag:
        return (
            qtc.Qt.ItemFlag.ItemIsEditable
            | qtc.Qt.ItemFlag.ItemIsEnabled
            | qtc.Qt.ItemFlag.ItemIsSelectable
        )

    def setData(
        self,
        index: qtc.QModelIndex,
        value: Union[qtg.QImage, dict],
        role: qtc.Qt.ItemDataRole,
    ) -> None:
        if not index.isValid():
            return False

        if role == qtc.Qt.ItemDataRole.DisplayRole:
            if isinstance(value, dict):
                self._data.descriptions[index.row()] = Description(**value)
            elif value is None:
                self._data.descriptions[index.row()] = value
        elif role == qtc.Qt.ItemDataRole.DecorationRole:
            self._data.thumbnails[index.row()] = value
        else:
            return False

        self.dataChanged.emit(index, index, [role])
        return True

    def removeRows(self, row: int, count: int):
        self.beginRemoveRows(qtc.QModelIndex(), row, count)
        for r in range(row, count):
            index = self.createIndex(r, 0)
            self.setData(index, None, qtc.Qt.ItemDataRole.DisplayRole)
            self.setData(index, None, qtc.Qt.ItemDataRole.DecorationRole)
        self.endRemoveRows()

    def rowCount(self, _: Optional[qtc.QModelIndex] = None) -> int:
        return len(self._data.thumbnails) - self._data.thumbnails.count(None)
