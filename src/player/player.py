from dataclasses import dataclass
from typing import Optional


@dataclass
class Player:
    """
    A PokerPal user. `id` is what games and payments refer to.
    """
    id: int
    display_name: str
    phone_number: Optional[str] = None
    venmo_username: Optional[str] = None
    active_game_id: Optional[int] = None
