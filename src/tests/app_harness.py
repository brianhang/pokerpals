"""
Sets up the Flask app against a temporary database for route tests.

Codes are generated locally (dev mode) instead of through Twilio, and Venmo
username lookups are faked. If the socket.io, mobility, gevent or QR code
packages are not installed, small stand-ins are used so the routes can still
be tested.
"""
import importlib.util
import os
import sys
import tempfile
import types
import unittest
from unittest import mock


def stub_missing_modules() -> None:
    def missing(name: str) -> bool:
        try:
            return importlib.util.find_spec(name) is None
        except ValueError:
            return name not in sys.modules

    if missing('gevent'):
        gevent = types.ModuleType('gevent')
        gevent.monkey = types.SimpleNamespace(patch_all=lambda: None)
        sys.modules['gevent'] = gevent
        sys.modules['gevent.monkey'] = gevent.monkey

    if missing('flask_socketio'):
        flask_socketio = types.ModuleType('flask_socketio')

        class SocketIO:
            def __init__(self, app=None):
                self.emitted = []

            def emit(self, *args):
                self.emitted.append(args)

        flask_socketio.SocketIO = SocketIO
        sys.modules['flask_socketio'] = flask_socketio

    if missing('flask_mobility'):
        from flask import request

        flask_mobility = types.ModuleType('flask_mobility')

        class Mobility:
            def __init__(self, app):
                @app.before_request
                def set_mobile():
                    request.MOBILE = False

        flask_mobility.Mobility = Mobility
        sys.modules['flask_mobility'] = flask_mobility

    if missing('qrcode'):
        sys.modules['qrcode'] = types.ModuleType('qrcode')


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tmp_dir.name, 'database.db')

        self.env = mock.patch.dict(os.environ, {
            'APP_DEBUG': '1',
            'APP_SECRET_KEY': 'test-secret',
        })
        self.env.start()
        for name in ['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_VERIFY_SERVICE_SID']:
            os.environ.pop(name, None)

        stub_missing_modules()

        import db.connection
        self.db_path_patch = mock.patch.object(
            db.connection, 'DB_PATH', db_path)
        self.db_path_patch.start()

        import app as app_module
        import utils.verification
        self.app_module = app_module
        self.dev_codes = utils.verification._dev_codes
        self.dev_codes.clear()

        self.valid_venmo_usernames = set()
        self.venmo_patches = [
            mock.patch(
                f'{module}.is_valid_venmo_username',
                lambda username: username in self.valid_venmo_usernames,
            )
            for module in ['player.route', 'player.profile']
        ]
        for venmo_patch in self.venmo_patches:
            venmo_patch.start()

        self.app = app_module.app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def tearDown(self):
        for venmo_patch in self.venmo_patches:
            venmo_patch.stop()
        self.db_path_patch.stop()
        self.env.stop()
        self.tmp_dir.cleanup()

    def run_sql(self, script: str) -> None:
        import db.connection
        with db.connection.open_connection() as connection:
            connection.executescript(script)
            connection.commit()

    def query(self, sql: str, params=()) -> list:
        import db.connection
        with db.connection.open_connection() as connection:
            return connection.execute(sql, params).fetchall()

    def create_schema(self) -> None:
        with open('schema.sql') as schema_file:
            self.run_sql(schema_file.read())

    def send_code(self, phone_number: str, client=None, **params):
        client = client or self.client
        response = client.post(
            '/login', data={'phone-number': phone_number, **params})
        return response

    def last_code(self, phone_number: str) -> str:
        return self.dev_codes[phone_number].code

    def verify(self, code: str, client=None):
        client = client or self.client
        return client.post('/login/verify', data={'code': code})

    def log_in_new(self, phone_number: str, display_name: str, client=None, **params):
        """
        Logs in with a phone number and creates a profile for it.
        """
        from utils.phone import normalize

        client = client or self.client
        self.send_code(phone_number, client=client, **params)
        self.verify(self.last_code(normalize(phone_number)), client=client)
        return client.post('/login/welcome', data={
            'action': 'create',
            'display-name': display_name,
        })
