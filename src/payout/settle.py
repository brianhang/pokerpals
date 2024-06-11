from typing import Callable

from game_players.game_players import GamePlayer
from payout.payout_type import PayoutType
from payout.settle_by_biggest_winner import get_transactions as settle_by_biggest_winner
from payout.settle_minimize_transactions import get_transactions as settle_minimize_transactions
from payout.transaction import Transaction


GetTransactionsType = Callable[[list[GamePlayer]], list[Transaction]]


def get_settle_function(payout_type: PayoutType) -> GetTransactionsType:
    if payout_type == PayoutType.BIGGEST_WINNER:
        return settle_by_biggest_winner
    if payout_type == PayoutType.MINIMIZE_TRANSACTIONS:
        return settle_minimize_transactions


def get_transactions_with_payout_type(payout_type: PayoutType, game_players: list[GamePlayer]) -> list[Transaction]:
    settle = get_settle_function(payout_type)
    return settle(game_players)
