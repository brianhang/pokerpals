import math
from random import choices
from string import ascii_uppercase
from typing import Optional

from flask import Response, abort, redirect, render_template, request, url_for
from flask_socketio import SocketIO

import game.repository
import game_players.repository as game_players_repository
import payment.repository
import payout.settle
import utils.cents as cents_utils
import utils.venmo.link
from game_players.game_players import GamePlayer, GamePlayers
from player.player import Player

from .validation import get_end_game_err


def broadcast_reload(socketio: SocketIO, game_id: Optional[int]) -> None:
    socketio.emit('reload', str(game_id) if game_id else None)


def generate_entry_code() -> str:
    return ''.join(choices(ascii_uppercase, k=4))


def get_max_cashout_cents(cur_game_players: GamePlayers, cur_game_player: GamePlayer) -> int:
    game_remaining_cents = cur_game_players.total_buyin_cents() \
        - cur_game_players.total_cashout_cents() \
        + (cur_game_player.cashout_cents or 0)
    return game_remaining_cents


def find_game_player(cur_game_players: GamePlayers, player_id: str) -> Optional[GamePlayer]:
    return next((game_player
                 for game_player in cur_game_players.players
                 if game_player.player_venmo_username == player_id), None)


def handle_game_list(player: Player) -> Response:
    active_games = game.repository.fetch_all_active()
    current_game = next(
        (game for game in active_games if player.active_game_id == game.id), None)

    num_recent_games = 5
    recent_game_ids = game_players_repository.fetch_recent_game_ids(
        player.venmo_username,
        limit=num_recent_games,
        reverse=True,
    )
    recent_games = game.repository.fetch_many(recent_game_ids, reverse=True)

    return render_template('game/list.html', player=player, active_games=active_games, recent_games=recent_games, current_game=current_game)


def handle_history(player: Player) -> Response:
    recent_game_ids = game_players_repository.fetch_recent_game_ids(
        player.venmo_username,
        limit=None,
    )
    recent_games = game.repository.fetch_many(recent_game_ids, reverse=True)

    return render_template('game/history.html', player=player, recent_games=recent_games)


def handle_create_game_form(player: Player) -> Response:
    lobby_name = f"{player.venmo_username}'s Game"
    entry_code = generate_entry_code()
    return render_template('game/create.html', lobby_name=lobby_name, entry_code=entry_code)


def handle_create_game(player: Player, socketio: SocketIO) -> Response:
    active_game_id = player.active_game_id
    if active_game_id:
        return redirect(url_for('game_view', game_id=active_game_id), code=303)

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
    game_players_repository.add_player(new_game_id, player_id)

    broadcast_reload(socketio, None)
    return redirect(url_for('game_view', game_id=new_game_id), code=303)


def handle_view_game(player: Optional[Player], game_id: int) -> Response:
    req_game = game.repository.fetch(game_id)
    if not req_game:
        return abort(404)

    req_game_players = game_players_repository.fetch(game_id)
    game_player = find_game_player(
        req_game_players, player.venmo_username
    ) if player else None
    buyin_amount = cents_utils.to_string(req_game.buyin_cents)
    buyin_total = cents_utils.to_string(req_game_players.total_buyin_cents())
    cashout_total = cents_utils.to_string(
        req_game_players.total_cashout_cents())
    payments = payment.repository.fetch_for_game(game_id)

    if player:
        pending_payment = next(
            (
                payment for payment in payments
                if payment.from_player_id == player.venmo_username and not payment.completed
            ),
            None
        )
    else:
        pending_payment = None

    venmo_url = None

    if pending_payment:
        venmo_url = utils.venmo.link.get_payment_url(
            venmo_username=pending_payment.to_player_id,
            txn=utils.venmo.link.Transaction.PAY,
            amount_cents=pending_payment.cents,
            is_mobile=request.MOBILE)

    return render_template('game/view.html', game=req_game, player=player, players=req_game_players, buyin_total=buyin_total, game_player=game_player, cashout_total=cashout_total, payments=payments, venmo_url=venmo_url, pending_payment=pending_payment, buyin_amount=buyin_amount)


def handle_buyin_form(player: Player) -> Response:
    game_id = player.active_game_id
    if not game_id:
        return redirect(url_for('home'))

    active_game = game.repository.fetch(game_id)
    if not active_game:
        return redirect(url_for('home'))

    buyin_prefill = cents_utils.to_string(active_game.buyin_cents)
    return render_template('game/buyin.html', buyin_prefill=buyin_prefill, game=active_game, player=player)


def handle_buyin(player: Player, socketio: SocketIO) -> Response:
    game_id = player.active_game_id
    if not game_id:
        return redirect(url_for('home'))

    active_game = game.repository.fetch(game_id)
    if not active_game:
        return redirect(url_for('home'))

    err = None

    amount = float(request.form.get('amount', '0'))
    cents = math.ceil(amount * 100)
    if cents <= 0:
        err = 'Please provide a valid amount to buy in'

    if err:
        return render_template('game/buyin.html', err=err, buyin_prefill=amount, game=active_game, player=player), 400

    game_players_repository.buy_in(game_id, player.venmo_username, cents)
    broadcast_reload(socketio, game_id)
    return redirect(url_for('game_view', game_id=game_id), code=303)


def handle_cashout_form(player: Player) -> Response:
    game_id = player.active_game_id
    if not game_id:
        return redirect(url_for('home'))

    active_game = game.repository.fetch(game_id)
    if not active_game:
        return redirect(url_for('home'))

    active_game_players = game_players_repository.fetch(game_id)
    game_player = find_game_player(active_game_players, player.venmo_username)
    if not game_player:
        return redirect(url_for('home'))

    cashout_max_cents = get_max_cashout_cents(active_game_players, game_player)
    cashout_max = cents_utils.to_string(cashout_max_cents)
    cashout_prefill = cents_utils.to_string(game_player.cashout_cents or 0)
    return render_template('game/cashout.html', cashout_max=cashout_max, cashout_max_cents=cashout_max_cents, cashout_prefill=cashout_prefill, game=active_game, player=player)


def handle_cashout(player: Player, socketio: SocketIO) -> Response:
    player_id = player.venmo_username
    game_id = player.active_game_id
    if not game_id:
        return redirect(url_for('home'))

    active_game = game.repository.fetch(game_id)
    if not active_game:
        return redirect(url_for('home'))

    active_game_players = game_players_repository.fetch(game_id)
    game_player = find_game_player(active_game_players, player.venmo_username)
    if not game_player:
        return redirect(url_for('home'))

    err = None
    amount = float(request.form.get('amount', '0'))
    cashout_max_cents = get_max_cashout_cents(active_game_players, game_player)
    cents = math.ceil(amount * 100)

    if cents > cashout_max_cents:
        err = f'You can only cash out at most {cents_utils.to_string(cashout_max_cents)}'
    elif cents < 0:
        err = 'Please provide a valid amount to cash out'

    if err:
        return render_template('game/cashout.html', err=err, cashout_prefill=amount, game=active_game, player=player), 400

    game_players_repository.cash_out(game_id, player_id, cents)
    game_players_repository.remove_player(game_id, player_id)
    broadcast_reload(socketio, game_id)

    new_active_game_players = game_players_repository.fetch(game_id)
    leftover_cents = new_active_game_players.total_buyin_cents() - \
        new_active_game_players.total_cashout_cents()
    if leftover_cents == 0 and active_game.is_active:
        create_payments_and_end_game(
            new_active_game_players,
            socketio=socketio,
        )

    return redirect(url_for('game_view', game_id=game_id), code=303)


def handle_join_game_form(player: Player, game_id: int) -> Response:
    active_game_id = player.active_game_id
    if active_game_id:
        return redirect(url_for('game_view', game_id=active_game_id))

    req_game = game.repository.fetch(game_id)
    if not req_game or not req_game.is_active:
        return abort(404)

    entry_code = request.args.get('code', '')
    game_player = game_players_repository.fetch_player(
        game_id,
        player.venmo_username,
    )

    if game_player and not entry_code:
        entry_code = req_game.entry_code

    return render_template('game/join.html', game=req_game, player=player, entry_code_prefill=entry_code)


def handle_join_game(player: Player, game_id: int, socketio: SocketIO) -> Response:
    active_game_id = player.active_game_id
    if active_game_id:
        return redirect(url_for('game_view', game_id=active_game_id))

    req_game = game.repository.fetch(game_id)
    if not req_game or not req_game.is_active:
        return abort(404)

    err = None
    entry_code = request.form.get('entry-code')

    if entry_code.upper().strip() != req_game.entry_code.upper().strip():
        err = 'The provided entry code is incorrect, please try again'

    if err:
        return render_template('game/join.html', err=err, entry_code_prefill=entry_code, game=req_game, player=player), 403

    game_players_repository.add_player(game_id, player.venmo_username)
    broadcast_reload(socketio, game_id)
    return redirect(url_for('game_view', game_id=game_id), code=303)


def handle_end_game_form(player: Player, game_id: int) -> Response:
    req_game = game.repository.fetch(game_id)
    if not req_game:
        return redirect(url_for('home'))

    if not req_game.is_active or req_game.creator_id != player.venmo_username:
        return redirect(url_for('game_view', game_id=game_id)), abort(403)

    players = game_players_repository.fetch(game_id)

    warning = None
    err = None

    leftover_cents = players.total_buyin_cents() - players.total_cashout_cents()
    if leftover_cents > 0:
        warning = f'There is ${cents_utils.to_string(leftover_cents)} left on the table, please check everyone has cashed out'
    else:
        err = get_end_game_err(players)

    return render_template('game/end.html', player=player, game=req_game, warning=warning, err=err)


def create_payments_and_end_game(game_players: GamePlayers, socketio: SocketIO) -> None:
    err = get_end_game_err(game_players)
    if err:
        return

    game_id = game_players.game_id
    transactions = payout.settle.get_transactions(game_players.players)

    for transaction in transactions:
        payment.repository.create(
            game_id=game_id,
            from_player_id=transaction.sender_id,
            to_player_id=transaction.receiver_id,
            cents=transaction.cents
        )

    game_players_repository.remove_all_players(game_id)
    game.repository.set_active(game_id, False)

    broadcast_reload(socketio, game_id)
    broadcast_reload(socketio, None)


def handle_end_game(player: Player, game_id: int, socketio: SocketIO) -> Response:
    req_game = game.repository.fetch(game_id)
    if not req_game:
        return redirect(url_for('home'))

    if not req_game.is_active:
        return redirect(url_for('game_view', game_id=game_id)), abort(400)
    if req_game.creator_id != player.venmo_username:
        return redirect(url_for('game_view', game_id=game_id)), abort(403)

    req_game_players = game_players_repository.fetch(game_id)
    create_payments_and_end_game(req_game_players, socketio=socketio)
    return redirect(url_for('game_view', game_id=game_id), code=303)
