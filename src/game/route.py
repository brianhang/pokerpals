import math
from random import choice, choices
from string import ascii_uppercase
from typing import Callable, NamedTuple, Optional

from flask import Response, abort, redirect, render_template, request, url_for
from flask_socketio import SocketIO

import game.repository
import game_players.repository as game_players_repository
from payment.payment import Payment
import payment.repository as payment_repository
from payout.payout_type import NAMES as PAYOUT_TYPE_NAMES, PayoutType
import payout.settle_minimize_transactions
import utils.cents as cents_utils
import utils.venmo.link
from game_players.game_players import GamePlayer, GamePlayers
from player.player import Player

from .validation import get_end_game_err

VENMO_NOTES = ['P', '♠️', '♦️', '♣️', '❤️', '🅿️']


def broadcast_reload(socketio: SocketIO, game_id: Optional[int]) -> None:
    socketio.emit('reload', str(game_id) if game_id else None)


def generate_entry_code() -> str:
    return ''.join(choices(ascii_uppercase, k=4))


def get_optional_cents_form_param(name: str) -> Optional[int]:
    return cents_utils.from_string(request.form.get(name))


def get_cents_form_param(name: str, default: int = 0) -> int:
    cents = get_optional_cents_form_param(name)
    return default if cents is None else cents


def get_max_cashout_cents(cur_game_players: GamePlayers, cur_game_player: GamePlayer) -> int:
    game_remaining_cents = cur_game_players.total_buyin_cents() \
        - cur_game_players.total_cashout_cents() \
        + (cur_game_player.cashout_cents or 0)
    return game_remaining_cents


def find_game_player(cur_game_players: GamePlayers, player_id: str) -> Optional[GamePlayer]:
    return next((game_player
                 for game_player in cur_game_players.players
                 if game_player.player_venmo_username == player_id), None)


PaymentURL = NamedTuple('PaymentURL', [('url', str), ('is_send', bool)])
PaymentURL.__doc__ = '''
Information for rendering a Venmo payment link

`url` - The full Venmo payment link URL
`is_send` - If the payment link is for sending money to someone els
'''


def get_payment_and_urls(
    player: Player,
    payments: list[Payment],
    get_venmo_note: Callable[[Payment], str],
) -> list[(Payment, PaymentURL)]:
    """
    Returns a list of `PaymentURL`s for rendering Venmo payment links that
    `player` should see to complete the given list of payments that they are
    involved in
    """
    payment_and_urls = []

    for payment in payments:
        is_send = payment.from_player_id == player.venmo_username

        if is_send:
            venmo_username = payment.to_player_id
            txn = utils.venmo.link.Transaction.PAY
        else:
            venmo_username = payment.from_player_id
            txn = utils.venmo.link.Transaction.CHARGE

        note = get_venmo_note(payment)
        venmo_url = utils.venmo.link.get_payment_url(
            venmo_username=venmo_username,
            txn=txn,
            amount_cents=payment.cents,
            is_mobile=request.MOBILE,
            note=note,
        )
        payment_url = PaymentURL(venmo_url, is_send)
        payment_and_urls.append((payment, payment_url))

    return payment_and_urls


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
    payments = payment_repository.fetch_for_player(player.venmo_username)
    payment_and_urls = get_payment_and_urls(player, payments, get_venmo_note)

    return render_template('game/list.html', player=player, active_games=active_games, recent_games=recent_games, current_game=current_game, payment_and_urls=payment_and_urls)


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
    return render_template(
        'game/create.html',
        lobby_name=lobby_name,
        entry_code=entry_code,
        payout_type_names=PAYOUT_TYPE_NAMES,
    )


def handle_create_game(player: Player, socketio: SocketIO) -> Response:
    active_game_id = player.active_game_id
    if active_game_id:
        return redirect(url_for('game_view', game_id=active_game_id), code=303)

    lobby_name = request.form.get('lobby-name', '').strip()
    buyin_cents = get_cents_form_param('buy-in')
    entry_code = request.form.get('entry-code', '').strip()
    raw_payout_type = request.form.get('payout-type', '').strip()
    err = None

    try:
        payout_type = PayoutType(int(raw_payout_type))
    except:
        payout_type = None

    if len(lobby_name) < 1:
        err = 'Please enter a valid lobby name'
    elif buyin_cents < 100:
        err = 'A buy in must be at least $1.00, please provide a higher amount'
    elif len(entry_code) < 1:
        err = 'Please provide a valid entry code'

    if err:
        return render_template(
            'game/create.html',
            err=err,
            lobby_name=lobby_name,
            entry_code=entry_code,
            payout_type_names=PAYOUT_TYPE_NAMES,
            selected_payout_type=payout_type,
        )

    player_id = player.venmo_username
    new_game = game.repository.create(
        creator_id=player_id,
        lobby_name=lobby_name,
        buyin_cents=buyin_cents,
        entry_code=entry_code,
        payout_type=payout_type,
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

    entry_code = request.args.get('code', '')
    if not entry_code and game_player:
        return redirect(
            url_for('game_view', game_id=game_id, code=req_game.entry_code),
            code=302,
        )

    buyin_amount = cents_utils.to_string(req_game.buyin_cents)
    buyin_total = cents_utils.to_string(req_game_players.total_buyin_cents())
    cashout_total = cents_utils.to_string(
        req_game_players.total_cashout_cents())
    payments = payment_repository.fetch_for_game(game_id)

    payment_and_urls = []

    if player:
        player_payments = [
            payment for payment in payments
            if (player.venmo_username == payment.from_player_id or
                player.venmo_username == payment.to_player_id) and
            not payment.completed
        ]
        payment_and_urls = get_payment_and_urls(
            player,
            player_payments,
            get_venmo_note,
        )

    return render_template(
        'game/view.html',
        game=req_game,
        player=player,
        players=req_game_players,
        buyin_total=buyin_total,
        game_player=game_player,
        cashout_total=cashout_total,
        payments=payments,
        payment_and_urls=payment_and_urls,
        buyin_amount=buyin_amount,
        entry_code=entry_code,
        can_edit_player=can_edit_player,
    )


def handle_buyin_form(player: Player) -> Response:
    game_id = player.active_game_id
    if not game_id:
        return redirect(url_for('home'))

    active_game = game.repository.fetch(game_id)
    if not active_game:
        return redirect(url_for('home'))

    buyin_prefill = cents_utils.to_numerical_string(active_game.buyin_cents)
    return render_template('game/buyin.html', buyin_prefill=buyin_prefill, game=active_game, player=player)


def handle_buyin(player: Player, socketio: SocketIO) -> Response:
    game_id = player.active_game_id
    if not game_id:
        return redirect(url_for('home'))

    active_game = game.repository.fetch(game_id)
    if not active_game:
        return redirect(url_for('home'))

    err = None

    cents = get_cents_form_param('amount')
    buyin_prefill = cents_utils.to_string(cents)
    if cents <= 0:
        err = 'Please provide a valid amount to buy in'

    if err:
        return render_template('game/buyin.html', err=err, buyin_prefill=buyin_prefill, game=active_game, player=player), 400

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

    if game_player.cashout_cents:
        cashout_prefill = cents_utils.to_numerical_string(
            game_player.cashout_cents)
    else:
        cashout_prefill = ""

    return render_template('game/cashout.html',
                           cashout_prefill=cashout_prefill,
                           game=active_game,
                           player=player)


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
    cents = get_cents_form_param('amount')

    if cents < 0:
        err = 'Please provide a valid amount to cash out'

    if err:
        cashout_prefill = cents_utils.to_string(cents)
        return render_template('game/cashout.html',
                               err=err,
                               cashout_prefill=cashout_prefill,
                               game=active_game,
                               player=player), 400

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
    if not req_game:
        return abort(404)

    if not req_game.is_active:
        return redirect(url_for('game_view', game_id=game_id), code=303)

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
    if not req_game:
        return abort(404)

    if not req_game.is_active:
        return redirect(url_for('game_view', game_id=game_id), code=303)

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
        warning = f'There is {cents_utils.to_string(leftover_cents)} left on' \
            ' the table, please check everyone has cashed out'
    else:
        err = get_end_game_err(players)

    return render_template('game/end.html', player=player, game=req_game, warning=warning, err=err)


def create_payments_and_end_game(game_players: GamePlayers, socketio: SocketIO) -> None:
    err = get_end_game_err(game_players)
    if err:
        return

    game_id = game_players.game_id
    transactions = payout.settle_minimize_transactions.get_transactions(
        game_players.players)

    for transaction in transactions:
        payment_repository.create(
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


def handle_edit_player_form(player: Player, game_id: int, target_player_id: str) -> Response:
    req_game = game.repository.fetch(game_id)
    if not req_game:
        return redirect(url_for('home'))

    if not req_game.is_active:
        return redirect(url_for('game_view', game_id=game_id)), abort(400)
    if not can_edit_player(req_game, player, target_player_id):
        return redirect(url_for('game_view', game_id=game_id)), abort(403)

    target_player = game_players_repository.fetch_player(
        game_id, target_player_id)
    if not target_player:
        return redirect(url_for('game_view', game_id=game_id)), abort(403)

    buyin_prefill = cents_utils.to_numerical_string(
        target_player.buyin_cents) if target_player.buyin_cents is not None else None
    cashout_prefill = cents_utils.to_numerical_string(
        target_player.cashout_cents) if target_player.cashout_cents is not None else None

    return render_template('game/edit_player.html', player=player, target_player=target_player, game=req_game, buyin_prefill=buyin_prefill, cashout_prefill=cashout_prefill)


def handle_edit_player(player: Player, game_id: int, target_player_id: str, socketio: SocketIO) -> Response:
    req_game = game.repository.fetch(game_id)
    if not req_game:
        return redirect(url_for('home'))

    if not req_game.is_active:
        return redirect(url_for('game_view', game_id=game_id)), abort(400)
    if not can_edit_player(req_game, player, target_player_id):
        return redirect(url_for('game_view', game_id=game_id)), abort(403)

    target_player = game_players_repository.fetch_player(
        game_id, target_player_id)
    if not target_player:
        return redirect(url_for('game_view', game_id=game_id)), abort(403)

    new_buyin_cents = get_optional_cents_form_param('buyin')
    if new_buyin_cents is not None:
        game_players_repository.buy_in(
            game_id, target_player_id, new_buyin_cents, override=True)

    new_cash_out = get_optional_cents_form_param('cashout')
    game_players_repository.cash_out(game_id, target_player_id, new_cash_out)

    broadcast_reload(socketio, game_id)
    return redirect(url_for('game_view', game_id=game_id), code=303)


def can_edit_player(
    req_game: game.repository.Game,
    player: Player,
    target_player_id: str,
) -> bool:
    player_id = player.venmo_username

    if req_game.creator_id == player_id:
        return True

    if player_id == target_player_id:
        return True

    return False


def get_venmo_note(payment: Payment) -> str:
    return f'{choice(VENMO_NOTES)} {payment.game_id}'
