import db.cursor
from typing import Optional
from .player import Player


def fetch(venmo_username: str) -> Optional[Player]:
    with db.cursor.get() as cursor:
        cursor.execute(
            'SELECT venmo_username, active_game_id FROM players WHERE venmo_username = ? LIMIT 1', (venmo_username,))
        row = cursor.fetchone()

        if not row:
            return None

        return Player(
            venmo_username=row[0],
            active_game_id=row[1]
        )


def create(venmo_username: str) -> Player:
    with db.cursor.get() as cursor:
        cursor.execute(
            "INSERT INTO players (venmo_username) VALUES (?)", (venmo_username,))
    return Player(
        venmo_username=venmo_username
    )
