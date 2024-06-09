import math
from typing import Optional

from game_players.game_players import GamePlayer


def find_biggest_winner(game_players: list[GamePlayer]) -> Optional[GamePlayer]:
    if not game_players:
        return None

    highest_earnings = -math.inf
    biggest_winner = None

    for player in game_players:
        earnings = player.earnings_cents()

        if earnings and earnings > highest_earnings:
            biggest_winner = player
            highest_earnings = earnings

    return biggest_winner
