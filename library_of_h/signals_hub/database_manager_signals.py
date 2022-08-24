from PySide6 import QtCore as qtc


class DatabaseManagerSignals(qtc.QObject):
    create_table_if_not_exists_finished_signal = qtc.Signal()
