from game_players.game_players import GamePlayer
from payout.transaction import Transaction
from utils.biggest_winner import find_biggest_winner


def get_transactions(game_players: list[GamePlayer]) -> list[Transaction]:
    if not game_players:
        return []

    biggest_winner = find_biggest_winner(game_players)

    transactions = []

    for player in game_players:
        earnings = player.earnings_cents()

        if player == biggest_winner:
            continue

        if not earnings:
            continue

        if earnings > 0:
            sender = biggest_winner
            receiver = player
        elif earnings < 0:
            sender = player
            receiver = biggest_winner
        else:
            continue

        transactions.append(Transaction(
            sender_id=sender.player_venmo_username,
            receiver_id=receiver.player_venmo_username,
            cents=abs(earnings),
        ))

    return transactions
