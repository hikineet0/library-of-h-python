from typing import Any, NamedTuple

from PySide6 import QtCore as qtc


class TableData(NamedTuple):
    status: list[int]
    item_name: list[str]
    download_type: list[int]


class TableRowData(NamedTuple):
    status: int
    item_name: str
    download_type: int


class TableRowIndices(NamedTuple):
    status: int
    item_name: int
    download_type: int


class DownloadItemsModel(qtc.QAbstractTableModel):

    _STATUS = {
        -3: "Invalid",
        -2: "Aborted",
        -1: "Pending",
        0: "Downloading",
        1: "Completed",
    }
    _HEADERS = {
        0: "Status",
        1: "Item name",
        2: "Download type",
    }

    _data: TableData

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._i = -1
        self._data = TableData([], [], [])

    def add_item(self, item_name: str, download_type: str) -> None:
        self._data.status.append(-1)
        self._data.item_name.append(item_name)
        self._data.download_type.append(download_type)

    def rowCount(self, _: qtc.QModelIndex = qtc.QModelIndex()) -> int:
        return len(self._data.status)

    def columnCount(self, _: qtc.QModelIndex = qtc.QModelIndex()) -> int:
        return len(self._data)

    def data(
        self,
        index: qtc.QModelIndex,
        role: qtc.Qt.ItemDataRole = qtc.Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if not index.isValid():
            return None

        if role == qtc.Qt.ItemDataRole.TextAlignmentRole:
            return int(qtc.Qt.AlignmentFlag.AlignCenter)

        if role == qtc.Qt.ItemDataRole.DisplayRole:
            if index.column() == 0:
                return self._STATUS[self._data.status[index.row()]]
            else:
                return self._data[index.column()][index.row()]

        return None

    def setData(
        self,
        index: qtc.QModelIndex,
        value: int,
        for_: str,
        role: qtc.Qt.ItemDataRole = qtc.Qt.ItemDataRole.DisplayRole,
    ) -> bool:
        if not index.isValid():
            return False

        if for_ == "status":
            if value == -2:
                for i in range(index.row(), len(self._data.status)):
                    self._data.status[i] = value
            else:
                self._data.status[index.row()] = value

        self.dataChanged.emit(index, index, [role])
        return True

    def headerData(
        self, section: int, orientation: qtc.Qt.Orientation, role: qtc.Qt.ItemDataRole
    ) -> Any:
        if role != qtc.Qt.ItemDataRole.DisplayRole:
            return None

        if orientation == qtc.Qt.Orientation.Horizontal:
            return self._HEADERS[section]
        elif orientation == qtc.Qt.Orientation.Vertical:
            return section + 1

    def get_current_data(self) -> TableRowData:
        """
        Gets data in current index of data structure.

        Returns
        --------
            TableRowData:
                status:
                    Status of data in current index.
                item_name:
                    Name of data in current index.
                download_type:
                    Download type of data in current index.
        """

        return TableRowData(
            self._data[0][self._i],
            self._data[1][self._i],
            self._data[2][self._i],
        )

    def get_current_index(self) -> TableRowIndices:
        return TableRowIndices(
            self.createIndex(self._i, 0),
            self.createIndex(self._i, 1),
            self.createIndex(self._i, 2),
        )

    def current(self) -> TableRowData:
        """
        Gets data in current index of table.

        Returns
        --------
            TableRowData:
                status:
                    Status of data in current index.
                item_name:
                    Name of data in current index.
                download_type:
                    Download type of data in current index.
        """
        status_index = self.createIndex(self._i, 0)
        item_name_index = self.createIndex(self._i, 1)
        download_type_index = self.createIndex(self._i, 2)

        return TableRowData(
            status_index.data(qtc.Qt.ItemDataRole.DisplayRole),
            item_name_index.data(qtc.Qt.ItemDataRole.DisplayRole),
            download_type_index.data(qtc.Qt.ItemDataRole.DisplayRole),
        )

    def __next__(self, default: Any = None) -> TableRowData:
        """
        Gets next data.

        Returns
        --------
            TableRowData:
                status:
                    Status of next data.
                item_name:
                    Name of next data.
                download_type:
                    Download type of next data.
        Raises
        -------
            StopIteration:
                There is no more data left.
        """
        self._i += 1

        if self._i >= self.rowCount() or self._i < 0:
            self._i = -1
            if not default is None:
                return default
            raise StopIteration()

        status_index = self.createIndex(self._i, 0)
        item_name_index = self.createIndex(self._i, 1)
        download_type_index = self.createIndex(self._i, 2)

        return TableRowData(
            status_index.data(qtc.Qt.ItemDataRole.DisplayRole),
            item_name_index.data(qtc.Qt.ItemDataRole.DisplayRole),
            download_type_index.data(qtc.Qt.ItemDataRole.DisplayRole),
        )
