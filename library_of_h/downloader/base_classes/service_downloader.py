import logging
import os
from weakref import proxy

import magic
from PySide6 import QtCore as qtc
from PySide6 import QtNetwork as qtn

from library_of_h.custom_widgets.elapsed_timer import ElapsedTimer
from library_of_h.downloader.base_classes.metadata import GalleryMetadataBase
from library_of_h.downloader.base_classes.network_access_manager import \
    NetworkAccessManagerBase
from library_of_h.downloader.custom_sub_classes.download_files_model import \
    DownloadFilesModel
from library_of_h.logger import (DownloaderServiceType, DownloaderSubType,
                                 MainType, get_logger)
from library_of_h.preferences import Preferences


class ServiceDownloaderBase(qtc.QObject):

    _logger: logging.Logger
    _current_working_local_file: qtc.QFile
    _network_access_manager: NetworkAccessManagerBase
    _current_working_gallery_metadata: GalleryMetadataBase

    get_file_signal = qtc.Signal()
    file_finished_signal = qtc.Signal()
    gallery_file_already_exist_signal = qtc.Signal(str)

    def __init__(self) -> None:
        super().__init__()

        self._current_downloading_file_size = 0
        self._logger = get_logger(
            main_type=MainType.DOWNLOADER,
            sub_types=[
                DownloaderSubType.DOWNLOADER,
                getattr(
                    DownloaderServiceType,
                    type(self).__name__.replace("Downloader", "").upper(),
                ),
            ],
        )
        self._download_timer = ElapsedTimer()

    def set_network_access_manager(
        self, network_access_manager: NetworkAccessManagerBase
    ):
        self._network_access_manager = proxy(network_access_manager)
        self._network_access_manager.disconnected.connect(self._download_timer.pause)
        self._network_access_manager.reconnected.connect(self._download_timer.resume)

    def set_current_working_gallery_metadata(
        self, gallery_metadata: GalleryMetadataBase
    ):
        self._current_working_gallery_metadata = gallery_metadata

    def set_download_files_model(self, download_files_model: DownloadFilesModel):
        self._download_files_model = download_files_model

    def set_current_working_local_file(self, filename: str) -> None:
        location = qtc.QDir(self._current_working_gallery_metadata.location)

        if not location.mkpath(abs_save_destination := location.absolutePath()):
            self._logger.warning(
                "Failed to create directory: " f'PATH="{abs_save_destination}"'
            )
            return

        self._current_working_local_file = qtc.QFile(
            os.path.join(abs_save_destination, filename)
        )

    def _write_to_disk(self, data: qtc.QByteArray) -> None:
        if self._current_working_local_file.write(data) == -1:
            self._logger.error(
                f"[{self._current_working_local_file.errorString()}] "
                "Error writing to file: "
                f'FILE="{self._current_working_local_file.fileName()}"'
            )

    def _download_progress_slot(self, bytes_received: int, total_bytes: int) -> None:
        # To keep track of the appropriate amount for bytes received even after
        # a network disconnection; `_continue`ing causes `bytes_received` to
        # re-start from 0.
        self._actual_total_bytes = max(self._actual_total_bytes, total_bytes)
        bytes_received += self._actual_total_bytes - total_bytes
        self._download_files_model.setData(
            index=self._download_files_model.get_current_index().download_progress,
            value=bytes_received,
            for_="progress",
        )  # Set progress for current downloading file.

        current_size = self._download_files_model.get_current_data().download_progress
        bytes_per_second = (
            current_size
            / (self._download_timer.elapsed() or 1)  # Prevent zero division.
        ) * 1000

        self._download_files_model.setData(
            index=self._download_files_model.get_current_index().download_speed,
            value=bytes_per_second,
            for_="speed",
        )  # Set progress for current downloading file.

    def _ready_read_slot(self) -> None:
        data = self._network_access_manager.reply.readAll()
        if "text/html" == magic.from_buffer(data.data(), mime=True):
            self._logger.error(
                "[Unknown] Received text/html: "
                f"GALLERY ID={self._current_working_gallery_metadata.gallery_id}, "
                f"URL={self._network_access_manager.reply.url().toString()}"
            )
            return
        self._write_to_disk(data)

    def _HEAD(self, url: str) -> None:
        self._network_access_manager.set_request_url(url)
        self._network_access_manager.head(
            reconnect_callback=lambda: self._HEAD(url),
            finished=self._HEAD_finished_slot,
        )

    def download(self) -> None:
        self.get_file_signal.emit()

    def start_file_download(self, url: str) -> None:
        self._logger.info(f"Begin file download: URL={url}")
        self._HEAD(url)

    def _continue(self, url: str) -> None:
        if not self._current_working_local_file.isOpen():
            if not self._current_working_local_file.open(
                qtc.QFile.OpenModeFlag.Append | qtc.QIODevice.OpenModeFlag.Text
            ):
                self._logger.error(
                    f"[{self._current_working_local_file.errorString()}] "
                    "Error opening file: "
                    f'FILE="{self._current_working_local_file.fileName()}"'
                )
                return
        self._network_access_manager.set_request_header(
            qtc.QByteArray(b"Range"),
            qtc.QByteArray(
                f"bytes={self._current_working_local_file.size()}-".encode("utf-8")
            ),
        )
        self._network_access_manager.set_request_url(url)
        self._network_access_manager.get(
            reconnect_callback=lambda: self._continue(url),
            finished=self._GET_finished_slot,
            downloadProgress=self._download_progress_slot,
            readyRead=self._ready_read_slot,
        )

    def _check_file_existence(self) -> bool:
        """
        Checks if a file already exists.

        Returns
        --------
            True: File exists.
            False: File does not exist.
        """
        if (
            self._current_working_local_file.exists()
            and self._current_working_local_file.size()
            == self._current_downloading_file_size
        ):
            return True
        return False

    def _handle_network_runtime_error(
        self, error: qtn.QNetworkReply.NetworkError
    ) -> int:
        return self._network_access_manager.handle_error(error)

    def _begin_download(self) -> None:
        if not self._current_working_local_file.isOpen():
            if not self._current_working_local_file.open(
                qtc.QFile.OpenModeFlag.WriteOnly | qtc.QIODevice.OpenModeFlag.Text
            ):
                self._logger.error(
                    f"[{self._current_working_local_file.errorString()}] "
                    "Error opening file: "
                    f'FILE="{self._current_working_local_file.fileName()}"'
                )
                return

        self._download_files_model.setData(
            index=self._download_files_model.get_current_index().status,
            value=0,
            for_="status",
        )  # Set status of current to-be-downloaded file.

        self._actual_total_bytes = 0
        self._download_timer.start()
        url = self._network_access_manager.reply.url().toString()
        self._network_access_manager.get(
            reconnect_callback=lambda: self._continue(url),
            finished=self._GET_finished_slot,
            downloadProgress=self._download_progress_slot,
            readyRead=self._ready_read_slot,
        )

    def _HEAD_finished_slot(self) -> None:
        handled = self._handle_network_runtime_error(
            self._network_access_manager.reply.error()
        )
        if handled != 0:
            return

        try:
            self._current_downloading_file_size = int(
                self._network_access_manager.reply.rawHeader(
                    qtc.QByteArray(b"Content-Length")
                ).data()
            )
        except ValueError:
            # Sometimes, the Content-Length is `b''`. Might have been due to
            # cache, most likely fixed with cache-control HTTP header set to
            # no-cache.
            self._logger.warning(
                "[Unknown] Unable to get remote file size: "
                f"URL={self._network_access_manager.reply.url().toString()}"
            )
            self._current_downloading_file_size = -1

        if (
            qtc.QStorageInfo(
                self._current_working_gallery_metadata.location
            ).bytesAvailable()
            + 1 * 1024
            <= self._current_downloading_file_size
        ):
            self._logger.error(
                "[Not Enough Space] "
                "Disk running low on space: "
                f"LOCATION={self._current_working_gallery_metadata.location}"
            )
            return

        self._download_files_model.setData(
            index=self._download_files_model.get_current_index().file_size,
            value=int(
                self._network_access_manager.reply.rawHeader(
                    qtc.QByteArray(b"Content-Length")
                )
                or -1
            ),
            for_="size",
        )  # Set size of current to-be-downloaded file.

        if self._check_file_existence():
            # If file already exists
            if Preferences.get_instance()["download_preferences"]["overwrite"]:
                # If the user wants existing downloads to be overwritten
                self._begin_download()
            else:
                self.gallery_file_already_exist_signal.emit(
                    self._current_working_local_file.fileName()
                )
        else:
            self._begin_download()

    def _GET_finished_slot(self) -> None:
        self._network_access_manager.set_request_header(
            qtc.QByteArray(b"Range"), qtc.QByteArray(b"bytes=0-")
        )

        handled = self._handle_network_runtime_error(
            self._network_access_manager.reply.error()
        )
        if handled == -4:
            self._download_files_model.setData(
                index=self._download_files_model.get_current_index().download_speed,
                value=0,
                for_="speed",
            )  # -4 means disconnected, so set speed to 0 B/s.
            return
        elif handled != 0:
            return

        if self._current_working_local_file.isOpen():
            self._current_working_local_file.close()

            if (
                self._current_downloading_file_size != -1
                and self._current_downloading_file_size
                != self._current_working_local_file.size()
            ):
                self._logger.warning(
                    "[Size Mismatch] Error downloading file: re-downloading."
                )
                self._begin_download()
                return
            elif self._current_downloading_file_size == -1:
                self._logger.warning(
                    "[Invalid Remote File Size] Unable to perform file size check: "
                    f"URL={self._network_access_manager.reply.url().toString()}; "
                    f'FILE="{self._current_working_local_file.fileName()}"'
                )

        self._logger.info(
            f"Finished file download: LOCATION={self._current_working_local_file.fileName()}"
        )

        self._download_files_model.setData(
            index=self._download_files_model.get_current_index().status,
            value=1,
            for_="status",
        )  # Set status of current to-be-downloaded file.

        self.file_finished_signal.emit()
