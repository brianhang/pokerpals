from dataclasses import dataclass


@dataclass
class Payment:
    id: int
    game_id: int
    from_player_id: str
    to_player_id: str
    cents: int
    completed: bool = False
