import sqlite3
from typing import Optional

import db.cursor
from .player import Player

VENMO = 'venmo'
ZELLE = 'zelle'

SELECT_PLAYER = '''
    SELECT u.id, u.display_name, u.phone_number, v.handle, u.active_game_id,
        z.handle
    FROM users u
    LEFT JOIN user_payment_methods v ON v.user_id = u.id AND v.method = 'venmo'
    LEFT JOIN user_payment_methods z ON z.user_id = u.id AND z.method = 'zelle'
'''


class PhoneNumberTakenError(Exception):
    pass


class PaymentMethodTakenError(Exception):
    pass


class VenmoUsernameTakenError(PaymentMethodTakenError):
    pass


def row_to_player(row) -> Player:
    return Player(
        id=row[0],
        display_name=row[1],
        phone_number=row[2],
        venmo_username=row[3],
        active_game_id=row[4],
        zelle_handle=row[5],
    )


def fetch(user_id: Optional[int]) -> Optional[Player]:
    if user_id is None:
        return None

    with db.cursor.get() as cursor:
        cursor.execute(f'{SELECT_PLAYER} WHERE u.id = ? LIMIT 1', (user_id,))
        row = cursor.fetchone()
        return row_to_player(row) if row else None


def fetch_by_phone_number(phone_number: str) -> Optional[Player]:
    with db.cursor.get() as cursor:
        cursor.execute(
            f'{SELECT_PLAYER} WHERE u.phone_number = ? LIMIT 1', (phone_number,))
        row = cursor.fetchone()
        return row_to_player(row) if row else None


def fetch_by_venmo_username(venmo_username: str) -> Optional[Player]:
    """
    Finds the user with a Venmo username. Venmo usernames are not case
    sensitive, so an exact match is preferred, then a case-insensitive one.
    """
    with db.cursor.get() as cursor:
        cursor.execute(
            f'{SELECT_PLAYER} WHERE v.handle = ? COLLATE NOCASE '
            'ORDER BY v.handle = ? DESC, u.phone_number IS NULL DESC, u.id ASC '
            'LIMIT 1',
            (venmo_username, venmo_username),
        )
        row = cursor.fetchone()
        return row_to_player(row) if row else None


def create(
    phone_number: str,
    display_name: str,
    venmo_username: Optional[str] = None,
) -> Player:
    with db.cursor.get() as cursor:
        try:
            cursor.execute(
                'INSERT INTO users (phone_number, display_name) VALUES (?, ?)',
                (phone_number, display_name),
            )
        except sqlite3.IntegrityError as ex:
            raise PhoneNumberTakenError(phone_number) from ex

        user_id = cursor.lastrowid

        if venmo_username:
            try:
                cursor.execute(
                    'INSERT INTO user_payment_methods (user_id, method, handle) '
                    'VALUES (?, ?, ?)',
                    (user_id, VENMO, venmo_username),
                )
            except sqlite3.IntegrityError as ex:
                cursor.connection.rollback()
                raise VenmoUsernameTakenError(venmo_username) from ex

    return Player(
        id=user_id,
        display_name=display_name,
        phone_number=phone_number,
        venmo_username=venmo_username,
    )


def claim(user_id: int, phone_number: str) -> bool:
    """
    Attaches a verified phone number to a user that does not have one yet
    (a profile migrated from the old Venmo login). Returns False if the user
    was already claimed.
    """
    with db.cursor.get() as cursor:
        try:
            cursor.execute(
                'UPDATE users SET phone_number = ? '
                'WHERE id = ? AND phone_number IS NULL',
                (phone_number, user_id),
            )
        except sqlite3.IntegrityError as ex:
            raise PhoneNumberTakenError(phone_number) from ex
        return cursor.rowcount == 1


def update_display_name(user_id: int, display_name: str) -> None:
    with db.cursor.get() as cursor:
        cursor.execute(
            'UPDATE users SET display_name = ? WHERE id = ?',
            (display_name, user_id),
        )


def set_payment_method(user_id: int, method: str, handle: Optional[str]) -> None:
    """
    Sets or, with `handle` None, removes one of a user's payment methods.
    Raises PaymentMethodTakenError if another user has the same handle.
    """
    with db.cursor.get() as cursor:
        if not handle:
            cursor.execute(
                'DELETE FROM user_payment_methods WHERE user_id = ? AND method = ?',
                (user_id, method),
            )
            return

        try:
            cursor.execute(
                'INSERT INTO user_payment_methods (user_id, method, handle) '
                'VALUES (?, ?, ?) '
                'ON CONFLICT (user_id, method) DO UPDATE SET handle = excluded.handle',
                (user_id, method, handle),
            )
        except sqlite3.IntegrityError as ex:
            raise PaymentMethodTakenError(handle) from ex


def is_handle_taken(method: str, handle: str, user_id: int) -> bool:
    """
    If someone other than `user_id` already uses this handle. Handles are
    compared case-insensitively.
    """
    with db.cursor.get() as cursor:
        cursor.execute(
            'SELECT 1 FROM user_payment_methods '
            'WHERE method = ? AND handle = ? COLLATE NOCASE AND user_id != ? LIMIT 1',
            (method, handle, user_id),
        )
        return cursor.fetchone() is not None


def shares_game(user_id: int, other_user_id: int) -> bool:
    """
    If the two users have been in a game together.
    """
    with db.cursor.get() as cursor:
        cursor.execute(
            'SELECT 1 FROM game_players a '
            'JOIN game_players b ON a.game_id = b.game_id '
            'WHERE a.player_id = ? AND b.player_id = ? LIMIT 1',
            (user_id, other_user_id),
        )
        return cursor.fetchone() is not None
