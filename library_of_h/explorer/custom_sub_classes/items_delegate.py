from typing import Union

from PySide6 import QtCore as qtc
from PySide6 import QtGui as qtg
from PySide6 import QtWidgets as qtw

from library_of_h.explorer.constants import (BROWSER_ITEMS_V_SPACING,
                                             SELECTION_TINT_WIDTH,
                                             THUMBNAIL_SIZE)


class DescriptionTextEdit(qtw.QTextEdit):
    def wheelEvent(self, e: qtg.QWheelEvent):
        if abs(e.angleDelta().x()) > abs(e.angleDelta().y()):
            qtc.QCoreApplication.sendEvent(self.horizontalScrollBar(), e)
        else:
            qtc.QCoreApplication.sendEvent(self.verticalScrollBar(), e)

        e.accept()

        return


class ItemsDelegate(qtw.QStyledItemDelegate):
    def createEditor(
        self,
        parent: qtw.QWidget,
        option: qtw.QStyleOptionViewItem,
        index: qtc.QModelIndex,
    ) -> DescriptionTextEdit:
        editor = DescriptionTextEdit(parent)
        editor.setDocument(qtg.QTextDocument())
        editor.setReadOnly(True)
        return editor

    def paint(
        self,
        painter: qtg.QPainter,
        option: qtw.QStyleOptionViewItem,
        index: qtc.QModelIndex,
    ) -> None:
        option = self._get_option(option, index)
        if option.state & qtw.QStyle.StateFlag.State_Selected:
            painter.fillRect(
                qtc.QRect(
                    option.rect.left() - SELECTION_TINT_WIDTH,
                    option.rect.top(),
                    SELECTION_TINT_WIDTH,
                    option.rect.height(),
                ),
                qtc.Qt.GlobalColor.blue,
            )
        option.state &= ~qtw.QStyle.StateFlag.State_Selected
        option.state &= ~qtw.QStyle.StateFlag.State_HasFocus
        widget = option.widget
        style = self._get_style(widget)

        description_rect = style.subElementRect(qtw.QStyle.SE_ItemViewItemText, option)
        description_text_document = qtg.QTextDocument()
        description_text_document.setHtml(option.text)

        option.text = None
        style.drawControl(qtw.QStyle.CE_ItemViewItem, option, painter, widget)

        painter.save()
        gradient = qtg.QLinearGradient(
            description_rect.bottomLeft(), description_rect.topLeft()
        )
        gradient.setColorAt(0, qtg.QColor(64, 64, 64, 255))
        gradient.setColorAt(0.1, qtc.Qt.GlobalColor.white)
        path = qtg.QPainterPath()
        path.addRoundedRect(description_rect, 5, 5)
        painter.fillPath(path, gradient)
        # painter.drawPath(path)
        painter.restore()

        painter.save()
        painter.translate(description_rect.left(), description_rect.top())
        description_text_document.drawContents(
            painter,
            qtc.QRect(0, 0, description_rect.width(), description_rect.height()),
        )
        painter.restore()

    def setEditorData(
        self, editor: DescriptionTextEdit, index: qtc.QModelIndex
    ) -> None:
        description = index.model().data(index, qtc.Qt.ItemDataRole.DisplayRole)
        editor.setHtml(description)

    def sizeHint(
        self, option: qtw.QStyleOptionViewItem, index: qtc.QModelIndex
    ) -> qtc.QSize:
        return qtc.QSize(500, THUMBNAIL_SIZE[1] + BROWSER_ITEMS_V_SPACING)

    def updateEditorGeometry(
        self,
        editor: DescriptionTextEdit,
        option: qtw.QStyleOptionViewItem,
        index: qtc.QModelIndex,
    ) -> None:
        option = self._get_option(option, index)
        style = self._get_style(option)

        editor.setGeometry(style.subElementRect(qtw.QStyle.SE_ItemViewItemText, option))

    def _get_option(
        self, option: qtw.QStyleOptionViewItem, index: qtc.QModelIndex
    ) -> qtw.QStyleOptionViewItem:
        option = qtw.QStyleOptionViewItem(option)
        self.initStyleOption(option, index)
        option.rect = qtc.QRect(
            option.rect.left() + SELECTION_TINT_WIDTH,
            option.rect.top() + BROWSER_ITEMS_V_SPACING,
            option.rect.width() - SELECTION_TINT_WIDTH - 10,
            option.rect.height() - BROWSER_ITEMS_V_SPACING,
        )
        option.decorationSize = qtc.QSize(*THUMBNAIL_SIZE)
        option.showDecorationSelected = True
        option.TextElideMode = qtc.Qt.TextElideMode.ElideRight
        return option

    def _get_style(
        self, arg__1: Union[qtw.QWidget, qtw.QStyleOptionViewItem]
    ) -> qtw.QStyle:
        if isinstance(arg__1, qtw.QStyleOptionViewItem):
            widget = arg__1.widget
        else:
            widget = arg__1
        style = widget.style() if widget else qtw.QApplication.style()
        return style
