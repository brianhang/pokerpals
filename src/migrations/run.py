"""
Database migrations, in the order they must run.

Pending migrations run when the app is loaded, before it serves anything,
however it is started: `python app.py`, gunicorn with --preload (loaded once,
in the master process) or gunicorn without it (loaded by every worker). A
lock file makes processes take turns, so only the first one migrates and the
rest find nothing left to do. They can also be run by hand with
`python -m scripts.migrate` from the src/ directory.

Each migration checks whether it is needed, so running them again is safe.
"""
import fcntl
from contextlib import contextmanager
from os import path
from typing import Callable, NamedTuple

import db.connection

from . import add_payout_type, add_users

Migration = NamedTuple('Migration', [
    ('name', str),
    ('needs_migration', Callable),
    ('run', Callable[[], None]),
])

MIGRATIONS = [
    Migration('add_payout_type', add_payout_type.needs_migration,
              add_payout_type.migrate_add_payout_type),
    Migration('add_users', add_users.needs_migration,
              add_users.migrate_add_users),
]


class PendingMigrationsError(Exception):
    pass


def pending_migrations() -> list[str]:
    with db.connection.open_connection() as connection:
        return [
            migration.name for migration in MIGRATIONS
            if migration.needs_migration(connection)
        ]


@contextmanager
def migration_lock():
    """
    Holds an exclusive lock on a file next to the database while migrating.
    It is a separate file because closing any handle to the database file
    would release SQLite's own locks on it.
    """
    lock_path = path.join(path.dirname(path.abspath(db.connection.DB_PATH)),
                          'migrations.lock')
    with open(lock_path, 'w') as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)


def run_migrations() -> None:
    with migration_lock():
        for migration in MIGRATIONS:
            migration.run()


def check_migrations() -> None:
    """
    Refuses to start the app on a database that hasn't been migrated, which
    would otherwise fail on most requests.
    """
    pending = pending_migrations()
    if pending:
        raise PendingMigrationsError(
            f'The database has pending migrations ({", ".join(pending)}). '
            'Run `python -m scripts.migrate` from the src/ directory.')
