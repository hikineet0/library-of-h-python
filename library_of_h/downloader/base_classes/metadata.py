from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Iterator, List, NamedTuple

from PySide6 import QtCore as qtc

from library_of_h.miscellaneous.functions import validate_pathname


class FilesData(NamedTuple):
    file_url: list[str]
    filename: list[str]
    ext: list[str]
    formatted_filename: list[str]


class FileData(NamedTuple):
    file_url: str
    filename: str
    ext: str
    formatted_filename: str


class FileMetadataBase:

    __slots__ = "_data"

    _data: FilesData

    def __init__(self) -> None:
        self._data = FilesData([], [], [], [])

    def insert(self, file_url: str, filename: str, ext: str) -> None:
        self._data.file_url.append(file_url)
        self._data.filename.append(filename)
        self._data.ext.append(ext)
        self._data.formatted_filename.append("")

    def set_formatted_filename(self, formatted_filename: str, index: int) -> None:
        self._data.formatted_filename[index] = formatted_filename

    def __getattr__(self, attr: str) -> Any:
        return getattr(self._data, attr)

    def __len__(self) -> int:
        return len(self._data.filename)

    def __iter__(self) -> Iterator:
        return map(FileData, *self._data)

    def __getitem__(self, index: int) -> FileData:
        return FileData(
            self._data.file_url[index],
            self._data.filename[index],
            self._data.ext[index],
            self._data.formatted_filename[index],
        )


@dataclass
class GalleryMetadataBase:

    title: str
    japanese_title: str
    gallery_id: int
    series: list[str]
    characters: list[str]
    tags: list[str]
    artists: list[str]
    groups: list[str]
    language: list[str]
    type: list[str]
    upload_date: int
    source: str

    files: List[FileMetadataBase] = field(init=True)

    original_title: str = field(init=False)
    translated_title: str = field(init=False)
    artist_name: str = field(init=False)
    group_name: str = field(init=False)
    pages: int = field(init=False)
    location: str = field(init=False)

    def __post_init__(self) -> None:
        (self.original_title, self.translated_title) = (
            self.title.split("|")
            if "|" in self.title
            else ("original_title(NA)", "translated_title(NA)")
        )

        self.artist_name = self.artists[0]
        self.group_name = self.groups[0]

        self.pages = len(self.files)

        import math

        for i, file in enumerate(self.files):
            padding = int(math.log10(len(self.files))) + 1
            self.files.set_formatted_filename(f"{i + 1:0{padding}}.{file.ext}", i)

    def as_dict(self) -> dict:
        return {
            "gallery_id": self.gallery_id,
            "title": self.title,
            "japanese_title": self.japanese_title,
            "original_title": self.original_title,
            "translated_title": self.translated_title,
            "artist_name": self.artist_name,
            "group_name": self.group_name,
            "upload_date": self.upload_date,
        }

    def set_location(
        self,
        destination_format: str,
        item: str,
    ) -> bool:
        """
        Set location for gallery as metadata instance attribute.

        Returns
        --------
            bool: Denotes whether this method failed or not.
        """

        self.location = "/".join(
            validate_pathname(pathname)
            for pathname in qtc.QDir.cleanPath(
                os.path.abspath(destination_format.format(**self.as_dict(), item=item))
            ).split("/")
        )
