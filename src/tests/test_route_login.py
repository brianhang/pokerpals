import time
import unittest

from tests.app_harness import AppTestCase
from tests.test_migration_add_users import OLD_DATA, OLD_SCHEMA

PHONE = '+14155550123'
OTHER_PHONE = '+14155550199'


class TestPhoneLogin(AppTestCase):
    def setUp(self):
        super().setUp()
        self.create_schema()

    def test_logged_out_home_shows_phone_login(self):
        response = self.client.get('/')
        self.assertEqual(200, response.status_code)
        self.assertIn(b'name="phone-number"', response.data)

    def test_invalid_phone_number(self):
        response = self.send_code('555-0123')
        self.assertEqual(400, response.status_code)
        self.assertIn(b'valid phone number', response.data)
        self.assertEqual({}, self.dev_codes)

    def test_new_user(self):
        response = self.send_code('(415) 555-0123')
        self.assertEqual(303, response.status_code)
        self.assertTrue(response.location.endswith('/login/verify'))

        page = self.client.get('/login/verify')
        self.assertIn('+1 •••-•••-0123'.encode(), page.data)

        response = self.verify(self.last_code(PHONE))
        self.assertTrue(response.location.endswith('/login/welcome'))

        self.valid_venmo_usernames.add('new-venmo')
        response = self.client.post('/login/welcome', data={
            'action': 'create',
            'display-name': '  Dana   Smith ',
            'venmo-username': '@new-venmo',
        })
        self.assertEqual(303, response.status_code)

        self.assertEqual(
            [(PHONE, 'Dana Smith', 'new-venmo')],
            self.query(
                'SELECT u.phone_number, u.display_name, v.handle FROM users u '
                'LEFT JOIN user_payment_methods v ON v.user_id = u.id'),
        )
        self.assertIn(b'Welcome, Dana Smith!', self.client.get('/').data)

    def test_new_user_without_venmo(self):
        response = self.log_in_new(PHONE, 'Dana')
        self.assertEqual(303, response.status_code)
        self.assertEqual(0, self.query(
            'SELECT COUNT(*) FROM user_payment_methods')[0][0])

    def test_new_user_unknown_venmo(self):
        self.send_code(PHONE)
        self.verify(self.last_code(PHONE))
        response = self.client.post('/login/welcome', data={
            'action': 'create',
            'display-name': 'Dana',
            'venmo-username': 'nobody',
        })
        self.assertEqual(400, response.status_code)
        self.assertIn(b'Could not find @nobody', response.data)
        self.assertEqual(0, self.query('SELECT COUNT(*) FROM users')[0][0])

    def test_new_user_needs_name(self):
        self.send_code(PHONE)
        self.verify(self.last_code(PHONE))
        response = self.client.post(
            '/login/welcome', data={'action': 'create', 'display-name': '  '})
        self.assertEqual(400, response.status_code)
        response = self.client.post(
            '/login/welcome', data={'action': 'create', 'display-name': 'x' * 41})
        self.assertEqual(400, response.status_code)
        self.assertEqual(0, self.query('SELECT COUNT(*) FROM users')[0][0])

    def test_returning_user_skips_welcome(self):
        self.log_in_new(PHONE, 'Dana')
        self.client.post('/logout')
        self.assertIn(b'name="phone-number"', self.client.get('/').data)

        self.send_code(PHONE)
        response = self.verify(self.last_code(PHONE))
        self.assertEqual(303, response.status_code)
        self.assertTrue(response.location.endswith('/'))
        self.assertIn(b'Welcome, Dana!', self.client.get('/').data)

    def test_wrong_code(self):
        self.send_code(PHONE)
        code = self.last_code(PHONE)
        wrong = '000000' if code != '000000' else '111111'

        response = self.verify(wrong)
        self.assertEqual(400, response.status_code)
        self.assertIn(b'not right', response.data)

        # Still on the code step, and the right code still works
        response = self.verify(code)
        self.assertTrue(response.location.endswith('/login/welcome'))

    def test_too_many_wrong_codes(self):
        self.send_code(PHONE)
        code = self.last_code(PHONE)
        wrong = '000000' if code != '000000' else '111111'

        for _ in range(5):
            self.verify(wrong)

        response = self.verify(code)
        self.assertEqual(400, response.status_code)

    def test_code_is_for_one_number(self):
        self.send_code(OTHER_PHONE)
        other_code = self.last_code(OTHER_PHONE)
        self.send_code(PHONE)
        if other_code != self.last_code(PHONE):
            self.assertEqual(400, self.verify(other_code).status_code)

    def test_cannot_skip_verification(self):
        self.send_code(PHONE)
        response = self.client.get('/login/welcome')
        self.assertTrue(response.location.endswith('/login'))
        response = self.client.post(
            '/login/welcome', data={'action': 'create', 'display-name': 'Mallory'})
        self.assertTrue(response.location.endswith('/login'))
        self.assertEqual(0, self.query('SELECT COUNT(*) FROM users')[0][0])

    def test_pending_login_expires(self):
        self.send_code(PHONE)
        with self.client.session_transaction() as session:
            session['login'] = {**session['login'], 'started': time.time() - 16 * 60}
        response = self.verify(self.last_code(PHONE))
        self.assertTrue(response.location.endswith('/login'))

    def test_resend_cooldown(self):
        self.send_code(PHONE)
        response = self.client.post('/login/resend')
        self.assertEqual(429, response.status_code)

        with self.client.session_transaction() as session:
            session['login'] = {**session['login'], 'sent': time.time() - 31}
        response = self.client.post('/login/resend')
        self.assertEqual(200, response.status_code)
        self.assertIn(b'new code', response.data)

    def test_return_to_game(self):
        self.run_sql(
            "INSERT INTO users (id, display_name) VALUES (50, 'Host');"
            "INSERT INTO games VALUES (3, 50, '2024-01-01 20:00:00', 'Game', 100, 'CODE', 1, NULL);")
        page = self.client.get('/game/join/3?code=CODE')
        self.assertIn(b'name="return" value="game_join_form"', page.data)

        response = self.log_in_new(
            PHONE, 'Dana',
            **{'return': 'game_join_form', 'return_game_id': '3', 'return_game_code': 'CODE'})
        self.assertTrue(response.location.endswith('/game/join/3?code=CODE'))

    def test_return_endpoint_is_allowlisted(self):
        response = self.log_in_new(PHONE, 'Dana', **{'return': 'logout'})
        self.assertTrue(response.location.endswith('/'))

    def test_session_cookie_cannot_be_forged(self):
        self.client.set_cookie('session', '{"user_id": 1}')
        self.client.set_cookie('venmo_username', 'alice')
        self.assertIn(b'name="phone-number"', self.client.get('/').data)

    def test_no_code_without_twilio_or_debug(self):
        import os
        os.environ.pop('APP_DEBUG')

        page = self.client.get('/login')
        self.assertIn(b'value="Log In"', page.data)
        self.assertNotIn(b'text you a code', page.data)

        # New number: straight to sign up, no code sent
        response = self.send_code(PHONE)
        self.assertTrue(response.location.endswith('/login/welcome'))
        self.assertEqual({}, self.dev_codes)
        self.client.post('/login/welcome', data={'action': 'create', 'display-name': 'Dana'})
        self.assertIn(b'Welcome, Dana!', self.client.get('/').data)

        # Known number: logged straight in
        self.client.post('/logout')
        response = self.send_code(PHONE)
        self.assertTrue(response.location.endswith('/'))
        self.assertIn(b'Welcome, Dana!', self.client.get('/').data)

    def test_code_required_in_debug(self):
        self.assertIn(b'value="Send Code"', self.client.get('/login').data)
        response = self.send_code(PHONE)
        self.assertTrue(response.location.endswith('/login/verify'))
        self.assertEqual(302, self.client.get('/login/welcome').status_code)

class TestClaimVenmoProfile(AppTestCase):
    def setUp(self):
        super().setUp()
        self.run_sql(OLD_SCHEMA + OLD_DATA)

        import db.connection
        from migrations.add_users import migrate
        with db.connection.open_connection() as connection:
            migrate(connection)

        self.bob_id = self.query(
            "SELECT user_id FROM user_payment_methods WHERE handle = 'bob'")[0][0]

    def claim(self, venmo_username: str, phone_number=PHONE, client=None):
        client = client or self.client
        self.send_code(phone_number, client=client)
        self.verify(self.last_code(phone_number), client=client)
        return client.post('/login/welcome', data={
            'action': 'claim',
            'venmo-username': venmo_username,
        })

    def test_claim_keeps_history(self):
        response = self.claim('@bob')
        self.assertEqual(303, response.status_code)
        self.assertEqual([(PHONE,)], self.query(
            'SELECT phone_number FROM users WHERE id = ?', (self.bob_id,)))

        home = self.client.get('/').data.decode()
        self.assertIn('Welcome, bob!', home)
        # bob owes alice from game 1 and is still playing game 2
        self.assertIn('$15.00 to alice', home)
        self.assertIn('venmo.com/?recipients=alice', home)
        self.assertIn("You are currently in Bob&#39;s Game", home)

        game = self.client.get('/g/1?code=ABCD').data.decode()
        self.assertIn('Created by alice', game)
        self.assertIn('bob\n                sends $15.00 to\n                alice', game)

        # bob created game 2, so he can manage it and edit players
        game = self.client.get('/g/2?code=WXYZ').data.decode()
        self.assertIn('/game/end/2/', game)
        carol_id = self.query(
            "SELECT user_id FROM user_payment_methods WHERE handle = 'carol'")[0][0]
        self.assertIn(f'/game/edit/2/{carol_id}', game)

    def test_claim_prefers_exact_venmo_match(self):
        # 'bob' and 'Bob' were separate players under the old login
        self.claim('bob')
        self.assertEqual([(self.bob_id,)], self.query(
            'SELECT id FROM users WHERE phone_number IS NOT NULL'))

    def test_claim_is_case_insensitive(self):
        self.claim('ALICE')
        self.assertEqual([('alice',)], self.query(
            'SELECT display_name FROM users WHERE phone_number IS NOT NULL'))

    def test_cannot_claim_twice(self):
        self.claim('bob')
        self.client.post('/logout')

        other_client = self.app.test_client()
        response = self.claim('bob', phone_number=OTHER_PHONE,
                              client=other_client)
        self.assertEqual(400, response.status_code)
        self.assertIn(b'already been claimed', response.data)
        self.assertEqual([(PHONE,)], self.query(
            'SELECT phone_number FROM users WHERE id = ?', (self.bob_id,)))

    def test_claim_unknown_venmo(self):
        response = self.claim('nobody')
        self.assertEqual(400, response.status_code)
        self.assertIn(b'No one has played as @nobody', response.data)

    def test_new_profile_pointed_to_claim(self):
        self.valid_venmo_usernames.add('alice')
        self.send_code(PHONE)
        self.verify(self.last_code(PHONE))
        response = self.client.post('/login/welcome', data={
            'action': 'create',
            'display-name': 'Alice',
            'venmo-username': 'alice',
        })
        self.assertEqual(400, response.status_code)
        self.assertIn(b'claim it above', response.data)
        self.assertEqual(0, self.query(
            'SELECT COUNT(*) FROM users WHERE phone_number IS NOT NULL')[0][0])

    def test_new_profile_with_taken_venmo(self):
        self.claim('alice')
        self.client.post('/logout')

        self.valid_venmo_usernames.add('alice')
        other_client = self.app.test_client()
        self.send_code(OTHER_PHONE, client=other_client)
        self.verify(self.last_code(OTHER_PHONE), client=other_client)
        response = other_client.post('/login/welcome', data={
            'action': 'create',
            'display-name': 'Not Alice',
            'venmo-username': 'Alice',
        })
        self.assertEqual(400, response.status_code)
        self.assertIn(b'already used by someone else', response.data)


class TestGamesWithUsers(AppTestCase):
    def setUp(self):
        super().setUp()
        self.create_schema()

    def test_game_round_trip(self):
        host = self.client
        guest = self.app.test_client()

        self.valid_venmo_usernames.add('host-venmo')
        self.send_code(PHONE, client=host)
        self.verify(self.last_code(PHONE), client=host)
        host.post('/login/welcome', data={
            'action': 'create', 'display-name': 'Host', 'venmo-username': 'host-venmo'})
        self.log_in_new(OTHER_PHONE, 'Guest', client=guest)

        create_form = host.get('/game/create').data
        self.assertIn(b"Host&#39;s Game", create_form)

        response = host.post('/game/create', data={
            'lobby-name': 'Friday', 'buy-in': '20', 'entry-code': 'FRI', 'payout-type': '1'})
        game_id = int(response.location.rstrip('/').split('/')[-1])

        guest.post(f'/game/join/{game_id}', data={'entry-code': 'fri'})
        host.post('/game/buyin', data={'amount': '20'})
        guest.post('/game/buyin', data={'amount': '20'})
        host.post('/game/cashout', data={'amount': '30'})
        guest.post('/game/cashout', data={'amount': '10'})

        self.assertEqual([(0,)], self.query(
            'SELECT is_active FROM games WHERE id = ?', (game_id,)))

        guest_home = guest.get('/').data.decode()
        self.assertIn('$10.00 to Host', guest_home)
        self.assertIn('recipients=host-venmo', guest_home)
        self.assertIn('txn=pay', guest_home)

        # The host has no way to charge a guest without Venmo
        host_home = host.get('/').data.decode()
        self.assertIn('$10.00 from Guest', host_home)
        self.assertIn('No Venmo set up', host_home)

        payment_id = self.query('SELECT id FROM game_payments')[0][0]
        response = guest.post(
            f'/payment/dismiss/{payment_id}', data={'confirmed': '1'})
        self.assertEqual(303, response.status_code)
        self.assertNotIn('$10.00 to Host', guest.get('/').data.decode())

    def test_edit_player_requires_permission(self):
        host = self.client
        guest = self.app.test_client()
        self.log_in_new(PHONE, 'Host', client=host)
        self.log_in_new(OTHER_PHONE, 'Guest', client=guest)

        response = host.post('/game/create', data={
            'lobby-name': 'Friday', 'buy-in': '20', 'entry-code': 'FRI'})
        game_id = int(response.location.rstrip('/').split('/')[-1])
        guest.post(f'/game/join/{game_id}', data={'entry-code': 'FRI'})

        host_id, guest_id = [row[0] for row in self.query(
            'SELECT id FROM users ORDER BY id')]

        self.assertEqual(403, guest.get(
            f'/game/edit/{game_id}/{host_id}').status_code)
        page = host.get(f'/game/edit/{game_id}/{guest_id}')
        self.assertEqual(200, page.status_code)
        self.assertIn(b'editing the details for Guest', page.data)


if __name__ == '__main__':
    unittest.main()
