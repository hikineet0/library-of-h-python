from __future__ import annotations

import datetime
import json
import re
from weakref import proxy

from bs4 import BeautifulSoup
from PySide6 import QtCore as qtc

from library_of_h.downloader.services.nhentai.constants import *
from library_of_h.downloader.services.nhentai.metadata import (
    nhentaiFileMetadata, nhentaiGalleryMetadata)
from library_of_h.downloader.services.nhentai.network_access_manager import \
    nhentaiNetworkAccessManager
from library_of_h.logger import (DownloaderServiceType, DownloaderSubType,
                                 MainType, get_logger)
from library_of_h.preferences import Preferences


class nhentaiExtractor(qtc.QObject):

    _logger: logging.Logger
    _current_gallery: tuple(int, int)
    _current_url: str
    _current_page_page_number: int

    page_ready_signal = qtc.Signal(int)
    item_finished_signal = qtc.Signal()
    item_invalid_signal = qtc.Signal()
    metadata_ready_signal = qtc.Signal(nhentaiGalleryMetadata)

    def __init__(self) -> None:
        super().__init__()
        self._logger = get_logger(
            main_type=MainType.DOWNLOADER,
            sub_types=[DownloaderSubType.EXTRACTOR, DownloaderServiceType.NHENTAI],
        )

        self._destination_formats = Preferences.get_instance()[
            "download_preferences", "destination_formats", "nhentai"
        ]

        self._gallery_link_pattern = re.compile("/g/(\d+)")
        self._gallery_page_link_pattern = re.compile("/g/(\d+)/1")
        self._total_galleries_pattern = re.compile("[\d,]+")
        self._cdn_server_pattern = re.compile("\d+")

    def set_user_selections(self, download_type: str, order_by: str) -> None:
        self._download_type = download_type

        self._download_category = DOWNLOAD_TYPES[download_type]

        self._order_by = ""
        if order_by == "Today" or order_by == "Week":
            self._order_by = f"/popular-{order_by.lower()}"
        elif order_by == "All time":
            self._order_by = "/popular"

    def set_destination_formats(self) -> None:
        self._destination_formats = Preferences.get_instance()[
            "download_preferences", "destination_formats", "nhentai"
        ]

    def set_network_access_manager(
        self, network_access_manager: nhentaiNetworkAccessManager
    ):
        self._network_access_manager = proxy(network_access_manager)

    def _parse_page_html(self) -> None:
        text = self._network_access_manager.reply.readAll().data().decode("utf-8")
        soup = BeautifulSoup(text, "lxml")

        if soup.h3 is not None:
            # 2022-06-12: When trying to access a category page higher than
            # available, the "No results, sorry." is displayed as a <h3>:
            # Example: https://www.nhentai.net/artist/kanju/?page=1111111
            # Other than that, there is no `h3` tag in the HTML.
            if soup.h3.text == "No results, sorry.":
                self.item_finished_signal.emit()
            return

        try:
            total_galleries = int(
                self._total_galleries_pattern.findall(
                    soup.find("span", class_="count").text
                )[0].replace(",", "")
            )
        except (
            AttributeError,  # For dot notations with soup.
            IndexError,  # For [0]
            ValueError,  # For `int()`
        ) as e:
            # Means the soup or regex failed in some part; means nhentai changed
            # how number of results is displayed.
            self._logger.error(
                "[Assumption Error: regex match for galleries count failed] "
                f"[{str(e)}] "
                "Most likely nhentai made changes to their website. "
                f"URL={self._current_url.format(self._current_page_page_number)}"
            )
            return

        try:
            self._galleries = iter(
                (
                    int(
                        self._cdn_server_pattern.findall(
                            gallery_url.noscript.img["src"]
                        )[0]
                    ),
                    int(self._gallery_link_pattern.findall(gallery_url["href"])[0]),
                )
                for gallery_url in soup.find_all("a", href=self._gallery_link_pattern)
            )
        except (
            AttributeError,  # For dot notations with soup.
            TypeError,
            # For `for gallery_url in soup.find_all('a', href=self._gallery_link_pattern)`
            # (failure returns `None`).
            # And subscriptions with None.
            KeyError,  # For subscriptions
        ) as e:
            # Means the regex failed in some part; means nhentai changed how
            # thumbnail images are displayed in category page.
            self._logger.error(
                "[Assumption Error: regex match for page thumbnails failed] "
                f"[{str(e)}] "
                "Most likely nhentai made changes to their website. "
                f"URL={self._current_url.format(self._current_page_page_number)}"
            )
            return

        self.page_ready_signal.emit(total_galleries)

    def _parse_gallery_html(self) -> None:
        text = self._network_access_manager.reply.readAll().data().decode("utf-8")
        soup = BeautifulSoup(text, "lxml")

        try:
            res = soup.find("a", href=self._gallery_page_link_pattern)
            self._galleries = iter(
                (
                    (
                        int(
                            self._cdn_server_pattern.findall(res.noscript.img["src"])[0]
                        ),
                        int(self._gallery_page_link_pattern.findall(res["href"])[0]),
                    ),
                )
            )
        except (
            AttributeError,  # For dot notations with soup.
            TypeError,
            # For `for gallery_url in soup.find_all('a', href=self._gallery_link_pattern)`
            # (failure returns `None`).
            # And subscriptions with None.
            KeyError,  # For subscriptions
        ) as e:
            # Means the regex failed in some part; means nhentai changed how
            # thumbnail images are displayed in gallery page.
            self._logger.error(
                "[Assumption Error: regex match for gallery page failed] "
                f"[{str(e)}] "
                "Most likely nhentai made changes to their website. "
                f"URL={self._current_url.format(self._current_page_page_number)}"
            )
            return

        self.page_ready_signal.emit(1)

    def _get_page_finished_slot(self) -> None:
        handled = self._network_access_manager.handle_error(
            self._network_access_manager.reply.error()
        )
        if handled == 203:
            # Wrong page number looks like: https://www.nhentai.net/artist/kanju/?page=1111111
            # i.e. not a 404 HTTP error.
            self._logger.error(
                "[Assumption Error: Unable to load gallery metadata] "
                "Most likely nhentai made changes to their website. "
                f"URL={self._network_access_manager.reply.url().toString()}"
            )
            return
        elif handled != 0:
            return

        self._parse_page_html()

    def get_page(self, url: str) -> None:
        self._current_url = url
        self._current_page_page_number = 1
        self._network_access_manager.set_request_url(
            url.format(self._current_page_page_number)
        )
        self._network_access_manager.get(
            reconnect_callback=lambda: self.get_page(url),
            finished=self._get_page_finished_slot,
        )

    def _get_next_page(self) -> None:
        self._network_access_manager.set_request_url(
            self._current_url.format(self._current_page_page_number)
        )
        self._network_access_manager.get(
            reconnect_callback=self._get_next_page,
            finished=self._get_page_finished_slot,
        )

    def next_gallery(self) -> int:
        try:
            self._current_gallery = next(self._galleries)
        except StopIteration:
            self._get_next_page()
            return -1
        else:
            return self._current_gallery

    def _get_gallery_CDN_server_finished_slot(self) -> None:
        handled = self._network_access_manager.handle_error(
            self._network_access_manager.reply.error()
        )
        if handled == 203:
            self.item_invalid_signal.emit()
            return
        elif handled != 0:
            return

        self._parse_gallery_html()

    def get_gallery_CDN_server(self, gallery_id: int) -> None:
        self._current_url = GALLERY_PAGE.format(gallery_id=gallery_id)
        self._current_page_page_number = 1
        self._network_access_manager.set_request_url(self._current_url)
        self._network_access_manager.get(
            reconnect_callback=lambda: self.get_gallery_CDN_server(gallery_id),
            finished=self._get_gallery_CDN_server_finished_slot,
        )

    def get_download_item_url(self, item: str) -> str:
        """
        Gets category url-> URL for specified item, based on user selections.

        Returns
        --------
            str:
                Search URL for specified item.
                Example: https://nhentai.net/artist/kanju/popular?page=2

        """
        if self._download_category == "":
            self._item = "gallery"
            return item

        self._item = item

        download_item_url = (
            CATEGORY_URL.format(category=self._download_category, item=item)
            + self._order_by
            + "?page={}"
        )

        return download_item_url

    def _get_gallery_metadata_finished_slot(self) -> None:
        handled = self._network_access_manager.handle_error(
            self._network_access_manager.reply.error()
        )
        if handled == 203:
            self._logger.error(
                "[Assumption Error: Unable to load gallery metadata] "
                "Most likely nhentai made changes to their website. "
                f"URL={self._network_access_manager.reply.url().toString()}"
            )
            return
        elif handled != 0:
            return

        self._extract_gallery_metadata()

    def get_gallery_metadata(self, gallery_id: int) -> None:
        self._network_access_manager.set_request_url(
            GALLERY_JSON.format(gallery_id=gallery_id)
        )
        self._network_access_manager.get(
            reconnect_callback=lambda: self.get_gallery_metadata(gallery_id),
            finished=self._get_gallery_metadata_finished_slot,
        )

    def _extract_gallery_metadata(self) -> nhentaiGalleryMetadata:
        reply_text = self._network_access_manager.reply.readAll().data().decode("utf-8")
        try:
            json_data = json.loads(reply_text)
        except json.JSONDecodeError as e:
            self._logger.error(
                "[Assumption Error: unable to load gallery metadata JSON from API] "
                f"[{str(e)}] "
                "Most likely nhentai made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1]}"
            )
            return

        try:
            gallery_id = int(json_data.get("id"))
        except TypeError as e:  # Can't use None with `int()`.
            self._logger.error(
                "[Assumption Error: unable to get gallery ID from metadata JSON] "
                f"[{str(e)}] "
                "Most likely nhentai made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1]}"
            )
            return

        try:
            media_id = int(json_data.get("media_id"))
        except TypeError as e:  # Can't use None with `int()`.
            self._logger.error(
                "[Assumption Error: unable to get media ID from metadata JSON] "
                f"[{str(e)}] "
                "Most likely nhentai made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1]}"
            )
            return

        try:
            title = json_data.get("title").get("english")
        except AttributeError as e:  # 'NoneType' object has no attribute 'get'
            self._logger.error(
                "[Assumption Error: unable to get English title from metadata JSON] "
                f"[{str(e)}] "
                "Most likely nhentai made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1]}"
            )
            return

        try:
            japanese_title = json_data.get("title").get("japanese")
        except AttributeError as e:  # 'NoneType' object has no attribute 'get'
            self._logger.error(
                "[Assumption Error: unable to get Japanese title from metadata JSON] "
                f"[{str(e)}] "
                "Most likely nhentai made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1]}"
            )
            return

        try:
            artists = [
                tag["name"]
                for tag in json_data.get("tags")
                if tag.get("type") == "artist"
            ]
        except TypeError as e:  # NoneType is not iterable.
            self._logger.error(
                "[Assumption Error: unable to get artist(s) list from metadata JSON] "
                f"[{str(e)}] "
                "Most likely nhentai made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1]}"
            )
            return
        except KeyError as e:
            self._logger.error(
                "[Assumption Error: unable to get artist(s) names from metadata JSON] "
                f"[{str(e)}] "
                "Most likely nhentai made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1]}"
            )
            return

        try:
            groups = [
                tag["name"]
                for tag in json_data.get("tags")
                if tag.get("type") == "group"
            ]
        except TypeError as e:  # NoneType is not iterable.
            self._logger.error(
                "[Assumption Error: unable to get group(s) list from metadata JSON] "
                f"[{str(e)}] "
                "Most likely nhentai made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1]}"
            )
            return
        except KeyError as e:
            self._logger.error(
                "[Assumption Error: unable to get group(s) names from metadata JSON] "
                f"[{str(e)}] "
                "Most likely nhentai made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1]}"
            )
            return

        try:
            type_ = [
                tag["name"]
                for tag in json_data.get("tags")
                if tag.get("type") == "category"
            ]
        except TypeError as e:  # NoneType is not iterable.
            self._logger.error(
                "[Assumption Error: unable to get category from metadata JSON] "
                f"[{str(e)}] "
                "Most likely nhentai made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1]}"
            )
            return
        except KeyError as e:
            self._logger.error(
                "[Assumption Error: unable to get category name from metadata JSON] "
                f"[{str(e)}] "
                "Most likely nhentai made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1]}"
            )
            return

        try:
            language = [
                tag["name"]
                for tag in json_data.get("tags")
                if tag.get("type") == "language" and tag.get("name") != "translated"
            ]
        except TypeError as e:  # NoneType is not iterable.
            self._logger.error(
                "[Assumption Error: unable to get language from metadata JSON] "
                f"[{str(e)}] "
                "Most likely nhentai made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1]}"
            )
            return

        except KeyError as e:
            self._logger.error(
                "[Assumption Error: unable to get language names from metadata JSON] "
                f"[{str(e)}] "
                "Most likely nhentai made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1]}"
            )
            return

        try:
            series = [
                tag["name"]
                for tag in json_data.get("tags")
                if tag.get("type") == "parody"
            ]
        except TypeError as e:  # NoneType is not iterable.
            self._logger.error(
                "[Assumption Error: unable to get parodies list from metadata JSON] "
                f"[{str(e)}] "
                "Most likely nhentai made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1]}"
            )
            return
        except KeyError as e:
            self._logger.error(
                "[Assumption Error: unable to get parodies names from metadata JSON] "
                f"[{str(e)}] "
                "Most likely nhentai made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1]}"
            )
            return

        try:
            characters = [
                tag["name"]
                for tag in json_data.get("tags")
                if tag.get("type") == "character"
            ]
        except TypeError as e:  # NoneType is not iterable.
            self._logger.error(
                "[Assumption Error: unable to get character(s) list from metadata JSON] "
                f"[{str(e)}] "
                "Most likely nhentai made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1]}"
            )
            return
        except KeyError as e:
            self._logger.error(
                "[Assumption Error: unable to get character(s) names from metadata JSON] "
                f"[{str(e)}] "
                "Most likely nhentai made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1]}"
            )
            return

        try:
            tags = [
                tag["name"] for tag in json_data.get("tags") if tag.get("type") == "tag"
            ]
        except TypeError as e:  # NoneType is not iterable.
            self._logger.error(
                "[Assumption Error: unable to get tag(s) list from metadata JSON] "
                f"[{str(e)}] "
                "Most likely nhentai made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1]}"
            )
            return
        except KeyError as e:
            self._logger.error(
                "[Assumption Error: unable to get tag(s) names from metadata JSON] "
                f"[{str(e)}] "
                "Most likely nhentai made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1]}"
            )
            return

        try:
            upload_date = int(json_data.get("upload_date"))
        except TypeError as e:  # utcfromtimestamp requires an integer (got type NoneType).
            self._logger.error(
                "[Assumption Error: unable to get upload date from metadata JSON] "
                f"[{str(e)}] "
                "Most likely nhentai made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1]}"
            )
            return
        except ValueError as e:  # Invalid literal for int() with base 10: '...'
            self._logger.error(
                "[Assumption Error: unable to get upload date from metadata JSON] "
                f"[{str(e)}] "
                "Most likely nhentai made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1]}"
            )
            return

        try:
            files = nhentaiFileMetadata()
            server_n, gallery_id = self._current_gallery
            for page_n, file_dict in enumerate(
                json_data.get("images").get("pages"), start=1
            ):
                files.insert(
                    file_url=IMAGE_URL_FORMAT.format(
                        server_n=server_n,
                        media_id=media_id,
                        page_n=page_n,
                        ext=EXTENSIONS[file_dict.get("t")],
                    ),
                    filename=str(page_n),
                    ext=EXTENSIONS[file_dict.get("t")],
                )
        except (
            TypeError,  # 'NoneType' object is not iterable.
            AttributeError,  # 'NoneType' has no attribute 'get'.
        ) as e:
            self._logger.error(
                "[Assumption Error: unable to extract file(s) data from metadata JSON] "
                f"[{str(e)}] "
                "Most likely nhentai made changes to their website. "
                f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1]}"
            )
            return
        except KeyError as e:  # For EXTENSIONS[file_dict.get('t')]
            if e.args[0] == None:
                self._logger.error(
                    "[Assumption Error: unable to extract file(s) extensions from metadata JSON] "
                    f"[{str(e)}] "
                    "Most likely nhentai made changes to their website. "
                    f"GALLERY ID={self._network_access_manager.reply.url().toString().split('/')[-1]}"
                )
            else:
                self._logger.error(
                    "Unexpected image file format: " f"FORMAT={file_dict.get('t')}"
                )
            return

        gallery_metadata = nhentaiGalleryMetadata(
            gallery_id=gallery_id,
            media_id=media_id,
            title=title,
            japanese_title=japanese_title,
            artists=artists or ["---"],
            groups=groups or ["---"],
            type=type_ or ["---"],
            language=language or ["---"],
            series=series or ["---"],
            characters=characters or ["---"],
            tags=tags or ["---"],
            upload_date=upload_date,
            files=files,
            source="nhentai",
        )

        gallery_metadata.set_location(
            self._destination_formats[self._download_type],
            self._item,
        )
        self.metadata_ready_signal.emit(gallery_metadata)
