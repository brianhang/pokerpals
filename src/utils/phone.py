import re
from typing import Optional

# E.164: a +, a country code that does not start with 0, up to 15 digits total
E164_PATTERN = re.compile(r'^\+[1-9]\d{7,14}$')
SEPARATORS = re.compile(r'[\s().\-]')


def normalize(raw: Optional[str]) -> Optional[str]:
    """
    Turns user input into an E.164 phone number such as +14155550123, or
    returns None if it does not look like a phone number.

    Numbers without a country code are assumed to be US/Canada (+1).
    International numbers must start with + or 00.
    """
    if not raw:
        return None

    number = SEPARATORS.sub('', raw.strip())

    if number.startswith('00'):
        number = '+' + number[2:]

    if number.startswith('+'):
        return number if E164_PATTERN.match(number) else None

    if not number.isdigit():
        return None

    if len(number) == 11 and number.startswith('1'):
        number = number[1:]

    # North American numbers: area code and exchange can't start with 0 or 1
    if len(number) == 10 and number[0] not in '01' and number[3] not in '01':
        return f'+1{number}'

    return None


def mask(phone_number: str) -> str:
    """
    Hides all but the last 4 digits, e.g. +1 •••-•••-0123.
    """
    if phone_number.startswith('+1') and len(phone_number) == 12:
        return f'+1 •••-•••-{phone_number[-4:]}'
    return f'•••{phone_number[-4:]}'
