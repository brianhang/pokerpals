from typing import Optional
import db.cursor

from .payment import Payment

SELECT_PAYMENT = '''
    SELECT p.id, p.game_id, p.from_player_id, p.to_player_id, p.cents,
        p.completed, fu.display_name, tu.display_name, fv.handle, tv.handle
    FROM game_payments p
    LEFT JOIN users fu ON fu.id = p.from_player_id
    LEFT JOIN users tu ON tu.id = p.to_player_id
    LEFT JOIN user_payment_methods fv
        ON fv.user_id = p.from_player_id AND fv.method = 'venmo'
    LEFT JOIN user_payment_methods tv
        ON tv.user_id = p.to_player_id AND tv.method = 'venmo'
'''


def row_to_payment(row) -> Payment:
    return Payment(
        id=row[0],
        game_id=row[1],
        from_player_id=row[2],
        to_player_id=row[3],
        cents=row[4],
        completed=bool(row[5]),
        from_name=row[6] or '',
        to_name=row[7] or '',
        from_venmo_username=row[8],
        to_venmo_username=row[9],
    )


def fetch(payment_id: int) -> Optional[Payment]:
    with db.cursor.get() as cursor:
        cursor.execute(f'{SELECT_PAYMENT} WHERE p.id = ?', (payment_id,))
        row = cursor.fetchone()
        return row_to_payment(row) if row else None


def fetch_for_game(game_id: int, only_incomplete=False) -> list[Payment]:
    conditions = 'p.game_id = ?'

    if only_incomplete:
        conditions += ' AND p.completed = 0'

    with db.cursor.get() as cursor:
        cursor.execute(
            f'{SELECT_PAYMENT} WHERE {conditions} ORDER BY p.id ASC',
            (game_id,),
        )
        return [row_to_payment(row) for row in cursor]


def fetch_for_player(
    player_id: int,
    only_incomplete=True,
    only_from=False,
) -> list[Payment]:
    with db.cursor.get() as cursor:
        if only_from:
            conditions = ['p.from_player_id = ?']
            params = (player_id,)
        else:
            conditions = ['(p.from_player_id = ? OR p.to_player_id = ?)']
            params = (player_id, player_id,)

        if only_incomplete:
            conditions.append('p.completed = 0')

        cursor.execute(
            f'{SELECT_PAYMENT} WHERE {" AND ".join(conditions)} '
            'ORDER BY p.id ASC',
            params,
        )
        return [row_to_payment(row) for row in cursor]


def create(game_id: int, from_player_id: int, to_player_id: int, cents: int) -> Payment:
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
