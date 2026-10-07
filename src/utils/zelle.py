"""
Zelle has no public link that opens a payment with the recipient and amount
filled in, and its standalone app has been shut down, so payments are made in
each person's bank app. PokerPal shows the recipient's Zelle phone number or
email and the amount, ready to copy.
"""
import re
from typing import Optional

from utils import phone as phone_utils

EMAIL_PATTERN = re.compile(r'^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$')
MAX_EMAIL_LENGTH = 254


def normalize(raw: Optional[str]) -> Optional[str]:
    """
    A Zelle handle is a phone number (stored as E.164) or an email address
    (stored lowercase). Returns None if it is neither.
    """
    raw = (raw or '').strip()

    if '@' in raw:
        email = raw.lower()
        if len(email) <= MAX_EMAIL_LENGTH and EMAIL_PATTERN.match(email):
            return email
        return None

    return phone_utils.normalize(raw)


def is_email(handle: str) -> bool:
    return '@' in handle


def display(handle: str) -> str:
    """
    How to show a handle, e.g. (415) 555-0123 for US numbers.
    """
    if not is_email(handle) and handle.startswith('+1') and len(handle) == 12:
        digits = handle[2:]
        return f'({digits[:3]}) {digits[3:6]}-{digits[6:]}'
    return handle
