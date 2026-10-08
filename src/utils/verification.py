"""
Sends and checks phone number login codes.

In production this uses Twilio Verify, configured with the environment
variables TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and TWILIO_VERIFY_SERVICE_SID.
Twilio generates the codes, sends the texts, expires codes and limits
attempts.

When Twilio is not configured and the app runs with APP_DEBUG set, codes are
generated locally and printed to the server log instead, so development does
not need a Twilio account.

With neither, verification is off: people log in by entering a phone number,
without a code. This lets the app run before Twilio is set up; anyone can log
in with any number, just as anyone could type any Venmo username before.
"""
import logging
import os
import secrets
import time
from dataclasses import dataclass
from typing import Optional

import requests

TWILIO_VERIFY_URL = 'https://verify.twilio.com/v2/Services/{service_sid}'
TWILIO_TIMEOUT_SECONDS = 10

DEV_CODE_LENGTH = 6
DEV_CODE_TTL_SECONDS = 10 * 60
DEV_MAX_ATTEMPTS = 5

logger = logging.getLogger(__name__)


class VerificationError(Exception):
    """
    A code could not be sent or checked. The message is safe to show users.
    """


@dataclass
class DevCode:
    code: str
    expires_at: float
    attempts: int = 0


_dev_codes: dict[str, DevCode] = {}


def twilio_config() -> Optional[tuple[str, str, str]]:
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    service_sid = os.environ.get('TWILIO_VERIFY_SERVICE_SID')

    if account_sid and auth_token and service_sid:
        return account_sid, auth_token, service_sid
    return None


def is_dev_mode() -> bool:
    return twilio_config() is None and os.environ.get('APP_DEBUG') is not None


def is_enabled() -> bool:
    """
    If logging in requires a texted code.
    """
    return twilio_config() is not None or is_dev_mode()


def send_code(phone_number: str) -> None:
    config = twilio_config()

    if config:
        twilio_request(config, 'Verifications', {
            'To': phone_number,
            'Channel': 'sms',
        })
        return

    if not is_dev_mode():
        logger.error('Phone login is not configured: set the TWILIO_* '
                     'environment variables')
        raise VerificationError(
            'Phone login is not set up yet, please try again later')

    code = ''.join(secrets.choice('0123456789')
                   for _ in range(DEV_CODE_LENGTH))
    _dev_codes[phone_number] = DevCode(
        code=code,
        expires_at=time.time() + DEV_CODE_TTL_SECONDS,
    )
    print(f'[dev] Login code for {phone_number}: {code}', flush=True)


def check_code(phone_number: str, code: str) -> bool:
    code = ''.join(code.split())
    if not code.isdigit():
        return False

    config = twilio_config()

    if config:
        result = twilio_request(config, 'VerificationCheck', {
            'To': phone_number,
            'Code': code,
        }, not_found_ok=True)
        return bool(result) and result.get('status') == 'approved'

    if not is_dev_mode():
        raise VerificationError(
            'Phone login is not set up yet, please try again later')

    dev_code = _dev_codes.get(phone_number)
    if not dev_code or dev_code.expires_at < time.time():
        _dev_codes.pop(phone_number, None)
        return False

    dev_code.attempts += 1
    if dev_code.attempts > DEV_MAX_ATTEMPTS:
        _dev_codes.pop(phone_number, None)
        return False

    if secrets.compare_digest(dev_code.code, code):
        _dev_codes.pop(phone_number, None)
        return True

    return False


def twilio_request(
    config: tuple[str, str, str],
    endpoint: str,
    data: dict[str, str],
    not_found_ok: bool = False,
) -> Optional[dict]:
    account_sid, auth_token, service_sid = config
    url = f'{TWILIO_VERIFY_URL.format(service_sid=service_sid)}/{endpoint}'

    try:
        response = requests.post(
            url,
            data=data,
            auth=(account_sid, auth_token),
            timeout=TWILIO_TIMEOUT_SECONDS,
        )
    except requests.exceptions.RequestException as ex:
        logger.exception('Twilio Verify request failed')
        raise VerificationError(
            'Could not reach the texting service, please try again') from ex

    # Twilio returns 404 when there is no pending code for the number, e.g.
    # it expired, was already used, or had too many wrong attempts.
    if response.status_code == 404 and not_found_ok:
        return None

    if response.status_code == 429:
        raise VerificationError(
            'Too many attempts, please wait a few minutes and try again')

    if response.status_code >= 400:
        try:
            twilio_code = response.json().get('code')
        except ValueError:
            twilio_code = None

        logger.error('Twilio Verify %s failed: %s %s', endpoint,
                     response.status_code, response.text[:500])

        # 60200: invalid parameter, e.g. a number Twilio can't text
        if twilio_code == 60200:
            raise VerificationError(
                'That phone number cannot receive texts, please check it')
        raise VerificationError(
            'Could not send a code, please try again')

    return response.json()
