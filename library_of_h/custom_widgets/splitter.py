from PySide6 import QtCore as qtc
from PySide6 import QtGui as qtg
from PySide6 import QtWidgets as qtw


class SplitterHandle(qtw.QSplitterHandle):

    is_collapsed: bool

    def __init__(self, o: qtc.Qt.Orientation, *args, **kwargs) -> None:
        super().__init__(o, *args, **kwargs)

        self.is_collapsed = False

    def mouseDoubleClickEvent(self, a0: qtg.QMouseEvent) -> None:
        super().mouseDoubleClickEvent(a0)
        if not self.is_collapsed:
            self.collapse()
        else:
            self.expand()

    def expand(self) -> None:
        self._sizeof_1 = self.parent().widget(0).maximumWidth()
        self._sizeof_2 = (
            self.parent().parent().width()
            - self._sizeof_1
            - self.parent().handleWidth()
        )
        self.parent().setSizes([self._sizeof_1, self._sizeof_2])

    def collapse(self) -> None:
        self._sizeof_1 = 0
        self._sizeof_2 = self.parent().parent().width() - self.parent().handleWidth()
        self.parent().setSizes([self._sizeof_1, self._sizeof_2])


class Splitter(qtw.QSplitter):

    is_collapsed: bool

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.is_collapsed = False

    def createHandle(self) -> SplitterHandle:
        handle = SplitterHandle(self.orientation(), self)
        return handle

    def collapse(self) -> None:
        self.is_collapsed = True
        self.handle(0).collapse()

    def expand(self) -> None:
        self.is_collapsed = False
        self.handle(0).expand()
