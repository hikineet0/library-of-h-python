from typing import Callable, Sequence, Union

from PySide6 import QtCore as qtc
from PySide6 import QtGui as qtg
from PySide6 import QtWidgets as qtw


class ConfirmationDialog(qtw.QDialog):

    _details_widget: qtw.QWidget
    _show_details_widget: Callable

    def __init__(
        self,
        parent: qtw.QWidget = None,
        icon: qtg.QIcon = None,
        title: str = "Confirmation dialog",
        text: str = "",
        buttons: qtw.QDialogButtonBox.StandardButtons = None,
        flags: qtc.Qt.WindowFlags = None,
    ):
        super().__init__(parent)

        self.setWindowTitle(title)
        self.setLayout(qtw.QVBoxLayout())
        self.resize(335, 75)
        self.setMaximumSize(335, 75)

        self.layout().addWidget(qtw.QLabel(text, self))

        if icon:
            self.setWindowIcon(icon)

        if buttons:
            self._button_box = qtw.QDialogButtonBox(self)
            self._button_box.setStandardButtons(buttons)
            self._button_box.accepted.connect(self.accept)
            self._button_box.rejected.connect(self.reject)
            self._button_box.clicked.connect(self._button_clicked_slot)
            self.layout().addWidget(self._button_box)

        if flags:
            self.setWindowFlags(
                qtc.Qt.WindowType.CustomizeWindowHint
                | qtc.Qt.WindowType.Dialog
                | qtc.Qt.WindowType.WindowCloseButtonHint
            )

    # <PRIVATE METHODS>
    def _hide_details_widget(self):
        self.layout().removeWidget(self._details_widget)
        self._details_widget.deleteLater()
        self.resize(335, 75)
        self.setMaximumSize(335, 75)

    def _show_details_list_widget(self):
        self._details_widget = qtw.QListWidget(self)
        self._details_widget.addItems(self._details)
        self._details_widget.setAlternatingRowColors(True)
        self.layout().addWidget(self._details_widget)
        self.setMaximumSize(16777215, 16777215)
        self.resize(335, 300)

    # </PRIVATE METHODS>

    def _show_details_text_edit(self):
        self._details_widget = qtw.QTextEdit(self)
        self._details_widget.setText(self._details)
        self._details_widget.setReadOnly(True)
        self.layout().addWidget(self._details_widget)
        self.setMaximumSize(16777215, 16777215)
        self.resize(335, 300)

    # </PRIVATE METHODS>

    # <PUBLIC METHODS>
    def set_default_button(self, button: qtw.QDialogButtonBox.StandardButton):
        self._button_box.button(button).setDefault(True)

    def set_details(self, details: Union[Sequence[str], str]):
        if isinstance(details, Sequence):
            self._show_details_widget = self._show_details_list_widget
        elif isinstance(details, str):
            self._show_details_widget = self._show_details_text_edit

        self._details = details
        show_details_button = qtw.QPushButton("Show Details...", self)
        self._button_box.addButton(
            show_details_button, qtw.QDialogButtonBox.ButtonRole.ActionRole
        )

    # </PUBLIC METHODS>

    # <SLOTS>
    def _button_clicked_slot(self, button: qtw.QAbstractButton):
        if "Show" in button.text():
            self._button_box.removeButton(button)
            button.deleteLater()
            hide_details_button = qtw.QPushButton("Hide Details...", self)
            self._button_box.addButton(
                hide_details_button, qtw.QDialogButtonBox.ButtonRole.ActionRole
            )
            self._show_details_widget()
        if "Hide" in button.text():
            self._button_box.removeButton(button)
            button.deleteLater()
            show_details_button = qtw.QPushButton("Show Details...", self)
            self._button_box.addButton(
                show_details_button, qtw.QDialogButtonBox.ButtonRole.ActionRole
            )
            self._hide_details_widget()

    # </SLOTS>
