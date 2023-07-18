import db.cursor
from typing import Optional, List

from game.game import Game
from .game_players import GamePlayers, GamePlayer


def fetch(game_id: int) -> GamePlayers:
    players = []
    game_players = GamePlayers(
        game_id=game_id,
        players=players
    )
    with db.cursor.get() as cursor:
        cursor.execute(
            'SELECT player_id, join_time, buyin_cents, cashout_cents FROM game_players WHERE game_id = ? ORDER BY join_time ASC', (game_id,))

        for row in cursor:
            players.append(GamePlayer(
                player_venmo_username=row[0],
                join_time=row[1],
                buyin_cents=row[2],
                cashout_cents=row[3]
            ))

    return game_players


def fetch_player(game_id: int, player_id: str) -> Optional[GamePlayer]:
    with db.cursor.get() as cursor:
        cursor.execute(
            'SELECT join_time, buyin_cents, cashout_cents FROM game_players WHERE game_id = ? AND player_id = ?', (game_id, player_id))
        row = cursor.fetchone()

        if not row:
            return None

        return GamePlayer(
            player_venmo_username=player_id,
            join_time=row[0],
            buyin_cents=row[1],
            cashout_cents=row[2]
        )


def fetch_recent_game_ids(player_id: str, limit: Optional[int], reverse: bool = False) -> list[int]:
    recent_game_ids = []

    with db.cursor.get() as cursor:
        order = 'DESC' if reverse else 'ASC'

        if limit and limit > 0:
            limit_clause = f'LIMIT {limit}'
        else:
            limit_clause = ''

        cursor.execute(
            f'SELECT game_id FROM game_players WHERE player_id = ? AND cashout_cents IS NOT NULL ORDER BY game_id {order} {limit_clause}', (player_id,))

        for row in cursor:
            recent_game_ids.append(row[0])

    return recent_game_ids


def add_player(game_id: int, player_id: str) -> None:
    with db.cursor.get() as cursor:
        cursor.execute(
            'UPDATE players SET active_game_id = ? WHERE venmo_username = ?', (game_id, player_id,))
        cursor.execute(
            'INSERT OR IGNORE INTO game_players (game_id, player_id, buyin_cents) VALUES (?, ?, 0)', (game_id, player_id,))


def remove_player(game_id: int, player_id: str) -> None:
    with db.cursor.get() as cursor:
        cursor.execute(
            'UPDATE players SET active_game_id = NULL WHERE active_game_id = ? AND venmo_username = ?', (game_id, player_id,))


def remove_all_players(game_id):
    with db.cursor.get() as cursor:
        cursor.execute(
            'UPDATE players SET active_game_id = NULL WHERE active_game_id = ?', (game_id,))


def buy_in(game_id: str, player_id: str, cents: int) -> None:
    with db.cursor.get() as cursor:
        cursor.execute(
            'SELECT buyin_cents FROM game_players WHERE game_id = ? AND player_id = ?', (game_id, player_id,))
        res = cursor.fetchone()
        current_buyin_cents = res[0] if res else None

        if current_buyin_cents is None:
            raise Exception(
                f"Player {player_id} has not joined game {game_id}")

        new_buyin_cents = current_buyin_cents + cents
        cursor.execute('UPDATE game_players SET buyin_cents = ? WHERE game_id = ? AND player_id = ?',
                       (new_buyin_cents, game_id, player_id,))


def cash_out(game_id: str, player_id: str, cents: int) -> None:
    with db.cursor.get() as cursor:
        cursor.execute(
            'SELECT cashout_cents FROM game_players WHERE game_id = ? AND player_id = ?', (game_id, player_id,))
        res = cursor.fetchone()

        if res is None:
            raise Exception(
                f"Player {player_id} has not joined game {game_id}")

        cursor.execute('UPDATE game_players SET cashout_cents = ? WHERE game_id = ? AND player_id = ?',
                       (cents, game_id, player_id,))
