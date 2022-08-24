from PySide6 import QtCore as qtc


class LoggerSignals(qtc.QObject):
    halt_signal = qtc.Signal()
    new_error_signal = qtc.Signal()
    new_warning_signal = qtc.Signal()
    create_logs_icon_signal = qtc.Signal()
    create_message_box_signal = qtc.Signal(str)
