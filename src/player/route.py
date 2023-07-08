from contextlib import contextmanager
from flask import Response, make_response, redirect, request, render_template, url_for
from typing import Optional

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


def handle_login_page() -> str:
    last_username = request.args.get('last_username', '').strip()
    if last_username and len(last_username) > 0:
        return render_template('login.html', last_username=last_username)

    return render_template('login.html')


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
        response = make_response(
            redirect(url_for('home', last_username=venmo_username)))

    return response


def handle_logout() -> Response:
    response = make_response(redirect('/'))
    response.delete_cookie(VENMO_USERNAME_COOKIE)
    return response
