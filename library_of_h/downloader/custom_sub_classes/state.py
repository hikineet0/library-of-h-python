from typing import Callable

from PySide6 import QtCore as qtc
from PySide6 import QtStateMachine as qsm


class State(qsm.QState):
    def set_on_entry(self, callback: Callable):
        self._on_entry_callback = callback

    def onEntry(self, event: qtc.QEvent):
        try:
            self._on_entry_callback(*event.arguments())
        except AttributeError:
            # If no on_entry_callback specified, do nothing.
            pass
