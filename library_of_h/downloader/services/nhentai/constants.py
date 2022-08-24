DOWNLOAD_TYPES = {
    "Artist(s)": "artist",
    "Character(s)": "character",
    "Gallery ID(s)": "",
    "Group(s)": "group",
    "Parody(s)": "parody",
    "Tag(s)": "tag",
}
ORDER_BY = ("Recent", "Today", "Week", "All time")
EXTENSIONS = {"j": "jpg", "p": "png"}

############################## WEBSITE constants ###############################
ROOT_URL = "https://www.nhentai.net/"
CATEGORY_URL = "https://www.nhentai.net/{category}/{item}"
GALLERY_PAGE = "https://nhentai.net/g/{gallery_id}"
GALLERY_JSON = "https://nhentai.net/api/gallery/{gallery_id}"
SEARCH_FORMAT = "https://nhentai.net/search/?q={query}"
SEARCH_SORT_FORMAT = "&sort=popular{sort_order}"
IMAGE_URL_FORMAT = "https://i{server_n}.nhentai.net/galleries/{media_id}/{page_n}.{ext}"
################################################################################
