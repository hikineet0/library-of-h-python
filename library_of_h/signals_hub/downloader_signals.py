from PySide6 import QtCore as qtc


class DownloaderSignals(qtc.QObject):
    download_session_began_signal = qtc.Signal()
    download_session_finished_signal = qtc.Signal()
