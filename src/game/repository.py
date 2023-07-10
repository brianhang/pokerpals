import datetime
import time
import db.cursor
from typing import Optional, List
from .game import Game


class CreateGameException(Exception):
    pass


def fetch_all_active() -> List[Game]:
    games = []

    with db.cursor.get() as cursor:
        cursor.execute(
            'SELECT id, creator_id, created, lobby_name, buyin_cents, entry_code FROM games WHERE is_active = 1 ORDER BY id ASC')

        for row in cursor:
            games.append(Game(
                id=row[0],
                creator_id=row[1],
                created=row[2],
                lobby_name=row[3],
                buyin_cents=row[4],
                entry_code=row[5],
                is_active=True
            ))

    return games


def fetch(game_id: int) -> Optional[Game]:
    with db.cursor.get() as cursor:
        cursor.execute(
            'SELECT creator_id, created, lobby_name, buyin_cents, entry_code, is_active FROM games WHERE id = ?', (game_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return Game(
            id=game_id,
            creator_id=row[0],
            created=row[1],
            lobby_name=row[2],
            buyin_cents=row[3],
            entry_code=row[4],
            is_active=row[5]
        )


def create(creator_id: str, lobby_name: str, buyin_cents: int, entry_code: str) -> Game:
    game_id = None
    ts = time.time()
    created = datetime.datetime.fromtimestamp(ts)

    with db.cursor.get() as cursor:
        cursor.execute("INSERT INTO games (creator_id, lobby_name, created, buyin_cents, entry_code, is_active) VALUES (?, ?, ?, ?, ?, 1)",
                       (creator_id, lobby_name, created, buyin_cents, entry_code,))
        game_id = cursor.lastrowid

    if not game_id:
        raise CreateGameException("Could not insert into database")

    return Game(
        id=game_id,
        creator_id=creator_id,
        created=created,
        lobby_name=lobby_name,
        buyin_cents=buyin_cents,
        entry_code=entry_code,
        is_active=True
    )
