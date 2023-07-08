from sqlite3 import connect, Connection, PARSE_DECLTYPES
from flask import g
from .constants import DB_PATH

APP_DB_GLOBAL_KEY = 'app_db'


def get() -> Connection:
    connection = g.get(APP_DB_GLOBAL_KEY)
    if connection:
        return connection

    connection = connect(
        DB_PATH,
        detect_types=PARSE_DECLTYPES
    )
    setattr(g, APP_DB_GLOBAL_KEY, connection)
    return connection


def close() -> None:
    connection = g.pop(APP_DB_GLOBAL_KEY, None)

    if connection:
        connection.close()
