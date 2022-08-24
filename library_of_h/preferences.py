from __future__ import annotations

import json
import os
from copy import deepcopy
from typing import Any, Mapping, Union

from library_of_h.constants import (USER_DATA_DIRECTORY,
                                    USER_PREFERENCES_LOCATION)
from library_of_h.miscellaneous.classes.nested_dict import NestedDict


class Preferences:

    _preferences_dict: NestedDict

    _instance = None
    slots = "_preferences_dict"
    _preferences_defaults_dict = NestedDict(
        {
            "explorer_preferences": {"delete_db_record_if_not_in_disk": False},
            "database_preferences": {"location": USER_DATA_DIRECTORY},
            "download_preferences": {
                "overwrite": False,
                "destination_formats": {
                    "Hitomi": {
                        "Artist(s)": USER_DATA_DIRECTORY + "/Hitomi/{gallery_id}/",
                        "Character(s)": USER_DATA_DIRECTORY + "/Hitomi/{gallery_id}/",
                        "Gallery ID(s)": USER_DATA_DIRECTORY + "/Hitomi/{gallery_id}/",
                        "Group(s)": USER_DATA_DIRECTORY + "/Hitomi/{gallery_id}/",
                        "Series(s)": USER_DATA_DIRECTORY + "/Hitomi/{gallery_id}/",
                        "Type(s)": USER_DATA_DIRECTORY + "/Hitomi/{gallery_id}/",
                        "Tag(s)": USER_DATA_DIRECTORY + "/Hitomi/{gallery_id}/",
                    },
                    "nhentai": {
                        "Artist(s)": USER_DATA_DIRECTORY + "/nhentai/{gallery_id}/",
                        "Character(s)": USER_DATA_DIRECTORY + "/nhentai/{gallery_id}/",
                        "Gallery ID(s)": USER_DATA_DIRECTORY + "/nhentai/{gallery_id}/",
                        "Group(s)": USER_DATA_DIRECTORY + "/nhentai/{gallery_id}/",
                        "Parody(s)": USER_DATA_DIRECTORY + "/nhentai/{gallery_id}/",
                        "Tag(s)": USER_DATA_DIRECTORY + "/nhentai/{gallery_id}/",
                    },
                },
            },
        }
    )

    def __init__(self):
        raise RuntimeError("Use the classmethod 'get_instance' to get an instance.")

    def __eq__(self, other: Mapping):
        return self._preferences_dict == other._preferences_dict

    def __getitem__(self, key: Union[tuple[str, ...], str]):
        if key[0] == "default":
            return self._preferences_defaults_dict[key[1:]]
        else:
            return self._preferences_dict[key]

    def __ne__(self, other: Mapping):
        return not self == other

    def __setitem__(self, key: Union[tuple[str, ...], str], value: Any):
        self._preferences_dict[key] = value

    def copy(self):
        return deepcopy(self)

    def get_difference(self) -> "Preferences":
        """
        Gets the difference between `self` and `_preferences_default` and
        creates a copy `Preferences` object with the difference as its
        preferences dictionary.

        Returns
        -------
            copy (Preferences):
                Preferences object with difference between `self` and
                `_preferences_default` as the preferences dictionary.
        """
        difference = self._preferences_dict - self._preferences_defaults_dict
        copy = self.copy()
        if not difference:
            copy._preferences_dict = NestedDict()
        else:
            copy._preferences_dict = difference
        return copy

    @classmethod
    def get_instance(cls) -> "Preferences":
        if cls._instance is None:
            instance = cls.__new__(cls)
            # By default, _preferences_dicr is the same as _preferences_defaults_dict,
            # unless preferences.json specifies otherswise.
            instance._preferences_dict = NestedDict(instance._preferences_defaults_dict)
            try:
                filename = USER_PREFERENCES_LOCATION
                if not os.path.getsize(filename):
                    raise ValueError("Empty file.")

                with open(filename) as file:
                    user_changes_dict = json.load(file)
            except (
                ValueError,  # preference.json is empty.
                FileNotFoundError,  # preference.json does not exist.
                json.JSONDecodeError,  # preference.json is malformed.
            ):
                instance._preferences_dict = NestedDict(
                    instance._preferences_defaults_dict
                )
            else:
                instance.nested_replace(user_changes_dict)
            cls._instance = instance

        return cls._instance

    def nested_update(self, mapping: Mapping):
        self._preferences_dict.nested_update(mapping)

    def nested_replace(self, mapping: Mapping):
        self._preferences_dict.nested_replace(mapping)

    def save(self):
        with open(USER_PREFERENCES_LOCATION, "w") as preferences_file:
            if self._preferences_dict:
                json.dump(dict(self._preferences_dict), preferences_file, indent=4)
        Preferences._instance = None


PREFERENCES_TEMPLATE = {
    "explorer_preferences": {"delete_db_record_if_not_in_disk": ""},
    "database_preferences": {"location": ""},
    "download_preferences": {
        "overwrite": "",
        "destination_formats": {
            "Hitomi": {
                "Artist(s)": "",
                "Character(s)": "",
                "Gallery ID(s)": "",
                "Group(s)": "",
                "Series(s)": "",
                "Type(s)": "",
                "Tag(s)": "",
            },
            "nhentai": {
                "Artist(s)": "",
                "Character(s)": "",
                "Gallery ID(s)": "",
                "Group(s)": "",
                "Parody(s)": "",
                "Tag(s)": "",
            },
        },
    },
}
