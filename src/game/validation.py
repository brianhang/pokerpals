from typing import Optional

import utils.cents as cents_utils
from game_players.game_players import GamePlayers


def get_end_game_err(players: GamePlayers) -> Optional[str]:
    leftover_cents = players.total_buyin_cents() - players.total_cashout_cents()

    if leftover_cents < 0:
        return f'There is ${cents_utils.to_string(-leftover_cents)} extra being cashed out, please check the cash out amounts are valid'

    return None
