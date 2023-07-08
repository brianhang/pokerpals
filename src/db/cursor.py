from contextlib import contextmanager
from .connection import get as get_connection


@contextmanager
def get():
    with get_connection() as connection:
        cursor = connection.cursor()
        yield cursor
        connection.commit()
