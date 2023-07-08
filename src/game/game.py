from dataclasses import dataclass
from datetime import datetime


@dataclass
class Game:
    id: int
    creator_id: str
    created: datetime
    lobby_name: str
    buyin_cents: int
    entry_code: str
