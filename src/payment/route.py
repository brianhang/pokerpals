from flask import Response, abort, redirect, render_template, request, url_for

from player.player import Player
from . import repository as payment_repository


def handle_payment_dismiss(player: Player, payment_id: int) -> Response:
    payment = payment_repository.fetch(payment_id)

    if not payment:
        return abort(404)
    if player.venmo_username not in (payment.from_player_id, payment.to_player_id):
        return abort(403)

    confirmed = bool(request.form.get('confirmed', ''))

    try:
        game_id = int(request.form.get('return-game', ''))
    except ValueError:
        game_id = None

    if game_id:
        return_url = url_for('game_view', game_id=game_id)
    else:
        return_url = url_for('home')

    if not confirmed:
        return render_template('payment/confirm.html', player=player, payment=payment, return_url=return_url, game_id=game_id)

    if confirmed and not payment.completed:
        payment_repository.set_completed(payment_id, True)

    return redirect(return_url, code=303)
