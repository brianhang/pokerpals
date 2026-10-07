import sqlite3
import unittest

from migrations.add_users import LEGACY_PLAYERS_TABLE, migrate, table_names

# The schema before users existed, including the later payout_type column
OLD_SCHEMA = '''
CREATE TABLE games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    creator_id TEXT NOT NULL,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    lobby_name TEXT NOT NULL,
    buyin_cents INTEGER NOT NULL,
    entry_code TEXT NOT NULL,
    is_active BOOLEAN NOT NULL,
    payout_type INTEGER
);
CREATE TABLE players (
    venmo_username TEXT PRIMARY KEY NOT NULL,
    active_game_id INTEGER
);
CREATE TABLE game_players (
    game_id INTEGER NOT NULL,
    player_id TEXT NOT NULL,
    join_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    buyin_cents INTEGER NOT NULL,
    cashout_cents INTEGER,
    PRIMARY KEY (game_id, player_id)
);
CREATE TABLE game_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    from_player_id TEXT NOT NULL,
    to_player_id TEXT NOT NULL,
    cents INTEGER NOT NULL,
    completed BOOLEAN NOT NULL
);
'''

OLD_DATA = '''
INSERT INTO players VALUES ('alice', NULL), ('bob', 2), ('Bob', NULL), ('carol', 2);
INSERT INTO games VALUES
    (1, 'alice', '2024-01-01 20:00:00', 'Alice''s Game', 2000, 'ABCD', 0, 1),
    (2, 'bob', '2024-02-01 20:00:00', 'Bob''s Game', 1000, 'WXYZ', 1, NULL);
INSERT INTO game_players VALUES
    (1, 'alice', '2024-01-01 20:00:00', 2000, 3500),
    (1, 'bob', '2024-01-01 20:01:00', 2000, 500),
    (1, 'ghost', '2024-01-01 20:02:00', 0, 0),
    (2, 'bob', '2024-02-01 20:00:00', 1000, NULL),
    (2, 'carol', '2024-02-01 20:01:00', 1000, NULL),
    (2, 'Bob', '2024-02-01 20:02:00', 0, NULL);
INSERT INTO game_payments VALUES
    (7, 1, 'bob', 'alice', 1500, 0),
    (8, 1, 'ghost', 'alice', 1, 1);
'''


class TestMigrationAddUsers(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(':memory:')
        self.connection.executescript(OLD_SCHEMA + OLD_DATA)
        self.connection.commit()

    def tearDown(self):
        self.connection.close()

    def user_ids(self) -> dict[str, int]:
        rows = self.connection.execute(
            "SELECT handle, user_id FROM user_payment_methods WHERE method = 'venmo'")
        return {handle: user_id for handle, user_id in rows}

    def test_migrates_everything(self):
        self.assertTrue(migrate(self.connection))

        tables = table_names(self.connection)
        self.assertIn('users', tables)
        self.assertIn(LEGACY_PLAYERS_TABLE, tables)
        self.assertNotIn('players', tables)
        for table in ['games_new', 'game_players_new', 'game_payments_new']:
            self.assertNotIn(table, tables)

        ids = self.user_ids()
        # 'ghost' only appears in games and payments, never in players
        self.assertEqual({'alice', 'bob', 'Bob', 'carol', 'ghost'}, set(ids))

        users = {
            row[0]: row[1:]
            for row in self.connection.execute(
                'SELECT display_name, phone_number, active_game_id, id FROM users')
        }
        self.assertEqual((None, None, ids['alice']), users['alice'])
        self.assertEqual((None, 2, ids['bob']), users['bob'])
        self.assertEqual((None, 2, ids['carol']), users['carol'])
        self.assertEqual((None, None, ids['ghost']), users['ghost'])

        games = self.connection.execute(
            'SELECT id, creator_id, created, lobby_name, buyin_cents, entry_code, '
            'is_active, payout_type FROM games ORDER BY id').fetchall()
        self.assertEqual([
            (1, ids['alice'], '2024-01-01 20:00:00',
             "Alice's Game", 2000, 'ABCD', 0, 1),
            (2, ids['bob'], '2024-02-01 20:00:00',
             "Bob's Game", 1000, 'WXYZ', 1, None),
        ], games)

        game_players = self.connection.execute(
            'SELECT game_id, player_id, join_time, buyin_cents, cashout_cents '
            'FROM game_players ORDER BY game_id, join_time').fetchall()
        self.assertEqual([
            (1, ids['alice'], '2024-01-01 20:00:00', 2000, 3500),
            (1, ids['bob'], '2024-01-01 20:01:00', 2000, 500),
            (1, ids['ghost'], '2024-01-01 20:02:00', 0, 0),
            (2, ids['bob'], '2024-02-01 20:00:00', 1000, None),
            (2, ids['carol'], '2024-02-01 20:01:00', 1000, None),
            (2, ids['Bob'], '2024-02-01 20:02:00', 0, None),
        ], game_players)

        payments = self.connection.execute(
            'SELECT id, game_id, from_player_id, to_player_id, cents, completed '
            'FROM game_payments ORDER BY id').fetchall()
        self.assertEqual([
            (7, 1, ids['bob'], ids['alice'], 1500, 0),
            (8, 1, ids['ghost'], ids['alice'], 1, 1),
        ], payments)

        # New rows keep counting up from the old IDs
        self.connection.execute(
            "INSERT INTO games (creator_id, lobby_name, buyin_cents, entry_code, is_active) "
            "VALUES (1, 'x', 100, 'A', 1)")
        self.assertEqual(3, self.connection.execute(
            'SELECT MAX(id) FROM games').fetchone()[0])

    def test_runs_once(self):
        self.assertTrue(migrate(self.connection))
        self.assertFalse(migrate(self.connection))
        self.assertEqual(5, self.connection.execute(
            'SELECT COUNT(*) FROM users').fetchone()[0])

    def test_fresh_schema_is_untouched(self):
        connection = sqlite3.connect(':memory:')
        with open('schema.sql') as schema_file:
            connection.executescript(schema_file.read())
        self.assertFalse(migrate(connection))
        connection.close()

    def test_rolls_back_on_failure(self):
        # A leftover table makes the migration fail after users were created
        self.connection.execute('CREATE TABLE game_players_new (x)')
        self.connection.commit()

        with self.assertRaises(sqlite3.OperationalError):
            migrate(self.connection)

        tables = table_names(self.connection)
        self.assertIn('players', tables)
        self.assertNotIn('users', tables)
        self.assertNotIn('user_payment_methods', tables)
        self.assertNotIn('games_new', tables)
        self.assertEqual('alice', self.connection.execute(
            'SELECT creator_id FROM games WHERE id = 1').fetchone()[0])


if __name__ == '__main__':
    unittest.main()
