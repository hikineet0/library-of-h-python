from library_of_h.signals_hub.browser_signals import BrowserSignals
from library_of_h.signals_hub.database_manager_signals import \
    DatabaseManagerSignals
from library_of_h.signals_hub.downloader_signals import DownloaderSignals
from library_of_h.signals_hub.logger_signals import LoggerSignals
from library_of_h.signals_hub.main_signals import MainSignals

main_signals = MainSignals()
logger_signals = LoggerSignals()
downloader_signals = DownloaderSignals()
database_manager_signals = DatabaseManagerSignals()
browser_signals = BrowserSignals()
