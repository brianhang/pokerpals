import datetime
import time
from typing import List, Optional

import db.cursor
from payout.payout_type import PayoutType

from .game import Game


class CreateGameException(Exception):
    pass


def fetch_all_active() -> List[Game]:
    games = []

    with db.cursor.get() as cursor:
        cursor.execute(
            'SELECT id, creator_id, created, lobby_name, buyin_cents, entry_code, payout_type FROM games WHERE is_active = 1 ORDER BY id ASC')

        for row in cursor:
            games.append(Game(
                id=row[0],
                creator_id=row[1],
                created=row[2],
                lobby_name=row[3],
                buyin_cents=row[4],
                entry_code=row[5],
                is_active=True,
                payout_type=convert_payout_type(row[6]),
            ))

    return games


def fetch(game_id: int) -> Optional[Game]:
    with db.cursor.get() as cursor:
        cursor.execute(
            'SELECT creator_id, created, lobby_name, buyin_cents, entry_code, is_active, payout_type FROM games WHERE id = ?',
            (game_id,),
        )
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
            is_active=bool(row[5]),
            payout_type=convert_payout_type(row[6]),
        )


def fetch_many(game_ids: list[int], reverse=False) -> list[Game]:
    games = []

    with db.cursor.get() as cursor:
        order = 'DESC' if reverse else 'ASC'
        game_id_list = ','.join(['?'] * len(game_ids))
        cursor.execute(
            f'SELECT id, creator_id, created, lobby_name, buyin_cents, entry_code, is_active, payout_type FROM games WHERE id IN ({game_id_list}) ORDER BY id {order}',
            game_ids,
        )

        for row in cursor:
            games.append(Game(
                id=row[0],
                creator_id=row[1],
                created=row[2],
                lobby_name=row[3],
                buyin_cents=row[4],
                entry_code=row[5],
                is_active=bool(row[6]),
                payout_type=convert_payout_type(row[7]),
            ))

    return games


def create(
    creator_id: str,
    lobby_name: str,
    buyin_cents: int,
    entry_code: str,
    payout_type: Optional[PayoutType] = None,
) -> Game:
    game_id = None
    ts = time.time()
    created = datetime.datetime.fromtimestamp(ts)

    with db.cursor.get() as cursor:
        cursor.execute(
            'INSERT INTO games (creator_id, lobby_name, created, buyin_cents, entry_code, is_active, payout_type) VALUES (?, ?, ?, ?, ?, 1, ?)',
            (
                creator_id,
                lobby_name,
                created,
                buyin_cents,
                entry_code,
                payout_type.value if payout_type else None,
            ),
        )
        game_id = cursor.lastrowid

    if not game_id:
        raise CreateGameException('Could not insert into database')

    return Game(
        id=game_id,
        creator_id=creator_id,
        created=created,
        lobby_name=lobby_name,
        buyin_cents=buyin_cents,
        entry_code=entry_code,
        is_active=True,
        payout_type=payout_type,
    )


def set_active(game_id: int, is_active: bool) -> None:
    with db.cursor.get() as cursor:
        cursor.execute(
            'UPDATE games SET is_active = ? WHERE id = ?', (is_active, game_id,))


def convert_payout_type(raw_value: any) -> Optional[PayoutType]:
    try:
        return PayoutType(raw_value)
    except ValueError:
        return None
