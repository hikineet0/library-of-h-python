from dataclasses import dataclass, field

from library_of_h.downloader.base_classes.metadata import (FileMetadataBase,
                                                           GalleryMetadataBase)


@dataclass
class nhentaiGalleryMetadata(GalleryMetadataBase):
    media_id: int = field(init=True)


class nhentaiFileMetadata(FileMetadataBase):
    pass
