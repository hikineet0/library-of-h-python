from __future__ import annotations

from typing import Generator

from library_of_h.database_manager.main import DatabaseManager
from library_of_h.downloader.base_classes.service import ServiceBase
from library_of_h.downloader.custom_sub_classes.download_files_model import \
    DownloadFilesModel
from library_of_h.downloader.custom_sub_classes.download_items_model import \
    DownloadItemsModel
from library_of_h.downloader.filter import Filter
from library_of_h.downloader.output_dialog import OutputDialog
from library_of_h.downloader.services.hitomi.common import (
    url_from_url, url_from_url_from_hash)
from library_of_h.downloader.services.hitomi.downloader import HitomiDownloader
from library_of_h.downloader.services.hitomi.extractor import HitomiExtractor
from library_of_h.downloader.services.hitomi.metadata import (
    HitomiFileMetadata, HitomiGalleryMetadata)
from library_of_h.downloader.services.hitomi.network_access_manager import \
    HitomiNetworkAccessManager
from library_of_h.signals_hub.signals_hub import downloader_signals


class Hitomi(ServiceBase):

    _current_working_gallery_metadata: HitomiGalleryMetadata

    def _initialize_session(
        self,
        items: str,
        download_type: str,
        order_by: str,
    ):
        self._logger.debug("Initializing session.")
        self._total_download_time_elapsed_timer.restart()
        downloader_signals.download_session_began_signal.emit()

        self._session_summary = {
            "items completed": 0,
            "items invalid": 0,
            "galleries downloaded": 0,
            "galleries filtered": 0,
            "galleries already downloaded": 0,
            "files downloaded": 0,
            "files already downloaded": 0,
            "total download size": 0,
            "total time taken": 0,
        }

        self._download_type = download_type
        if download_type == "Tag(s)":
            items = items.replace("f:", "female:")
            items = items.replace("m:", "male:")

        items = [item.strip() for item in items.lower().split(",")]

        self._logger.debug("Setting filters.")
        self._filter = Filter()

        self._logger.debug("Instanciating classes.")

        self._database_manager = DatabaseManager.get_instance()

        self._network_access_manager = HitomiNetworkAccessManager()

        self._output_dialog = OutputDialog(parent=self.parent().parent())

        self._extractor = HitomiExtractor()
        self._downloader = HitomiDownloader()

        self._logger.debug("Setting up instances.")

        self._extractor.metadata_ready_signal.connect(self._metadata_ready_slot)
        self._extractor.nozomi_ready_signal.connect(self._nozomi_ready_slot)
        self._extractor.item_finished_signal.connect(self._end_item_download)
        self._extractor.item_invalid_signal.connect(self._item_invalid_slot)
        self._extractor.set_network_access_manager(self._network_access_manager)
        self._extractor.set_user_selections(
            download_type=download_type, order_by=order_by
        )

        self._downloader.gallery_file_already_exist_signal.connect(
            self._gallery_file_already_exists_slot
        )
        self._downloader.get_file_signal.connect(self._get_file_slot)
        self._downloader.file_finished_signal.connect(self._end_file_download)
        self._downloader.set_network_access_manager(self._network_access_manager)

        self._output_dialog.canceled_signal.connect(self._output_dialog_canceled_slot)

        self._network_access_manager.gg_error_handled_signal.connect(
            self._gg_error_handled_slot
        )

        self._output_table_view.remove_table_model()

        self._logger.debug("Preparing download items data model.")
        if hasattr(self, "_download_items_model"):
            self._download_items_model.deleteLater()
            del self._download_items_model

        self._download_items_model = DownloadItemsModel()

        for element in items:  # Comma separated items.
            # Doesn't look like hitomi uses commas in URL, solely based on
            # https://hitomi.la/series/slime%20taoshite%20300-nen%20shiranai%20uchi%20ni%20level%20max%20ni%20nattemashita-all.html
            # which has a comma in it's title, according to
            # https://myanimelist.net/anime/40586/Slime_Taoshite_300-nen_Shiranai_Uchi_ni_Level_Max_ni_Nattemashita
            self._download_items_model.add_item(
                item_name=element.strip(), download_type=download_type
            )
        self._logger.info(
            f"{self._download_items_model.rowCount()} {('item', 'items')[self._download_items_model.rowCount() != 1]} found."
        )
        self._output_table_view.setModel(self._download_items_model)

        self._session_initialized.emit()

    # MISCELLANEOUS METHODS
    def _get_file_url(self, file: HitomiFileMetadata) -> str:
        """
        Gets the URL corresponding to the `file` following the process that
        Hitomi.la has for it.
        """
        id = self._current_working_gallery_metadata.gallery_id
        if file.haswebp:
            url = url_from_url_from_hash(id, file, "webp", None, "a")
        else:
            url = url_from_url_from_hash(id, file)
        return url

    def _get_next_anime_file(self) -> Generator:
        """
        For when the gallery is an anime gallery.
        Only ever yields a single value.
        """
        try:
            filename = next(self._download_files_model).filename
        except (StopIteration, ValueError):
            self._end_gallery_download()
        else:
            self._downloader.set_current_working_local_file(filename)

        url = "https:" + url_from_url(
            "//g.hitomi.la/videos/"
            + self._current_working_gallery_metadata.videofilename
        )
        yield url

    def _get_next_image_file(self) -> Generator:
        """
        Generator that yields file URLs.
        """
        # URL can change due to gg.js changing, but fret not, just call
        # this function and you get the new URL!
        for file in self._current_working_gallery_metadata.files:
            try:
                filename = next(self._download_files_model).filename
            except (StopIteration, ValueError):
                self._end_gallery_download()
            else:
                self._downloader.set_current_working_local_file(filename)

                url = self._get_file_url(file)
                if url is None:
                    return

                while True:
                    get_previous = yield url
                    if get_previous is True:
                        yield file
                    break

    # BEGIN METHODS
    def _begin_item_download(self, url_or_gallery_id: str) -> None:
        """
        Start download of the next item.

        Parameters
        -----------
            url_or_gallery_id (str):
                Nozomi URL for the item or the gallery ID if download type is
                "Gallery ID(s)".
        """
        self._logger.info(
            f'Begin item download: ITEM="{self._download_items_model.current().item_name}"'
        )
        if self._download_type == "Gallery ID(s)":
            try:
                gallery_id = int(url_or_gallery_id)
            except ValueError:
                self._item_invalid_slot()
            else:
                self._begin_gallery_download(total_galleries=1, gallery_id=gallery_id)
        else:
            self._extractor.fetch_nozomi(url_or_gallery_id)
            self._download_items_model.setData(
                index=self._download_items_model.get_current_index().status,
                value=0,
                for_="status",
            )  # Set current item as downloading.

    def _begin_gallery_download(self, total_galleries: int, gallery_id: int) -> None:
        """
        Begin the download of/from the first gallery of the current item.

        Parameters
        -----------
            total_galleries (int):
                Total number of galleries in current item.
            gallery_id (int):
                Gallery ID to download.
        """
        self._logger.info(
            f"{total_galleries} {('gallery', 'galleries')[total_galleries != 1]} found."
        )
        self._output_dialog.set_gallery_progress_max_value(total_galleries)
        self._logger.info(f"Begin gallery download: GALLERY ID={gallery_id}")
        self._extractor.get_gallery_metadata(gallery_id)

    def _begin_file_download(self) -> None:
        """
        Prepares files; creates files model, sets table modelfor
        output dialog.

        Parameters
        -----------
            gallery_metadata (GalleryMetadata):
                A gallery's metadata.
        """
        total_files = (
            1
            if not self._current_working_gallery_metadata.videofilename is None
            else self._current_working_gallery_metadata.pages
        )

        self._logger.info(f"{total_files} files found.")
        self._logger.debug("Preparing files data model.")
        self._output_dialog.set_file_progress_max_value(total_files)

        if hasattr(self, "_download_files_model"):
            self._download_files_model.deleteLater()
            del self._download_files_model

        self._download_files_model = DownloadFilesModel(
            self._current_working_gallery_metadata.files.formatted_filename
        )
        self._downloader.set_download_files_model(self._download_files_model)
        self._output_dialog.set_table_model(self._download_files_model)

        self._downloader.download()

    # CONTINUE METHODS
    def _continue_gallery_download(self) -> None:
        self._output_dialog.update_gallery_progress()
        # Here because each gallery will have a new set of files.
        self._output_dialog.reset_file_progress_value()
        self._output_dialog.remove_table_model()

        if (gallery_id := self._extractor.next_nozomi()) != -1:
            # -1 denotes "no more items left"
            self._logger.info(f"Begin gallery download: GALLERY ID={gallery_id}")
            self._extractor.get_gallery_metadata(gallery_id)

    # SLOTS
    def _get_file_slot(self, type_: str) -> None:
        self._file_url_generator = getattr(self, f"_get_next_{type_}_file")()
        try:
            url = next(self._file_url_generator)
        except StopIteration:
            self._end_gallery_download()
        else:
            self._downloader.start_file_download(url)

    def _gg_error_handled_slot(self) -> None:
        url = self._get_file_url(self._file_url_generator.send(True))
        if url is None:
            return

        self._downloader.start_file_download(url)

    def _nozomi_ready_slot(self, total_galleries: int) -> None:
        gallery_id = self._extractor.next_nozomi()
        if gallery_id != -1:
            self._begin_gallery_download(
                total_galleries=total_galleries, gallery_id=gallery_id
            )
