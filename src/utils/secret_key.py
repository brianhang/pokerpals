import os
import secrets
from os import path

from db.constants import DB_PATH

SECRET_KEY_ENV = 'APP_SECRET_KEY'
# Kept next to the database, outside the source tree, and ignored by git
SECRET_KEY_PATH = path.join(path.dirname(DB_PATH), 'secret_key')


def load_secret_key() -> str:
    """
    The key that signs session cookies. Uses APP_SECRET_KEY if set, otherwise
    a random key generated on first start and saved to a file, so logins
    survive restarts without extra setup.
    """
    key = os.environ.get(SECRET_KEY_ENV)
    if key:
        return key

    try:
        with open(SECRET_KEY_PATH, 'r') as key_file:
            key = key_file.read().strip()
            if key:
                return key
    except FileNotFoundError:
        pass

    key = secrets.token_hex(32)
    fd = os.open(SECRET_KEY_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as key_file:
        key_file.write(key)

    return key
