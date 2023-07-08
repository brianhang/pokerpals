from sqlite3 import Connection
from flask import g
from .connection import get as get_connection, close as close_connection


def get() -> Connection:
    return get_connection(g)


def close() -> None:
    return close_connection(g)
