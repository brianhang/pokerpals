import sqlite3

import db.connection


COLUMN_NAME = 'payout_type'


def needs_migration(connection: sqlite3.Connection) -> bool:
    columns = [info[1] for info in connection.execute(
        'PRAGMA table_info(games);').fetchall()]
    # No columns means no games table yet, e.g. a database not created yet
    return bool(columns) and COLUMN_NAME not in columns


def migrate_add_payout_type():
    with db.connection.open_connection() as connection:
        if needs_migration(connection):
            connection.execute(
                f'ALTER TABLE games ADD COLUMN {COLUMN_NAME} INTEGER;',
            )
            print(f'Added {COLUMN_NAME} column to games', flush=True)

        connection.commit()
