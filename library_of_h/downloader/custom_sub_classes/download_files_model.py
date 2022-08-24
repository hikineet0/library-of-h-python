from typing import Any, NamedTuple

from PySide6 import QtCore as qtc

from library_of_h.miscellaneous.functions import get_value_and_unit_from_Bytes


class TableData(NamedTuple):
    status: list[int]
    filename: list[str]
    file_size: list[int]
    download_speed: list[int]
    download_progress: list[int]


class TableRowData(NamedTuple):
    status: int
    filename: str
    file_size: int
    download_speed: int
    download_progress: int


class TableRowIndices(NamedTuple):
    status: int
    filename: int
    file_size: int
    download_speed: int
    download_progress: int


class DownloadFilesModel(qtc.QAbstractTableModel):

    _HEADERS = {0: "Status", 1: "File name", 2: "File size", 3: "Speed", 4: "Progress"}
    _STATUS = {-1: "Pending", 0: "Downloading", 1: "Completed"}

    _data: TableData

    def __init__(self, filenames: list[str], *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._i = -1
        self._data = TableData(
            [-1 for _ in filenames],
            filenames,
            [-1 for _ in filenames],
            [-1 for _ in filenames],
            [-1 for _ in filenames],
        )

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
            elif index.column() == 1:
                return self._data.filename[index.row()]
            elif index.column() == 2:
                if self._data.file_size[index.row()] == -1:
                    return "---"
                size, unit = get_value_and_unit_from_Bytes(
                    self._data.file_size[index.row()]
                )
                return f"{size} {unit}"
            elif index.column() == 3:
                if self._data.download_speed[index.row()] == -1:
                    return "---"
                size, unit = get_value_and_unit_from_Bytes(
                    self._data.download_speed[index.row()]
                )
                return f"{size} {unit}/s"
            elif index.column() == 4:
                if self._data.download_progress[index.row()] == -1:
                    return "---"
                size, unit = get_value_and_unit_from_Bytes(
                    self._data.download_progress[index.row()]
                )
                return f"{size} {unit}"
                # return self._data.download_progress[index.row()]

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
            self._data.status[index.row()] = value
        elif for_ == "size":
            self._data.file_size[index.row()] = value
        elif for_ == "speed":
            self._data.download_speed[index.row()] = value
        elif for_ == "progress":
            self._data.download_progress[index.row()] = (
                self._data.file_size[index.row()] if value == -1 else value
            )

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

    def get_current_index(self) -> TableRowIndices:
        """
        Gets ModelIndex for current data row index.

        Returns
        --------
            TableRowIndices:
                status:
                filename:
                file_size:
                download_speed:
                download_progress:
                    Index for the corresponding items in a table row.
        """
        return TableRowIndices(
            self.createIndex(self._i, 0),  # Status
            self.createIndex(self._i, 1),  # File name
            self.createIndex(self._i, 2),  # File size
            self.createIndex(self._i, 3),  # Download speed
            self.createIndex(self._i, 4),  # Download progress
        )

    def get_current_data(self) -> TableRowData:
        """
        Gets data in current index of data structure.

        Returns
        --------
            TableRowData:
                status:
                    Status of data in current index.
                filename:
                    Name of data in current index.
                file_size:
                    Size in Bytes of data in current index.
                download_speed:
                    Download speed of data in current index.
                download_progress:
                    Download progress of data in current index.
        """

        return TableRowData(
            self._data[0][self._i],
            self._data[1][self._i],
            self._data[2][self._i],
            self._data[3][self._i],
            self._data[4][self._i],
        )

    def current(self) -> TableRowData:
        """
        Gets data in current index of table.

        Returns
        --------
            TableRowData:
                status:
                    Status of data in current index.
                filename:
                    Name of data in current index.
                file_size:
                    Size in Bytes of data in current index.
                download_speed:
                    Download speed of data in current index.
                download_progress:
                    Download progress of data in current index.
        """
        status_index = self.createIndex(self._i, 0)
        file_name_index = self.createIndex(self._i, 1)
        file_size_index = self.createIndex(self._i, 2)
        download_speed_index = self.createIndex(self._i, 3)
        download_progress_index = self.createIndex(self._i, 4)

        return TableRowData(
            status_index.data(qtc.Qt.ItemDataRole.DisplayRole),
            file_name_index.data(qtc.Qt.ItemDataRole.DisplayRole),
            file_size_index.data(qtc.Qt.ItemDataRole.DisplayRole),
            download_speed_index.data(qtc.Qt.ItemDataRole.DisplayRole),
            download_progress_index.data(qtc.Qt.ItemDataRole.DisplayRole),
        )

    def __next__(self, default: Any = None) -> TableRowData:
        """
        Gets next data.

        Returns
        --------
            TableRowData:
                status:
                    Status of next data.
                filename:
                    Name of next data.
                file_size:
                    Size in Bytes of next data.
                download_speed:
                    Download speed of next data.
                download_progress:
                    Download progress of next data.

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
        file_name_index = self.createIndex(self._i, 1)
        file_size_index = self.createIndex(self._i, 2)
        download_speed_index = self.createIndex(self._i, 3)
        download_progress_index = self.createIndex(self._i, 4)

        return TableRowData(
            status_index.data(qtc.Qt.ItemDataRole.DisplayRole),
            file_name_index.data(qtc.Qt.ItemDataRole.DisplayRole),
            file_size_index.data(qtc.Qt.ItemDataRole.DisplayRole),
            download_speed_index.data(qtc.Qt.ItemDataRole.DisplayRole),
            download_progress_index.data(qtc.Qt.ItemDataRole.DisplayRole),
        )
