from PySide6 import QtCore as qtc


class MainSignals(qtc.QObject):
    close_signal = qtc.Signal()
    close_canceled_signal = qtc.Signal()
