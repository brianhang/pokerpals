from typing import Optional

from game_players.game_players import GamePlayer


def find_biggest_winner(game_players: list[GamePlayer]) -> Optional[GamePlayer]:
    if not game_players:
        return None

    return max(game_players, key=lambda player: player.earnings_cents())
