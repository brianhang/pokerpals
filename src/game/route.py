import math
from typing import Optional
from player.player import Player
from flask import Response, render_template, redirect, url_for, request, abort
from random import choices
from string import ascii_uppercase

import game.repository
import game_players.repository


def generate_entry_code() -> str:
    return ''.join(choices(ascii_uppercase, k=4))


def handle_game_list(player: Player) -> Response:
    active_game_id = player.active_game_id
    if active_game_id:
        return redirect(url_for('game_view', game_id=active_game_id))

    games = game.repository.fetch_all()

    return render_template('game/list.html', player=player, games=games)


def handle_create_game_form(player: Player) -> Response:
    lobby_name = f"{player.venmo_username}'s Game"
    entry_code = generate_entry_code()
    return render_template('game/create.html', lobby_name=lobby_name, entry_code=entry_code)


def handle_create_game(player: Player) -> Response:
    active_game_id = player.active_game_id
    if active_game_id:
        return redirect(url_for('game_view', game_id=active_game_id))

    lobby_name = request.form.get('lobby-name', '').strip()
    buyin_cents = int(float(request.form.get('buy-in', '0.0')) * 100)
    entry_code = request.form.get('entry-code', '').strip()
    err = None

    if len(lobby_name) < 1:
        err = 'Please enter a valid lobby name'
    elif buyin_cents < 100:
        err = 'A buy in must be at least $1.00, please provide a higher amount'
    elif len(entry_code) < 1:
        err = 'Please provide a valid entry code'

    if err:
        return render_template('game/create.html', err=err, lobby_name=lobby_name, entry_code=entry_code)

    player_id = player.venmo_username
    new_game = game.repository.create(
        creator_id=player_id,
        lobby_name=lobby_name,
        buyin_cents=buyin_cents,
        entry_code=entry_code
    )
    new_game_id = new_game.id
    game_players.repository.add_player(new_game_id, player_id)

    return redirect(url_for('game_view', game_id=new_game_id))


def handle_view_game(player: Optional[Player], game_id: int) -> Response:
    req_game = game.repository.fetch(game_id)
    if not req_game:
        return abort(404)

    players = game_players.repository.fetch(game_id)
    return render_template('game/view.html', game=req_game, player=player, players=players)


def handle_buyin_form(player: Player) -> Response:
    game_id = player.active_game_id
    if not game_id:
        return redirect(url_for('home')), 400

    active_game = game.repository.fetch(game_id)
    if not active_game:
        return redirect(url_for('home')), 400

    buyin_prefill = '{:.2f}'.format(active_game.buyin_cents / 100)
    return render_template('game/buyin.html', buyin_prefill=buyin_prefill, game=active_game, player=player)


def handle_buyin(player: Player) -> Response:
    game_id = player.active_game_id
    if not game_id:
        return redirect(url_for('home')), 400

    active_game = game.repository.fetch(game_id)
    if not active_game:
        return redirect(url_for('home')), 400

    err = None

    amount = float(request.form.get('amount', '0'))
    cents = math.ceil(amount * 100)
    if cents <= 0:
        err = 'Please provide a valid amount to buy in'

    if err:
        return render_template('game/buyin.html', err=err, buyin_prefill=amount, game=active_game, player=player), 400

    game_players.repository.buy_in(game_id, player.venmo_username, cents)
    return redirect(url_for('game_view', game_id=game_id))
