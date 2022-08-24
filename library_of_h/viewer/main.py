import os
from typing import Optional

from PySide6 import QtCore as qtc
from PySide6 import QtGui as qtg
from PySide6 import QtWidgets as qtw

from library_of_h.signals_hub.signals_hub import browser_signals


class Viewer(qtw.QGraphicsView):
    _current_gallery_location: str = ''
    _current_page_number: int = 0
    _files: list[str] = []
    _ZOOM_IN_FACTOR = 1.2
    _ZOOM_OUT_FACTOR = 0.7

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(qtc.Qt.FocusPolicy.ClickFocus)
        self.setRenderHint(qtg.QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setBackgroundRole(qtg.QPalette.ColorRole.Dark)
        self.setAlignment(qtc.Qt.AlignmentFlag.AlignCenter)
        self.setDragMode(qtw.QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(qtw.QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        self._scene = qtw.QGraphicsScene()
        self._pixmap_item = qtw.QGraphicsPixmapItem()
        self._pixmap_item.setTransformationMode(qtc.Qt.TransformationMode.SmoothTransformation)
        self._scene.addItem(self._pixmap_item)
        self.setScene(self._scene)

        browser_signals.view_new_item_signal.connect(self._load_gallery)

    def _load_gallery(self, location: str) -> None:
        self._files = sorted(os.listdir(location))
        self._current_gallery_location = location
        self._change_page(1)

    def _change_page(self, requested_page_number: int) -> None:
        page_number_backup = self._current_page_number
        self._current_page_number = requested_page_number
        try:
            if self._current_page_number < 1:
                raise IndexError
            new_file = self._files[self._current_page_number - 1]
        except IndexError:
            self._current_page_number = page_number_backup
        else:
            new_pixmap = qtg.QPixmap(os.path.join(self._current_gallery_location, new_file))
            self._pixmap_item.setPixmap(new_pixmap)
            self.setSceneRect(0, 0, new_pixmap.width(), new_pixmap.height())

    def _zoom_in(self, cursor_hover: Optional[qtc.QPoint] = None) -> None:
        self.scale(self._ZOOM_IN_FACTOR, self._ZOOM_IN_FACTOR)

    def _zoom_out(self, cursor_hover: Optional[qtc.QPoint] = None) -> None:
        self.scale(self._ZOOM_OUT_FACTOR, self._ZOOM_OUT_FACTOR)

    def _fit_in_view(self):
        self.fitInView(self._pixmap_item, qtc.Qt.AspectRatioMode.KeepAspectRatio)

    def contextMenuEvent(self, event: qtg.QContextMenuEvent):
        menu = qtw.QMenu(self)

        menu.addAction(
            qtg.QIcon.fromTheme("zoom-in", qtg.QPixmap("assets:/zoom-in.svg")),
            "Zoom in",
            self._zoom_in,
        )
        menu.addAction(
            qtg.QIcon.fromTheme("zoom-out", qtg.QPixmap("assets:/zoom-out.svg")),
            "Zoom out",
            self._zoom_out
        )
        menu.addAction(
            qtg.QIcon.fromTheme("zoom-fit-best"),
            "&Fit to view",
            self._fit_in_view
        )
        menu.addAction(
            qtg.QIcon.fromTheme("zoom-original"),
            "Restore &Original size",
            self.resetTransform
        )
        menu.addAction(
            qtg.QIcon.fromTheme("edit-copy", qtg.QPixmap("assets:/clipboard.svg")),
            "&Copy image",
            self._action_copy_image
        )

        menu.popup(event.globalPos())

    def _action_copy_image(self):
        qtg.QGuiApplication.clipboard().setPixmap(self._pixmap_item.pixmap())

    def keyPressEvent(self, event: qtg.QKeyEvent) -> None:
        if event.key() == qtc.Qt.Key.Key_O:
            self.resetTransform()
            event.accept()
            return

        if event.key() == qtc.Qt.Key.Key_F:
            self._fit_in_view()

        if (
            event.key() == qtc.Qt.Key.Key_Minus
            or event.key() == qtc.Qt.Key.Key_Underscore
        ) and event.modifiers() & qtc.Qt.Modifier.CTRL:
            self._zoom_out()
            event.accept()
            return

        if (
            event.key() == qtc.Qt.Key.Key_Equal or event.key() == qtc.Qt.Key.Key_Plus
        ) and event.modifiers() & qtc.Qt.Modifier.CTRL:
            self._zoom_in()
            event.accept()
            return

        if event.key() == qtc.Qt.Key.Key_Up:
            self.verticalScrollBar().setValue(
                max(self.verticalScrollBar().value() - 10, 0)
            )
            event.accept()
            return

        if event.key() == qtc.Qt.Key.Key_Down:
            self.verticalScrollBar().setValue(
                min(
                    self.verticalScrollBar().value() + 10,
                    self.verticalScrollBar().maximum(),
                )
            )
            event.accept()
            return

        if event.key() == qtc.Qt.Key.Key_Left:
            self._change_page(self._current_page_number - 1)
            event.accept()
            return

        if event.key() == qtc.Qt.Key.Key_Right:
            self._change_page(self._current_page_number + 1)
            event.accept()
            return

        super().keyPressEvent(event)
        return

    def wheelEvent(self, event: qtg.QWheelEvent) -> None:
        if event.modifiers() & qtc.Qt.Modifier.CTRL:
            x = event.angleDelta().x()
            y = event.angleDelta().y()

            if y < 0:
                self._zoom_out()
            elif y > 0:
                self._zoom_in()
            elif x < 0:
                self._zoom_in()
            elif x > 0:
                self._zoom_out()

            event.accept()
            return

        super().wheelEvent(event)
        return