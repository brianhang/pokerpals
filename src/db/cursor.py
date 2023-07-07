from contextlib import contextmanager
from .constants import DB_PATH
import sqlite3

@contextmanager
def get():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    yield cursor
    connection.commit()
    connection.close()
