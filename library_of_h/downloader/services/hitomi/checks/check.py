import re

import requests

__all__ = ["check_fetch_nozomi", "check_gg_js"]


def check_fetch_nozomi() -> bool:
    with open("hitomi_downloader/checks/fetch_nozomi.js") as file:
        fetch_nozomi = file.read().strip()

    res = requests.get("https://ltn.hitomi.la/galleryblock.js")
    if not res.ok:
        return False
    match = (
        re.search("(function fetch_nozomi()(.|\n)*)function set_title()", res.text)
        .group(1)
        .strip()
    )

    return match == fetch_nozomi


def check_gg_js() -> bool:
    from library_of_h.downloader.services.hitomi.template import (gg_js_0,
                                                                  gg_js_1)

    res = requests.get("https://ltn.hitomi.la/gg.js")
    if not res.ok:
        res.raise_for_status

    online_text = res.text

    if re.search(gg_js_0, online_text) or re.search(gg_js_1, online_text):
        return True
    else:
        return False
