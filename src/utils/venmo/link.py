import urllib.parse

import utils.cents as cent_utils

from enum import Enum


class Transaction(Enum):
    CHARGE = 'charge'
    PAY = 'pay'


def get_payment_url(
    venmo_username: str,
    txn: Transaction,
    amount_cents: int,
    is_mobile=False,
    note='Poker',
) -> str:
    amount = cent_utils.to_numerical_string(amount_cents)

    if is_mobile:
        base_url = 'venmo://paycharge'
    else:
        base_url = f'https://venmo.com/'

    query = urllib.parse.urlencode({
        'recipients': venmo_username,
        'txn': txn.value,
        'note': note,
        'amount': amount,
    }, quote_via=urllib.parse.quote)
    return f'{base_url}?{query}'
