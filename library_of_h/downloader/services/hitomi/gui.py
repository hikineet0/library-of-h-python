from library_of_h.downloader.base_classes.gui import GUIBase
from library_of_h.downloader.services.hitomi.constants import (DOWNLOAD_TYPES,
                                                               ORDER_BY)


class HitomiGUI(GUIBase):
    _DOWNLOAD_TYPES = tuple(DOWNLOAD_TYPES.keys())
    _ORDER_BY = ORDER_BY
    _TOP_WIDGETS = ("file_download", "download")
    _BOTTOM_WIDGETS = (
        "download_type_combo_box",
        "order_by_combo_box",
    )
