from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from payout.payout_type import PayoutType
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
    payout_type: Optional[PayoutType]

    def buyin_text(self) -> str:
        return cent_utils.to_string(self.buyin_cents)

    def human_created_time(self) -> str:
        return self.created.strftime("%B %d, %Y %I:%M %p")
