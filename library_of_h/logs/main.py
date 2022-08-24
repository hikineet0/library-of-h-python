from PySide6 import QtCore as qtc

from library_of_h.custom_widgets.code_editor import CodeEditor
from library_of_h.logs.custom_sub_classes.logs_highlighter import \
    LogsHighlighter


class Logs(CodeEditor):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__()
        self.setFocusPolicy(qtc.Qt.FocusPolicy.StrongFocus)
        self._plain_text_edit.setReadOnly(True)
        self._plain_text_edit.setMaximumBlockCount(1000)
        self._syntax_highlighter = LogsHighlighter(self.document())
