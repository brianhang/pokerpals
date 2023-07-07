import datetime
import time
import db.cursor
from typing import Optional
from .game import Game


class CreateGameException(Exception):
    pass


def fetch(game_id: int) -> Optional[Game]:
    with db.cursor.get() as cursor:
        cursor.execute(
            'SELECT created, lobby_name, buyin_amt_cents FROM games WHERE id = ?', (game_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return Game(
            id=game_id,
            created=row[0],
            lobby_name=row[1],
            buyin_cents=row[2]
        )


def create(lobby_name: str, buyin_cents: int) -> Game:
    game_id = None
    ts = time.time()
    created = datetime.datetime.fromtimestamp(ts)
    created_str = created.strftime("%d-%m-%Y-%H-%M-%S")

    with db.cursor.get() as cursor:
        cursor.execute("INSERT INTO games (lobby_name, created, buyin_amt_cents) VALUES (?, ?, ?)",
                       (lobby_name, created_str, buyin_cents,))
        game_id = cursor.lastrowid()

    if not game_id:
        raise CreateGameException("Could not insert into database")

    return Game(
        game_id=game_id,
        created=created_str,
        lobby_name=lobby_name,
        buyin_cents=buyin_cents
    )
