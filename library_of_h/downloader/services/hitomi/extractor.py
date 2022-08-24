from __future__ import annotations

import datetime
import json
import re
from typing import Iterator
from weakref import proxy

from PySide6 import QtCore as qtc

from library_of_h.downloader.services.hitomi.constants import *
from library_of_h.downloader.services.hitomi.metadata import (
    HitomiFileMetadata, HitomiGalleryMetadata)
from library_of_h.logger import (DownloaderServiceType, DownloaderSubType,
                                 MainType, get_logger)
from library_of_h.preferences import Preferences


class HitomiExtractor(qtc.QObject):

    _logger: logging.Logger

    nozomi_ready_signal = qtc.Signal(int)
    item_finished_signal = qtc.Signal()
    item_invalid_signal = qtc.Signal()
    metadata_ready_signal = qtc.Signal(HitomiGalleryMetadata)

    def __init__(self) -> None:
        super().__init__()
        self._logger = get_logger(
            main_type=MainType.DOWNLOADER,
            sub_types=[DownloaderSubType.EXTRACTOR, DownloaderServiceType.HITOMI],
        )
        self._destination_formats = Preferences.get_instance()[
            "download_preferences", "destination_formats", "Hitomi"
        ]
        self._filename_and_ext_pattern = re.compile(".([A-Za-z0-9]+$)")

    def set_user_selections(self, download_type: str, order_by: str):
        self._download_type = download_type
        self._search_category = DOWNLOAD_TYPES[download_type]

        self._order_by = ""
        if self._order_by in ("Today", "Week", "Month", "Year"):
            self._order_by = f"popular/{self._order_by.lower()}/"

    def set_destination_formats(self) -> None:
        self._destination_formats = Preferences.get_instance()[
            "download_preferences", "destination_formats", "Hitomi"
        ]

    def set_network_access_manager(
        self, network_access_manager: nhentaiNetworkAccessManager
    ):
        self._network_access_manager = proxy(network_access_manager)

    def fetch_nozomi(self: HitomiExtractor, url: str) -> None:
        """
        `nozomi_address` gets you a file that stores gallery IDs (in bytes) of
        all the galleries to be shown under a URL, I think. i.e. if the URL is
        `https://hitomi.la/series/some%20series.html`, it gets you all the
        galleries belonging to that series.
        Pretty much verbatim copied from https://ltn.hitomi.la/galleryblock.js
        with some code redacted for not being relevant, can be found in
        extractor.py.bak.
        Hence, I don't have a clear idea as to what it does.

        Parameters
        -----------
            url (str):
                URL to fetch the nozomi(s) for.
        """
        tag, area, language = (1,) * 3
        popular = None

        # Gets everything after "hitomi.la/":
        filepath = re.sub(".*hitomi\.la\/", "", url)

        # (hitomi.la)"series/some-series-name-english.html?page=2"
        # to
        # "series/some-series-name-english"
        # to
        # ["series/some-series-name", "english"]
        elements = re.sub("\.html(?:\?page=\d+)?$", "", filepath).rsplit("-", 1)

        tag = elements[0]
        # series/popular/today/female:filming
        # popular/today

        if "/" in tag:
            area_elements = tag.split("/")
            # [series, popular, today, female:filming]
            # [popular, today]
            if area_elements[1] == "popular":
                popular = area_elements[2]
                # today
                del area_elements[1:3]  # Delete second and third elements.
                # [series, female:filming]
            elif area_elements[0] == "popular":
                popular = area_elements[1]
                # today

            area = area_elements[0]
            # series
            # popular

            tag = area_elements[1]
            # female:filming
            # today

        language = elements[1]

        nozomi_address = "/".join([DOMAIN, "-".join([tag, language])]) + NOZOMIEXTENSION

        if area:
            nozomi_address = (
                "/".join([DOMAIN, area, "-".join([tag, language])]) + NOZOMIEXTENSION
            )
            if (
                popular and area != "popular"
            ):  # series/popular/today/female:filming-german
                nozomi_address = (
                    "/".join(
                        [DOMAIN, area, "popular", popular, "-".join([tag, language])]
                    )
                    + NOZOMIEXTENSION
                )

        self._get_nozomi(nozomi_address)

    def _get_nozomi_finished_slot(self) -> None:
        handled = self._network_access_manager.handle_error(
            self._network_access_manager.reply.error()
        )
        if handled == 203:
            self.item_invalid_signal.emit()
            return
        elif handled != 0:
            return

        reply_text = self._network_access_manager.reply.readAll().data()

        total_galleries = len(reply_text) // 4
        self._nozomi_generator = self._get_nozomi_from_bytes(reply_text)
        self.nozomi_ready_signal.emit(total_galleries)

    def _get_nozomi(self, nozomi_address: str) -> None:
        self._network_access_manager.set_request_url("https://" + nozomi_address)
        self._network_access_manager.get(
            reconnect_callback=lambda: self._get_nozomi(nozomi_address),
            finished=self._get_nozomi_finished_slot,
        )

    def next_nozomi(self) -> int:
        try:
            return next(self._nozomi_generator)
        except (
            # `AttributeError` because `self._gallery_id_from_nozomi_generator`
            # will not ; if download type is Gallery ID(s). In that case,
            # calling this function denotes end of a download item.
            AttributeError,
            # If no more gallery IDs in `self._gallery_id_from_nozomi_generator`
            # then that denotes the end if an item.
            StopIteration,
        ):
            self.item_finished_signal.emit()
            return -1

    def _get_gallery_metadata_finished_slot(self) -> None:
        handled = self._network_access_manager.handle_error(
            self._network_access_manager.reply.error()
        )
        if handled == 203:
            self.item_invalid_signal.emit()
            return
        elif handled != 0:
            return

        self._extract_gallery_metadata()

    def get_gallery_metadata(self, gallery_id: int) -> None:
        self._network_access_manager.set_request_url(
            GALLERY_JS.format(gallery_id=gallery_id)
        )
        self._network_access_manager.get(
            reconnect_callback=lambda: self.get_gallery_metadata(gallery_id),
            finished=self._get_gallery_metadata_finished_slot,
        )

    def _extract_gallery_metadata(self) -> HitomiGalleryMetadata:
        reply_text = self._network_access_manager.reply.readAll().data().decode("utf-8")
        try:
            json_data = re.search(r"{[\s\S]*}", reply_text).group(0)
        except AttributeError as e:  # NoneType has no attribute `group`
            self._logger.error(
                "[Assumption Error: unable to get gallery metadata JSON from JS API] "
                f"[{str(e)}] "
                "Most likely Hitomi made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1].split('.')[0]}"
            )
            return

        try:
            json_data = json.loads(json_data)
        except json.JSONDecodeError as e:
            self._logger.error(
                "[Assumption Error: unable to load gallery metadata JSON from API] "
                f"[{str(e)}] "
                "Most likely Hitomi made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1].split('.')[0]}"
            )
            return

        try:
            gallery_id = int(json_data.get("id"))
        except TypeError as e:  # Can't use None with `int()`.
            self._logger.error(
                "[Assumption Error: unable to get gallery ID from metadata JSON] "
                f"[{str(e)}] "
                "Most likely Hitomi made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1].split('.')[0]}"
            )
            return

        try:
            title = json_data["title"]
        except KeyError as e:
            # Even without a value, the JSON should have `"title": null`.
            # Can't say for certain, was one gallery with no `"japanese_title"`
            # key at all while there were others with `"japanese_title": null`.
            self._logger.error(
                "[Assumption Error: unable to get title from metadata JSON] "
                f"[{str(e)}] "
                "Most likely Hitomi made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1].split('.')[0]}"
            )
            return

        try:
            japanese_title = json_data["japanese_title"]
        except KeyError as e:
            # Even without a value, the JSON should have `"japanese_title":null`.
            # Can't say for certain, was one gallery with no `"japanese_title"`
            # key at all.
            self._logger.error(
                "[Assumption Error: unable to get Japanese title from metadata JSON] "
                f"[{str(e)}] "
                "Most likely Hitomi made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1].split('.')[0]}"
            )
            return

        try:
            artists = [dict_.get("artist") for dict_ in json_data["artists"]]
        except KeyError as e:
            # Even without a value, the JSON should have {"artists":null},
            # if there's no such key, they changed the JSON format.
            self._logger.error(
                "[Assumption Error: unable to get artist(s) list from metadata JSON] "
                f"[{str(e)}] "
                "Most likely Hitomi made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1].split('.')[0]}"
            )
            return
        except TypeError:
            artists = ["---"]

        try:
            groups = [dict_.get("group") for dict_ in json_data["groups"]]
        except KeyError as e:
            # Even without a value, the JSON should have {"groups":null},
            # if there's no such key, they changed the JSON format.
            self._logger.error(
                "[Assumption Error: unable to get group(s) list from metadata JSON] "
                f"[{str(e)}] "
                "Most likely Hitomi made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1].split('.')[0]}"
            )
            return
        except TypeError:
            groups = ["---"]

        try:
            type_ = json_data["type"]
        except KeyError as e:
            # There should always be a type, if not they changed format.
            self._logger.error(
                "[Assumption Error: unable to get gallery type from metadata JSON] "
                f"[{str(e)}] "
                "Most likely Hitomi made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1].split('.')[0]}"
            )
            return
        else:
            if type_ is None:
                type_ = ["---"]
            if not isinstance(type_, list):
                type_ = [type_]

        try:
            language = json_data["language"]
        except KeyError as e:
            # Should always have a value, I think.
            self._logger.error(
                "[Assumption Error: unable to get gallery language from metadata JSON] "
                f"[{str(e)}] "
                "Most likely Hitomi made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1].split('.')[0]}"
            )
            return
        else:
            if language is None:
                language = ["---"]
            if not isinstance(language, list):
                language = [language]

        try:
            series = [dict_.get("parody") for dict_ in json_data["parodys"]]
        except TypeError:
            # Either exists with a value or does not exist as a key at all.
            series = ["---"]

        try:
            characters = [dict_.get("character") for dict_ in json_data["characters"]]
        except KeyError as e:
            # Even without a value, the JSON should have {"characters":null},
            # if there's no such key, they changed the JSON format.
            self._logger.error(
                "[Assumption Error: unable to get character(s) list from metadata JSON] "
                f"[{str(e)}] "
                "Most likely Hitomi made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1].split('.')[0]}"
            )
            return
        except TypeError:
            characters = ["---"]

        try:
            tags = [
                f'{sex}:{tag["tag"]}'
                if (
                    sex := (
                        "f" if tag.get("female") else "m" if tag.get("male") else ""
                    )
                )
                else tag.get(
                    "tag"
                )  # Prefix tag name with (fe)male: if either is True else just tag name.
                for tag in json_data["tags"]
            ]
        except KeyError as e:
            # Every gallery should have a tag, right?!
            self._logger.error(
                "[Assumption Error: unable to get tag(s) list from metadata JSON] "
                f"[{str(e)}] "
                "Most likely Hitomi made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1].split('.')[0]}"
            )
            return
        except TypeError:
            # Apparently not: hitomi.la/gamecg/dokidoki-vacation-～kirameku-kisetsu-no-naka-de～-480440.html
            tags = ["---"]

        try:
            upload_date = int(
                datetime.datetime.strptime(
                    json_data.get("date")[:-3], "%Y-%m-%d %H:%M:%S"
                ).timestamp()
            )
        except TypeError as e:  # 'NoneType' object is not subscriptable
            self._logger.error(
                "[Assumption Error: unable to get upload date from metadata JSON] "
                f"[{str(e)}] "
                "Most likely Hitomi made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1].split('.')[0]}"
            )
            return
        except ValueError as e:
            # Time data '...' does not match format '%Y-%m-%d %H:%M:%S'
            self._logger.error(
                "[Assumption Error: unable to get upload date from metadata JSON] "
                f"[{str(e)}] "
                "Most likely Hitomi made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1].split('.')[0]}"
            )
            return

        try:
            files = HitomiFileMetadata()
            if vfn := json_data.get("videofilename"):
                res = self._filename_and_ext_pattern.split(json_data["videofilename"])[
                    :-1
                ]
                files.insert(
                    filename=res[0], ext=res[1], hash_="", hasavif=False, haswebp=False
                )
            else:
                for file in json_data["files"]:
                    res = self._filename_and_ext_pattern.split(file["name"])[:-1]
                    files.insert(
                        filename=res[0],
                        ext=res[1],
                        hash_=file["hash"],
                        hasavif=file["hasavif"],
                        haswebp=file["haswebp"],
                    )
        except KeyError as e:
            # There should always be files, if not they changed the format.
            self._logger.error(
                "[Assumption Error: unable to get file(s) list from metadata JSON] "
                f"[{str(e)}] "
                "Most likely Hitomi made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1].split('.')[0]}"
            )
            return
        except TypeError as e:  # 'NoneType' is not subscriptable.
            # Files should have filename and extension, if not they changed the format.
            self._logger.error(
                "[Assumption Error: unable to extract file(s) data from metadata JSON] "
                f"[{str(e)}] "
                "Most likely Hitomi made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1].split('.')[0]}"
            )
            return

        gallery_metadata = HitomiGalleryMetadata(
            gallery_id=gallery_id,
            title=title,
            japanese_title=japanese_title,
            artists=artists,
            groups=groups,
            type=type_,
            language=language,
            series=series,
            characters=characters,
            tags=tags,
            upload_date=upload_date,
            files=files,
            video=json_data.get("video"),
            videofilename=json_data.get("videofilename"),
            source="hitomi",
        )

        gallery_metadata.set_location(
            self._destination_formats[self._download_type],
            self._item,
        )
        self.metadata_ready_signal.emit(gallery_metadata)

    def get_download_item_url(self, item: str) -> str:
        if self._search_category == "":
            self._item = "gallery"
            return item

        self._item = item

        download_item_url = "".join(
            (
                ROOT_URL,
                self._search_category,
                self._order_by,
                self._item,
                "-all",
                ".html",
            )
        )

        return download_item_url

    def _get_nozomi_from_bytes(self, bytes_array: bytes) -> Iterator[int]:
        """
        Takes four bytes from bytes_array and converts it into big-endian signed
        int32 (nozomi).

        Returns
        -------
            Iterator[int]:
                Iterator of big-endian signed int32.

        Yields
        -------
            int
        """
        # '>i' means big-endian, as specified in
        # https://ltn.hitomi.la/galleryblock.js as:
        # nozomi.push(view.getInt32(i*4, false /* big-endian */));
        return (
            int.from_bytes(bytes_array[i : i + 4], "big", signed=True)
            for i in range(len(bytes_array))[::4]
        )
