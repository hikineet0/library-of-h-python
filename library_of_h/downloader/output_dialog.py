from PySide6 import QtCore as qtc
from PySide6 import QtGui as qtg
from PySide6 import QtWidgets as qtw

from library_of_h.downloader.custom_sub_classes.download_files_model import \
    DownloadFilesModel


class Progresses(qtw.QWidget):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setLayout(qtw.QFormLayout())

        self.gallery_progress = qtw.QProgressBar(parent=self)
        self.gallery_progress.setFixedHeight(15)
        self.gallery_progress.setFormat("%v/%m")
        self.file_progress = qtw.QProgressBar(parent=self)
        self.file_progress.setFixedHeight(15)
        self.file_progress.setFormat("%v/%m")

        self.layout().addRow("Galleries progress:", self.gallery_progress)
        self.layout().addRow("Files progress:", self.file_progress)


class Table(qtw.QTableView):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.horizontalHeader().setSectionResizeMode(qtw.QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setHighlightSections(False)
        self.setSelectionBehavior(qtw.QTableView.SelectionBehavior.SelectRows)
        self.setFocusPolicy(qtc.Qt.FocusPolicy.NoFocus)


class OutputDialog(qtw.QDialog):

    canceled_signal = qtc.Signal()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setWindowTitle("Download progress")
        self.setAttribute(qtc.Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setLayout(qtw.QGridLayout())
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(10, 0, 10, 10)

        self.setWindowFlags(
            qtc.Qt.WindowType.Dialog
            | qtc.Qt.WindowType.WindowMinimizeButtonHint  # This only hints the window manager, i.e. does not enforce anything.
        )

    def _create_gui(self) -> None:
        self._progresses = Progresses(self)
        self._table = Table()

        self._cancel_button = qtw.QPushButton("Cancel")
        self._cancel_button.clicked.connect(self.canceled_signal)
        self._cancel_button.setFocusPolicy(qtc.Qt.FocusPolicy.NoFocus)

        self.layout().addWidget(self._progresses, 0, 0, 1, 2)
        self.layout().addWidget(self._table, 1, 0, 1, 2)
        self.layout().addWidget(self._cancel_button, 2, 0, 1, 2)

        self.reset_gallery_progress_value()
        self.reset_file_progress_value()
        self.set_gallery_progress_max_value(0)
        self.set_file_progress_max_value(0)

    def show(self) -> None:
        self._create_gui()
        return super().show()

    def reset_gallery_progress_value(self) -> None:
        self._progresses.gallery_progress.setValue(0)

    def reset_file_progress_value(self) -> None:
        self._progresses.file_progress.setValue(0)

    def set_gallery_progress_max_value(self, max_value: int) -> None:
        self._progresses.gallery_progress.setMaximum(max_value)

    def set_file_progress_max_value(self, max_value: int) -> None:
        self._progresses.file_progress.setMaximum(max_value)

    def get_gallery_progress_max_value(self) -> int:
        return self._progresses.gallery_progress.maximum()

    def get_file_progress_max_value(self) -> int:
        return self._progresses.file_progress.maximum()

    def update_gallery_progress(self) -> None:
        self._progresses.gallery_progress.setValue(
            self._progresses.gallery_progress.value() + 1
        )

    def update_file_progress(self) -> None:
        self._progresses.file_progress.setValue(
            self._progresses.file_progress.value() + 1
        )

    def remove_table_model(self) -> None:
        self._table.setModel(None)

    def set_table_model(self, model: DownloadFilesModel) -> None:
        self._table.setModel(model)

    def keyPressEvent(self, a0: qtg.QKeyEvent) -> None:
        if a0.key() == qtc.Qt.Key.Key_Escape:
            return
        return super().keyPressEvent(a0)

    def closeEvent(self, a0: qtg.QCloseEvent) -> None:
        a0.ignore()
