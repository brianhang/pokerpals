from dataclasses import dataclass
from typing import Optional


@dataclass
class Player:
    venmo_username: str
    active_game_id: Optional[int] = None
