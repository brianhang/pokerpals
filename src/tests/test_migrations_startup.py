import multiprocessing
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import db.connection
import migrations.add_users
import utils.secret_key as secret_key
from migrations.run import (PendingMigrationsError, check_migrations,
                            pending_migrations, run_migrations)
from tests.test_migration_add_users import OLD_DATA, OLD_SCHEMA

# The database before payout_type and users existed
OLDEST_SCHEMA = OLD_SCHEMA.replace(',\n    payout_type INTEGER', '')
OLDEST_DATA = OLD_DATA.replace(", 0, 1),", ", 0),").replace(", 1, NULL);", ", 1);")


def migrate_in_worker(db_path: str, start, results) -> None:
    import db.connection as worker_db_connection
    worker_db_connection.DB_PATH = db_path
    from migrations.run import run_migrations as worker_run_migrations
    start.wait()
    try:
        worker_run_migrations()
        results.put('ok')
    except Exception as ex:  # reported back to the test
        results.put(repr(ex))


def read_key_in_worker(tmp_dir: str, start, results) -> None:
    import utils.secret_key as worker_secret_key
    worker_secret_key.SECRET_KEY_PATH = os.path.join(tmp_dir, 'secret_key')
    start.wait()
    results.put(worker_secret_key.load_secret_key())


class TestMigrationsAtStartup(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, 'database.db')
        self.patches = [
            mock.patch.object(db.connection, 'DB_PATH', self.db_path),
            mock.patch.object(secret_key, 'SECRET_KEY_PATH',
                              os.path.join(self.tmp_dir.name, 'secret_key')),
            mock.patch.dict(os.environ, {}),
        ]
        for patch in self.patches:
            patch.start()
        os.environ.pop('APP_SECRET_KEY', None)

    def tearDown(self):
        for patch in reversed(self.patches):
            patch.stop()
        self.tmp_dir.cleanup()

    def create_old_database(self) -> None:
        connection = sqlite3.connect(self.db_path)
        connection.executescript(OLDEST_SCHEMA + OLDEST_DATA)
        connection.commit()
        connection.close()

    def query(self, sql: str):
        connection = sqlite3.connect(self.db_path)
        try:
            return connection.execute(sql).fetchall()
        finally:
            connection.close()

    def test_pending_and_run(self):
        self.create_old_database()
        self.assertEqual(['add_payout_type', 'add_users'], pending_migrations())
        with self.assertRaisesRegex(PendingMigrationsError, 'scripts.migrate'):
            check_migrations()

        run_migrations()

        self.assertEqual([], pending_migrations())
        check_migrations()
        self.assertEqual([(5,)], self.query('SELECT COUNT(*) FROM users'))
        self.assertIn('payout_type', [row[1] for row in self.query('PRAGMA table_info(games)')])

        # Running again changes nothing
        run_migrations()
        self.assertEqual([(5,)], self.query('SELECT COUNT(*) FROM users'))

    def test_new_and_empty_databases_need_nothing(self):
        self.assertEqual([], pending_migrations())  # no tables yet
        with open('schema.sql') as schema_file:
            connection = sqlite3.connect(self.db_path)
            connection.executescript(schema_file.read())
            connection.close()
        self.assertEqual([], pending_migrations())
        check_migrations()

    def start_processes(self, target, extra_args=()):
        context = multiprocessing.get_context('spawn')
        start = context.Event()
        results = context.Queue()
        workers = [
            context.Process(target=target, args=(*extra_args, start, results))
            for _ in range(8)
        ]
        for worker in workers:
            worker.start()
        start.set()
        for worker in workers:
            worker.join(timeout=60)
        return [results.get(timeout=5) for _ in workers]

    def test_workers_migrate_once(self):
        # gunicorn without --preload: every worker loads the app at once
        self.create_old_database()
        results = self.start_processes(migrate_in_worker, (self.db_path,))

        self.assertEqual(['ok'] * 8, results)
        self.assertEqual([], pending_migrations())
        self.assertEqual([(5,)], self.query('SELECT COUNT(*) FROM users'))
        self.assertEqual([(6,)], self.query('SELECT COUNT(*) FROM game_players'))
        self.assertEqual(1, len([name for name in os.listdir(self.tmp_dir.name)
                                 if name.endswith('.bak')]))

    def test_migrate_command(self):
        self.create_old_database()
        from scripts import migrate
        with mock.patch('builtins.print') as printed:
            migrate.main()
            migrate.main()
        messages = [call.args[0] for call in printed.call_args_list]
        self.assertIn('Running migrations: add_payout_type, add_users', messages)
        self.assertEqual('No pending migrations', messages[-1])

    def load_app(self) -> subprocess.CompletedProcess:
        """
        Imports the app in a fresh process, as gunicorn --preload does.
        """
        code = (
            'import sys; sys.path.insert(0, ".");'
            'from tests.app_harness import stub_missing_modules; stub_missing_modules();'
            f'import db.connection; db.connection.DB_PATH = {self.db_path!r};'
            'import app; print("loaded")'
        )
        return subprocess.run(
            [sys.executable, '-c', code],
            capture_output=True, text=True,
            env={**os.environ, 'APP_SECRET_KEY': 'x'},
        )

    def test_loading_app_migrates(self):
        self.create_old_database()
        result = self.load_app()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn('loaded', result.stdout)
        self.assertIn('Migrated 5 Venmo players to users', result.stdout)
        self.assertEqual([], pending_migrations())

        # Loading again finds nothing to do
        result = self.load_app()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotIn('Migrated', result.stdout)

    def test_app_does_not_start_if_migration_fails(self):
        # A leftover table makes the users migration fail partway
        self.create_old_database()
        connection = sqlite3.connect(self.db_path)
        connection.execute('CREATE TABLE game_players_new (x)')
        connection.commit()
        connection.close()

        result = self.load_app()
        self.assertNotEqual(0, result.returncode)
        self.assertNotIn('loaded', result.stdout)
        self.assertIn('table game_players_new already exists', result.stderr)
        self.assertIn('add_users', pending_migrations())

    def test_workers_share_one_session_key(self):
        context = multiprocessing.get_context('spawn')
        start = context.Event()
        results = context.Queue()
        workers = [
            context.Process(target=read_key_in_worker,
                            args=(self.tmp_dir.name, start, results))
            for _ in range(8)
        ]
        for worker in workers:
            worker.start()
        start.set()
        for worker in workers:
            worker.join(timeout=60)

        keys = {results.get(timeout=5) for _ in workers}
        self.assertEqual(1, len(keys))
        self.assertEqual(64, len(keys.pop()))
        self.assertEqual(['secret_key'], [name for name in os.listdir(
            self.tmp_dir.name) if 'secret_key' in name])


if __name__ == '__main__':
    unittest.main()
