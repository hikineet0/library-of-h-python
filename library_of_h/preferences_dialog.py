from collections import defaultdict
from typing import Literal, Union

from PySide6 import QtCore as qtc
from PySide6 import QtGui as qtg
from PySide6 import QtWidgets as qtw

from library_of_h.constants import SERVICES
from library_of_h.custom_widgets.combo_box import ComboBox
from library_of_h.preferences import Preferences


class DestinationFormatsDialogBase(qtw.QDialog):

    _TYPES = ()

    def __init__(self, preferences_copy: Preferences, *args, **kwargs):
        self._preferences_copy = preferences_copy
        self._current_preferences = preferences_copy.copy()
        self._inputs: dict[str, qtw.QLineEdit] = defaultdict(dict)

        subclass_name = type(self).__name__
        self._subclass_service_name = subclass_name.replace(
            "DestinationFormatsDialog", ""
        )

        super().__init__(*args, **kwargs)

        self.setWindowTitle(f"{self._subclass_service_name} destination formats")
        self.setLayout(qtw.QGridLayout())

        self._inputs_widget = qtw.QWidget(self)
        self._inputs_widget.setLayout(qtw.QFormLayout())
        self._inputs_widget.layout().setSpacing(10)

        self._inputs_scroll_area = qtw.QScrollArea(self)
        self._inputs_scroll_area.setWidgetResizable(True)
        self._inputs_scroll_area.setWidget(self._inputs_widget)

        self._create_inputs()
        self._create_buttons()

        self._populate()

        self.setMaximumHeight((len(self._inputs) * 25) + (len(self._inputs) * 10) + 80)

        self.layout().addWidget(self._inputs_scroll_area, 0, 0, 1, 4)
        self.layout().addWidget(self._button_box, 1, 1, 1, 1)

    def accept(self):
        format_: str
        input_: dict
        key: str
        line_edit: qtw.QLineEdit
        for type_, line_edit in self._inputs.items():
            self._preferences_copy[
                "download_preferences",
                "destination_formats",
                self._subclass_service_name,
                type_,
            ] = line_edit.text()
        return super().accept()

    def _create_buttons(self):
        restore_defaults = qtw.QPushButton("&Restore Defaults")
        self._button_box = qtw.QDialogButtonBox(
            qtw.QDialogButtonBox.StandardButton.Ok
            | qtw.QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.addButton(
            restore_defaults, qtw.QDialogButtonBox.ButtonRole.ResetRole
        )
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)
        self._button_box.clicked.connect(self._dialog_button_clicked_slot)

        self.layout().addWidget(self._button_box, 1, 2, 1, 1)

    def _create_inputs(self):
        for type_ in self._TYPES:
            destination_format_line_edit = qtw.QLineEdit()
            self._inputs[type_] = destination_format_line_edit
            self._inputs_widget.layout().addRow(
                f"{type_}:", destination_format_line_edit
            )

    def _populate(self, mode: Union[Literal[""], Literal["default"]] = ""):
        """
        Populates the empty user input areas with current/default preferences.

        Parameters
        -----------
            mode (
                Union[
                    Literal['']:
                        Populates with current user preferences.
                    Literal["default"]:
                        Populates with default user preferences.
                ]
            )
        """
        if mode == "default":
            mode = (mode,)
        else:
            mode = ()

        type_: str
        input_: dict
        key: str
        line_edit: qtw.QLineEdit
        for type_, line_edit in self._inputs.items():
            line_edit.setText(
                self._preferences_copy[
                    (
                        *mode,
                        "download_preferences",
                        "destination_formats",
                        self._subclass_service_name,
                        type_,
                    )
                ]
            )

    def _dialog_button_clicked_slot(self, button: qtw.QPushButton):
        if button.text() == "&Restore Defaults":
            self._populate("default")


class HitomiDestinationFormatsDialog(DestinationFormatsDialogBase):
    _TYPES = (
        "Artist(s)",
        "Character(s)",
        "Gallery ID(s)",
        "Group(s)",
        "Series(s)",
        "Type(s)",
        "Tag(s)",
    )


class nhentaiDestinationFormatsDialog(DestinationFormatsDialogBase):
    _TYPES = (
        "Artist(s)",
        "Character(s)",
        "Gallery ID(s)",
        "Group(s)",
        "Parody(s)",
        "Tag(s)",
    )


class PreferencesDialog(qtw.QDialog):
    def __init__(self, *args, **kwargs):
        self._preferences = Preferences.get_instance()
        self._preferences_copy = self._preferences.copy()

        super().__init__(*args, **kwargs)
        self.setLayout(qtw.QGridLayout())
        self.setMaximumHeight(347)
        self.setWindowTitle("Preferences")
        self.setWindowIcon(
            qtg.QIcon.fromTheme("preferences-system", qtg.QPixmap("assets:/cog.svg"))
        )

        self.setWindowFlags(
            qtc.Qt.WindowType.CustomizeWindowHint
            | qtc.Qt.WindowType.Dialog
            | qtc.Qt.WindowType.WindowCloseButtonHint
        )

        self._preferences_widget = qtw.QWidget()
        self._preferences_widget.setLayout(qtw.QVBoxLayout())
        self._preferences_widget.setMaximumHeight(213 + 84)

        self._preferences_scroll_area = qtw.QScrollArea(self)
        self._preferences_scroll_area.setWidgetResizable(True)
        self._preferences_scroll_area.setWidget(self._preferences_widget)

        self._create_explorer_preferences()
        self._create_database_preferences()
        self._create_downloader_preferences()
        self._create_buttons()

        self._populate()

        self._preferences_widget.layout().addWidget(self._browser_group_box)
        self._preferences_widget.layout().addWidget(self._database_group_box)
        self._preferences_widget.layout().addWidget(self._downloader_group_box)

        self.layout().addWidget(self._preferences_scroll_area, 0, 0, 1, 4)
        self.layout().addWidget(self._button_box, 1, 1, 1, 1)

    def accept(self):
        self._preferences_copy[
            "explorer_preferences", "delete_db_record_if_not_in_disk"
        ] = (
            self._browser_db_and_disk_discrepancy_combobox.currentText()
            == "Delete database record"
        )
        self._preferences_copy[
            "database_preferences", "location"
        ] = self._database_location_line_edit.text()
        self._preferences_copy[
            "download_preferences", "overwrite"
        ] = self._downloader_overwrite_check_box.isChecked()

        if self._preferences != self._preferences_copy:
            self._preferences_copy.get_difference().save()

        return super().accept()

    def _create_buttons(self):
        restore_defaults = qtw.QPushButton("&Restore Defaults")
        self._button_box = qtw.QDialogButtonBox(
            qtw.QDialogButtonBox.StandardButton.Ok
            | qtw.QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.addButton(
            restore_defaults, qtw.QDialogButtonBox.ButtonRole.ResetRole
        )
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)
        self._button_box.clicked.connect(self._dialog_button_clicked_slot)

    def _create_explorer_preferences(self):
        self._browser_group_box = qtw.QGroupBox("Browser preferences", self)
        self._browser_group_box.setMaximumHeight(84)
        self._browser_group_box.setLayout(qtw.QFormLayout())

        self._browser_db_and_disk_discrepancy_label = qtw.QLabel(
            "If gallery exists in database but not on disk:"
        )
        self._browser_db_and_disk_discrepancy_combobox = qtw.QComboBox(self)
        self._browser_db_and_disk_discrepancy_combobox.addItems(
            ["Do nothing", "Delete database record"]
        )
        self._browser_group_box.layout().addRow(
            self._browser_db_and_disk_discrepancy_label,
            self._browser_db_and_disk_discrepancy_combobox,
        )

    def _create_database_preferences(self):
        self._database_group_box = qtw.QGroupBox("Database preferences", self)
        self._database_group_box.setMaximumHeight(84)
        self._database_group_box.setLayout(qtw.QFormLayout())

        self._database_location_widget = qtw.QWidget()
        self._database_location_widget.setLayout(qtw.QGridLayout())

        self._database_location_label = qtw.QLabel("Location:")
        self._database_location_line_edit = qtw.QLineEdit(self)
        self._database_location_dialog_button = qtw.QPushButton("...", self)
        self._database_location_dialog_button.setFocusPolicy(
            qtc.Qt.FocusPolicy.TabFocus
        )

        self._database_location_dialog_button.clicked.connect(
            self._database_location_dialog_button_clicked_slot
        )

        self._database_location_dialog_button.setFixedSize(23, 23)

        self._database_location_widget.layout().addWidget(
            self._database_location_label, 0, 0, 1, 1
        )
        self._database_location_widget.layout().addWidget(
            self._database_location_line_edit, 0, 1, 1, 1
        )
        self._database_location_widget.layout().addWidget(
            self._database_location_dialog_button, 0, 2, 1, 1
        )

        self._database_group_box.layout().addRow(self._database_location_widget)

    def _create_downloader_preferences(self):
        self._downloader_group_box = qtw.QGroupBox("Downloader preferences", self)
        self._downloader_group_box.setMaximumHeight(106)
        self._downloader_group_box.setLayout(qtw.QFormLayout())

        self._downloader_overwrite_check_box = qtw.QCheckBox(self)

        self._downloader_overwrite_label = qtw.QLabel("Overwrite", self)
        self._downloader_overwrite_label.mousePressEvent = (
            lambda event: self._downloader_overwrite_check_box.setChecked(
                not self._downloader_overwrite_check_box.isChecked()
            )
        )

        self._downloader_destination_formats_widget = qtw.QWidget()
        self._downloader_destination_formats_widget.setLayout(qtw.QGridLayout())

        self._downloader_destination_formats_label = qtw.QLabel("Destination formats:")
        self._downloader_destination_formats_label.setFixedSize(134, 24)

        self._downloader_destination_formats_combobox = ComboBox(self)
        self._downloader_destination_formats_combobox.setFixedHeight(24)
        for service in SERVICES:
            self._downloader_destination_formats_combobox.addItem(service)

        self._downloader_destination_formats_button = qtw.QPushButton("View/Edit", self)
        self._downloader_destination_formats_button.setFocusPolicy(
            qtc.Qt.FocusPolicy.TabFocus
        )
        self._downloader_destination_formats_button.setFixedSize(80, 24)
        self._downloader_destination_formats_button.clicked.connect(
            self._downloader_destination_formats_button_clicked_slot
        )

        self._downloader_destination_formats_widget.layout().addWidget(
            self._downloader_destination_formats_label, 0, 0, 1, 1
        )
        self._downloader_destination_formats_widget.layout().addWidget(
            self._downloader_destination_formats_combobox, 0, 1, 1, 1
        )
        self._downloader_destination_formats_widget.layout().addWidget(
            self._downloader_destination_formats_button, 0, 2, 1, 1
        )

        self._downloader_group_box.layout().addRow(
            self._downloader_overwrite_check_box, self._downloader_overwrite_label
        )
        self._downloader_group_box.layout().addRow(
            self._downloader_destination_formats_widget
        )

    def _populate(self, mode: Union[Literal[""], Literal["default"]] = ""):
        """
        Populates the empty user input areas with current/default preferences.

        Parameters
        -----------
            mode (
                Union[
                    Literal['']:
                        Populates with current user preferences.
                    Literal["default"]:
                        Populates with default user preferences.
                ]
            )
        """
        if mode == "default":
            mode = (mode,)
        else:
            mode = ()

        self._browser_db_and_disk_discrepancy_combobox.setCurrentText(
            ("Do nothing", "Delete database record")[
                self._preferences_copy[
                    (*mode, "explorer_preferences", "delete_db_record_if_not_in_disk")
                ]
            ]
        )

        self._database_location_line_edit.setText(
            self._preferences_copy[(*mode, "database_preferences", "location")]
        )
        self._downloader_overwrite_check_box.setChecked(
            self._preferences_copy[(*mode, "download_preferences", "overwrite")]
        )

    def _database_location_dialog_button_clicked_slot(self) -> None:
        self._database_location_line_edit.setText(
            qtw.QFileDialog.getExistingDirectory(
                parent=self,
                caption="Select a directory",
                dir="",
                options=qtw.QFileDialog.Option.ShowDirsOnly,
            )
        )

    def _downloader_destination_formats_button_clicked_slot(self):
        service = self._downloader_destination_formats_combobox.currentText()
        dialog: qtw.QDialog = globals()[service + "DestinationFormatsDialog"](
            self._preferences_copy, parent=self
        )
        resp = dialog.exec()

    def _dialog_button_clicked_slot(self, button: qtw.QPushButton):
        if button.text() == "&Restore Defaults":
            self._populate("default")
