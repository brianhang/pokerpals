from contextlib import contextmanager
from flask import Response, make_response, redirect, request, render_template, url_for
from typing import Optional

from player.player import Player
from . import repository as player_repository
from utils.venmo.username import is_valid_venmo_username

VENMO_USERNAME_COOKIE = 'venmo_username'
ALLOWED_ENDPOINTS = ['home', 'game_view', 'history', 'game_join_form']


def get_venmo_username() -> Optional[str]:
    return request.cookies.get(VENMO_USERNAME_COOKIE)


@contextmanager
def fetch_player() -> Optional[Player]:
    venmmo_username = get_venmo_username()
    player = player_repository.fetch(venmmo_username)
    yield player


def handle_login_page(return_endpoint='', return_game_id=None, return_game_code='') -> str:
    last_username = request.args.get('last_username', '').strip()
    return_endpoint = request.args.get('return', return_endpoint).strip()
    return_game_id = request.args.get('return_game_id', return_game_id)
    return_game_code = request.args.get(
        'return_game_code', return_game_code).strip()
    return render_template('login.html', last_username=last_username, return_endpoint=return_endpoint, return_game_id=return_game_id, return_game_code=return_game_code)


def handle_login() -> Response:
    venmo_username = request.form.get('venmo-username')
    return_endpoint = request.form.get('return-endpoint')
    return_game_id = request.form.get('return-game-id')
    return_game_code = request.form.get('return-game-id')

    if return_endpoint not in ALLOWED_ENDPOINTS:
        return_endpoint = None

    player = player_repository.fetch(venmo_username)

    if not player and is_valid_venmo_username(venmo_username):
        player = player_repository.create(
            venmo_username=venmo_username
        )

    if player:
        params = {}
        if return_game_id and return_game_id.isdigit():
            params['game_id'] = int(return_game_id)
        if return_game_code:
            params['code'] = return_game_code

        response = make_response(
            redirect(url_for(return_endpoint or 'home', **params)))
        response.set_cookie(VENMO_USERNAME_COOKIE, venmo_username)
    else:
        response = redirect(url_for('login_page', last_username=venmo_username, return_endpoint=return_endpoint,
                            return_game_id=return_game_id, return_game_code=return_game_code))

    return response


def handle_logout() -> Response:
    response = make_response(redirect('/'))
    response.delete_cookie(VENMO_USERNAME_COOKIE)
    return response
