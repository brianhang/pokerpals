from dataclasses import dataclass
from typing import Optional
from utils import cents as cent_utils


@dataclass
class Payment:
    id: int
    game_id: int
    from_player_id: int
    to_player_id: int
    cents: int
    completed: bool = False
    from_name: str = ''
    to_name: str = ''
    from_venmo_username: Optional[str] = None
    to_venmo_username: Optional[str] = None

    def amount_text(self) -> str:
        return cent_utils.to_string(self.cents)
