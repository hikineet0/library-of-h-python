THUMBNAIL_SIZE = (200, 200)
BROWSER_IMAGES_LIMIT = 25
BROWSER_ITEMS_V_SPACING = 10
SELECTION_TINT_WIDTH = 20
DESCRIPTION_OBJECT_ROLE = -1

TAGS_SEX_MAPPING = {
    -1: "",
    0: "F",
    1: "M",
}

DESCRIPTION_HTML_FIELDS = {
    "singles": [
        "title",
        "jtitle",
        "gallery",
        # lists
        "language",
        "type",
        "udate",
        "pages",
        "source",
        "location",
        "size_in_bytes",
    ],
    "lists": ["series", "character", "tag", "artist", "group"],
}
DESCRIPTION_HTML_TEMPLATE = """<h2>{title}</h2>
<h3>{jtitle}</h3>
<h4>{gallery}</h4>
<p>
<b>Series: </b>{series}<br/>
<b>Characters: </b>{character}<br/>
<b>Tags: </b>{tag}<br/>
<b>Artists: </b>{artist}<br/>
<b>Groups: </b>{group}<br/>
<b>Language: </b>{language}<br/>
<b>Type: </b>{type}<br/>
<b>Uploaded: </b>{udate}<br/>
<b>Pages: </b>{pages}<br/>
<b>Source: </b>{source}<br/>
<b>Location: </b>{location}<br/>
<b>Size: </b>{size_in_bytes}<br/>
</p>
"""

ACTION_GROUP_MAPPING = {
    "By &Download Date": "download_date",
    "By &Japanese Title": "japanese_title",
    "By &Pages": "pages",
    "By &Size": "size_in_bytes",
    "By &Title": "title",
    "By &Upload Date": "upload_date",
    "&Ascending": "ASC",
    "D&escending": "DESC",
}
