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

    Every worker process must use the same key, or a login made in one would
    be rejected by the others. If several workers start at once, the file is
    created atomically so they all end up reading the same key.
    """
    key = os.environ.get(SECRET_KEY_ENV)
    if key:
        return key

    key = read_key()
    if key:
        return key

    # Write the new key to a temporary file, then link it into place. Linking
    # fails if another worker got there first, in which case use its key.
    new_key = secrets.token_hex(32)
    tmp_path = f'{SECRET_KEY_PATH}.{os.getpid()}.tmp'
    fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as key_file:
        key_file.write(new_key)

    try:
        os.link(tmp_path, SECRET_KEY_PATH)
    except FileExistsError:
        pass
    finally:
        os.unlink(tmp_path)

    return read_key()


def read_key() -> str:
    try:
        with open(SECRET_KEY_PATH, 'r') as key_file:
            return key_file.read().strip()
    except FileNotFoundError:
        return ''
