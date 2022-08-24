from PySide6 import QtCore as qtc
from PySide6 import QtWidgets as qtw


class ProgressDialog(qtw.QProgressDialog):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setWindowTitle("Progress dialog")
        self.setValue(0)
        self.setFixedSize(278, 67)  # Gives segfault when resizing for some reason.
        self.setAttribute(qtc.Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowFlags(
            qtc.Qt.WindowType.CustomizeWindowHint | qtc.Qt.WindowType.WindowTitleHint
        )

    def update_progress(self) -> None:
        self.setValue(self.value() + 1)

    def closeEvent(self, event):
        event.ignore()
