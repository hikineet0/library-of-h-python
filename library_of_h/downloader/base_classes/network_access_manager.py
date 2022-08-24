import logging

from PySide6 import QtCore as qtc
from PySide6 import QtNetwork as qtn

from library_of_h.logger import (DownloaderServiceType, DownloaderSubType,
                                 MainType, get_logger)


class NetworkAccessManagerBase(qtn.QNetworkAccessManager):

    _logger: logging.Logger

    _RETRY_COOLDOWN = 3000  # Microseconds or 3 Seconds
    _REPLY_TIMEOUT = 10_000  # Microseconds or 10 Seconds
    _REQUEST_COOLDOWN = 2000  # Microseconds or 2 Seconds

    disconnected = qtc.Signal()
    reconnected = qtc.Signal()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._reconnect_callback = None
        self._retry_url = "https://github.com/london-69/library-of-h"

        self._logger = get_logger(
            main_type=MainType.DOWNLOADER,
            sub_types=[
                DownloaderSubType.NETWORK,
                getattr(
                    DownloaderServiceType,
                    type(self).__name__.replace("NetworkAccessManager", "").upper(),
                ),
            ],
        )

        # For when `abort()` is called on `reply` due to timeout.
        # `abort()` called manually changes `timeout` to `False`.
        # This value is used to decide how to handle the error in `handle_5()`.
        self._timeout = True
        self._retry_timer = qtc.QTimer(self)
        self._retry_timer.setSingleShot(True)
        self._retry_timer.setInterval(self._RETRY_COOLDOWN)
        self._retry_timer.timeout.connect(self._retry)

        self._cooldown_timer_get = qtc.QElapsedTimer()
        self._cooldown_timer_get.start()

        self._cooldown_timer_head = qtc.QElapsedTimer()
        self._cooldown_timer_head.start()

        self._cooldown_wait_timer_get = qtc.QTimer()
        self._cooldown_wait_timer_get.setSingleShot(True)
        self._cooldown_wait_timer_get.timeout.connect(self.get)

        self._cooldown_wait_timer_head = qtc.QTimer()
        self._cooldown_wait_timer_head.setSingleShot(True)
        self._cooldown_wait_timer_head.timeout.connect(self.head)

        self._request = qtn.QNetworkRequest()
        self._request.setTransferTimeout(self._REPLY_TIMEOUT)
        self._request.setAttribute(
            qtn.QNetworkRequest.Attribute.Http2AllowedAttribute, False
        )

        self._request.setRawHeader(
            qtc.QByteArray(b"User-Agent"),
            qtc.QByteArray(
                b"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36 OPR/86.0.4363.50"
            ),
        )

        self._request.setRawHeader(
            qtc.QByteArray(b"Cache-Control"), qtc.QByteArray(b"no-cache")
        )
        self._request.setRawHeader(
            qtc.QByteArray(b"Pragma"), qtc.QByteArray(b"no-cache")
        )

    def set_request_header(self, *args: tuple[qtc.QByteArray, qtc.QByteArray]) -> None:
        self._request.setRawHeader(*args)

    def set_request_url(self, url: str) -> None:
        url = qtc.QUrl(url)
        self._request.setUrl(url)

    def abort(self):
        self._timeout = False
        self.reply.abort()

    def _retry_finished_slot(self) -> None:
        handled = self.handle_error(self.reply.error())
        if handled != 0:
            return
        else:
            self.reconnected.emit()
            self._logger.info("Reconnected.")
            if self._reconnect_callback:
                self._reconnect_callback()
            return

    def _retry(self) -> None:
        self.set_request_url(self._retry_url)
        self.reply = super().head(self._request)
        self.reply.finished.connect(self._retry_finished_slot)

    def head(
        self, reconnect_callback: "function" = None, **signals_and_slots
    ) -> qtn.QNetworkReply:
        if reconnect_callback:
            self._reconnect_callback = reconnect_callback

        if signals_and_slots:
            self.signals_and_slots = signals_and_slots

        if self._cooldown_timer_head.elapsed() < self._REQUEST_COOLDOWN:  # milliseconds
            self._cooldown_wait_timer_head.start(
                (self._REQUEST_COOLDOWN) - self._cooldown_timer_head.elapsed()
            )
        else:
            self.reply = super().head(self._request)
            self._connect_signals_and_slots()
            self._cooldown_timer_head.start()

    def get(self, reconnect_callback: "function" = None, **signals_and_slots) -> None:
        if reconnect_callback:
            self._reconnect_callback = reconnect_callback

        if signals_and_slots:
            self.signals_and_slots = signals_and_slots

        if self._cooldown_timer_get.elapsed() < self._REQUEST_COOLDOWN:  # milliseconds
            self._cooldown_wait_timer_get.start(
                (self._REQUEST_COOLDOWN) - self._cooldown_timer_get.elapsed()
            )
        else:
            self.reply = super().get(self._request)
            self._connect_signals_and_slots()
            self._cooldown_timer_get.start()

    def _connect_signals_and_slots(self) -> None:
        for key, value in self.signals_and_slots.items():
            getattr(self.reply, key).connect(value)

    def disconnect_signals_and_slots(self) -> None:
        for key, value in self.signals_and_slots.items():
            getattr(self.reply, key).disconnect()

    def _handle_reply_timeout(self) -> int:
        """
        [-4  ReplyTimeoutError]: no new data received from the server in
        REPLY_TIMEOUT seconds.
        """
        self._logger.warning(
            "[-4 Reply Timeout Error] Temporary error: attempting to reconnect."
        )
        self._retry_timer.start()
        return -4

    def handle_error(self, error: qtn.QNetworkReply.NetworkError) -> int:
        try:
            return getattr(self, f"_handle_{int(error)}")()
        except AttributeError:
            return self._handle_other(error)

    def _handle_other(self, error) -> int:
        """
        Handles errors that don't already have a dedicated method.
        """
        code = int(error)
        name = error.name
        self._logger.warning(f"[{code} {name}] Unhandled error.")
        return code

    def _handle_0(self) -> int:
        """
        [0 NoError]: no error occured.
        """
        return 0

    def _handle_1(self) -> int:
        """
        [1 ConnectionRefusedError]: the remote server refused the connection
        (the server is not accepting requests).
        """
        self._logger.warning(
            "[1 Connection Refused] Temporary error: attempting to reconnect."
        )
        self._retry_timer.start()
        return 1

    def _handle_2(self) -> int:
        """
        [2 RemoteHostClosedError]: the remote server closed the connection
        prematurely, before the entire reply was received and processed.
        """
        self._logger.warning(
            "[2 Remote Host Closed] Temporary error: attempting to reconnect."
        )
        self._retry_timer.start()
        return 2

    def _handle_3(self) -> int:
        """
        [3 HostNotFoundError]: the remote host name was not found (invalid
        hostname).
        """
        self._logger.warning(
            "[2 Host Not Found] Temporary error: attempting to reconnect."
        )
        self._retry_timer.start()
        return 3

    def _handle_4(self) -> int:
        """
        [4 TimeoutError]: the connection to the remote server timed out.
        """
        self._logger.warning(
            "[4 Timeout Error] Temporary error: attempting to reconnect."
        )
        self._retry_timer.start()
        return 4

    def _handle_5(self) -> int:
        """
        [5 OperationCanceledError]: network connection was aborted.
        """
        if self._timeout:
            # If reply aborted due to timeout:
            self.disconnected.emit()
            return self._handle_reply_timeout()
        else:
            # If reply aborted by manually calling `reply.abort()`:
            self._logger.warning("[5 Connection Aborted]")
            self._timeout = True
            return 5

    def _handle_201(self) -> int:
        """
        [201 ContentAccessDenied]: similar to HTTP status code 403, means
        forbidden webpage/access denied.
        """
        self._logger.warning("[201 Access Denied]")
        return 201

    def _handle_203(self) -> int:
        """
        [203 ContentNotFoundError]: similar to HTTP status code 404, means
        page not found.
        """
        self._logger.warning("[203 Page Not Found]")
        return 203

    def _handle_403(self) -> int:
        """
        [403 ServiceUnavailableError]: the server is unable to handle the
        request at this time.
        """
        self._logger.warning(
            "[403 Service Unavailable] Temporary error: attempting to reconnect."
        )
        self._retry_timer.start()
        return 403
