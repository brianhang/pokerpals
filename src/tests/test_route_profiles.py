import unittest

from tests.app_harness import AppTestCase
from tests.test_route_login import page_text

HOST_PHONE = '+14155550101'
GUEST_PHONE = '+14155550102'
STRANGER_PHONE = '+14155550103'


class ProfileTestCase(AppTestCase):
    def setUp(self):
        super().setUp()
        self.create_schema()

        self.host = self.client
        self.guest = self.app.test_client()
        self.stranger = self.app.test_client()

        self.log_in_new(HOST_PHONE, 'Host', client=self.host)
        self.log_in_new(GUEST_PHONE, 'Guest', client=self.guest)
        self.log_in_new(STRANGER_PHONE, 'Stranger', client=self.stranger)
        self.host_id, self.guest_id, self.stranger_id = [
            row[0] for row in self.query('SELECT id FROM users ORDER BY id')]

    def save_account(self, client, **fields):
        data = {
            'display-name': fields.get('name', 'Someone'),
            'venmo-username': fields.get('venmo', ''),
            'zelle-handle': fields.get('zelle', ''),
        }
        return client.post('/account', data=data)

    def methods(self, user_id: int) -> dict[str, str]:
        rows = self.query(
            'SELECT method, handle FROM user_payment_methods WHERE user_id = ?', (user_id,))
        return dict(rows)

    def play_game(self, host_cashout: str = '30', guest_cashout: str = '10') -> int:
        """
        Host and guest each buy in $20 and cash out; the game ends.
        """
        response = self.host.post('/game/create', data={
            'lobby-name': 'Friday', 'buy-in': '20', 'entry-code': 'FRI'})
        game_id = int(response.location.rstrip('/').split('/')[-1])
        self.guest.post(f'/game/join/{game_id}', data={'entry-code': 'FRI'})
        self.host.post('/game/buyin', data={'amount': '20'})
        self.guest.post('/game/buyin', data={'amount': '20'})
        self.host.post('/game/cashout', data={'amount': host_cashout})
        self.guest.post('/game/cashout', data={'amount': guest_cashout})
        return game_id


class TestAccount(ProfileTestCase):
    def test_save_name_and_methods(self):
        self.valid_venmo_usernames.add('host-v')
        response = self.save_account(
            self.host, name=' Host  Person ', venmo='@host-v', zelle='(415) 555-0177')
        self.assertEqual(303, response.status_code)
        self.assertTrue(response.location.endswith('/account?saved=1'))

        self.assertEqual([('Host Person',)], self.query(
            'SELECT display_name FROM users WHERE id = ?', (self.host_id,)))
        self.assertEqual(
            {'venmo': 'host-v', 'zelle': '+14155550177'}, self.methods(self.host_id))

        text = page_text(self.host.get('/account?saved=1'))
        self.assertIn('Saved!', text)
        self.assertIn('(415) 555-0177', self.host.get('/account').data.decode())

    def test_zelle_email(self):
        self.save_account(self.host, name='Host', zelle=' Host@Example.COM ')
        self.assertEqual({'zelle': 'host@example.com'}, self.methods(self.host_id))

    def test_clear_methods(self):
        self.valid_venmo_usernames.add('host-v')
        self.save_account(self.host, name='Host', venmo='host-v', zelle='host@example.com')
        self.save_account(self.host, name='Host')
        self.assertEqual({}, self.methods(self.host_id))

    def test_unchanged_venmo_is_not_looked_up_again(self):
        self.valid_venmo_usernames.add('host-v')
        self.save_account(self.host, name='Host', venmo='host-v')
        self.valid_venmo_usernames.clear()
        response = self.save_account(self.host, name='New Name', venmo='Host-V')
        self.assertEqual(303, response.status_code)
        self.assertEqual({'venmo': 'Host-V'}, self.methods(self.host_id))

    def test_invalid_inputs(self):
        cases = [
            ({'name': ''}, 'enter your name'),
            ({'name': 'x' * 41}, 'at most 40'),
            ({'name': 'Host', 'venmo': 'not-on-venmo'}, 'Could not find @not-on-venmo'),
            ({'name': 'Host', 'zelle': 'nope'}, 'phone number or email'),
            ({'name': 'Host', 'zelle': '555-0123'}, 'phone number or email'),
        ]
        for fields, message in cases:
            response = self.save_account(self.host, **fields)
            self.assertEqual(400, response.status_code, fields)
            self.assertIn(message, page_text(response), fields)

        self.assertEqual({}, self.methods(self.host_id))
        self.assertEqual([('Host',)], self.query(
            'SELECT display_name FROM users WHERE id = ?', (self.host_id,)))

    def test_taken_handles(self):
        self.valid_venmo_usernames.update({'host-v', 'HOST-V'})
        self.save_account(self.host, name='Host', venmo='host-v', zelle='host@example.com')

        response = self.save_account(self.guest, name='Guest', venmo='HOST-V')
        self.assertEqual(400, response.status_code)
        self.assertIn('already used', page_text(response))

        response = self.save_account(self.guest, name='Guest', zelle='HOST@example.com')
        self.assertEqual(400, response.status_code)
        self.assertIn('already used', page_text(response))

        self.assertEqual({}, self.methods(self.guest_id))

    def test_requires_login(self):
        client = self.app.test_client()
        self.assertIn(b'name="phone-number"', client.get('/account').data)
        response = client.post('/account', data={'display-name': 'Hacker'})
        self.assertEqual(302, response.status_code)


class TestProfile(ProfileTestCase):
    def setUp(self):
        super().setUp()
        self.valid_venmo_usernames.add('host-v')
        self.save_account(self.host, name='Host', venmo='host-v', zelle='4155550177')

    def test_co_player_sees_zelle(self):
        self.play_game()
        text = page_text(self.guest.get(f'/u/{self.host_id}'))
        self.assertIn('@host-v', text)
        self.assertIn('(415) 555-0177', text)

    def test_stranger_does_not_see_zelle(self):
        text = page_text(self.stranger.get(f'/u/{self.host_id}'))
        self.assertIn('@host-v', text)
        self.assertNotIn('555-0177', text)

    def test_self_sees_zelle_and_edit_link(self):
        response = self.host.get(f'/u/{self.host_id}')
        self.assertIn('(415) 555-0177', page_text(response))
        self.assertIn(b'href="/account"', response.data)
        self.assertNotIn(b'href="/account"', self.guest.get(f'/u/{self.host_id}').data)

    def test_no_methods(self):
        text = page_text(self.host.get(f'/u/{self.guest_id}'))
        self.assertIn("Guest hasn't shared a way to get paid", text)

    def test_requires_login_and_existing_user(self):
        client = self.app.test_client()
        self.assertIn(b'name="phone-number"', client.get(f'/u/{self.host_id}').data)
        self.assertEqual(404, self.host.get('/u/999').status_code)

    def test_game_page_links_to_profiles(self):
        game_id = self.play_game()
        game = self.guest.get(f'/g/{game_id}?code=FRI').data.decode()
        self.assertIn(f'href="/u/{self.host_id}">Host</a>', game)
        self.assertIn(f'href="/u/{self.guest_id}">Guest</a>', game)


class TestPaymentPage(ProfileTestCase):
    def payment_id(self) -> int:
        return self.query('SELECT id FROM game_payments')[0][0]

    def test_sender_sees_venmo_and_zelle(self):
        self.valid_venmo_usernames.add('host-v')
        self.save_account(self.host, name='Host', venmo='host-v', zelle='host@example.com')
        self.play_game()

        response = self.guest.get(f'/payment/{self.payment_id()}')
        html, text = response.data.decode(), page_text(response)
        self.assertIn('Pay $10.00 to Host', text)
        self.assertIn('recipients=host-v&amp;txn=pay', html)
        self.assertIn('amount=10.00', html)
        self.assertIn('data-copy="host@example.com"', html)
        self.assertIn('data-copy="10.00"', html)
        self.assertIn('$10.00', text)

    def test_zelle_only(self):
        self.save_account(self.host, name='Host', zelle='4155550177')
        self.play_game()

        response = self.guest.get(f'/payment/{self.payment_id()}')
        html = response.data.decode()
        self.assertNotIn('<h3>Venmo</h3>', html)
        self.assertIn('data-copy="(415) 555-0177"', html)

        # The home page card sends them to the payment page
        home = self.guest.get('/').data.decode()
        self.assertIn(f'href="/payment/{self.payment_id()}">', home)
        self.assertIn('Pay', page_text(self.guest.get('/')))

    def test_receiver_requests_and_shares_zelle(self):
        self.valid_venmo_usernames.add('guest-v')
        self.save_account(self.guest, name='Guest', venmo='guest-v')
        self.save_account(self.host, name='Host', zelle='host@example.com')
        self.play_game()

        response = self.host.get(f'/payment/{self.payment_id()}')
        html, text = response.data.decode(), page_text(response)
        self.assertIn('Collect $10.00 from Guest', text)
        self.assertIn('recipients=guest-v&amp;txn=charge', html)
        self.assertIn('Guest can send it to your Zelle at host@example.com', text)

    def test_no_methods(self):
        self.play_game()
        text = page_text(self.guest.get(f'/payment/{self.payment_id()}'))
        self.assertIn("Host hasn't added Venmo or Zelle yet", text)
        text = page_text(self.host.get(f'/payment/{self.payment_id()}'))
        self.assertIn("Guest hasn't added Venmo, and you haven't added Zelle", text)

    def test_mark_done_returns_to_payment(self):
        self.play_game()
        payment_id = self.payment_id()

        confirm = self.guest.post(
            f'/payment/dismiss/{payment_id}', data={'return-payment': '1'})
        self.assertIn(b'name="return-payment"', confirm.data)

        response = self.guest.post(
            f'/payment/dismiss/{payment_id}',
            data={'return-payment': '1', 'confirmed': '1'})
        self.assertTrue(response.location.endswith(f'/payment/{payment_id}'))
        self.assertIn('marked as done', page_text(self.guest.get(response.location)))

    def test_only_participants(self):
        self.play_game()
        payment_id = self.payment_id()
        self.assertEqual(403, self.stranger.get(f'/payment/{payment_id}').status_code)
        self.assertEqual(404, self.host.get('/payment/999').status_code)


if __name__ == '__main__':
    unittest.main()
