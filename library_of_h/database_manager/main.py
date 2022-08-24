import logging
import os
import queue
import re
import time
from contextlib import contextmanager
from datetime import datetime
from functools import partial
from typing import (Callable, Generator, Iterator, Literal, Optional, Sequence,
                    Union)
from weakref import proxy

import more_itertools
import sqlparse
from PySide6 import QtCore as qtc
from PySide6 import QtSql
from PySide6 import QtWidgets as qtw

from library_of_h.custom_widgets.progress_dialog import ProgressDialog
from library_of_h.database_manager.constants import (CREATE_QUERIES,
                                                     MATCH_TEMPLATE,
                                                     NUMERICAL_FILTER_OPTIONS,
                                                     ORDER_BY_MAPPING,
                                                     SELECT_MAPPING,
                                                     SELECT_TEMPLATE,
                                                     SEX_MAPPING,
                                                     TEXT_FILTER_OPTIONS,
                                                     VALID_KEYS,
                                                     WHERE_TEMPLATE)
from library_of_h.logger import MainType, get_logger
from library_of_h.miscellaneous.functions import (Bytes_from_value_and_unit,
                                                  relative_time_to_timestamp)
from library_of_h.preferences import Preferences


class DatabaseManager(qtc.QObject):

    _instance = None

    _logger: logging.Logger

    _update_progress_dialog_signal = qtc.Signal()
    _write_thread_closed_signal = qtc.Signal()
    _read_operation_finished_signal = qtc.Signal(object, list)

    def __init__(self) -> None:
        raise RuntimeError("Use the classmethod 'get_instance' to get an instance.")

    # <CONTEXT MANAGERS>
    @contextmanager
    def _read_context_manager(self, connection: str) -> Union[None, QtSql.QSqlDatabase]:
        db = QtSql.QSqlDatabase.database(connection)
        try:
            if not db.open():
                self._logger.error(
                    f"[Context Manager] Error opening database for read: "
                    + QtSql.QSqlDatabase.database(connection).lastError().text()
                )
                yield None
            if not db.exec("PRAGMA foreign_keys = ON;"):
                self._logger.error(
                    f"[Context Manager] Error setting PRAGMA foreign_keys: "
                    + QtSql.QSqlDatabase.database(connection).lastError().text()
                )
                yield None
            else:
                yield db
        finally:
            db.close()

    @contextmanager
    def _write_open_context_manager(
        self, connection: str
    ) -> Union[None, QtSql.QSqlDatabase]:
        db = QtSql.QSqlDatabase.database(connection)
        try:
            if not db.open():
                self._logger.error(
                    f"[Context Manager] Error opening database for write: "
                    + db.lastError().text()
                    or "UNKNOWN"
                )
                yield None
            if not db.exec("PRAGMA foreign_keys = ON;"):
                self._logger.error(
                    f"[Context Manager] Error setting PRAGMA foreign_keys: "
                    + db.lastError().text()
                )
                yield None
            else:
                yield db
        finally:
            db.close()

    @contextmanager
    def _write_transaction_context_manager(self, db: QtSql.QSqlDatabase) -> bool:
        try:
            if not db.transaction():
                self._logger.error(
                    f"[Context Manager] Error starting database transaction for write: "
                    + db.lastError().text()
                    or "UNKNOWN"
                )
                yield False
            else:
                yield True

        finally:
            if not db.commit():
                self._logger.error(
                    f"[Context Manager] Error commiting changes to database: "
                    + db.lastError().text()
                    or "UNKNOWN"
                )

    # </CONTEXT MANAGERS>

    # <CLASS METHODS>
    @classmethod
    def clean_up(cls):
        instance = cls._instance
        if instance.write_query_queue.qsize() == instance.read_query_queue.qsize() == 0:
            instance.write_query_queue.put(None)
            instance.read_query_queue.put(None)
            return

        instance.write_query_queue.put(None)
        instance.read_query_queue.put(None)
        instance._create_progress_dialog(
            f"Waiting on {instance.write_query_queue.qsize() + instance.read_query_queue.qsize()} database operations...",
            None,
            0,
            0,
        )

    @classmethod
    def get_instance(cls, *args, **kwargs) -> Union["DatabaseManager", None]:
        if cls._instance:
            return proxy(cls._instance)

        instance = super().__new__(cls)
        if not instance._initialize(*args, **kwargs):
            return None
        cls._instance = instance
        return proxy(cls._instance)

    # </CLASS METHODS>

    # <PRIVATE METHODS>
    def _call_callback(
        self, callback: Callable, results: list[QtSql.QSqlRecord] = None
    ):
        if results is not None:
            callback(results)
        else:
            callback()

    def _create_progress_dialog(
        self,
        labelText: str,
        cancelButtonText: Union[str, None],
        minimum: int,
        maximum: int,
        parent: qtw.QWidget = None,
        f: qtc.Qt.WindowType = qtc.Qt.WindowType.Dialog,
    ):
        if hasattr(self, "_progress_dialog"):
            return

        self._progress_dialog = ProgressDialog(
            labelText, cancelButtonText, minimum, maximum, parent, f
        )
        self._progress_dialog.setWindowTitle("Database progress")
        self._progress_dialog.open()

    def _create_tables_if_not_exist(self) -> bool:
        def _execute() -> bool:
            # Nested function to have `db` and the query be removed due to out
            # of scope: https://doc.qt.io/qt-6/qsqldatabase.html#removeDatabase
            with self._write_open_context_manager("create") as db:
                if db is None:
                    return False

                with self._write_transaction_context_manager(db) as res:
                    if res is False:
                        return False

                    for sql_query in CREATE_QUERIES:
                        QtSql.QSqlQuery(sql_query, db)
                        self._update_progress_dialog_signal.emit()

            self._delete_progress_dialog()
            return True

        QtSql.QSqlDatabase.addDatabase("QSQLITE", "create")
        QtSql.QSqlDatabase.database("create").setDatabaseName(self._database_file_path)

        self._create_progress_dialog(
            "Waiting on database create operations...", None, 0, 0
        )
        # A non blocking sleep for 50 milliseconds to have the progress dialog
        # visualize before running a blocking function.
        event_loop = qtc.QEventLoop()  # Start a new event loop temporarily.
        # Quit the event loop after 50 ms.
        qtc.QTimer.singleShot(50, event_loop.quit)
        event_loop.exec()
        # This should run before the single shot timer times out. Resulting in
        # something being shown in the progress dialog window, as opposed to an
        # empty frame.
        res = _execute()

        QtSql.QSqlDatabase.removeDatabase("create")
        return res

    def _delete_progress_dialog(self) -> None:
        if hasattr(self, "_progress_dialog"):
            # Don't need to self._progress_dialog.close() because the dialog is
            # closed when progress finishes.
            self._progress_dialog.deleteLater()
            del self._progress_dialog

    def _get_where(self, user_query: str, bind_values: list) -> tuple[str, str]:
        """
        Parses `user_query` string to create a valid SQL query.

        Parameters
        -----------
            user_query (str):
                A custom query that looks like 'key1=value1 value2 key2>value3 ...'

        Returns
        --------
        tuple[
            Iterator[
                Union[
                    Operator:
                        SQL operation from python-sql.
                    Literal["||"]
                    Literal["&&"]:
                        Represent logical operators OR and AND, respectively.
                ]
            ]:
                Stores user input query as SQL queries that include rows in the
                result, separated by logical operators.
            list[
                Operator:
                    SQL operation from python-sql.
            ]:
                Stores user input query as SQL queries that exclude rows from the
                result.
        ]
        """
        text_match_queries = []
        numerical_where_queries = []
        numerical_where_bind_values = []
        logical_operator = None

        try:
            # See if the user input a gallery ID.
            gallery = int(user_query)
        except ValueError:
            pass
        else:
            bind_values.append(gallery)
            return '"gallery" = ?'

        for parsed_query in _parse_query(user_query):
            if parsed_query in ("&&", "||"):
                logical_operator = "AND" if parsed_query == "&&" else "OR"

            elif isinstance(parsed_query, tuple):
                (user_key, operator, value) = parsed_query
                if not value:
                    raise ValueError(f"No value passed for operation.")
                value = value.lower()

                if user_key == "" and operator in ("<", ">"):
                    # For value only queries that use comparision operators since
                    # they're parsed as keyword queries without the keyword.

                    if value.startswith(("d", "u")):
                        # Flip the operator because it makes sense that way for
                        # date filtering.
                        operator = ">" if operator == "<" else "<"
                        prefix = value[0]
                        value = _parse_date_time_format(value[1:])
                        user_key = "ddate" if prefix == "d" else "udate"
                    elif value.startswith("p"):
                        value = int(value[1:])
                        user_key = "pages"

                    if user_key:
                        if logical_operator:
                            numerical_where_queries.append(logical_operator)
                        numerical_where_queries.append(f'"{user_key}" {operator} ?')
                        numerical_where_bind_values.append(value)

                elif user_key in TEXT_FILTER_OPTIONS:
                    if operator not in TEXT_FILTER_OPTIONS[user_key]:
                        raise ValueError(
                            f"Wrong comparision operator used for key {user_key}."
                        )
                    wildcard = "*" if "~=" in operator else ""
                    value = value.strip("\"'")  # See if needed or not.

                    if operator.startswith("!"):
                        if logical_operator == "OR":
                            text_match_queries.append("OR")
                        text_match_queries.append(f"NOT {user_key} : {value}{wildcard}")
                    else:
                        if logical_operator == "OR":
                            text_match_queries.append("OR")
                        text_match_queries.append(f"{user_key} : {value}{wildcard}")

                elif user_key in NUMERICAL_FILTER_OPTIONS:
                    if operator not in NUMERICAL_FILTER_OPTIONS[user_key]:
                        raise KeyError(
                            f"Wrong comparision operator used for key {user_key}."
                        )
                    if user_key in ("ddate", "udate"):
                        value = _parse_date_time_format(value)
                        # Flip the operator because it makes sense that way for
                        # date filtering.
                        operator = ">" if operator == "<" else "<"
                        if logical_operator:
                            numerical_where_queries.append(logical_operator)
                        numerical_where_queries.append(f'"{user_key}" {operator} ?')
                        numerical_where_bind_values.append(value)
                    elif user_key == "size":
                        *value, unit = value
                        value = Bytes_from_value_and_unit("".join(value), unit)
                    else:
                        value = int(value)
                        if logical_operator is not None:
                            numerical_where_queries.append(logical_operator)
                        numerical_where_queries.append(f'"{user_key}" {operator} ?')
                        numerical_where_bind_values.append(value)

                if user_key == "":
                    raise ValueError("Comparison operator found with no key.")

            else:
                value = parsed_query

                if value.startswith("-"):
                    if logical_operator == "OR":
                        text_match_queries.append(logical_operator)
                    text_match_queries.append(f"NOT {value}*")
                else:
                    if logical_operator == "OR":
                        text_match_queries.append(logical_operator)
                    text_match_queries.append(f"{value}*")

        if text_match_queries and numerical_where_queries:
            numerical_where_queries.insert(0, "AND")

        if text_match_queries:
            bind_values.append(
                " ".join(
                    more_itertools.rstrip(
                        text_match_queries, lambda x: str(x) in ("OR", "AND")
                    )
                )
            )
        bind_values.extend(numerical_where_bind_values)

        if text_match_queries:
            text_match_queries = "MATCH ?"
        else:
            text_match_queries = ""

        return (
            text_match_queries,
            " ".join(
                more_itertools.rstrip(
                    numerical_where_queries, lambda x: str(x) in ("OR", "AND")
                )
            ),
        )

    def _initialize(self, *args, **kwargs) -> bool:
        super().__init__(*args, **kwargs)

        self._logger = get_logger(
            main_type=MainType.DATABASE,
            sub_types=[],
        )

        self._queries_iter = iter(CREATE_QUERIES)

        self.write_query_queue = queue.Queue()
        self.read_query_queue = queue.Queue()

        directory = qtc.QDir(
            qtc.QDir.cleanPath(
                Preferences.get_instance()["database_preferences", "location"]
            )
        )
        if not directory.makeAbsolute():
            self._logger.error(
                f"Failed to makeAbsolute directory: LOCATION={directory}"
            )
            return False
        if not directory.mkpath(directory.path()):
            self._logger.error(f"Failed to mkpath directory: LOCATION={directory}")
            return False
        self._database_file_path = directory.absoluteFilePath("LoH_galleries.db")

        if not self._set_journal_mode_wal():
            return False
        if not self._create_tables_if_not_exist():
            return False

        qtc.QThreadPool.globalInstance().start(self._threaded_execute_write_queries)
        qtc.QThreadPool.globalInstance().start(self._threaded_execute_read_queries)

        self._update_progress_dialog_signal.connect(self._update_progress_dialog_slot)
        self._write_thread_closed_signal.connect(self._remove_databases)
        self._read_operation_finished_signal.connect(self._call_callback)

        return True

    def _read(self, query: QtSql.QSqlQuery) -> list:
        if not query.exec():
            self._logger.error(
                f"[{query.lastError().text()}] "
                f"Error reading from database: "
                f'QUERY="{query.lastQuery()}"'
            )
            self.read_query_queue = queue.Queue()  # Empty queue.
            return []

        model = QtSql.QSqlQueryModel()
        model.setQuery(query)

        results = [model.record(i) for i in range(model.rowCount())]

        return results

    def _remove_databases(self):
        QtSql.QSqlDatabase.removeDatabase("write")
        QtSql.QSqlDatabase.removeDatabase("read")

    def _set_journal_mode_wal(self) -> bool:
        QtSql.QSqlDatabase.addDatabase("QSQLITE", "PRAGMA")
        QtSql.QSqlDatabase.database("PRAGMA").setDatabaseName(self._database_file_path)

        def _execute() -> bool:
            db = QtSql.QSqlDatabase.database("PRAGMA")
            if not db.open():
                self._logger.error(
                    f"Error opening database for journal mode change: "
                    + db.lastError().text()
                    or "UNKNOWN"
                )
                return False

            query = QtSql.QSqlQuery(db)
            if not query.exec("PRAGMA journal_mode=WAL"):
                self._logger.error(
                    f"Error setting journal mode changes to database: "
                    + query.lastError().text()
                    or "UNKNOWN"
                )
                db.close()
                return False

            db.close()
            return True

        exec_res = _execute()
        QtSql.QSqlDatabase.removeDatabase("PRAGMA")
        return exec_res

    def _threaded_execute_read_queries(self) -> None:
        QtSql.QSqlDatabase.addDatabase("QSQLITE", "read")
        QtSql.QSqlDatabase.database("read").setDatabaseName(self._database_file_path)

        with self._read_context_manager("read") as db:
            if db is None:
                return

            while True:
                value = self.read_query_queue.get(block=True, timeout=None)
                while True:
                    if value is None:
                        return
                    elif len(value) == 3:
                        query_str = value[0]
                        bind_values = value[1]
                        callback = value[2]
                    elif len(value) == 2:
                        query_str = value[0]
                        bind_values = ()
                        callback = value[1]

                    query = QtSql.QSqlQuery(db)
                    query.prepare(query_str)
                    for bind_value in bind_values:
                        query.addBindValue(bind_value, QtSql.QSql.ParamTypeFlag.Out)

                    self._read_operation_finished_signal.emit(
                        callback, self._read(query)
                    )

                    try:
                        value = self.read_query_queue.get(block=False, timeout=None)
                    except queue.Empty:
                        break

                    query.clear()

    def _threaded_execute_write_queries(self) -> None:
        QtSql.QSqlDatabase.addDatabase("QSQLITE", "write")
        QtSql.QSqlDatabase.database("write").setDatabaseName(self._database_file_path)

        with self._write_open_context_manager("write") as db:
            if db is None:
                return

            while True:
                value = self.write_query_queue.get(block=True, timeout=None)
                query = QtSql.QSqlQuery(db)

                with self._write_transaction_context_manager(db) as res:
                    if res is False:
                        return

                    while True:
                        if isinstance(value, tuple):
                            query_str = value[0]
                            bind_values = value[1]
                        elif len(value) == 2:
                            query_str = value[0]
                            bind_values = ()
                        elif value is None:
                            self._delete_progress_dialog()
                            self._write_thread_closed_signal.emit()
                            return

                        query.prepare(query_str)
                        for bind_value in bind_values:
                            query.addBindValue(bind_value)

                        if not self._write(query):
                            break

                        try:
                            self._update_progress_dialog_signal.emit()
                        except AttributeError:
                            pass

                        try:
                            value = self.write_query_queue.get(
                                block=False, timeout=None
                            )
                        except queue.Empty:
                            break

    def _update_progress_dialog_slot(self) -> None:
        try:
            self._progress_dialog.update_progress()
        except AttributeError:
            # For when this is called when the progress dialog has not been
            # created.
            pass

    def _write(self, query: QtSql.QSqlQuery) -> None:
        if not query.exec():
            self._logger.error(
                f"[{query.lastError().text()}] "
                f"Error writing to database: "
                f'QUERY="{query.lastQuery()}"'
            )
            self.write_query_queue = queue.Queue()
            return False
        return True

    # </PRIVATE METHODS>

    # <PUBLIC METHODS>
    def delete(self, **kwargs):
        for key, value in kwargs.items():
            self.write_query_queue.put(
                (f'DELETE FROM "Galleries" WHERE "{key}"=?', (value,))
            )

    def get(
        self,
        get_callback: Callable,
        select: Union[Literal["*"], Literal["count"], list[str]] = "*",
        count: bool = False,
        count_callback: Callable = None,
        user_query: str = "",
        limit: int = 0,
        offset: int = 0,
        sort_by: str = None,
        sort_order: str = "ASC",
    ) -> bool:
        s1 = time.time()
        """
        Queries the directory with provided arguments.

        Parameters
        -----------
            callback (Callable):
                Function to call when get operation ends.
            select (str):
                Which columns to select data from. Defaults to '*'.
            count (bool):
                Whether to count the total number of results or not.
            count_callback (Callable):
                Function to call when count operation ends.
            user_query (str):
                A custom query that looks like 'key1:"value1, value2, ..." key2:"..." ...'
            limit (int):
                Limit for maximum number of records to get.
            offset (int):
                Row offset to start getting records from. Defaults to 0.
            sort_by (str):
                Column to sort results by.
            sort_order (str):
                Order to sort results by (ASC/DESC).

        Returns
        --------
            bool:
                True:
                    An SQL query created based on the parameters was
                    successfully added to the read query queue.
                False:
                    No SQL query was created nor added to the read query queue.
                    Denotes a syntax error in the passed `filter`.
        """
        bind_values = []
        text_match_query = ""
        numerical_where_query = ""

        if count:
            if count_callback is None:
                return False
            self.get(
                get_callback=count_callback,
                select="count",
                count=False,
                user_query=user_query,
            )

        try:
            if user_query:
                (
                    text_match_query,
                    numerical_where_query,
                ) = self._get_where(user_query, bind_values)
        except (KeyError, ValueError):
            # One of the following raised an error due to wrong input:
            #   - Could not cast user value to `int()` when integer was expected,
            #   - Special character value(s) (example:>d30d, size<30M) was(were)
            #     not used properly.
            #   - Empty value for operation.
            return False

        if select == "count":
            select = 'COUNT(1) "total_rows"'
            if text_match_query or numerical_where_query:
                if text_match_query:
                    match = MATCH_TEMPLATE.format(
                        query=text_match_query,
                    )
                else:
                    match = ""
                query = SELECT_TEMPLATE.format(
                    select=select,
                    where=WHERE_TEMPLATE.format(
                        match=match,
                        conditionals=numerical_where_query,
                    ),
                    sort_by="",
                    sort_order="",
                    limit_offset="",
                )
            else:
                query = SELECT_TEMPLATE.format(
                    select=select,
                    where="",
                    sort_by="",
                    sort_order="",
                    limit_offset="",
                )
            self.read_query_queue.put((query, bind_values, get_callback))
            return True

        if select == "*":
            select = "*"
        elif isinstance(select, str):
            select = f"{SELECT_MAPPING[select]}"
        elif isinstance(select, list):
            select = ", ".join(SELECT_MAPPING[s] for s in select)

        if limit != 0:
            limit_offset = f"LIMIT {limit} OFFSET {offset}"
        else:
            limit_offset = ""

        if sort_by is not None:
            sort_by = ORDER_BY_MAPPING[sort_by]
            sort_order = sort_order
            sort_by = f"ORDER BY {sort_by}"
        else:
            sort_by = ""
            sort_order = ""

        if text_match_query or numerical_where_query:
            if text_match_query:
                match = MATCH_TEMPLATE.format(
                    query=text_match_query,
                )
            else:
                match = ""

            query = SELECT_TEMPLATE.format(
                select=select,
                where=WHERE_TEMPLATE.format(
                    match=match,
                    conditionals=numerical_where_query,
                ),
                sort_by=sort_by,
                sort_order=sort_order,
                limit_offset=limit_offset,
            )
        else:
            query = SELECT_TEMPLATE.format(
                select=select,
                where="",
                sort_by=sort_by,
                sort_order=sort_order,
                limit_offset=limit_offset,
            )
        self.read_query_queue.put((query, bind_values, get_callback))
        return True

    def insert_into_database(self, gallery_metadata: "GalleryMetadataBase") -> None:
        gallery_id = gallery_metadata.gallery_id
        source = gallery_metadata.source

        for type in gallery_metadata.type:
            self._insert_into_types(gallery_metadata.gallery_id, type)

        self._insert_into_sources(gallery_metadata.gallery_id, source)

        size_in_bytes = 0
        for path, _, files in os.walk(gallery_metadata.location):
            for file in files:
                size_in_bytes += os.path.getsize(os.path.join(path, file))

        try:
            nhentai_media_id = gallery_metadata.media_id
        except AttributeError:
            nhentai_media_id = None

        self._insert_into_galleries(
            gallery_id=gallery_id,
            title=gallery_metadata.title,
            japanese_title=gallery_metadata.japanese_title,
            download_date=int(datetime.today().timestamp()),
            upload_date=gallery_metadata.upload_date,
            pages=gallery_metadata.pages,
            location=gallery_metadata.location,
            size_in_bytes=size_in_bytes,
            type_=gallery_metadata.type,
            source=source,
            nhentai_media_id=nhentai_media_id,
        )

        for artist_name in gallery_metadata.artists:
            self._insert_into_artists(gallery_id, artist_name, source)

        for character_name in gallery_metadata.characters:
            self._insert_into_characters(gallery_id, character_name, source)

        for group_name in gallery_metadata.groups:
            self._insert_into_groups(gallery_id, group_name, source)

        for language_name in gallery_metadata.language:
            self._insert_into_languages(gallery_id, language_name, source)

        for series_name in gallery_metadata.series:
            self._insert_into_series(gallery_id, series_name, source)

        for tag_name in gallery_metadata.tags:
            self._insert_into_tags(gallery_id, tag_name, source)

        fts5_insert_query = """
        INSERT INTO
            GalleriesFTS5
        SELECT
            *
        FROM
            GalleriesView
        WHERE
            gallery = ?
        AND
            source = ?
        """
        bind_values = (gallery_id, source)
        self.write_query_queue.put((fts5_insert_query, bind_values))

    def _insert_into_artists(
        self, gallery_id: int, artist_name: str, source: str
    ) -> None:
        artist_name = artist_name.lower()
        query = 'INSERT OR IGNORE INTO "Artists" ("artist_name") VALUES (?)'
        bind_values = (artist_name,)
        self.write_query_queue.put((query, bind_values))

        query = f"""
            INSERT OR IGNORE INTO
                "Artist_Gallery" ("artist_id", "gallery_id")
            SELECT
                "Artists"."artist_id", "Galleries"."gallery_database_id"
            FROM
                "Galleries"
            INNER JOIN
                "Artists"
            WHERE
                "Artists"."artist_name" = ?
            AND
                (
                    "Galleries"."gallery_id" = ?
                AND
                    "Galleries"."source" = (
                        SELECT
                            "source_id"
                        FROM
                            "Sources"
                        WHERE
                            "Sources"."source_name" = ?
                    )
            )
            """

        bind_values = (artist_name, gallery_id, source)
        self.write_query_queue.put((query, bind_values))

    def _insert_into_characters(
        self, gallery_id: int, character_name: str, source: str
    ) -> None:
        character_name = character_name.lower()
        query = 'INSERT OR IGNORE INTO "Characters" ("character_name") VALUES (?)'
        bind_values = (character_name,)
        self.write_query_queue.put((query, bind_values))

        query = f"""
            INSERT OR IGNORE INTO
                "Character_Gallery" ("character_id", "gallery_id")
            SELECT
                "Characters"."character_id", "Galleries"."gallery_database_id"
            FROM
            "Characters", "Galleries"
            WHERE
                "Characters"."character_name" = ?
            AND
                (
                    "Galleries"."gallery_id" = ?
                AND
                    "Galleries"."source" = (
                        SELECT
                            "source_id"
                        FROM
                            "Sources"
                        WHERE
                            "Sources"."source_name" = ?
                    )
            )
            """
        bind_values = (character_name, gallery_id, source)
        self.write_query_queue.put((query, bind_values))

    def _insert_into_galleries(
        self,
        gallery_id: int,
        title: str,
        download_date: int,
        japanese_title: str,
        upload_date: int,
        pages: int,
        location: str,
        size_in_bytes: int,
        type_: int,
        source: int,
        nhentai_media_id: Optional[int] = None,
    ) -> None:
        query = """
            INSERT OR IGNORE INTO "Galleries"
            (
                "gallery_id",
                "title",
                "japanese_title",
                "download_date",
                "upload_date",
                "pages",
                "location",
                "size_in_bytes",
                "nhentai_media_id",
                "type",
                "source"
            )
            SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, "type_id", "source_id"
            FROM
            "Types", "Sources"
            WHERE
            "Types"."type_name" = ? AND "Sources"."source_name" = ?
            """
        bind_values = (
            gallery_id,
            title,
            japanese_title,
            download_date,
            upload_date,
            pages,
            location,
            size_in_bytes,
            nhentai_media_id,
            type_,
            source,
        )
        self.write_query_queue.put((query, bind_values))

    def _insert_into_groups(
        self, gallery_id: int, group_name: str, source: str
    ) -> None:
        group_name = group_name.lower()
        query = 'INSERT OR IGNORE INTO "Groups" ("group_name") VALUES (?)'
        bind_values = (group_name,)
        self.write_query_queue.put((query, bind_values))

        query = f"""
            INSERT OR IGNORE INTO
                "Group_Gallery" ("group_id", "gallery_id")
            SELECT
                "Groups"."group_id", "Galleries"."gallery_database_id"
            FROM
                "Groups", "Galleries"
            WHERE
                "Groups"."group_name" = ?
            AND
                (
                    "Galleries"."gallery_id" = ?
                AND
                    "Galleries"."source" = (
                        SELECT
                            "source_id"
                        FROM
                            "Sources"
                        WHERE
                            "Sources"."source_name" = ?
                    )
            )
            """
        bind_values = (group_name, gallery_id, source)
        self.write_query_queue.put((query, bind_values))

    def _insert_into_languages(
        self, gallery_id: int, language_name: str, source: str
    ) -> None:
        language_name = language_name.lower()
        query = 'INSERT OR IGNORE INTO "Languages" ("language_name") VALUES (?)'
        bind_values = (language_name,)
        self.write_query_queue.put((query, bind_values))

        query = f"""
            INSERT OR IGNORE INTO
                "Language_Gallery" ("language_id", "gallery_id")
            SELECT
                "Languages"."language_id", "Galleries"."gallery_database_id"
            FROM
                "Languages", "Galleries"
            WHERE
                "Languages"."language_name" = ?
            AND
                (
                    "Galleries"."gallery_id" = ?
                AND
                    "Galleries"."source" = (
                        SELECT
                            "source_id"
                        FROM
                            "Sources"
                        WHERE
                            "Sources"."source_name" = ?
                    )
            )
            """
        bind_values = (language_name, gallery_id, source)
        self.write_query_queue.put((query, bind_values))

    def _insert_into_series(
        self, gallery_id: int, series_name: str, source: str
    ) -> None:
        series_name = series_name.lower()
        query = 'INSERT OR IGNORE INTO "Series" ("series_name") VALUES (?)'
        bind_values = (series_name,)
        self.write_query_queue.put((query, bind_values))

        query = f"""
            INSERT OR IGNORE INTO
                "Series_Gallery" ("series_id", "gallery_id")
            SELECT
                "Series"."series_id", "Galleries"."gallery_database_id"
            FROM
                "Series", "Galleries"
            WHERE
                "Series"."series_name" = ?
            AND
                (
                    "Galleries"."gallery_id" = ?
                AND
                    "Galleries"."source" = (
                        SELECT
                            "source_id"
                        FROM
                            "Sources"
                        WHERE
                            "Sources"."source_name" = ?
                    )
            )
            """
        bind_values = (series_name, gallery_id, source)
        self.write_query_queue.put((query, bind_values))

    def _insert_into_sources(self, gallery_id: int, source_name: str) -> None:
        source_name = source_name.lower()
        query = 'INSERT OR IGNORE INTO "Sources" ("source_name") VALUES (?)'
        bind_values = (source_name,)
        self.write_query_queue.put((query, bind_values))

    def _insert_into_tags(self, gallery_id: int, tag_name: str, source: str) -> None:
        tag_name = tag_name.lower()
        query = 'INSERT OR IGNORE INTO "Tags" ("tag_name") VALUES (?)'
        bind_values = (tag_name,)
        self.write_query_queue.put((query, bind_values))

        query = f"""
            INSERT OR IGNORE INTO
                "Tag_Gallery" ("tag_id", "gallery_id")
            SELECT
                "Tags"."tag_id", "Galleries"."gallery_database_id"
            FROM
                "Tags", "Galleries"
            WHERE
                "Tags"."tag_name" = ?
            AND
                (
                    "Galleries"."gallery_id" = ?
                AND
                    "Galleries"."source" = (
                        SELECT
                            "source_id"
                        FROM
                            "Sources"
                        WHERE
                            "Sources"."source_name" = ?
                    )
            )
            """
        bind_values = (tag_name, gallery_id, source)
        self.write_query_queue.put((query, bind_values))

    def _insert_into_types(self, gallery_id: int, type_name: str) -> None:
        type_name = type_name.lower()
        query = 'INSERT OR IGNORE INTO "Types" ("type_name") VALUES (?)'
        bind_values = (type_name,)
        self.write_query_queue.put((query, bind_values))

    # </PUBLIC METHODS>


def _parse_date_time_format(value: str) -> int:
    """
    Checks user query date value against various accepted formats.

    Parameters
    -----------
        value (str):
            User query date value.

    Return
    -------
        int:
            UNIX timestamp representation of passed user query date value.

    Raises
    -------
        ValueError:
            User passed query date value is not in any acceptable format.
    """
    try:
        # In the off-chance that the user passed a UNIX timestamp.
        value = int(float(value))
    except ValueError:
        try:
            # Check if the user passed relative time.
            value = int(relative_time_to_timestamp(value))
        except ValueError:
            # Check if the user passed date in YYYY-MM-DD format.
            value = int(datetime.strptime(value, "%Y-%m-%d").timestamp())
    return value


_COMPARISION_SPLIT_PATTERN = re.compile("(!~=|~=|>=|<=|!=|=|>|<)")
_LOGICAL_SPLIT_PATTERN = re.compile(r" (&&|\|\|) ")
_WHITE_SPACES_SUB_PATTERN = re.compile(r" {2,}")


def _parse_query(
    user_query: str,
) -> Iterator[Union[tuple[str, str, str], Literal["&&"], Literal["||"]]]:
    """
    Parses user filter query into a usable standard based on grammar.
    Grammar:
        <key><operator><value> ['&&'|'||'|' ' <key><operator><value> [...]]
        * No logical operator separation defaults to '&&'.
    Possible operators:
        - !~= (to be parsed as SQL NOT LIKE)
        - ~= (to be parsed as SQL LIKE)
        - >=
        - <=
        - !=
        - =
        - >
        - <

    Parameters
    -----------
        user_query (str):
            User query to parse.

    Returns
    --------
        Iterator[
            Union[
                tuple[
                    str:
                        Database column name.
                    str:
                        Comparision operator.
                    str:
                        Value to filter database column with.
                ],
                Literal["&&"],
                Literal["||"]:
                    Logical operators `AND` and `OR`, respectively.
            ]
        ]
    """
    # Say user_query = 'key1=val1 key2>val2 && key3<="val 3"'
    # Replace more than one consecutive white space with a single ' '.
    user_query = _WHITE_SPACES_SUB_PATTERN.sub(" ", user_query)

    quotes = False
    parsed_query = ""

    for char in user_query:
        #' 's within quotes are to be ignored during any operation involving ' '.
        # This loop replaces them with a placeholder.
        if quotes and char == " ":
            parsed_query += "^q_ign^"
            continue
        elif char in ('"', "'"):
            quotes = not quotes
        parsed_query += char

    # parsed_query = 'key1=val1 key2>val2 && key3<="val^q_ign^3"'

    logical_split = _LOGICAL_SPLIT_PATTERN.split(parsed_query)
    # logical_split = ['key1=val1 key2>val2', '&&', 'key3<="val^q_ign^3"']
    temp = []
    for split in logical_split:
        # Replaces ' 's that separate <key><operator><value> pairs with '&&' and
        # adds them to the main list.
        split = split.replace(" ", " && ")
        temp.extend(_LOGICAL_SPLIT_PATTERN.split(split))
    logical_split = temp
    # logical_split = ['key1=val1', '&&', 'key2>val2', '&&', 'key3<="val^q_ign^3"']

    comparison_split = [
        tuple(split)
        if len(
            split := _COMPARISION_SPLIT_PATTERN.split(
                prt := part.replace("^q_ign^", " ")  # Re-placing replaced ' 's.
            )
        )
        > 1
        else prt
        for part in logical_split
    ]
    # comparison_split = [
    #   ('key1', '=', 'val1'),
    #   '&&',
    #   ('key1', '>', 'val2'),
    #   '&&',
    #   ('key3', '<=', '"val^q_ign^3"')
    # ]
    return more_itertools.strip(comparison_split, lambda x: x in ("&&", "||"))
