from PySide6 import QtCore as qtc


class BrowserSignals(qtc.QObject):
    view_new_item_signal = qtc.Signal(str)
