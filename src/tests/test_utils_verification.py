import os
import unittest
from unittest import mock

import requests

from utils import verification

TWILIO_ENV = {
    'TWILIO_ACCOUNT_SID': 'AC123',
    'TWILIO_AUTH_TOKEN': 'token',
    'TWILIO_VERIFY_SERVICE_SID': 'VA456',
}
SERVICE_URL = 'https://verify.twilio.com/v2/Services/VA456'


def twilio_response(status_code: int, body: dict) -> mock.Mock:
    response = mock.Mock(status_code=status_code, text=str(body))
    response.json.return_value = body
    return response


@mock.patch.dict(os.environ, TWILIO_ENV)
class TestTwilioVerify(unittest.TestCase):
    @mock.patch('utils.verification.requests.post')
    def test_send_code(self, post):
        post.return_value = twilio_response(201, {'status': 'pending'})
        verification.send_code('+14155550123')
        post.assert_called_once_with(
            f'{SERVICE_URL}/Verifications',
            data={'To': '+14155550123', 'Channel': 'sms'},
            auth=('AC123', 'token'),
            timeout=verification.TWILIO_TIMEOUT_SECONDS,
        )

    @mock.patch('utils.verification.requests.post')
    def test_check_code_approved(self, post):
        post.return_value = twilio_response(200, {'status': 'approved'})
        self.assertTrue(verification.check_code('+14155550123', '123 456'))
        post.assert_called_once_with(
            f'{SERVICE_URL}/VerificationCheck',
            data={'To': '+14155550123', 'Code': '123456'},
            auth=('AC123', 'token'),
            timeout=verification.TWILIO_TIMEOUT_SECONDS,
        )

    @mock.patch('utils.verification.requests.post')
    def test_check_code_wrong(self, post):
        post.return_value = twilio_response(200, {'status': 'pending'})
        self.assertFalse(verification.check_code('+14155550123', '000000'))

    @mock.patch('utils.verification.requests.post')
    def test_check_code_expired(self, post):
        post.return_value = twilio_response(404, {'code': 20404})
        self.assertFalse(verification.check_code('+14155550123', '123456'))

    @mock.patch('utils.verification.requests.post')
    def test_check_code_not_digits_skips_twilio(self, post):
        self.assertFalse(verification.check_code('+14155550123', 'abc'))
        post.assert_not_called()

    @mock.patch('utils.verification.requests.post')
    def test_rate_limited(self, post):
        post.return_value = twilio_response(429, {'code': 60203})
        with self.assertRaisesRegex(verification.VerificationError, 'Too many'):
            verification.send_code('+14155550123')

    @mock.patch('utils.verification.requests.post')
    def test_invalid_number(self, post):
        post.return_value = twilio_response(400, {'code': 60200})
        with self.assertRaisesRegex(verification.VerificationError, 'cannot receive texts'):
            verification.send_code('+14155550123')

    @mock.patch('utils.verification.requests.post')
    def test_network_error(self, post):
        post.side_effect = requests.exceptions.ConnectionError()
        with self.assertRaisesRegex(verification.VerificationError, 'Could not reach'):
            verification.send_code('+14155550123')

    def test_twilio_wins_over_dev_mode(self):
        with mock.patch.dict(os.environ, {'APP_DEBUG': '1'}):
            self.assertFalse(verification.is_dev_mode())


class TestNotConfigured(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {})
        self.env.start()
        for name in [*TWILIO_ENV, 'APP_DEBUG']:
            os.environ.pop(name, None)

    def tearDown(self):
        self.env.stop()

    def test_refuses_without_twilio_or_debug(self):
        with self.assertLogs('utils.verification', 'ERROR'):
            with self.assertRaises(verification.VerificationError):
                verification.send_code('+14155550123')
        with self.assertRaises(verification.VerificationError):
            verification.check_code('+14155550123', '123456')


if __name__ == '__main__':
    unittest.main()
