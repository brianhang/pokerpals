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
            'SELECT player_id, join_time, buyin_cents, cashout_cents FROM game_players WHERE game_id = ?', (game_id,))

        for row in cursor:
            players.append(GamePlayer(
                player_venmo_username=row[0],
                join_time=row[1],
                buyin_cents=row[2],
                cashout_cents=row[3]
            ))

    return game_players


def add_player(game_id: int, player_id: str) -> None:
    with db.cursor.get() as cursor:
        cursor.execute(
            'UPDATE players SET active_game_id = ? WHERE venmo_username = ?', (game_id, player_id,))
        cursor.execute(
            'INSERT INTO game_players (game_id, player_id, buyin_cents) VALUES (?, ?, 0)', (game_id, player_id,))


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
        current_cashout_cents = res[0] if res else None

        if current_cashout_cents is None:
            raise Exception(
                f"Player {player_id} has not joined game {game_id}")

        new_cashout_cents = current_cashout_cents + cents
        cursor.execute('UPDATE game_players SET cashout_cents = ? WHERE game_id = ? AND player_id = ?',
                       (new_cashout_cents, game_id, player_id,))
