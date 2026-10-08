"""
Database migrations, in the order they must run.

Migrations run once before the app starts serving:
- under gunicorn, from the `on_starting` hook in gunicorn.conf.py, which runs
  in the master process before any workers start
- with `python app.py`, before the server starts
- by hand, with `python -m scripts.migrate` from the src/ directory

Each migration checks whether it is needed, so running them again is safe.
"""
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


def run_migrations() -> None:
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
            'Run `python -m scripts.migrate` from the src/ directory, or '
            'start the app with gunicorn from src/ so gunicorn.conf.py runs '
            'them.')
