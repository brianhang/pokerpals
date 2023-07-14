from dataclasses import dataclass
from utils import cents as cent_utils


@dataclass
class Payment:
    id: int
    game_id: int
    from_player_id: str
    to_player_id: str
    cents: int
    completed: bool = False

    def amount_text(self) -> str:
        return cent_utils.to_string(self.cents)
