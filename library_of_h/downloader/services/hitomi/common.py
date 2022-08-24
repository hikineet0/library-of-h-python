from __future__ import annotations

import importlib
import re

from library_of_h.downloader.services.hitomi.metadata import HitomiFileMetadata

from . import gg


def _subdomain_from_url(url, base) -> str:
    retval = "b"
    if base:
        retval = base

    b = 16

    r = re.compile("\/[0-9a-f]{61}([0-9a-f]{2})([0-9a-f])")
    m = r.search(url)
    if not m:
        return "a"

    g = int(m[2] + m[1], b)
    if not g is None:
        importlib.reload(gg)
        retval = chr(97 + gg.m(g)) + retval

    return retval


def url_from_url(url, base=None) -> str:
    return re.sub(
        "\/\/..?\.hitomi\.la\/",
        ("//" + _subdomain_from_url(url, base) + ".hitomi.la/"),
        url,
    )


def _full_path_from_hash(hash) -> str:
    importlib.reload(gg)
    return gg.b + gg.s(hash) + "/" + hash


def _real_full_path_from_hash(hash) -> str:
    return re.sub("^.*(..)(.)$", "$2/$1/" + hash, hash)


def _url_from_hash(file: HitomiFileMetadata, dir: str, ext: str) -> str:
    ext = ext or dir or file.filename.split(".").pop()
    dir = dir or "images"
    return (
        "https://a.hitomi.la/"
        + dir
        + "/"
        + _full_path_from_hash(file.hash_)
        + "."
        + ext
    )


def url_from_url_from_hash(
    galleryid: int,
    file: HitomiFileMetadata,
    dir: str = None,
    ext: str = None,
    base: str = None,
):
    if base == "tn":
        return url_from_url(
            "".join(
                "https://a.hitomi.la/"
                + dir
                + "/"
                + _real_full_path_from_hash(file.hash_)
                + "."
                + ext
            ),
            base,
        )
    return url_from_url(_url_from_hash(file, dir, ext), base)
