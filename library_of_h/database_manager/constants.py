FTS5_TABLE_NAME = "GalleriesFTS5"

SELECT_TEMPLATE = f"""\
SELECT
    {{select}}
FROM
    {FTS5_TABLE_NAME}
{{where}}
{{sort_by}} {{sort_order}}
{{limit_offset}}
"""
WHERE_TEMPLATE = f"""
WHERE
{{match}}
{{conditionals}}
"""

MATCH_TEMPLATE = f"""
{FTS5_TABLE_NAME}
{{query}}
"""

SELECT_MAPPING = {
    "artist": f'"artist"',
    "character": f'"character"',
    "group": f'"group"',
    "jtitle": f'"jtitle"',
    "language": f'"language"',
    "series": f'"series"',
    "tag": f'"tag"',
    "title": f'"title"',
    "source": f'"source"',
    "type": f'"type"',
    "gallery": f'"gallery"',
    "udate": f'"udate"',
    "ddate": f'"ddate"',
    "pages": f'"pages"',
    "size": f'"size_in_bytes"',
}

ORDER_BY_MAPPING = {
    "accuracy": f"rank",
    "size_in_bytes": f'"size_in_bytes"',
    "jtitle": f'"jtitle"',
    "pages": f'"pages"',
    "title": f'"title"',
    "udate": f'"udate"',
    "ddate": f'"ddate"',
}

TEXT_FILTER_OPTIONS = {
    "artist": ("=", "!=", "~=", "!~="),
    "character": ("=", "!=", "~=", "!~="),
    "group": ("=", "!=", "~=", "!~="),
    "jtitle": ("=", "!=", "~=", "!~="),
    "language": ("=", "!=", "~=", "!~="),
    "series": ("=", "!=", "~=", "!~="),
    "tag": ("=", "!=", "~=", "!~="),
    "title": ("=", "!=", "~=", "!~="),
    "source": ("=", "!=", "~=", "!~="),
    "type": ("=", "!=", "~=", "!~="),
}

MATCH_STATEMENT = "MATCH '{{\"{}\"}} : {}'".format(
    '" "'.join(TEXT_FILTER_OPTIONS.keys()), "{conditions}"
)

NUMERICAL_FILTER_OPTIONS = {
    "gallery": ("=", "<", ">", "<=", ">="),
    "udate": ("=", "<", ">", "<=", ">="),
    "ddate": ("=", "<", ">", "<=", ">="),
    "pages": ("=", "<", ">", "<=", ">="),
    "size": ("=", "<", ">", "<=", ">="),
}

VALID_KEYS = (TEXT_FILTER_OPTIONS | NUMERICAL_FILTER_OPTIONS).keys()

SEX_MAPPING = {"f": 0, "m": 1}

CREATE_QUERIES = [
    """
    CREATE TABLE IF NOT EXISTS "Artists"(
        "artist_id" INTEGER PRIMARY KEY,
        "artist_name" TEXT UNIQUE NOT NULL
    )""",
    """
    CREATE TABLE IF NOT EXISTS "Characters"(
        "character_id" INTEGER PRIMARY KEY,
        "character_name" TEXT UNIQUE NOT NULL
    )""",
    """
    CREATE TABLE IF NOT EXISTS "Groups"(
        "group_id" INTEGER PRIMARY KEY,
        "group_name" TEXT UNIQUE NOT NULL
    )""",
    """
    CREATE TABLE IF NOT EXISTS "Languages"(
        "language_id" INTEGER PRIMARY KEY,
        "language_name" TEXT UNIQUE NOT NULL
    )""",
    """
    CREATE TABLE IF NOT EXISTS "Series"(
        "series_id" INTEGER PRIMARY KEY,
        "series_name" TEXT UNIQUE NOT NULL
    )""",
    """
    CREATE TABLE IF NOT EXISTS "Sources"(
        "source_id" INTEGER PRIMARY KEY,
        "source_name" TEXT UNIQUE NOT NULL
    )""",
    """
    CREATE TABLE IF NOT EXISTS "Tags"(
        "tag_id" INTEGER PRIMARY KEY,
        "tag_name" TEXT NOT NULL
    )""",
    """
    CREATE TABLE IF NOT EXISTS "Types"(
        "type_id" INTEGER PRIMARY KEY,
        "type_name" TEXT UNIQUE NOT NULL
    )""",
    """
    CREATE TABLE IF NOT EXISTS "Artist_Gallery"(
        "artist_id" INTEGER NOT NULL,
        "gallery_id" INTEGER NOT NULL,

        UNIQUE("artist_id", "gallery_id"),
        
        FOREIGN KEY ("artist_id") REFERENCES "Artists"("artist_id") ON DELETE CASCADE,
        FOREIGN KEY ("gallery_id") REFERENCES "Galleries"("gallery_database_id") ON DELETE CASCADE
    )""",
    """
    CREATE TABLE IF NOT EXISTS "Character_Gallery"(
        "character_id" INTEGER NOT NULL,
        "gallery_id" INTEGER NOT NULL,

        UNIQUE("character_id", "gallery_id"),
        
        FOREIGN KEY ("character_id") REFERENCES "Characters"("character_id")
        ON DELETE CASCADE,
        FOREIGN KEY ("gallery_id") REFERENCES "Galleries"("gallery_database_id")
        ON DELETE CASCADE
    )""",
    """
    CREATE TABLE IF NOT EXISTS "Group_Gallery"(
        "group_id" INTEGER NOT NULL,
        "gallery_id" INTEGER NOT NULL,

        UNIQUE("group_id", "gallery_id"),
        
        FOREIGN KEY ("group_id") REFERENCES "Groups"("group_id")
        ON DELETE CASCADE,
        FOREIGN KEY ("gallery_id") REFERENCES "Galleries"("gallery_database_id")
        ON DELETE CASCADE
    )""",
    """
    CREATE TABLE IF NOT EXISTS "Language_Gallery"(
        "language_id" INTEGER NOT NULL,
        "gallery_id" INTEGER NOT NULL,

        UNIQUE("language_id", "gallery_id"),
        
        FOREIGN KEY ("language_id") REFERENCES "Languages"("language_id")
        ON DELETE CASCADE,
        FOREIGN KEY ("gallery_id") REFERENCES "Galleries"("gallery_database_id")
        ON DELETE CASCADE
    )""",
    """
    CREATE TABLE IF NOT EXISTS "Series_Gallery"(
        "series_id" INTEGER NOT NULL,
        "gallery_id" INTEGER NOT NULL,

        UNIQUE("series_id", "gallery_id"),
        
        FOREIGN KEY ("series_id") REFERENCES "Series"("series_id")
        ON DELETE CASCADE,
        FOREIGN KEY ("gallery_id") REFERENCES "Galleries"("gallery_database_id")
        ON DELETE CASCADE
    )""",
    """
    CREATE TABLE IF NOT EXISTS "Tag_Gallery"(
        "tag_id" INTEGER NOT NULL,
        "gallery_id" INTEGER NOT NULL,

        UNIQUE("tag_id", "gallery_id"),
        
        FOREIGN KEY ("tag_id") REFERENCES "Tags"("tag_id")
        ON DELETE CASCADE,
        FOREIGN KEY ("gallery_id") REFERENCES "Galleries"("gallery_database_id")
        ON DELETE CASCADE
    )""",
    """
    CREATE TABLE IF NOT EXISTS "Galleries"(
    "gallery_database_id" INTEGER PRIMARY KEY,
    "source" INTEGER NOT NULL,
    "gallery_id" INTEGER NULL,
    "title" TEXT NULL,
    "japanese_title" TEXT NULL,
    "type" INTEGER NOT NULL,
    "download_date" INTEGER NOT NULL,
    "upload_date" INTEGER NULL,
    "pages" INTEGER  NULL,
    "location" TEXT NOT NULL,
    "size_in_bytes" INTEGER NULL,
    "nhentai_media_id" INTEGER NULL,

    UNIQUE("source", "gallery_id"),

    FOREIGN KEY ("source") REFERENCES "Sources"("source_id")
    ON DELETE CASCADE,
    FOREIGN KEY ("type") REFERENCES "Types"("type_id")
    ON DELETE CASCADE
)""",
    """
    CREATE VIEW IF NOT EXISTS
        GalleriesView
    AS
        SELECT DISTINCT
            "Galleries"."gallery_database_id",
            "Galleries"."gallery_id" "gallery",
            GROUP_CONCAT(DISTINCT "Artists"."artist_name") "artist",
            GROUP_CONCAT(DISTINCT "Characters"."character_name") "character",
            GROUP_CONCAT(DISTINCT "Groups"."group_name") "group",
            "Galleries"."japanese_title" "jtitle",
            GROUP_CONCAT(DISTINCT "Languages"."Language_name") "language",
            GROUP_CONCAT(DISTINCT "Series"."series_name") "series",
            GROUP_CONCAT(DISTINCT "Tags"."tag_name") "tag",
            "Galleries"."title" "title",
            "Galleries"."upload_date" "udate",
            "Galleries"."download_date" "ddate",
            "Galleries"."pages" "pages",
            "Galleries"."size_in_bytes" "size_in_bytes",
            "Sources"."source_name" "source",
            "Types"."type_name" "type",
            "Galleries"."location" "location"
    FROM
        "Galleries"
    INNER JOIN
        "Artist_Gallery"
    ON
        ("Artist_Gallery"."gallery_id" = "Galleries"."gallery_database_id")
    INNER JOIN
        "Artists"
    ON
        ("Artist_Gallery"."artist_id" = "Artists"."artist_id")
    INNER JOIN
        "Character_Gallery"
    ON
        ("Character_Gallery"."gallery_id" = "Galleries"."gallery_database_id")
    INNER JOIN
        "Characters"
    ON
        ("Character_Gallery"."character_id" = "Characters"."character_id")
    INNER JOIN
        "Group_Gallery"
    ON
        ("Group_Gallery"."gallery_id" = "Galleries"."gallery_database_id")
    INNER JOIN
        "Groups"
    ON
        ("Group_Gallery"."group_id" = "Groups"."group_id")
    INNER JOIN
        "Language_Gallery"
    ON
        ("Language_Gallery"."gallery_id" = "Galleries"."gallery_database_id")
    INNER JOIN
        "Languages"
    ON
        ("Language_Gallery"."language_id" = "Languages"."language_id")
    INNER JOIN
        "Series_Gallery"
    ON
        ("Series_Gallery"."gallery_id" = "Galleries"."gallery_database_id")
    INNER JOIN
        "Series"
    ON
        ("Series_Gallery"."series_id" = "Series"."series_id")
    INNER JOIN
        "Tag_Gallery"
    ON
        ("Tag_Gallery"."gallery_id" = "Galleries"."gallery_database_id")
    INNER JOIN
        "Tags"
    ON
        ("Tag_Gallery"."tag_id" = "Tags"."tag_id")
    INNER JOIN
        "Types"
    ON
        ("Types"."type_id" = "Galleries"."type")
    INNER JOIN
        "Sources"
    ON
        ("Sources"."source_id" = "Galleries"."source")
    GROUP BY
        "Galleries"."gallery_database_id"
""",
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS
        GalleriesFTS5
    USING
        fts5(
            "gallery_database_id",
            "gallery",
            "artist",
            "character",
            "group",
            "jtitle",
            "language",
            "series",
            "tag",
            "title",
            "udate",
            "ddate",
            "pages",
            "size_in_bytes",
            "source",
            "type",
            "location",
            tokenize = "porter ascii",
            content="GalleriesView",
            content_rowid="gallery_database_id"
        )
""",
    """
    CREATE TRIGGER
        "Galleries_AftDel"
    AFTER
        DELETE
    ON
        "Galleries"
    BEGIN
        DELETE
        FROM
            GalleriesFTS5
        WHERE
            gallery_database_id = old.gallery_database_id;
    END
    """,
    """
    CREATE INDEX IF NOT EXISTS
        "IX_Galleries_gallery_id"
    ON
        "Galleries" ("gallery_id")
""",
    """
    CREATE INDEX IF NOT EXISTS
        "IX_Galleries_title"
    ON
        "Galleries" ("title" COLLATE NOCASE)
""",
    """
    CREATE INDEX IF NOT EXISTS
        "IX_Galleries_japanese_title"
    ON
        "Galleries" ("japanese_title" COLLATE NOCASE)
""",
    """
    CREATE INDEX IF NOT EXISTS
        "IX_Galleries_download_date"
    ON
        "Galleries" ("download_date")
""",
    """
    CREATE INDEX IF NOT EXISTS
        "IX_Galleries_upload_date"
    ON
        "Galleries" ("upload_date")
""",
    """
    CREATE INDEX IF NOT EXISTS
        "IX_Artists_artist_name"
    ON
        "Artists" ("artist_name" COLLATE NOCASE)
""",
    """
    CREATE INDEX IF NOT EXISTS
        "IX_Artist_Gallery_artist"
    ON
        "Artist_Gallery" ("artist_id")
""",
    """
    CREATE INDEX IF NOT EXISTS
        "IX_Artist_Gallery_gallery"
    ON
        "Artist_Gallery" ("gallery_id")
""",
    """
    CREATE INDEX IF NOT EXISTS
        "IX_Characters_character_name"
    ON
        "Characters" ("character_name" COLLATE NOCASE)
""",
    """
    CREATE INDEX IF NOT EXISTS
        "IX_Character_Gallery_character"
    ON
        "Character_Gallery" ("character_id")
""",
    """
    CREATE INDEX IF NOT EXISTS
        "IX_Character_Gallery_gallery"
    ON
        "Character_Gallery" ("gallery_id")
""",
    """
    CREATE INDEX IF NOT EXISTS
        "IX_Groups_group_name"
    ON
        "Groups" ("group_name" COLLATE NOCASE)
""",
    """
    CREATE INDEX IF NOT EXISTS
        "IX_Group_Gallery_group"
    ON
        "Group_Gallery" ("group_id")
""",
    """
    CREATE INDEX IF NOT EXISTS
        "IX_Group_Gallery_gallery"
    ON
        "Group_Gallery" ("gallery_id")
""",
    """
    CREATE INDEX IF NOT EXISTS
        "IX_Series_series_name"
    ON
        "Series" ("series_name" COLLATE NOCASE)
""",
    """
    CREATE INDEX IF NOT EXISTS
        "IX_Series_Gallery_series"
    ON
        "Series_Gallery" ("series_id")
""",
    """
    CREATE INDEX IF NOT EXISTS
        "IX_Series_Gallery_gallery"
    ON
        "Series_Gallery" ("gallery_id")
""",
    """
    CREATE INDEX IF NOT EXISTS
        "IX_Tags_tag_name"
    ON
        "Tags" ("tag_name" COLLATE NOCASE)
""",
    """
    CREATE INDEX IF NOT EXISTS
        "IX_Tag_Gallery_tag"
    ON
        "Tag_Gallery" ("tag_id")
""",
    """
    CREATE INDEX IF NOT EXISTS
        "IX_Tag_Gallery_gallery"
    ON
        "Tag_Gallery" ("gallery_id")
""",
]
