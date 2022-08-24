import os
from datetime import datetime

from PIL import Image
from PySide6 import QtCore as qtc
from PySide6 import QtGui as qtg
from PySide6 import QtSql

from library_of_h.explorer.constants import (DESCRIPTION_HTML_FIELDS,
                                             TAGS_SEX_MAPPING, THUMBNAIL_SIZE)
from library_of_h.miscellaneous.functions import get_value_and_unit_from_Bytes


class CreateBrowserItemWorker(qtc.QObject):

    browser_item_batch_finished_signal = qtc.Signal()
    batch_started_signal = qtc.Signal()
    item_created_signal = qtc.Signal(int, qtg.QImage, dict)
    item_not_found_signal = qtc.Signal(list)

    def _create_description_dict(self, record: QtSql.QSqlRecord) -> str:

        description_dict = {}

        for field in DESCRIPTION_HTML_FIELDS["singles"]:
            value = record.value(field)
            if isinstance(value, str):
                if not field in ("type", "location"):
                    description_dict[field] = record.value(field).title()
                else:
                    description_dict[field] = record.value(field)
            else:
                if field == "udate":
                    description_dict[field] = datetime.fromtimestamp(
                        int(record.value(field))
                    ).date()
                elif field == "size_in_bytes":
                    description_dict[field] = " ".join(
                        map(str, get_value_and_unit_from_Bytes(record.value(field)))
                    )
                else:
                    description_dict[field] = record.value(field)
        for field in DESCRIPTION_HTML_FIELDS["lists"]:
            description_dict[field] = ", ".join(
                value.title() for value in record.value(field).split(",")
            )

        return description_dict

    def _create_thumbnail(self, record: QtSql.QSqlRecord) -> tuple[qtg.QImage, bool]:
        location = record.value("location")
        if os.path.exists(location):
            file = os.path.join(location, sorted(os.listdir(location))[0])
            image = Image.open(file)
            if image.width > THUMBNAIL_SIZE[0] or image.height > THUMBNAIL_SIZE[0]:
                image.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
            source = image.toqimage()

            # Create a blank `QImage` with `THUMBNAIL_SIZE` dimensions:
            qimage = qtg.QImage(
                *THUMBNAIL_SIZE, source.format()
            )  # The maximum area for a thumbnail image.
            # Make it black.
            qimage.fill(qtc.Qt.GlobalColor.transparent)

            # Create a `QPainter` to draw on the blank `QImage`.
            temp_painter = qtg.QPainter(qimage)

            # Get the bounding box of the source image.
            image_rect = source.rect()  # The area of the actual thumbnail image.
            # Move the center of the bounding box of the source image to the
            # center of the bounding box of the blank `QImage`.
            image_rect.moveCenter(qimage.rect().center())
            # Now `image_rect`'s dimensions are the exact dimensions of the
            # source image if placed at the center of the thumbnail area.

            # Finally, draw the source image onto the thumbnail area using
            # `image_rect`'s dimensions.
            temp_painter.drawImage(
                # The (x,y) co-ordinates for the start of `image_rect`.
                image_rect.topLeft(),
                source,
            )

            temp_painter.end()
            return qimage, True
        else:
            qimage = qtg.QImage("assets:/not_found.svg")
            return qimage, False

    def create_items(self):
        gallery_not_founds = []

        for index, record in enumerate(self._records):
            if (thumbnail := self._create_thumbnail(record))[1] is False:
                gallery_not_founds.append(
                    (record.value("gallery_database_id"), record.value("location"))
                )
            description_dict = self._create_description_dict(record)
            self.item_created_signal.emit(index, thumbnail[0], description_dict)

        if gallery_not_founds:
            self.item_not_found_signal.emit(gallery_not_founds)

        self.browser_item_batch_finished_signal.emit()

    def prepare(self, records: list[QtSql.QSqlRecord]) -> None:
        self._records = records
