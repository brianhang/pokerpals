from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class GamePlayer:
    player_venmo_username: str
    join_time: datetime
    buyin_cents: int
    cashout_cents: Optional[int]


@dataclass
class GamePlayers:
    game_id: int
    players: List[GamePlayer]

    def total_buyin_cents(self) -> int:
        return sum(player.buyin_cents for player in self.players)

    def total_cashout_cents(self) -> int:
        return sum(player.cashout_cents for player in self.players if player.cashout_cents)
