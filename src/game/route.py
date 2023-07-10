import math
from typing import Optional
from player.player import Player
from flask import Response, render_template, redirect, url_for, request, abort
from random import choices
from string import ascii_uppercase

import game.repository
import game_players.repository
import utils.cents as cents_utils


def generate_entry_code() -> str:
    return ''.join(choices(ascii_uppercase, k=4))


def handle_game_list(player: Player) -> Response:
    active_games = game.repository.fetch_all_active()
    current_game = next(
        (game for game in active_games if player.active_game_id == game.id), None)

    return render_template('game/list.html', player=player, active_games=active_games, current_game=current_game)


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

    buyin_prefill = cents_utils.to_string(active_game.buyin_cents)
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


def handle_cashout_form(player: Player) -> Response:
    game_id = player.active_game_id
    if not game_id:
        return redirect(url_for('home')), 400

    active_game = game.repository.fetch(game_id)
    if not active_game:
        return redirect(url_for('home')), 400

    game_player = game_players.repository.fetch_player(
        game_id, player.venmo_username)
    if not game_player:
        return redirect(url_for('home')), 400

    cashout_max_cents = game_player.buyin_cents
    cashout_max = cents_utils.to_string(cashout_max_cents)
    cashout_prefill = cents_utils.to_string(game_player.cashout_cents or 0)
    return render_template('game/cashout.html', cashout_max=cashout_max, cashout_max_cents=cashout_max_cents, cashout_prefill=cashout_prefill, game=active_game, player=player)


def handle_cashout(player: Player) -> Response:
    player_id = player.venmo_username
    game_id = player.active_game_id
    if not game_id:
        return redirect(url_for('home')), 400

    active_game = game.repository.fetch(game_id)
    if not active_game:
        return redirect(url_for('home')), 400

    game_player = game_players.repository.fetch_player(
        game_id, player.venmo_username)
    if not game_player:
        return redirect(url_for('home')), 400

    err = None
    amount = float(request.form.get('amount', '0'))
    max_cents = game_player.buyin_cents
    cents = math.ceil(amount * 100)

    if cents > max_cents:
        err = f'You can only cash out at most {cents_utils.to_string(max_cents)}'
    elif cents < 1:
        err = 'Please provide a valid amount to cash out'

    if err:
        return render_template('game/cashout.html', err=err, cashout_prefill=amount, game=active_game, player=player), 400

    game_players.repository.cash_out(game_id, player_id, cents)
    game_players.repository.remove_player(game_id, player_id)
    return redirect(url_for('game_view', game_id=game_id))


def handle_join_game_form(player: Player, game_id: int) -> Response:
    active_game_id = player.active_game_id
    if active_game_id:
        return redirect(url_for('game_view', game_id=active_game_id)), 400

    req_game = game.repository.fetch(game_id)
    if not req_game:
        return abort(404)

    return render_template('game/join.html', game=req_game, player=player)


def handle_join_game(player: Player, game_id: int) -> Response:
    active_game_id = player.active_game_id
    if active_game_id:
        return redirect(url_for('game_view', game_id=active_game_id)), 400

    req_game = game.repository.fetch(game_id)
    if not req_game:
        return abort(404)

    err = None
    entry_code = request.form.get('entry-code')

    if entry_code.upper().strip() != req_game.entry_code.upper().strip():
        err = 'The provided entry code is incorrect, please try again'

    if err:
        return render_template('game/join.html', err=err, entry_code_prefill=entry_code, game=req_game, player=player), 403

    game_players.repository.add_player(game_id, player.venmo_username)
    return redirect(url_for('game_view', game_id=game_id))
