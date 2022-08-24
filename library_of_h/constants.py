import os
import platform

testing = True

SERVICES = (
    "Hitomi",
    "nhentai",
)

APP_STATE_FILE_NAME = "library of H.state"
APP_LOG_FILE_NAME = "library of H.logs"
USER_PREFERENCES_FILE_NAME = "preferences.json"


SYSTEM = platform.system()
if SYSTEM == "Windows":
    APP_STATE_DIRECTORY = os.path.join(os.getenv("APPDATA"), "London69", "Library of H")
    APP_LOGS_DIRECTORY = os.path.join(os.getenv("APPDATA"), "London69", "Library of H")
    USER_PREFERENCES_DIRECTORY = os.path.join(
        os.getenv("APPDATA"), "London69", "Library of H"
    )
    USER_DATA_DIRECTORY = os.path.join(
        os.getenv("USERPROFILE"), "Documents", "London69", "Library of H", "Downloads"
    )

else:
    # Hopefully every non Windows OS has the same/similar structure.
    APP_STATE_DIRECTORY = os.path.join(
        os.getenv("HOME"), ".local", "share", "London69", "Library of H"
    )
    APP_LOGS_DIRECTORY = os.path.join(
        os.getenv("HOME"), ".local", "share", "London69", "Library of H"
    )
    USER_PREFERENCES_DIRECTORY = os.path.join(
        os.getenv("HOME"), ".config", "London69", "Library of H"
    )
    USER_DATA_DIRECTORY = os.path.join(
        os.getenv("HOME"), "Documents", "London69", "Library of H", "Downloads"
    )

if testing:
    APP_STATE_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
    APP_LOGS_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
    USER_PREFERENCES_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
    USER_DATA_DIRECTORY = os.path.abspath("./downloads")

APP_STATE_LOCATION = os.path.join(APP_STATE_DIRECTORY, APP_STATE_FILE_NAME)
APP_LOGS_LOCATION = os.path.join(APP_LOGS_DIRECTORY, APP_LOG_FILE_NAME)
USER_PREFERENCES_LOCATION = os.path.join(
    USER_PREFERENCES_DIRECTORY, USER_PREFERENCES_FILE_NAME
)

os.makedirs(name=APP_STATE_DIRECTORY, exist_ok=True)
os.makedirs(name=APP_LOGS_DIRECTORY, exist_ok=True)
os.makedirs(name=USER_PREFERENCES_DIRECTORY, exist_ok=True)


del platform
del os
