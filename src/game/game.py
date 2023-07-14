from dataclasses import dataclass
from datetime import datetime
from utils import cents as cent_utils


@dataclass
class Game:
    id: int
    creator_id: str
    created: datetime
    lobby_name: str
    buyin_cents: int
    entry_code: str
    is_active: bool

    def buyin_text(self) -> str:
        return cent_utils.to_string(self.buyin_cents)
