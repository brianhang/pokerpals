from collections import defaultdict, namedtuple
from typing import List

from game_players.game_players import GamePlayer

Transaction = namedtuple("Transaction", ["sender_id", "receiver_id", "cents"])

DIFF_CENTS = 0
DIFF_PLAYER_ID = 1


def get_transactions(game_players: list[GamePlayer]) -> list[Transaction]:
    transactions = []
    positive = []
    negative = []

    for player in game_players:
        diff = player.cashout_cents - player.buyin_cents
        entry = [diff, player.player_venmo_username]
        if diff > 0:
            positive.append(entry)
        else:
            negative.append(entry)

    positive.sort()
    negative.sort(reverse=True)

    while positive and negative:
        sender = negative[-1]
        receiver = positive[-1]
        cents = min(-sender[DIFF_CENTS], receiver[DIFF_CENTS])
        transactions.append(Transaction(
            sender[DIFF_PLAYER_ID],
            receiver[DIFF_PLAYER_ID],
            cents
        ))

        sender[DIFF_CENTS] += cents
        receiver[DIFF_CENTS] -= cents

        if sender[DIFF_CENTS] == 0:
            negative.pop()
        if receiver[DIFF_CENTS] == 0:
            positive.pop()

    return transactions
