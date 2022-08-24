from PySide6 import QtCore as qtc
from PySide6 import QtGui as qtg

from library_of_h.logger import (DownloaderServiceType, DownloaderSubType,
                                 ExplorerSubType, MainType)


class LogsHighlighter(qtg.QSyntaxHighlighter):

    _rules: list[tuple[qtc.QRegularExpression, qtg.QTextCharFormat]]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._rules = list()

        # Numerals
        format_ = qtg.QTextCharFormat()
        format_.setForeground(qtg.QColor(0, 134, 68))
        self._rules.append((qtc.QRegularExpression("\d+"), format_))

        # Level
        format_ = qtg.QTextCharFormat()
        format_.setForeground(qtg.QColor(8, 102, 0))
        self._rules.append((qtc.QRegularExpression("INFO"), format_))

        format_ = qtg.QTextCharFormat()
        format_.setForeground(qtg.QColor(130, 133, 0))
        self._rules.append((qtc.QRegularExpression("DEBUG|WARNING"), format_))

        format_ = qtg.QTextCharFormat()
        format_.setForeground(qtc.Qt.GlobalColor.red)
        self._rules.append((qtc.QRegularExpression("ERROR|CRITICAL"), format_))

        # Types
        format_ = qtg.QTextCharFormat()
        format_.setForeground(qtg.QColor(143, 0, 120))
        self._rules.append(
            (
                qtc.QRegularExpression(
                    f"({'|'.join(enum.name for enum in MainType)})"
                    ":?"
                    f"({'|'.join(enum.name for sub_type in [DownloaderSubType, ExplorerSubType] for enum in sub_type)})"
                    ":"
                    f"({'|'.join(enum.name for enum in DownloaderServiceType)})"
                ),
                format_,
            )
        )

        # Date
        format_ = qtg.QTextCharFormat()
        format_.setForeground(qtg.QColor(18, 0, 163))
        self._rules.append(
            (
                qtc.QRegularExpression("(\d{4}-\d{2}-\d{2})?_?(\d{2}:\d{2}:\d{2})?"),
                format_,
            )
        )

        # Backticks
        format_ = qtg.QTextCharFormat()
        format_.setForeground(qtc.Qt.GlobalColor.darkGray)
        self._rules.append((qtc.QRegularExpression("`.+?`"), format_))

        # Double quotes
        format_ = qtg.QTextCharFormat()
        format_.setForeground(qtc.Qt.GlobalColor.darkCyan)
        self._rules.append((qtc.QRegularExpression('".+?"'), format_))

        # Square brackets
        format_ = qtg.QTextCharFormat()
        format_.setForeground(qtg.QColor(135, 0, 5))
        self._rules.append((qtc.QRegularExpression("\[.+?\]"), format_))

        # Pathlike strings
        format_ = qtg.QTextCharFormat()
        format_.setForeground(qtg.QColor(6, 69, 173))
        self._rules.append((qtc.QRegularExpression("(URL|LOCATION)=.+"), format_))

        # Keywords
        format_ = qtg.QTextCharFormat()
        format_.setForeground(qtg.QColor(207, 54, 0))
        self._rules.append((qtc.QRegularExpression(f"[ A-Z]+="), format_))

    def highlightBlock(self, text: str) -> None:
        for pattern, format_ in self._rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format_)
