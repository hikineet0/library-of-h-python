from __future__ import annotations

import sys

from PySide6 import QtCore as qtc
from PySide6 import QtGui as qtg
from PySide6 import QtWidgets as qtw

from library_of_h.custom_widgets.splitter import Splitter
from library_of_h.database_manager.main import DatabaseManager
from library_of_h.downloader.main import Downloader
from library_of_h.explorer.main import Explorer
from library_of_h.logs.main import Logs
from library_of_h.preferences_dialog import PreferencesDialog
from library_of_h.signals_hub.signals_hub import logger_signals, main_signals
from library_of_h.viewer.main import Viewer

from . import logger


class LibraryOfH(qtw.QMainWindow):
    def __init__(self, logger_widget, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setWindowTitle("Library of H")
        self.setMinimumSize(600, 400)
        self.setAttribute(qtc.Qt.WidgetAttribute.WA_StyledBackground, True)

        logger_signals.create_message_box_signal.connect(
            self._create_logger_messsage_box_slot
        )
        logger_signals.create_logs_icon_signal.connect(self._create_logs_icon_slot)

        self._create_menu_bar()
        self._create_splitter_widget()
        self._create_viewer_widget()

        self._explorer = Explorer(parent=self)
        self._downloader = Downloader(parent=self)
        self._logger_widget = logger_widget

        self._tab_widget.insertTab(1, self._downloader, "Downloader")
        self._tab_widget.insertTab(0, self._explorer, "Explorer")
        self._tab_widget.insertTab(2, self._logger_widget, "Logs")

        self._splitter.addWidget(self._tab_widget)
        self._splitter.addWidget(self._viewer)
        self.setCentralWidget(self._splitter)

        self.show()

    def keyPressEvent(self, event: qtg.QKeyEvent):
        if event.key() == qtc.Qt.Key.Key_PageUp:
            if not self._splitter.is_collapsed:
                current_index = self._tab_widget.currentIndex()
                if current_index - 1 < 0:
                    self._tab_widget.setCurrentIndex(2)
                else:
                    self._tab_widget.setCurrentIndex(current_index - 1)
                event.accept()
                return

        if event.key() == qtc.Qt.Key.Key_PageDown:
            if not self._splitter.is_collapsed:
                current_index = self._tab_widget.currentIndex()
                if current_index + 1 > 2:
                    self._tab_widget.setCurrentIndex(0)
                else:
                    self._tab_widget.setCurrentIndex(current_index + 1)
                event.accept()
                return

        if event.key() == qtc.Qt.Key.Key_Escape:
            if self._splitter.is_collapsed:
                self._tab_widget.currentWidget().setFocus()
                self._splitter.expand()
            else:
                self._viewer.setFocus()
                self._splitter.collapse()
            event.accept()
            return

        if event.key() == qtc.Qt.Key.Key_E and event.modifiers() & qtc.Qt.Modifier.CTRL:
            if not self._splitter.is_collapsed:
                self._tab_widget.setCurrentIndex(0)
            else:
                self._splitter.expand()
                self._tab_widget.setCurrentIndex(0)
            event.accept()
            return

        if event.key() == qtc.Qt.Key.Key_D and event.modifiers() & qtc.Qt.Modifier.CTRL:
            if not self._splitter.is_collapsed:
                self._tab_widget.setCurrentIndex(1)
            else:
                self._splitter.expand()
                self._tab_widget.setCurrentIndex(1)
            event.accept()
            return

        if event.key() == qtc.Qt.Key.Key_L and event.modifiers() & qtc.Qt.Modifier.CTRL:
            if not self._splitter.is_collapsed:
                self._tab_widget.setCurrentIndex(2)
            else:
                self._splitter.expand()
                self._tab_widget.setCurrentIndex(2)
            event.accept()
            return

        if event.key() == qtc.Qt.Key.Key_F and event.modifiers() & qtc.Qt.Modifier.CTRL:
            if self._splitter.is_collapsed:
                self._splitter.expand()
            if not self._tab_widget.currentIndex() == 0:
                self._tab_widget.setCurrentIndex(0)
            qtc.QCoreApplication.sendEvent(self._explorer, event)
            event.accept()
            return

        super().keyPressEvent(event)

    def resizeEvent(self, a0: qtg.QResizeEvent) -> None:
        if self._tab_widget.currentIndex() != 1:
            self._splitter.widget(0).setMaximumWidth(self.width() // 1.5)
        else:
            self._splitter.widget(0).setMaximumWidth(450)
        return super().resizeEvent(a0)

    def closeEvent(self, event: qtg.QCloseEvent) -> None:
        # self._viewer.clean_up()
        # self._explorer.clean_up()
        clean_up_results: dict = self._downloader.close()

        if clean_up_results == {}:
            DatabaseManager.clean_up()
            return super().closeEvent(event)

        response = self._close_confirm_dialog(clean_up_results)

        if response == qtw.QMessageBox.StandardButton.Yes:
            DatabaseManager.clean_up()
            return super().closeEvent(event)

        elif response == qtw.QMessageBox.StandardButton.No:
            main_signals.close_canceled_signal.emit()
            return event.ignore()

    # <PRIVATE METHODS>
    def _close_confirm_dialog(self, clean_up_results: dict):
        message = qtw.QMessageBox(
            qtw.QMessageBox.Icon.Warning,
            "Warning!",
            "There are ongoing operations, are you sure you want to quit?",
            qtw.QMessageBox.StandardButton.Yes | qtw.QMessageBox.StandardButton.No,
            self,
        )
        message.setInformativeText(
            "Force quitting can:\n"
            "    - corrupt your download file(s) and\n"
            "    - corrupt your database."
        )
        message.setDefaultButton(qtw.QMessageBox.StandardButton.No)

        detailed_text = ""
        for service_name, details in clean_up_results.items():
            detailed_text += f"{service_name}:"
            if details.get("download"):
                detailed_text += "\n    - Ongoing files download."

        message.setDetailedText(detailed_text)
        return message.exec()

    def _create_logger_messsage_box_slot(self, level: str) -> None:
        qtw.QMessageBox.critical(
            self, level, "An error occured, see the logs for details."
        )

    def _create_menu_bar(self):
        menu_bar = self.menuBar()
        menu = menu_bar.addMenu("&Options")
        menu.addAction(
            qtg.QIcon.fromTheme("preferences-system", qtg.QPixmap("assets:/cog.svg")),
            "&Preferences",
            self._menu_bar_action_preferences,
        )
        menu.setToolTip("Open preferences dialog")

    def _create_splitter_widget(self) -> None:
        self._splitter = Splitter(parent=self)
        self._splitter.setContentsMargins(5, 5, 5, 5)
        self._splitter.setHandleWidth(15)
        self._tab_widget = qtw.QTabWidget(parent=self)
        self._tab_widget.setFocusPolicy(qtc.Qt.FocusPolicy.NoFocus)
        self._tab_widget.currentChanged.connect(self._tab_widget_current_changed_slot)

    def _create_viewer_widget(self) -> None:
        self._viewer = Viewer(parent=self)

    def _menu_bar_action_preferences(self):
        preference_dialog = PreferencesDialog(self)
        preference_dialog.exec()

    # </PRIVATE METHODS>

    # <SLOTS>
    def _create_logs_icon_slot(self) -> None:
        if not self._tab_widget.currentIndex() == 2:
            self._tab_widget.setTabIcon(
                2,
                qtg.QIcon.fromTheme(
                    "dialog-warning", qtg.QIcon("assets:exclamation-circle.svg")
                ),
            )

    def _tab_widget_current_changed_slot(self, index: int) -> None:
        if index == 2:
            self._tab_widget.setTabIcon(2, qtg.QIcon())
        if index == 1:
            self._tab_widget.setMaximumWidth(450)
        else:
            self._tab_widget.setMaximumWidth(self.width() // 1.5)

    # </SLOTS>


def main() -> None:
    qtc.QCoreApplication.setOrganizationName("London69")
    qtc.QCoreApplication.setApplicationName("Library of H")
    qtc.QDir.addSearchPath("assets", "library_of_h/assets/")
    qtc.QThreadPool.globalInstance().setMaxThreadCount(4)

    app = qtw.QApplication(sys.argv)

    logger_widget = Logs()
    logger.set_logger_widget(logger_widget)
    database_manager = DatabaseManager.get_instance()
    if database_manager is None:
        return
    del database_manager

    LoH = LibraryOfH(logger_widget)
    return app.exec()
