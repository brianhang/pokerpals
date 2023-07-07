from dataclasses import dataclass
from datetime import datetime


@dataclass
class Game:
    id: int
    created: datetime
    lobby_name: str
    buyin_cents: int
