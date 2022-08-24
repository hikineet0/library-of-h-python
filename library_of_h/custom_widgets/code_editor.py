from PySide6 import QtCore as qtc
from PySide6 import QtGui as qtg
from PySide6 import QtWidgets as qtw


class CodeEditor(qtw.QWidget):
    def __init__(self, *args, **kwargs) -> None:

        super().__init__(*args, **kwargs)

        super().setLayout(qtw.QVBoxLayout())
        super().layout().setContentsMargins(0, 0, 0, 0)
        super().layout().setSpacing(0)

        self._font = qtg.QFont("monospace")
        super().setFont(self._font)

        self._status_bar = qtw.QLabel()
        self._plain_text_edit = qtw.QPlainTextEdit()
        self._line_number_area = LineNumberArea(self)

        self._status_bar.setAlignment(qtc.Qt.AlignmentFlag.AlignLeft)
        self._status_bar.setFixedHeight(self._plain_text_edit.fontMetrics().height())

        self._plain_text_edit.blockCountChanged.connect(
            self._update_line_number_area_width
        )
        self._plain_text_edit.updateRequest.connect(self._update_line_number_area_slot)
        self._plain_text_edit.cursorPositionChanged.connect(
            self._highlight_current_line
        )
        self._plain_text_edit.setWordWrapMode(qtg.QTextOption.WrapMode.NoWrap)

        super().layout().addWidget(self._plain_text_edit)
        super().layout().addWidget(self._status_bar)

        self._update_line_number_area_width()
        self._highlight_current_line()

    def __getattr__(self, name: str):
        return self._plain_text_edit.__getattribute__(name)

    def appendPlainText(self, text: str):
        # store the current selection
        tc = self._plain_text_edit.textCursor()
        anchor = tc.anchor()
        position = tc.position()

        # change the text
        self._plain_text_edit.appendPlainText(text)

        # restore the selection
        tc.setPosition(anchor)
        tc.setPosition(position, qtg.QTextCursor.KeepAnchor)
        self._plain_text_edit.setTextCursor(tc)

    def resizeEvent(self, e: qtg.QResizeEvent) -> None:
        super().resizeEvent(e)
        self._update_line_number_area_geometry()

    def _line_number_area_width(self) -> int:
        """
        Gets the (new) width for line number area based on the final line number
        multiplied by the size of a single number in pixels + 3.
        """
        digits = len(str(self._plain_text_edit.blockCount()))

        # Get width for line number area by multiplying the max number of digits
        # in a line number by number of pixels for a single number and add 3 to
        # it.
        space = 3 + self._plain_text_edit.fontMetrics().horizontalAdvance("9") * digits

        return space

    def _update_line_number_area_geometry(self) -> None:
        cr = self._plain_text_edit.contentsRect()
        self._line_number_area.setGeometry(
            qtc.QRect(cr.left(), cr.top(), self._line_number_area_width(), cr.height())
        )

    def _update_line_number_area_width(self) -> None:
        self._update_line_number_area_geometry()
        self._plain_text_edit.setViewportMargins(
            self._line_number_area_width(), 0, 0, 0
        )

    def _update_line_number_area_slot(self, rect: qtc.QRect, dy: int) -> None:
        """
        If the plain text edit is scrolled, update/scroll line number area
        accordingly.
        """
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(
                0, rect.y(), self._line_number_area.width(), rect.height()
            )

        if rect.contains(self._plain_text_edit.viewport().rect()):
            self._update_line_number_area_width()

    def _highlight_current_line(self) -> None:
        extra_selections = list()

        selection = qtw.QTextEdit.ExtraSelection()
        line_color = qtg.QColor(qtc.Qt.GlobalColor.darkGray).lighter(160)

        selection.format.setBackground(line_color)
        selection.format.setProperty(qtg.QTextFormat.Property.FullWidthSelection, True)
        selection.cursor = self._plain_text_edit.textCursor()
        selection.cursor.clearSelection()
        extra_selections.append(selection)

        self._plain_text_edit.setExtraSelections(extra_selections)

    def _line_number_area_paint_event(self, event: qtg.QPaintEvent) -> None:
        painter = qtg.QPainter(self._line_number_area)
        painter.fillRect(event.rect(), qtc.Qt.GlobalColor.lightGray)

        block = self._plain_text_edit.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(
            self._plain_text_edit.blockBoundingGeometry(block)
            .translated(self._plain_text_edit.contentOffset())
            .top()
        )
        bottom = top + round(self._plain_text_edit.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(qtc.Qt.GlobalColor.black)
                painter.drawText(
                    0,
                    top,
                    self._line_number_area.width(),
                    self._plain_text_edit.fontMetrics().height(),
                    qtc.Qt.AlignmentFlag.AlignRight,
                    str(block_number + 1),
                )
            self._status_bar.setText(
                "line: "
                + str(self._plain_text_edit.textCursor().blockNumber() + 1)
                + " "
                + "column: "
                + str(self._plain_text_edit.textCursor().columnNumber() + 1)
            )

            block = block.next()
            top = bottom
            bottom = top + round(
                self._plain_text_edit.blockBoundingRect(block).height()
            )
            block_number += 1


class LineNumberArea(qtw.QWidget):
    def __init__(self, code_editor: CodeEditor) -> None:
        super().__init__(parent=code_editor)
        self._code_editor = code_editor

    def sizeHint(self) -> int:
        return QSize(self._code_editor._line_number_area_width(), 0)

    def paintEvent(self, event: qtg.QPaintEvent) -> None:
        self._code_editor._line_number_area_paint_event(event)
