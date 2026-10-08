"""
Moves from Venmo usernames as player IDs to a `users` table.

Before: `players.venmo_username` was the primary key and every other table
(`games.creator_id`, `game_players.player_id`, `game_payments.*_player_id`)
stored Venmo usernames.

After: each Venmo username becomes a `users` row (display name = the Venmo
username, no phone number yet) with a 'venmo' row in `user_payment_methods`,
and the other tables store integer user IDs. The old `players` table is kept
as `legacy_players` so nothing is lost; it can be dropped once the migration
has been verified in production.

The migration runs in a single transaction and is a no-op once the `users`
table exists, so it is safe to run on every start.
"""
import datetime
import shutil
import sqlite3
from os import path

import db.connection

LEGACY_PLAYERS_TABLE = 'legacy_players'

# Every Venmo username that appears anywhere, so that no row is orphaned even
# if it references a player that is somehow missing from `players`.
LEGACY_IDS_SQL = '''
    SELECT venmo_username AS v FROM players
    UNION SELECT player_id FROM game_players
    UNION SELECT from_player_id FROM game_payments
    UNION SELECT to_player_id FROM game_payments
    UNION SELECT creator_id FROM games
'''

MIGRATION_SQL = f'''
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone_number TEXT UNIQUE,
    display_name TEXT NOT NULL,
    active_game_id INTEGER,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_payment_methods (
    user_id INTEGER NOT NULL,
    method TEXT NOT NULL,
    handle TEXT NOT NULL,
    PRIMARY KEY (user_id, method),
    UNIQUE (method, handle)
);

INSERT INTO users (display_name, active_game_id)
SELECT ids.v, p.active_game_id
FROM ({LEGACY_IDS_SQL}) ids
LEFT JOIN players p ON p.venmo_username = ids.v
WHERE ids.v IS NOT NULL
ORDER BY ids.v;

INSERT INTO user_payment_methods (user_id, method, handle)
SELECT id, 'venmo', display_name FROM users;

CREATE TABLE games_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    creator_id INTEGER NOT NULL,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    lobby_name TEXT NOT NULL,
    buyin_cents INTEGER NOT NULL,
    entry_code TEXT NOT NULL,
    is_active BOOLEAN NOT NULL,
    payout_type INTEGER
);
INSERT INTO games_new
    (id, creator_id, created, lobby_name, buyin_cents, entry_code, is_active, payout_type)
SELECT g.id, m.user_id, g.created, g.lobby_name, g.buyin_cents, g.entry_code,
    g.is_active, g.payout_type
FROM games g
JOIN user_payment_methods m ON m.method = 'venmo' AND m.handle = g.creator_id;

CREATE TABLE game_players_new (
    game_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    join_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    buyin_cents INTEGER NOT NULL,
    cashout_cents INTEGER,
    PRIMARY KEY (game_id, player_id)
);
INSERT INTO game_players_new
    (game_id, player_id, join_time, buyin_cents, cashout_cents)
SELECT gp.game_id, m.user_id, gp.join_time, gp.buyin_cents, gp.cashout_cents
FROM game_players gp
JOIN user_payment_methods m ON m.method = 'venmo' AND m.handle = gp.player_id;

CREATE TABLE game_payments_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    from_player_id INTEGER NOT NULL,
    to_player_id INTEGER NOT NULL,
    cents INTEGER NOT NULL,
    completed BOOLEAN NOT NULL
);
INSERT INTO game_payments_new
    (id, game_id, from_player_id, to_player_id, cents, completed)
SELECT gp.id, gp.game_id, mf.user_id, mt.user_id, gp.cents, gp.completed
FROM game_payments gp
JOIN user_payment_methods mf ON mf.method = 'venmo' AND mf.handle = gp.from_player_id
JOIN user_payment_methods mt ON mt.method = 'venmo' AND mt.handle = gp.to_player_id;
'''

SWAP_SQL = f'''
DROP TABLE games;
ALTER TABLE games_new RENAME TO games;
DROP TABLE game_players;
ALTER TABLE game_players_new RENAME TO game_players;
DROP TABLE game_payments;
ALTER TABLE game_payments_new RENAME TO game_payments;
ALTER TABLE players RENAME TO {LEGACY_PLAYERS_TABLE};
'''

COPIED_TABLES = ['games', 'game_players', 'game_payments']


class MigrationError(Exception):
    pass


def table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row[0] for row in rows}


def needs_migration(connection: sqlite3.Connection) -> bool:
    tables = table_names(connection)
    return 'users' not in tables and 'players' in tables


def run_statements(connection: sqlite3.Connection, script: str) -> None:
    for statement in script.split(';'):
        if statement.strip():
            connection.execute(statement)


def migrate(connection: sqlite3.Connection) -> bool:
    """
    Runs the migration on `connection`. Returns True if anything changed.
    """
    if not needs_migration(connection):
        return False

    previous_isolation_level = connection.isolation_level
    connection.isolation_level = None  # manage the transaction ourselves

    try:
        connection.execute('BEGIN')
        run_statements(connection, MIGRATION_SQL)

        # Every row must have been carried over before the old tables go away.
        for table in COPIED_TABLES:
            old_count = connection.execute(
                f'SELECT COUNT(*) FROM {table}').fetchone()[0]
            new_count = connection.execute(
                f'SELECT COUNT(*) FROM {table}_new').fetchone()[0]
            if old_count != new_count:
                raise MigrationError(
                    f'{table}: expected {old_count} rows, copied {new_count}')

        run_statements(connection, SWAP_SQL)
        connection.execute('COMMIT')
    except Exception:
        connection.execute('ROLLBACK')
        raise
    finally:
        connection.isolation_level = previous_isolation_level

    return True


def migrate_add_users() -> None:
    """
    Migrates the app database, first copying it to a timestamped backup file
    next to it.
    """
    with db.connection.open_connection() as connection:
        if not needs_migration(connection):
            return

    db_path = db.connection.DB_PATH
    if path.exists(db_path):
        stamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        backup_path = f'{db_path}.pre-users-{stamp}.bak'
        shutil.copyfile(db_path, backup_path)
        print(f'Backed up database to {backup_path}')

    with db.connection.open_connection() as connection:
        if migrate(connection):
            count = connection.execute(
                'SELECT COUNT(*) FROM users').fetchone()[0]
            print(f'Migrated {count} Venmo players to users')
