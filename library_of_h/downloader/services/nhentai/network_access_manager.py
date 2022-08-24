from PySide6 import QtCore as qtc

from library_of_h.downloader.base_classes.network_access_manager import \
    NetworkAccessManagerBase


class nhentaiNetworkAccessManager(NetworkAccessManagerBase):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._request.setRawHeader(
            qtc.QByteArray(b"Accept"),
            qtc.QByteArray(
                b"text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9"
            ),
        )

        self._request.setRawHeader(
            qtc.QByteArray(b"Referer"), qtc.QByteArray(b"https://www.nhentai.net")
        )
