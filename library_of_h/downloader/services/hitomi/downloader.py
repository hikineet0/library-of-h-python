from __future__ import annotations

from PySide6 import QtCore as qtc
from PySide6 import QtNetwork as qtn

from library_of_h.downloader.base_classes.service_downloader import \
    ServiceDownloaderBase
from library_of_h.downloader.services.hitomi.metadata import \
    HitomiGalleryMetadata
from library_of_h.downloader.services.hitomi.network_access_manager import \
    HitomiNetworkAccessManager


class HitomiDownloader(ServiceDownloaderBase):
    # Declarations
    _current_working_gallery_metadata: HitomiGalleryMetadata
    _network_access_manager: HitomiNetworkAccessManager
    # Signal definitions
    _gg_error_signal = qtc.Signal(qtn.QNetworkReply.NetworkError)
    get_file_signal = qtc.Signal(
        str
    )  # Reimplemented get_file_signal to pass gallery type.

    def _handle_network_runtime_error(self, error: qtn.QNetworkReply.NetworkError):
        if self._current_working_gallery_metadata.type == "anime":
            return self._network_access_manager.handle_error(error)

        # This is only for image download because there is no gg.js magic for
        # video files (none that I know of at least).
        return self._network_access_manager.handle_gg_error(error)

    def download(self) -> None:
        self.get_file_signal.emit(
            "anime"
            if self._current_working_gallery_metadata.type == "anime"
            else "image"
        )

        # Possibly not needed because global "https://hitomi.la/" referer should
        # suffice -->
        # referer = ROOT_URL
        # self._network_access_manager.set_request_header(
        #     qtc.QByteArray(b"Referer"), qtc.QByteArray(bytes(referer,
        #     "utf-8")) )
