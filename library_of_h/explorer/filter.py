from PySide6 import QtCore as qtc
from PySide6 import QtGui as qtg
from PySide6 import QtWidgets as qtw


class Filter(qtw.QLineEdit):

    filter_signal = qtc.Signal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setPlaceholderText("Filter...")
        self.returnPressed.connect(self._return_pressed_slot)

    def keyPressEvent(self, event: qtg.QKeyEvent):
        if event.key() == qtc.Qt.Key.Key_Escape:
            self.parent().setFocus()
            return

        super().keyPressEvent(event)

    def _return_pressed_slot(self):
        self.filter_signal.emit(self.text())
