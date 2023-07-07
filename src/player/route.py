from contextlib import contextmanager
from flask import Request, Response, make_response, redirect, request
from typing import Optional
from html import escape as html_escape

from player.player import Player
from . import repository as player_repository
from .venmo_utils import is_valid_venmo_username

VENMO_USERNAME_COOKIE = 'venmo_username'

def get_venmo_username() -> Optional[str]:
    return request.cookies.get(VENMO_USERNAME_COOKIE)

@contextmanager
def fetch_player() -> Optional[Player]:
    venmmo_username = get_venmo_username()
    player = player_repository.fetch(venmmo_username)
    yield player

def handle_home() -> str:
    with fetch_player() as player:
        if player:
            logout_button = """
            <form method="post" action="/logout">
                <input type="hidden" name="_method" value="POST">
                <input type="submit" value="Logout">
            </form>
            """
            return f'Welcome back, {html_escape(player.venmo_username)}.{logout_button}'
        else:
            return """
            <!DOCTYPE html>
            <html>
            <head>
            <title>Venmo Login</title>
            </head>
            <body>
            <form action="/login" method="post">
                <label for="venmo-username">Venmo Username:</label>
                <input type="text" id="venmo-username" name="venmo-username" required>
                <br>
                <input type="submit" value="Login">
            </form>
            </body>
            </html>
            """

def handle_login() -> Response:
    venmo_username = request.form.get('venmo-username')

    player = player_repository.fetch(venmo_username)

    if not player and is_valid_venmo_username(venmo_username):
        player = player_repository.create(
            venmo_username=venmo_username
        )

    if player:
        response = make_response(redirect('/'))
        response.set_cookie(VENMO_USERNAME_COOKIE, venmo_username)
    else:
        response = make_response(redirect('/invalid_venmo'))

    return response

def handle_logout() -> Response:
    response = make_response(redirect('/'))
    response.delete_cookie(VENMO_USERNAME_COOKIE)
    return response

