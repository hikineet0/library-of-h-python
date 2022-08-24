from __future__ import annotations

from PySide6 import QtCore as qtc
from PySide6 import QtWidgets as qtw

from library_of_h.custom_widgets.combo_box import ComboBox


class GUIBase(qtw.QGroupBox):

    _DOWNLOAD_TYPES: tuple
    _ORDER_BY: tuple
    _TOP_WIDGETS: tuple
    _BOTTOM_WIDGETS: tuple

    download_button_clicked_signal = qtc.Signal(str, str, str)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setLayout(qtw.QHBoxLayout())
        self.layout().setContentsMargins(5, 5, 5, 5)
        self._create_download_tab()

    def _create_download_tab(self) -> None:
        self._download_widget = qtw.QWidget(self)
        self._download_widget.setLayout(qtw.QGridLayout(self._download_widget))

        for attr in self._TOP_WIDGETS:
            getattr(self, f"_create_{attr}")()

        for attr in self._BOTTOM_WIDGETS:
            getattr(self, f"_create_{attr}")()

        self._download_button = qtw.QPushButton("Download", self)
        self._download_button.setEnabled(False)
        self._download_widget.layout().addWidget(
            self._download_button, self._download_widget.layout().rowCount(), 0, 1, 3
        )
        self._download_button.clicked.connect(self._download_button_clicked_slot)

        self.layout().addWidget(self._download_widget)

    def _create_download(self) -> None:
        row = self._download_widget.layout().rowCount()
        self._download_line_edit = qtw.QLineEdit(self._download_widget)
        self._download_widget.layout().addWidget(
            qtw.QLabel("Enter items:"), row, 0, 1, 1
        )
        self._download_widget.layout().addWidget(self._download_line_edit, row, 1, 1, 2)

        self._download_line_edit.textEdited.connect(
            self._download_line_edit_text_edited_slot
        )
        self._download_line_edit.returnPressed.connect(
            self._download_button_clicked_slot
        )

    def _create_file_download(self) -> None:
        row = self._download_widget.layout().rowCount()
        self._file_download_line_edit = qtw.QLineEdit(self._download_widget)
        self._file_download_dialog_button = qtw.QPushButton(
            "...", self._download_widget
        )
        self._file_download_dialog_button.setFixedWidth(25)
        self._download_widget.layout().addWidget(
            qtw.QLabel("Items from file:"), row, 0, 1, 1
        )
        self._download_widget.layout().addWidget(
            self._file_download_line_edit, row, 1, 1, 1
        )
        self._download_widget.layout().addWidget(
            self._file_download_dialog_button, row, 2, 1, 1
        )

        self._file_download_line_edit.textChanged.connect(
            self._file_download_line_edit_text_changed_slot
        )
        self._file_download_dialog_button.clicked.connect(
            self._file_download_dialog_button_clicked_slot
        )
        self._file_download_line_edit.returnPressed.connect(
            self._download_button_clicked_slot
        )

    def _create_download_type_combo_box(self) -> None:
        row = self._download_widget.layout().rowCount()
        self._download_type_combo_box = ComboBox()
        self._download_type_combo_box.setMaximumWidth(150)
        for download_type in self._DOWNLOAD_TYPES:
            self._download_type_combo_box.addItem(download_type)
        self._download_widget.layout().addWidget(
            qtw.QLabel("Download type:"), row, 0, 1, 1
        )
        self._download_widget.layout().addWidget(
            self._download_type_combo_box, row, 1, 1, 1
        )

        self._download_type_combo_box.currentTextChanged.connect(
            self._download_type_combo_box_current_text_changed
        )

    def _create_order_by_combo_box(self) -> None:
        row = self._download_widget.layout().rowCount()
        self._order_by_combo_box = ComboBox()
        self._order_by_combo_box.setMaximumWidth(150)
        for order_by in self._ORDER_BY:
            self._order_by_combo_box.addItem(order_by)
        self._download_widget.layout().addWidget(qtw.QLabel("Order by:"), row, 0, 1, 1)
        self._download_widget.layout().addWidget(self._order_by_combo_box, row, 1, 1, 1)

    # SLOTS
    @qtc.Slot(str)
    def _file_download_line_edit_text_changed_slot(self, text: str) -> None:
        if text != "":
            self._download_button.setEnabled(True)
            self._download_line_edit.setEnabled(False)
            if self._download_type_combo_box.itemText(0) != "All":
                self._download_type_combo_box.insertItem(0, "All")
        else:
            self._download_button.setEnabled(False)
            self._download_line_edit.setEnabled(True)
            if self._download_type_combo_box.itemText(0) == "All":
                self._download_type_combo_box.removeItem(0)

    @qtc.Slot(str)
    def _download_line_edit_text_edited_slot(self, text: str) -> None:
        if text == "":
            self._download_button.setEnabled(False)
            self._file_download_dialog_button.setEnabled(True)
            self._file_download_line_edit.setEnabled(True)
        else:
            self._download_button.setEnabled(True)
            self._file_download_dialog_button.setEnabled(False)
            self._file_download_line_edit.setEnabled(False)

    @qtc.Slot(str)
    def _download_type_combo_box_current_text_changed(self, text: str) -> None:
        if text == "Gallery ID(s)":
            self._order_by_combo_box.setEnabled(False)
        else:
            self._order_by_combo_box.setEnabled(True)

    @qtc.Slot()
    def _file_download_dialog_button_clicked_slot(self) -> None:
        self._file_download_line_edit.setText(
            qtw.QFileDialog.getOpenFileName(
                parent=self._download_widget,
                caption="Select Items List",
                filter="Items List Files (*.txt *.lst)",
            )[0]
        )

    @qtc.Slot()
    def _download_button_clicked_slot(self) -> None:
        if not self._download_button.isEnabled():
            return

        if self._file_download_line_edit.isEnabled():
            self._parse_file()
        elif self._download_line_edit.isEnabled():
            items = self._download_line_edit.text()
            download_type = self._download_type_combo_box.currentText()
            order_by = self._order_by_combo_box.currentText()

        self.download_button_clicked_signal.emit(
            items,
            download_type,
            order_by,
        )
