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
