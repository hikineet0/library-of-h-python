from __future__ import annotations

import datetime
import logging
import re
from typing import Generator, Union

from PySide6 import QtCore as qtc
from PySide6 import QtStateMachine as qsm
from PySide6 import QtWidgets as qtw

from library_of_h.database_manager.main import DatabaseManager
from library_of_h.downloader.base_classes.metadata import (FileMetadataBase,
                                                           GalleryMetadataBase)
from library_of_h.downloader.custom_sub_classes.download_files_model import \
    DownloadFilesModel
from library_of_h.downloader.custom_sub_classes.download_items_model import \
    DownloadItemsModel
from library_of_h.downloader.custom_sub_classes.state import State
from library_of_h.downloader.filter import Filter
from library_of_h.downloader.output_table_view import ItemsTableView
from library_of_h.downloader.services.hitomi.gui import HitomiGUI
from library_of_h.downloader.services.nhentai.gui import nhentaiGUI
from library_of_h.logger import (DownloaderServiceType, DownloaderSubType,
                                 MainType, get_logger)
from library_of_h.miscellaneous.functions import get_value_and_unit_from_Bytes
from library_of_h.preferences import Preferences
from library_of_h.signals_hub.signals_hub import (downloader_signals,
                                                  logger_signals, main_signals)


class ServiceBase(qtc.QObject):

    gui: GUIBase
    _filter: Filter
    _logger: logging.Logger
    _file_url_generator: Generator
    _download_files_model: DownloadFilesModel
    _download_items_model: DownloadItemsModel
    _current_working_gallery_metadata: GalleryMetadataBase
    _database_manager: DatabaseManager

    _session_initialized = qtc.Signal()

    def __init__(self, output_table_view: ItemsTableView, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        subclass_name: str = type(self).__name__
        subclass = HitomiGUI if subclass_name == "Hitomi" else nhentaiGUI
        self.gui = subclass(*args, **kwargs)
        self._logger = get_logger(
            main_type=MainType.DOWNLOADER,
            sub_types=[
                DownloaderSubType.BASE,
                getattr(DownloaderServiceType, subclass_name.upper()),
            ],
        )

        main_signals.close_canceled_signal.connect(self._close_canceled)

        self._total_download_time_elapsed_timer = qtc.QElapsedTimer()
        self._output_table_view = output_table_view

        self._setup_machine()

    def _setup_machine(self):
        self._machine = qsm.QStateMachine()

        logger_signals.halt_signal.connect(self._machine.stop)
        self._machine.stopped.connect(self._machine_stop_slot)

        self._s_idle = State()
        self._s_initialize = State()
        self._s_download = State()

        self._s_idle.setObjectName("idle_state")
        self._s_idle.assignProperty(self._machine, "state", 0)
        self._s_idle.addTransition(
            self.gui,
            "download_button_clicked_signal(QString, QString ,QString)",
            self._s_initialize,
        )

        self._s_initialize.setObjectName("initialize_state")
        self._s_initialize.assignProperty(self._machine, "state", 1)
        self._s_initialize.set_on_entry(self._initialize_session)
        self._s_initialize.addTransition(
            self,
            "_session_initialized()",
            self._s_download,
        )

        self._s_download.setObjectName("download_state")
        self._s_download.assignProperty(self._machine, "state", 2)
        self._s_download.set_on_entry(self._begin_session)

        self._machine.addState(self._s_idle)
        self._machine.addState(self._s_initialize)
        self._machine.addState(self._s_download)
        self._machine.setInitialState(self._s_idle)
        self._machine.start()

    def _initialize_session(self, *args, **kwargs) -> None:
        """
        Initializes session.

        Emits
        ------
            signals_hub.downloader_signals.download_session_began_signal:
                Signaling the beginning of the download session.
        """
        raise NotImplementedError

    # MISCELLANEOUS METHODS
    def _get_file_url(self, file: FileMetadataBase) -> str:
        """
        Creates a URL corresponding to `file`.
        """
        raise NotImplementedError

    def _get_next_image_file(self) -> Generator:
        """
        Generator that yields file URLs from `gallery_metadata.files`.
        """
        raise NotImplementedError

    def _pass_through_filter(
        self, gallery_metadata: GalleryMetadataBase
    ) -> Union[str, bool]:
        """
        Filters out (or not) the gallery based on user set filters.

        Returns
        --------
            Union[
                str:
                    Text describing why the gallery was filtered out.
                bool:
                    Returns `False` when gallery is not filtered out.
            ]
        """
        if (
            self._filter.languages_to_include
            and not gallery_metadata.language in self._filter.languages_to_include
        ):
            return "Language not match"
        if self._filter.tags_blacklist and any(
            tag in gallery_metadata.tags for tag in self._filter.tags_blacklist
        ):
            return "Tags blacklist match"
        if (
            self._filter.types_blacklist
            and gallery_metadata.type in self._filter.types_blacklist
        ):
            return "Types blacklist match"
        return False

    # BEGIN METHODS
    def _begin_session(self, *args, **kwargs) -> None:
        """
        Begin the download session.
        """
        self._logger.debug("Session began.")
        try:
            url_or_gallery_id = self._extractor.get_download_item_url(
                next(self._download_items_model).item_name
            )
        except StopIteration:
            pass
        else:
            self._output_dialog.show()
            self._begin_item_download(url_or_gallery_id)

    def _begin_item_download(self, *args, **kwargs) -> None:
        """
        Start download of the next item.
        """
        raise NotImplementedError

    def _begin_gallery_download(self, *args, **kwargs) -> None:
        """
        Begin the download of/from the first gallery of the current item.
        """
        raise NotImplementedError

    def _begin_file_download(self, *args, **kwargs) -> None:
        """
        Begin the download of/from the first file of the current gallery.
        """
        raise NotImplementedError

    # CONTINUE METHODS
    def _continue_item_download(self) -> None:
        try:
            url_or_gallery_id = self._extractor.get_download_item_url(
                next(self._download_items_model).item_name
            )
        except StopIteration:
            self._machine.stop()
        else:
            self._begin_item_download(url_or_gallery_id)

    def _continue_gallery_download(self) -> None:
        """
        Created to handle different kinds of "end" in gallery download separately,
        with "continue" (to the next gallery) being in common between them.
        """
        raise NotImplementedError

    def _gallery_filtered_out(self, gallery_id: str, info: str) -> None:
        self._session_summary["galleries filtered"] += 1
        self._logger.info(
            f"[{info}] " f"Gallery filtered out: GALLERY ID={gallery_id}."
        )
        self._continue_gallery_download()

    # END METHODS
    def _end_file_download(self) -> None:
        """
        Denotes the completion of one file in the current gallery.
        """
        self._session_summary["files downloaded"] += 1
        self._session_summary[
            "total download size"
        ] += self._download_files_model.get_current_data().file_size

        self._output_dialog.update_file_progress()
        try:
            url = next(self._file_url_generator)
        except StopIteration:
            # If no more file url in `self._file_url_generator`:
            self._end_gallery_download()
        else:
            # Else start downloading file:
            self._downloader.start_file_download(url)

    def _end_gallery_download(self) -> None:
        """
        Denotes the completion of one gallery in the current item.
        """
        self._logger.info(
            f"Finished gallery download: LOCATION={self._current_working_gallery_metadata.location}"
        )
        self._session_summary["galleries downloaded"] += 1
        self._database_manager.insert_into_database(
            self._current_working_gallery_metadata
        )
        self._continue_gallery_download()

    def _end_item_download(self) -> None:
        """
        Denotes the completion of one item in the current session.
        """
        self._logger.info(
            f'Finished item download: ITEM="{self._download_items_model.current().item_name}"'
        )
        self._session_summary["items completed"] += 1
        # Here because each item will have a new set of galleries.
        self._output_dialog.reset_gallery_progress_value()

        # self._output_dialog.remove_table_model()

        self._download_items_model.setData(
            index=self._download_items_model.get_current_index().status,
            value=1,
            for_="status",
        )  # Set current item as completed.
        self._continue_item_download()

    def _deinitialize_session(self):
        self._logger.debug("Deinitializing session.")

        if hasattr(self, "_extractor"):
            self._logger.debug("Deinitializing extractor.")
            self._extractor.disconnect(None, None, None)
            self._extractor.deleteLater()
            del self._extractor

        if hasattr(self, "_network_access_manager"):
            self._logger.debug("Deinitializing network access manager.")
            qtc.QObject.disconnect(self._network_access_manager, None, None, None)
            if hasattr(self._network_access_manager, "reply"):
                self._network_access_manager.abort()
                self._download_items_model.setData(
                    index=self._download_items_model.get_current_index().status,
                    value=-2,
                    for_="status",
                )  # Set remaining items as aborted.

            self._network_access_manager.deleteLater()
            del self._network_access_manager

        del self._database_manager

        if hasattr(self, "_downloader"):
            self._logger.debug("Deinitializing downloader.")
            qtc.QObject.disconnect(self._downloader, None, None, None)
            self._downloader.deleteLater()
            del self._downloader

        if hasattr(self, "_output_dialog"):
            # Don't need close before deleteLater()
            self._output_dialog.deleteLater()
            del self._output_dialog

        if hasattr(self, "_current_working_gallery_metadata"):
            del self._current_working_gallery_metadata

    def _show_session_summary(self):
        result = re.findall(
            "(\d+) days, (\d{,2}):(\d{,2}):(\d{,2})\.\d*",
            str(
                datetime.timedelta(
                    milliseconds=self._total_download_time_elapsed_timer.elapsed()
                )
            ),
        ) or re.findall(
            "(\d{,2}):(\d{,2}):(\d{,2})\.\d*",
            str(
                datetime.timedelta(
                    milliseconds=self._total_download_time_elapsed_timer.elapsed()
                )
            ),
        )
        result = ("0",) + result[0] if len(result[0]) == 3 else result[0]
        self._session_summary["total time taken"] = {
            key: int(value)
            for key, value in zip(["days", "hours", "minutes", "seconds"], result)
            if value != "0" and value != "00"
        }
        text = "Downloaded {} in {}:".format(
            " ".join(
                map(
                    str,
                    get_value_and_unit_from_Bytes(
                        self._session_summary["total download size"]
                    ),
                )
            ),
            " ".join(
                f"{value} {key}"
                for key, value in self._session_summary["total time taken"].items()
            ),
        )

        informative_text = (
            "{} items completed.\n".format(self._session_summary["items completed"])
            + "{} items invalid.\n".format(self._session_summary["items invalid"])
            + "{} galleries downloaded.\n".format(
                self._session_summary["galleries downloaded"]
            )
            + "{} galleries filtered out.\n".format(
                self._session_summary["galleries filtered"]
            )
            + "{} galleries already downloaded.\n".format(
                self._session_summary["galleries already downloaded"]
            )
            + "{} files downloaded.\n".format(self._session_summary["files downloaded"])
            + "{} files already downloaded.".format(
                self._session_summary["files already downloaded"]
            )
        )

        self._summary_dialog = qtw.QMessageBox(
            qtw.QMessageBox.Icon.Information,
            "Session summary",
            text,
            qtw.QMessageBox.StandardButton.Ok,
            self.parent(),
        )
        self._summary_dialog.setInformativeText(informative_text)
        self._summary_dialog.setWindowModality(qtc.Qt.WindowModality.NonModal)
        self._summary_dialog.button(qtw.QMessageBox.StandardButton.Ok).setFocusPolicy(
            qtc.Qt.FocusPolicy.ClickFocus
        )
        self._summary_dialog.buttonClicked.connect(
            self._summary_dialog_button_clicked_slot
        )

        self._summary_dialog.show()

    def _end_session(self) -> None:
        """
        Denotes the completion of the current download session.
        """
        self._deinitialize_session()
        if hasattr(self, "_session_summary"):
            self._show_session_summary()
            session_summary = self._session_summary.copy()
            session_summary["total download size"] = " ".join(
                map(
                    str,
                    get_value_and_unit_from_Bytes(
                        self._session_summary["total download size"]
                    ),
                )
            )

            self._logger.info(
                "Session ended: SUMMARY="
                + str(session_summary).replace(": ", "=").replace("'", '"')
            )

    # SLOTS
    def _get_file_slot(self) -> None:
        """
        Slot for when `_downloader` raises `get_file_signal`.
        """
        raise NotImplementedError

    def _item_invalid_slot(self) -> None:
        invalid_item = self._download_items_model.current().item_name
        self._logger.warning(
            f"Invalid item for download of type `{self._download_type}`: "
            f'"{invalid_item}"'
        )
        self._session_summary["items invalid"] += 1
        # Here because each item will have a new set of galleries.
        self._output_dialog.reset_gallery_progress_value()

        # self._output_dialog.remove_table_model()

        self._download_items_model.setData(
            index=self._download_items_model.get_current_index().status,
            value=-3,
            for_="status",
        )  # Set current item as completed.
        self._continue_item_download()

    def _gallery_file_already_exists_slot(
        self, current_working_loca_filename: str
    ) -> None:
        self._logger.info(
            f"File already exists: LOCATION={current_working_loca_filename}"
        )
        self._session_summary["files already downloaded"] += 1
        self._output_dialog.update_file_progress()
        self._download_files_model.setData(
            index=self._download_files_model.get_current_index().status,
            value=1,
            for_="status",
        )  # Set status of current to-be-downloaded file.
        self._download_files_model.setData(
            index=self._download_files_model.get_current_index().download_progress,
            value=-1,
            for_="progress",
        )  # Set status of current to-be-downloaded file.
        try:
            url = next(self._file_url_generator)
        except StopIteration:
            self._end_gallery_download()
        else:
            self._downloader.start_file_download(url)

    def _ignore_or_download_gallery(self, result: list) -> None:
        if result != [] and result != [[]]:
            self._logger.info(
                f"Gallery already exists: LOCATION={self._current_working_gallery_metadata.location}"
            )
            if Preferences.get_instance()["download_preferences"]["overwrite"]:
                self._logger.info(
                    f"Overwriting existing gallery: ID={self._current_working_gallery_metadata.gallery_id}"
                )
            else:
                self._session_summary["galleries already downloaded"] += 1
                self._continue_gallery_download()
                return
        self._downloader.set_current_working_gallery_metadata(
            self._current_working_gallery_metadata
        )
        self._begin_file_download()

    def _metadata_ready_slot(self, gallery_metadata: GalleryMetadataBase) -> None:
        if res := self._pass_through_filter(gallery_metadata):
            self._gallery_filtered_out(gallery_metadata.gallery_id, res)
            return

        self._current_working_gallery_metadata = gallery_metadata
        self._output_dialog.setDisabled(True)
        self._database_manager.get(
            get_callback=self._database_manager_gallery_check_finished,
            select="gallery",
            user_query=f"gallery={gallery_metadata.gallery_id} source={self.__class__.__name__.lower()}",
        )

    def _database_manager_gallery_check_finished(self, results: list) -> None:
        self._output_dialog.setDisabled(False)
        self._ignore_or_download_gallery(results)

    def _summary_dialog_button_clicked_slot(self) -> None:
        """
        Emits
        ------
            signals_hub.downloader_signals.download_session_finished_signal:
                Signals the end of the download session.
        """
        # Don't need close before deleteLater()
        self._summary_dialog.deleteLater()
        del self._summary_dialog

        downloader_signals.download_session_finished_signal.emit()

    def _output_dialog_canceled_slot(self) -> None:
        if hasattr(self._network_access_manager, "reply"):
            self._network_access_manager.abort()
        self._download_items_model.setData(
            index=self._download_items_model.get_current_index().status,
            value=-2,
            for_="status",
        )  # Set remaining items as aborted.
        self._machine.stop()

    @qtc.Slot()
    def _machine_stop_slot(self):
        if self._machine.property("state") == 2:
            self._end_session()
        elif self._machine.property("state") == 1:
            self._deinitialize_session()
        self._machine.start()

    @qtc.Slot()
    def _close_canceled(self) -> None:
        # To be thought of/to be implemented.
        pass

    def close(self) -> Union[dict, None]:
        results = {}
        if hasattr(self, "_downloader"):
            results["download"] = True

        if results != {}:
            self._logger.warning("Pending operations exist.")
            return results

        return None
