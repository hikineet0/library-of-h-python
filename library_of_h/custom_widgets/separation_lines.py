from PySide6 import QtWidgets as qtw


class HSeperationLine(qtw.QFrame):
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(1)
        self.setFixedHeight(20)
        self.setFrameShape(qtw.QFrame.HLine)
        self.setFrameShadow(qtw.QFrame.Sunken)
        self.setSizePolicy(qtw.QSizePolicy.Preferred, qtw.QSizePolicy.Minimum)


class VSeperationLine(qtw.QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(20)
        self.setMinimumHeight(1)
        self.setFrameShape(qtw.QFrame.VLine)
        self.setFrameShadow(qtw.QFrame.Sunken)
        self.setSizePolicy(qtw.QSizePolicy.Minimum, qtw.QSizePolicy.Preferred)
