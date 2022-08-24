from PySide6 import QtCore as qtc


class ElapsedTimer(qtc.QElapsedTimer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pause_time = 0
        self._pause_time_elapsed = 0

    def start(self):
        super().start()
        self._pause_time_elapsed = 0

    def pause(self):
        self._pause_time = self.elapsed()

    def resume(self):
        self._pause_time_elapsed = super().elapsed() - self._pause_time

    def elapsed(self):
        return super().elapsed() - self._pause_time_elapsed
