from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
from utils import cents as cent_utils


@dataclass
class GamePlayer:
    player_venmo_username: str
    join_time: datetime
    buyin_cents: int
    cashout_cents: Optional[int]

    def buyin_text(self) -> str:
        return cent_utils.to_string(self.buyin_cents)

    def cashout_text(self) -> Optional[str]:
        if self.cashout_cents is not None:
            return cent_utils.to_string(self.cashout_cents)
        return None

    def earnings_cents(self) -> Optional[int]:
        if self.cashout_cents is None:
            return None

        return self.cashout_cents - self.buyin_cents


@dataclass
class GamePlayers:
    game_id: int
    players: List[GamePlayer]

    def total_buyin_cents(self) -> int:
        return sum(player.buyin_cents for player in self.players)

    def total_cashout_cents(self) -> int:
        return sum(player.cashout_cents for player in self.players if player.cashout_cents)
