from typing import Optional
import db.cursor

from .payment import Payment


def fetch(payment_id: int) -> Optional[Payment]:
    with db.cursor.get() as cursor:
        cursor.execute(
            'SELECT game_id, from_player_id, to_player_id, cents, completed FROM game_payments WHERE id = ?', (payment_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return Payment(
            id=payment_id,
            game_id=row[0],
            from_player_id=row[1],
            to_player_id=row[2],
            cents=row[3],
            completed=bool(row[4])
        )


def fetch_for_game(game_id: int, only_incomplete=False) -> list[Payment]:
    payments = []
    conditions = 'game_id = ?'

    if only_incomplete:
        conditions += ' AND completed = 0'

    with db.cursor.get() as cursor:
        cursor.execute(
            'SELECT id, from_player_id, to_player_id, cents, completed '
            f'FROM game_payments WHERE {conditions} ORDER BY id ASC',
            (game_id,),
        )

        for row in cursor:
            payments.append(Payment(
                id=row[0],
                game_id=game_id,
                from_player_id=row[1],
                to_player_id=row[2],
                cents=row[3],
                completed=bool(row[4])
            ))

    return payments


def fetch_for_player(player_id: str, only_incomplete=True, only_from=False) -> list[Payment]:
    payments = []
    with db.cursor.get() as cursor:
        if only_from:
            conditions = ['from_player_id = ?']
            params = (player_id,)
        else:
            conditions = ['(from_player_id = ? OR to_player_id = ?)']
            params = (player_id, player_id,)

        if only_incomplete:
            conditions.append('completed = 0')

        cursor.execute(
            'SELECT id, game_id, from_player_id, to_player_id, cents, '
            f'completed FROM game_payments WHERE {" AND ".join(conditions)} '
            'ORDER BY id ASC',
            params,
        )

        for row in cursor:
            payments.append(Payment(
                id=row[0],
                game_id=row[1],
                from_player_id=row[2],
                to_player_id=row[3],
                cents=row[4],
                completed=row[5]
            ))

    return payments


def create(game_id: int, from_player_id: str, to_player_id: str, cents: int) -> Payment:
    with db.cursor.get() as cursor:
        cursor.execute(
            'INSERT INTO game_payments (game_id, from_player_id, to_player_id, cents, completed) VALUES (?, ?, ?, ?, 0)', (game_id, from_player_id, to_player_id, cents,))
        payment_id = cursor.lastrowid
        return Payment(
            id=payment_id,
            game_id=game_id,
            from_player_id=from_player_id,
            to_player_id=to_player_id,
            cents=cents,
            completed=False
        )


def set_completed(payment_id: int, completed: bool) -> None:
    with db.cursor.get() as cursor:
        cursor.execute('UPDATE game_payments SET completed = ? WHERE id = ?',
                       (completed, payment_id,))
