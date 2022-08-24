from PySide6 import QtCore as qtc
from PySide6 import QtGui as qtg
from PySide6 import QtWidgets as qtw

from library_of_h.constants import SERVICES
from library_of_h.custom_widgets.combo_box import ComboBox
from library_of_h.custom_widgets.separation_lines import HSeperationLine
from library_of_h.downloader.output_table_view import ItemsTableView
from library_of_h.downloader.services.hitomi.main import Hitomi
from library_of_h.downloader.services.nhentai.main import nhentai
from library_of_h.signals_hub.signals_hub import downloader_signals


class Downloader(qtw.QWidget):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.setLayout(qtw.QVBoxLayout())
        self.setFocusPolicy(qtc.Qt.FocusPolicy.StrongFocus)

        self._services = {}

        self._items_table_view = ItemsTableView(parent=self)

        self._create_download_stack()
        self._create_service_combo_box()

        self.layout().addWidget(self._service_combo_box)
        self.layout().addWidget(self._download_stack)
        self.layout().addWidget(HSeperationLine())
        self.layout().addWidget(self._items_table_view)

        downloader_signals.download_session_began_signal.connect(
            self._download_session_began_slot
        )
        downloader_signals.download_session_finished_signal.connect(
            self._download_session_finished_slot
        )

    def close(self) -> dict:
        results = {}
        for service_name, service_widget in self._services.items():
            response = service_widget.close()
            if not response is None:
                results[service_name] = response
        return results

    def keyPressEvent(self, event: qtg.QKeyEvent):
        if event.key() == qtc.Qt.Key.Key_Escape:
            if qtw.QApplication.focusWidget() != self:
                self.setFocus()
                event.accept()
                return

        super().keyPressEvent(event)

    def _create_service_combo_box(self) -> None:
        self._service_combo_box = ComboBox(parent=self)
        self._service_combo_box.setMaximumHeight(30)
        self._service_combo_box.currentTextChanged.connect(
            self._service_combo_box_current_text_changed_slot
        )

        for service in SERVICES:
            self._service_combo_box.addItem(service)

    def _create_download_stack(self) -> None:
        self._download_stack = qtw.QStackedWidget(parent=self)
        self._download_stack.setMaximumHeight(195)
        for service_name, service_widget in zip(
            SERVICES,
            (
                Hitomi,
                nhentai,
            ),
        ):
            widget = service_widget(self._items_table_view, self)
            self._download_stack.addWidget(widget.gui)
            self._services[service_name] = widget

    def _service_combo_box_current_text_changed_slot(self, service_name: str) -> None:
        self._download_stack.setCurrentWidget(self._services[service_name].gui)

    def _download_session_began_slot(self) -> None:
        self._service_combo_box.setDisabled(True)
        self._download_stack.setDisabled(True)

    def _download_session_finished_slot(self) -> None:
        self._service_combo_box.setDisabled(False)
        self._download_stack.setDisabled(False)
