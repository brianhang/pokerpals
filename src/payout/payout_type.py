from enum import Enum


class PayoutType(Enum):
    MINIMIZE_TRANSACTIONS = 1
    BIGGEST_WINNER = 2


DEFAULT_PAYOUT_TYPE = PayoutType.MINIMIZE_TRANSACTIONS
