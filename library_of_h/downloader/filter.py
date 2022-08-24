class Filter:
    def __init__(self) -> None:
        self.tags_blacklist = set()
        self.types_blacklist = set()
        self.languages_to_include = set()

        self._load_tags_blacklist_if_exists()
        self._load_types_blacklist_if_exists()
        self._load_languages_to_include_if_exists()

    def _load_tags_blacklist_if_exists(self) -> None:
        try:
            with open("library_of_h/tags.blacklist") as file:
                self.tags_blacklist = {line.strip() for line in file}
        except FileNotFoundError:
            # If tags.blacklist file is not found, it is assumed that the user
            # doesn't want any tags blacklisted.
            pass

    def _load_types_blacklist_if_exists(self) -> None:
        try:
            with open("library_of_h/types.blacklist") as file:
                self.types_blacklist = {line.strip() for line in file}
        except FileNotFoundError:
            # If types.blacklist file is not found, it is assumed that the user
            # doesn't want any types blacklisted.
            pass

    def _load_languages_to_include_if_exists(self) -> None:
        try:
            with open("library_of_h/languages.include") as file:
                self.languages_to_include = {line.strip() for line in file}
        except FileNotFoundError:
            # If languages.include file is not found, it is assumed that the
            # user want galleries of all languages to be downloaded.
            pass
