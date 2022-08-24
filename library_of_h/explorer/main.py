import math
from typing import Optional

from PySide6 import QtCore as qtc
from PySide6 import QtGui as qtg
from PySide6 import QtSql
from PySide6 import QtWidgets as qtw

from library_of_h.custom_widgets.confirm_dialog import ConfirmationDialog
from library_of_h.database_manager.main import DatabaseManager
from library_of_h.explorer.browser import ListView
from library_of_h.explorer.constants import (ACTION_GROUP_MAPPING,
                                             BROWSER_IMAGES_LIMIT,
                                             DESCRIPTION_OBJECT_ROLE)
from library_of_h.explorer.filter import Filter
from library_of_h.explorer.workers.create_browser_item import \
    CreateBrowserItemWorker
from library_of_h.explorer.workers.move_to_trash import MoveToTrashWorker
from library_of_h.logger import ExplorerSubType, MainType, get_logger
from library_of_h.preferences import Preferences


class Explorer(qtw.QMainWindow):

    __current_page_items_range: tuple[int, int] = (0, 0)
    _range: tuple[int, int] = (0, 0)
    __current_page_number: int = 1
    __total_items: int = 0
    __total_number_of_pages: int = 0

    _current_query: dict
    _trashing: bool = False  # Indicates whether there's an ongoing move to trash.
    _refreshing: bool = False  # Indicates whether there's an ongoing view refresh.
    _items_list_view: ListView

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._current_query = {
            "user_query": "",
            "offset": 0,
            "limit": BROWSER_IMAGES_LIMIT,
            "sort_by": "accuracy",
            "sort_order": "ASC",
        }

        self._logger = get_logger(
            main_type=MainType.EXPLORER, sub_types=[ExplorerSubType.BASE]
        )

        self._main_widget = qtw.QWidget(self)
        self._main_widget.setLayout(qtw.QGridLayout())
        self._main_widget.layout().setContentsMargins(0, 0, 0, 10)

        self._database_manager = DatabaseManager.get_instance()
        self._create_browser_item_worker = CreateBrowserItemWorker(parent=self)

        self._create_menu_bar()
        self._create_numbers_widgets()
        self._create_stacked_widget()
        self._create_toolbar()

        self._filter_widget.filter_signal.connect(self._filter)

        self._main_widget.layout().addWidget(self._stacked_widget, 0, 0, 1, 12)
        self._main_widget.layout().addWidget(self._current_items_label, 1, 0, 1, 1)
        self._main_widget.layout().addWidget(self._previous_page_button, 1, 4, 1, 1)
        self._main_widget.layout().addWidget(self._page_number_line_edit, 1, 5, 1, 1)
        self._main_widget.layout().addWidget(self._page_number_label, 1, 6, 1, 1)
        self._main_widget.layout().addWidget(self._next_page_button, 1, 7, 1, 1)
        self._main_widget.layout().addWidget(self._total_items_label, 1, 11, 1, 1)

        self.setFocusPolicy(qtc.Qt.FocusPolicy.StrongFocus)
        self.setCentralWidget(self._main_widget)

        self._create_browser_item_worker.item_created_signal.connect(
            self._add_item_slot
        )
        self._create_browser_item_worker.browser_item_batch_finished_signal.connect(
            self._browser_item_batch_finished_slot
        )
        self._create_browser_item_worker.item_not_found_signal.connect(
            self._item_not_found_slot
        )

        self._initialize()

    # <PARENT OVERRIDES>
    def keyPressEvent(self, event: qtg.QKeyEvent):
        if event.key() == qtc.Qt.Key.Key_F and event.modifiers() & qtc.Qt.Modifier.CTRL:
            self._filter_widget.setFocus()
            event.accept()
            return

        if event.key() == qtc.Qt.Key.Key_Escape:
            if len(self._list_view.selectionModel().selectedIndexes()):
                self._list_view.selectionModel().clearSelection()
                event.accept()
                return

        if event.key() == qtc.Qt.Key.Key_Delete:
            if not self._trashing:
                self._trash()
                event.accept()
                return

        if (
            event.key() == qtc.Qt.Key.Key_F5
            or event.key() == qtc.Qt.Key.Key_R
            and event.modifiers() & qtc.Qt.Modifier.CTRL
        ):
            self._refresh_browser(self._current_page_number)
            event.accept()
            return

        if event.key() == qtc.Qt.Key.Key_Left:
            if self._previous_page_button.isEnabled():
                self._previous_page_button_clicked_slot()
                event.accept()
                return

        if event.key() == qtc.Qt.Key.Key_Right:
            if self._next_page_button.isEnabled():
                self._next_page_button_clicked_slot()
                event.accept()
                return

        super().keyPressEvent(event)

    # </PARENT OVERRIDES>

    # <PROPERTIES>
    @property
    def _current_page_items_range(self) -> tuple[int, int]:
        return self.__current_page_items_range

    @_current_page_items_range.setter
    def _current_page_items_range(self, value: tuple[int, int]):
        self.__current_page_items_range = value
        self._current_items_label.setText(f"{value[0]} - {value[1]}")

    @property
    def _current_page_number(self) -> int:
        return self.__current_page_number

    @_current_page_number.setter
    def _current_page_number(self, current_page_number: int):
        current_page_number = (
            1
            if current_page_number < 1
            else self._total_number_of_pages
            if current_page_number > self._total_number_of_pages
            else current_page_number
        )
        self._page_number_line_edit.setText(str(current_page_number))
        self.__current_page_number = current_page_number
        if current_page_number <= 1:
            self._previous_page_button.setDisabled(True)
        else:
            self._previous_page_button.setDisabled(False)

        if current_page_number == self._total_number_of_pages:
            self._next_page_button.setDisabled(True)
        else:
            self._next_page_button.setDisabled(False)

    @property
    def _total_number_of_pages(self) -> int:
        return self.__total_number_of_pages

    @_total_number_of_pages.setter
    def _total_number_of_pages(self, value: int):
        self.__total_number_of_pages = value
        self._page_number_label.setText(str(value))

    @property
    def _total_items(self) -> int:
        return self.__total_items

    @_total_items.setter
    def _total_items(self, value: int):
        self.__total_items = value
        self._total_items_label.setText(str(value))

    # </PROPERTIES>

    # <PRIVATE METHODS>
    def _batch_started(self):
        """Called when starting a database get to populate the view."""
        self._previous_page_button.setDisabled(True)
        self._page_number_line_edit.setDisabled(True)
        self._next_page_button.setDisabled(True)

    def _change_page(self):
        self._batch_started()
        self._list_view.model().removeRows(0, self._list_view.model().rowCount())
        self._current_query["offset"] = (
            self._current_page_number - 1
        ) * BROWSER_IMAGES_LIMIT
        if not self._database_manager.get(
            count=True,
            get_callback=self._create_items,
            count_callback=self._update_numbers,
            **self._current_query,
        ):
            self._show_bad_user_query()

    def _create_items(self, results: list[QtSql.QSqlRecord]) -> None:
        if not results:
            self._show_no_results()
            return
        self._create_browser_item_worker.prepare(results)
        qtc.QThreadPool.globalInstance().start(
            self._create_browser_item_worker.create_items
        )

    def _create_menu_bar(self):
        menu_bar = self.menuBar()
        menu_bar.setFocusPolicy(qtc.Qt.FocusPolicy.NoFocus)
        self._edit_menu = menu_bar.addMenu("&Edit")
        self._edit_menu.addAction(
            qtg.QIcon.fromTheme("user-trash", qtg.QPixmap("assets:/trash.svg")),
            "Move to &Trash",
            self._trash,
        )

        self._edit_menu.addSeparator()

        self._edit_menu.addAction(
            "&Select all items in page",
            qtg.QKeySequence(qtc.Qt.Modifier.CTRL | qtc.Qt.Key.Key_A),
            self._action_select_all_items_in_page_slot,
        )
        self._edit_menu.addAction(
            "Select all items in &result",
            qtg.QKeySequence(
                qtc.Qt.Modifier.CTRL | qtc.Qt.Modifier.SHIFT | qtc.Qt.Key.Key_A
            ),
            self._action_select_all_items_in_result_slot,
        )
        self._edit_menu.addAction(
            "&Inverse selection", self._action_inverse_selection_slot
        )

        self._view_menu = menu_bar.addMenu("&View")
        self._view_menu.addAction(
            qtg.QIcon.fromTheme("view-refresh", qtg.QPixmap("assets:/refresh.svg")),
            "&Refresh current page",
            qtg.QKeySequence(qtc.Qt.Modifier.CTRL | qtc.Qt.Key.Key_R),
            self._action_refresh_slot,
        )

        self._view_menu.addSeparator()

        self._sort_menu = self._view_menu.addMenu("&Sort")
        self._sort_by_action_group = qtg.QActionGroup(menu_bar)
        self._sort_by_action_group.setExclusive(True)
        self._sort_by_actions = [
            qtg.QAction("By &Title"),
            qtg.QAction("By &Japanese Title"),
            qtg.QAction("By &Pages"),
            qtg.QAction("By &Size"),
            qtg.QAction("By &Upload Date"),
            qtg.QAction("By &Download Date"),
        ]
        for action in self._sort_by_actions:
            action.setCheckable(True)
            self._sort_by_action_group.addAction(action)
            self._sort_menu.addAction(action)
        self._sort_by_actions[4].setChecked(True)

        self._sort_menu.addSeparator()

        self._sort_order_action_group = qtg.QActionGroup(menu_bar)
        self._sort_order_action_group.setExclusive(True)
        self._sort_order_actions = [
            qtg.QAction("&Ascending"),
            qtg.QAction("D&escending"),
        ]
        for action in self._sort_order_actions:
            action.setCheckable(True)
            self._sort_order_action_group.addAction(action)
            self._sort_menu.addAction(action)
        self._sort_order_actions[0].setChecked(True)
        self._sort_menu.triggered.connect(self._action_sort_slot)

    def _create_stacked_widget(self) -> None:
        self._stacked_widget = qtw.QStackedWidget(self)

        self._no_results_widget = qtw.QLabel("No results.")
        self._searching_widget = qtw.QLabel("Searching...")
        self._bad_user_query = qtw.QLabel("Bad filter string.")
        self._list_view = ListView()

        self._stacked_widget.addWidget(self._list_view)
        self._stacked_widget.addWidget(self._no_results_widget)
        self._stacked_widget.addWidget(self._searching_widget)
        self._stacked_widget.addWidget(self._bad_user_query)
        self._stacked_widget.setCurrentIndex(0)

        self._list_view.context_menu_move_to_trash_signal.connect(self._trash)

    def _create_toolbar(self) -> None:
        self._toolbar = qtw.QToolBar(self)
        self._toolbar.setObjectName("explorer_toolbar")
        self._toolbar.setStyleSheet("#explorer_toolbar {border: none;}")
        self._toolbar.setMovable(False)

        self._filter_widget = Filter()
        self._toolbar.addWidget(self._filter_widget)

        # spacer_widget = qtw.QWidget(self._toolbar)
        # spacer_widget.setSizePolicy(
        #     qtw.QSizePolicy.Policy.Expanding, qtw.QSizePolicy.Preferred
        # )
        # self._toolbar.addWidget(spacer_widget)

        self._refresh_action = qtg.QAction(
            qtg.QIcon.fromTheme("view-refresh", qtg.QPixmap("assets:/refresh.svg")),
            "",
            self._toolbar,
        )
        self._refresh_action.triggered.connect(self._action_refresh_slot)
        self._toolbar.addAction(self._refresh_action)
        self.addToolBar(self._toolbar)

    def _create_trash_progress_dialog(self, maximum: int):
        self._trash_progress_dialog = qtw.QProgressDialog(
            "", "Cancel", 0, maximum, self, qtc.Qt.WindowType.Dialog
        )
        self._trash_progress_dialog.setWindowTitle("Deleting items")

    def _create_numbers_widgets(self):
        self._current_items_label = qtw.QLabel("[0 - 0]", parent=self)
        self._current_items_label.setAlignment(qtc.Qt.AlignmentFlag.AlignCenter)

        self._previous_page_button = qtw.QPushButton(
            qtg.QIcon.fromTheme("go-previous", qtg.QPixmap("assets:/previous.svg")),
            "Previous",
            parent=self,
        )
        self._previous_page_button.setFocusPolicy(qtc.Qt.FocusPolicy.NoFocus)
        self._previous_page_button.clicked.connect(
            self._previous_page_button_clicked_slot
        )

        self._page_number_line_edit = qtw.QLineEdit("1", parent=self)
        self._page_number_line_edit.setFocusPolicy(qtc.Qt.FocusPolicy.ClickFocus)
        self._page_number_line_edit.textChanged.connect(
            self._page_number_line_edit_text_changed_slot
        )
        self._page_number_line_edit.returnPressed.connect(
            self._page_number_line_edit_return_pressed_slot
        )
        self._page_number_line_edit.setFixedSize(44, 22)
        self._page_number_line_edit.setAlignment(qtc.Qt.AlignmentFlag.AlignCenter)

        self._page_number_label = qtw.QLabel("1", parent=self)
        self._page_number_label.setAlignment(qtc.Qt.AlignmentFlag.AlignCenter)
        self._page_number_label.setMaximumWidth(44)

        self._next_page_button = qtw.QPushButton(
            qtg.QIcon.fromTheme("go-next", qtg.QPixmap("assets:/next.svg")),
            "Next",
            parent=self,
        )
        self._next_page_button.setFocusPolicy(qtc.Qt.FocusPolicy.NoFocus)
        self._next_page_button.setLayoutDirection(qtc.Qt.LayoutDirection.RightToLeft)
        self._next_page_button.clicked.connect(self._next_page_button_clicked_slot)

        self._total_items_label = qtw.QLabel("0", parent=self)
        self._total_items_label.setAlignment(qtc.Qt.AlignmentFlag.AlignCenter)

    def _filter(self, user_query: str):
        self._current_query["user_query"] = user_query
        self._current_query["offset"] = 0

        self._stacked_widget.setCurrentIndex(2)
        self._batch_started()
        self._list_view.model().removeRows(0, self._list_view.model().rowCount())
        if not self._database_manager.get(
            count=True,
            get_callback=self._create_items,
            count_callback=self._update_numbers,
            **self._current_query,
        ):
            self._show_bad_user_query()

    def _initialize(self):
        self._batch_started()
        self._stacked_widget.setCurrentIndex(2)
        if not self._database_manager.get(
            count=True,
            get_callback=self._create_items,
            count_callback=self._update_numbers,
            **self._current_query,
        ):
            self._show_bad_user_query()

    def _refresh_browser(self, page_number: int):
        if self._refreshing:
            return

        self._refreshing = True
        self._current_query["offset"] = (page_number - 1) * BROWSER_IMAGES_LIMIT
        self._current_page_number = page_number

        self._stacked_widget.setCurrentIndex(2)
        self._batch_started()
        self._list_view.model().removeRows(0, self._list_view.model().rowCount())
        if not self._database_manager.get(
            count=True,
            get_callback=self._create_items,
            count_callback=self._update_numbers,
            **self._current_query,
        ):
            self._show_bad_user_query()

    def _show_bad_user_query(self):
        self._stacked_widget.setCurrentIndex(3)
        self._total_items = 0
        self._total_number_of_pages = 0
        self._current_page_items_range = (0, 0)
        self._current_page_number = 0

    def _show_no_results(self):
        self._stacked_widget.setCurrentIndex(1)
        self._total_items = 0
        self._total_number_of_pages = 0
        self._current_page_items_range = (0, 0)
        self._current_page_number = 0

    def _update_numbers(self, result: list[QtSql.QSqlRecord]):
        total_rows = result[0].value("total_rows")
        from_ = ((self._current_page_number - 1) * BROWSER_IMAGES_LIMIT) + 1
        to = min(total_rows, from_ + BROWSER_IMAGES_LIMIT - 1)
        self._total_items = total_rows
        self._total_number_of_pages = math.ceil(total_rows / BROWSER_IMAGES_LIMIT)
        self._current_page_items_range = (from_, to)

    # </PRIVATE METHODS>

    # <SLOTS>
    def _add_item_slot(self, index: int, thumbnail: qtg.QImage, description_dict: dict):
        if self._stacked_widget.currentIndex() != 0:
            self._stacked_widget.setCurrentIndex(0)
        model_index = self._list_view.model().createIndex(index, 0)
        self._list_view.model().setData(
            model_index, thumbnail, qtc.Qt.ItemDataRole.DecorationRole
        )
        self._list_view.model().setData(
            model_index, description_dict, qtc.Qt.ItemDataRole.DisplayRole
        )
        self._list_view.update(model_index)

    def _browser_item_batch_finished_slot(self):
        self._refreshing = False
        self._page_number_line_edit.setDisabled(False)
        # Calling the getter property to disable/enable buttons based on page
        # number.
        self._current_page_number = self._current_page_number

    def _trash(self):
        if not len(self._list_view.selectionModel().selectedIndexes()):
            qtw.QMessageBox(
                qtw.QMessageBox.Icon.Information,
                "No items selected",
                "No items selected to move to trash.",
                qtw.QMessageBox.StandardButton.Ok,
            ).exec()
            return

        self._trashing = True
        selected_length = len(self._list_view.selectionModel().selectedIndexes())
        message = ConfirmationDialog(
            parent=self,
            icon=qtg.QIcon.fromTheme(
                "dialog-question", qtg.QPixmap("assets:/question.svg")
            ),
            title="Move selection to trash?",
            text=f"Are you sure you want to move {selected_length} {('item', 'items')[selected_length > 1]} to trash?",
            buttons=qtw.QDialogButtonBox.StandardButton.Yes | qtw.QDialogButtonBox.No,
        )

        locations = tuple(
            index.data(DESCRIPTION_OBJECT_ROLE).location
            for index in self._list_view.selectionModel().selectedIndexes()
        )
        message.set_default_button(qtw.QDialogButtonBox.StandardButton.No)
        message.set_details(locations)
        response = message.exec()
        if response:
            self._create_trash_progress_dialog(0)
            move_to_trash_worker = MoveToTrashWorker(
                parent=self._trash_progress_dialog, directory_paths=locations
            )
            move_to_trash_worker.item_trash_started_signal.connect(
                self._item_trash_started_slot
            )
            move_to_trash_worker.item_trash_finished_signal.connect(
                self._item_trash_finished_slot
            )
            move_to_trash_worker.trash_batch_finished_signal.connect(
                self._trash_batch_finished_slot
            )

            qtc.QThreadPool.globalInstance().start(move_to_trash_worker.move_to_trash)
        else:
            self._trashing = False

    def _item_not_found_slot(self, item_not_founds: list[tuple[int, str]]):
        preferences_instance = Preferences.get_instance()
        for gallery_database_id, location in item_not_founds:
            if preferences_instance[
                "explorer_preferences", "delete_db_record_if_not_in_disk"
            ]:
                # If the user wants to delete invalid database records
                self._database_manager.delete(gallery_database_id=gallery_database_id)
            self._logger.warning(
                "[Location Not Found] Location from database does not exist: "
                f'DATABASE ID={gallery_database_id}, LOCATION="{location}"'
            )

        if preferences_instance[
            "explorer_preferences", "delete_db_record_if_not_in_disk"
        ]:
            # If the user wanted to delete invalid database records
            if (self._total_items - len(item_not_founds)) % 25 == 0:
                callback = lambda: self._refresh_browser(self._current_page_number - 1)
            else:
                callback = lambda: self._refresh_browser(self._current_page_number)

            # Delay to let the deletion complete before refreshing the browser.Small
            # (infinitesimal?) chance it will fail, but doesn't matter. Failure here
            # refers to the timer timing out before deletion completed, in which
            # case the numbers shown in the numbers widget will be wrong and some
            # non-existent items will be listed in the view. Will be fixed with
            # another refresh.
            qtc.QTimer.singleShot(500, callback)

    def _item_trash_finished_slot(self, location: str):
        self._database_manager.delete(location=location)

    def _item_trash_started_slot(self, location: str):
        self._trash_progress_dialog.setLabelText(location)

    def _next_page_button_clicked_slot(self):
        self._current_page_number += 1
        self._change_page()

    def _page_number_line_edit_return_pressed_slot(self):
        text = self._page_number_line_edit.text()
        if not text:
            self._current_page_number = self._current_page_number
        else:
            self._current_page_number = int(text)
            self._change_page()

    def _page_number_line_edit_text_changed_slot(self, text: str):
        if not text:
            return
        if text[-1] not in "0123456789":
            self._page_number_line_edit.setText(text[:-1])

    def _previous_page_button_clicked_slot(self):
        self._current_page_number -= 1
        self._change_page()

    def _action_inverse_selection_slot(self):
        start = self._list_view.model().createIndex(0, 0)
        end = self._list_view.model().createIndex(self._list_view.model().rowCount(), 0)
        selection = qtc.QItemSelection(start, end)
        self._list_view.selectionModel().select(
            selection, qtc.QItemSelectionModel.Toggle
        )

    def _action_refresh_slot(self):
        self._refresh_browser(self._current_page_number)

    def _action_select_all_items_in_page_slot(self):
        self._list_view.selectAll()

    def _action_select_all_items_in_result_slot(self):
        pass

    def _action_sort_slot(self):
        sort_by = ACTION_GROUP_MAPPING[
            self._sort_by_action_group.checkedAction().text()
        ]
        sort_order = ACTION_GROUP_MAPPING[
            self._sort_order_action_group.checkedAction().text()
        ]
        self._current_query["sort_by"] = sort_by
        self._current_query["sort_order"] = sort_order
        self._filter(self._current_query["user_query"])

    def _selection_changed_slot(self):
        # Implement something for menu bar options.
        pass

    def _trash_batch_finished_slot(self, faulty_directories: list[Optional[str]]):
        rows_selected_for_deletion = self._list_view.selectionModel().selectedRows()
        successful_moves = len(rows_selected_for_deletion) - len(faulty_directories)
        dialog_text = f"Moved {successful_moves} {('item', 'items')[successful_moves != 1]} to trash."
        if (
            rows_selected_for_deletion
            and (self._total_items - len(rows_selected_for_deletion)) % 25 == 0
        ):
            self._current_page_number -= 1
        qtc.QTimer.singleShot(
            500, lambda: self._refresh_browser(self._current_page_number)
        )

        if faulty_directories:
            dialog_text += f"\nFailed to move {len(faulty_directories)} {('item', 'items')[len(faulty_directories) != 1]} to trash, see Logs for details."
            self._logger.error(
                "Problem moving the following items to the trash: "
                f"Path(s)={faulty_directories}".replace("'", '"')
            )

        message = qtw.QMessageBox(
            qtw.QMessageBox.Icon.Information,
            "Finished moving items to trash",
            dialog_text,
            qtw.QMessageBox.StandardButton.Ok,
            self,
        )
        message.show()
        self._trash_progress_dialog.deleteLater()
        self._trash_progress_dialog = None
        self._trashing = False

    # </SLOTS>
