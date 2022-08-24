import re

from PySide6 import QtCore as qtc
from PySide6 import QtNetwork as qtn

from library_of_h.downloader.base_classes.network_access_manager import \
    NetworkAccessManagerBase
from library_of_h.downloader.services.hitomi.constants import DOMAIN


class HitomiNetworkAccessManager(NetworkAccessManagerBase):

    gg_error_handled_signal = qtc.Signal()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._request.setRawHeader(
            qtc.QByteArray(b"Accept"),
            qtc.QByteArray(
                b"text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9"
            ),
        )
        self._request.setRawHeader(
            qtc.QByteArray(b"Referer"), qtc.QByteArray(b"https://hitomi.la/")
        )

    def handle_gg_error(self, error: qtn.QNetworkReply.NetworkError) -> int:
        if int(error) == 201 or int(error) == 203:
            if int(error) == 201:
                self._logger.warning("[201 Access Denied]")
            else:
                self._logger.warning("[203 Page Not Found]")
            self._logger.warning("Remote gg.js changed.")
            self.get_gg()
            return int(error)
        else:
            return super().handle_error(error)

    def get_gg(self) -> None:
        """
        hitomi.la re-freshes https://ltn.hitomi.la/gg.js every 30, they change
        important values in that file every so often minutes, this gets it.
        Significance of gg.b:
            https://**{gg.m()}**a.hitomi.la/{dir}/**{gg.b}**/{some_number_based_on_hash}/{file_hash}.{ext}
        where the above link is a template for any gallery's image link(s).
        """
        gg_url = "https://" + DOMAIN + "/gg.js"
        self.set_request_url(gg_url)
        self.get(readyRead=self._check_gg)

    def _check_gg(self) -> None:
        new_gg = self.reply.readAll().data().decode("utf-8")
        self.reply.close()
        try:
            new_o = re.findall("var o = ([0-9]*)", new_gg)[0]
            new_new_o = re.findall("o = ([0-9]*); break;", new_gg)[0]
            new_tuple = tuple(map(int, re.findall("case ([0-9]+):", new_gg)))
            new_b = re.findall("b: '([0-9]+/)'", new_gg)[0]
        except IndexError as e:
            self._logger.error(
                "[Assumption Error: unable to get data from gg.js] "
                f"[{str(e)}] "
                "Most likely Hitomi made changes to their website."
            )
            return

        template_file = qtc.QFile(
            "library_of_h/downloader/services/hitomi/gg.py.template"
        )
        if not template_file.open(
            qtc.QFile.OpenModeFlag.ReadOnly | qtc.QIODevice.OpenModeFlag.Text
        ):
            self._logger.error(
                f"[{template_file.errorString()}] " "Error opening `gg.py.template`."
            )
            return

        template = template_file.readAll().data().decode("utf-8")
        template_file.close()

        ggpy = re.sub(r"o = \(\) # First", f"o = {new_o}", template)
        ggpy = re.sub(r"o = \(\) # Second", f"o = {new_new_o}", ggpy)
        ggpy = re.sub(r"if g in \(\)", f"if g in {new_tuple}", ggpy)
        ggpy = re.sub("b = \(\)", f'b = "{new_b}"', ggpy)

        ggpy_file = qtc.QFile("library_of_h/downloader/services/hitomi/gg.py")
        if not ggpy_file.open(
            qtc.QFile.OpenModeFlag.WriteOnly | qtc.QIODevice.OpenModeFlag.Text
        ):
            self._logger.error(
                f"[{template_file.errorString()}] " "Error opening `gg.py`."
            )
            return

        ggpy_file.write(qtc.QByteArray(bytes(ggpy, "utf-8")))
        ggpy_file.close()
        self.gg_error_handled_signal.emit()
