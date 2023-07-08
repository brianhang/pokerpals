from contextlib import contextmanager
from sqlite3 import connect, Connection, PARSE_DECLTYPES
from .constants import DB_PATH

APP_DB_GLOBAL_KEY = 'app_db'

DEFAULT_CONTEXT = {}


def get(context) -> Connection:
    connection = context.get(APP_DB_GLOBAL_KEY)
    if connection:
        return connection

    connection = connect(
        DB_PATH,
        detect_types=PARSE_DECLTYPES
    )

    if type(context) is dict:
        context[APP_DB_GLOBAL_KEY] = connection
    else:
        setattr(context, APP_DB_GLOBAL_KEY, connection)

    return connection


def close(context) -> None:
    connection = context.pop(APP_DB_GLOBAL_KEY, None)

    if connection:
        connection.close()


@contextmanager
def open_connection():
    context = {}
    connection = get(context)
    yield connection
    close(context)
