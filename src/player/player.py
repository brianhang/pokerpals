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
    # A phone number (E.164) or email address enrolled with Zelle
    zelle_handle: Optional[str] = None

    def has_payment_method(self) -> bool:
        return bool(self.venmo_username or self.zelle_handle)
