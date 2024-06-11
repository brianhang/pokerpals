from enum import Enum


class PayoutType(Enum):
    MINIMIZE_TRANSACTIONS = 1
    BIGGEST_WINNER = 2


DEFAULT_PAYOUT_TYPE = PayoutType.MINIMIZE_TRANSACTIONS

# Human friendly names for the PayoutType values
NAMES = {
    PayoutType.BIGGEST_WINNER: 'Transact through biggest winner',
    PayoutType.MINIMIZE_TRANSACTIONS: 'Minimize transactions per player',
}
