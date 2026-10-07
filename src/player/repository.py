import sqlite3
from typing import Optional

import db.cursor
from .player import Player

VENMO = 'venmo'

SELECT_PLAYER = '''
    SELECT u.id, u.display_name, u.phone_number, v.handle, u.active_game_id
    FROM users u
    LEFT JOIN user_payment_methods v ON v.user_id = u.id AND v.method = 'venmo'
'''


class PhoneNumberTakenError(Exception):
    pass


class VenmoUsernameTakenError(Exception):
    pass


def row_to_player(row) -> Player:
    return Player(
        id=row[0],
        display_name=row[1],
        phone_number=row[2],
        venmo_username=row[3],
        active_game_id=row[4],
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
