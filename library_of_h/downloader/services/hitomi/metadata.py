from dataclasses import dataclass, field
from typing import NamedTuple

from library_of_h.downloader.base_classes.metadata import (FileMetadataBase,
                                                           GalleryMetadataBase)


@dataclass
class HitomiGalleryMetadata(GalleryMetadataBase):

    video: str = field(init=True, default=None)
    videofilename: str = field(init=True, default=None)

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.type == "anime":
            self.pages = 1


class FilesData(NamedTuple):
    filename: list[str]
    ext: list[str]
    formatted_filename: list[str]
    hash_: list[str]
    hasavif: list[bool]
    haswebp: list[bool]


class FileData(NamedTuple):
    filename: str
    ext: str
    formatted_filename: str
    hash_: str
    hasavif: bool
    haswebp: bool


class HitomiFileMetadata(FileMetadataBase):

    __slots__ = "_data"

    _dat: FilesData

    def __init__(self) -> None:
        self._data = FilesData([], [], [], [], [], [])

    def insert(self, filename: str, ext: str, hash_: str, hasavif: bool, haswebp: bool):
        self._data.filename.append(filename)
        self._data.ext.append(ext)
        self._data.formatted_filename.append("")
        self._data.hash_.append(hash_)
        self._data.hasavif.append(hasavif)
        self._data.haswebp.append(haswebp)

    def __iter__(self) -> None:
        return map(FileData, *self._data)

    def __getitem__(self, index: int) -> FileData:
        return FileData(
            self._data.filename[index],
            self._data.ext[index],
            self._data.formatted_filename[index],
            self._data.hash_[index],
            self._data.hasavif[index],
            self._data.haswebp[index],
        )
