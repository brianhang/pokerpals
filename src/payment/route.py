from flask import Response, abort, redirect, render_template, request, url_for

from player.player import Player
from . import repository as payment_repository


def handle_payment_dismiss(player: Player, payment_id: int) -> Response:
    payment = payment_repository.fetch(payment_id)

    if not payment:
        return abort(404)
    if player.id != payment.from_player_id and \
            player.id != payment.to_player_id:
        return abort(403)

    confirmed = bool(request.form.get('confirmed', ''))

    try:
        game_id = int(request.form.get('return-game', ''))
    except ValueError:
        game_id = None

    if game_id:
        return_url = url_for('game_view', game_id=game_id)
    elif request.form.get('return-payment'):
        return_url = url_for('payment_view', payment_id=payment_id)
    else:
        return_url = url_for('home')

    if not confirmed:
        return render_template('payment/confirm.html', player=player, payment=payment, return_url=return_url, game_id=game_id,
                               return_payment=bool(request.form.get('return-payment')))

    if confirmed and not payment.completed:
        payment_repository.set_completed(payment_id, True)

    return redirect(return_url, code=303)


def handle_view_payment(player: Player, payment_id: int) -> Response:
    """
    Every way to settle one payment: Venmo deep links when the other person
    has Venmo, and their Zelle details to copy into a bank app.
    """
    # Imported here: game.route imports this package's repository
    from game.route import get_venmo_note
    from player import repository as player_repository
    from utils import zelle as zelle_utils
    import utils.venmo.link as venmo_link

    payment = payment_repository.fetch(payment_id)

    if not payment:
        return abort(404)
    if player.id not in (payment.from_player_id, payment.to_player_id):
        return abort(403)

    is_send = payment.from_player_id == player.id
    other = player_repository.fetch(
        payment.to_player_id if is_send else payment.from_player_id)

    venmo_url = None
    if other and other.venmo_username:
        venmo_url = venmo_link.get_payment_url(
            venmo_username=other.venmo_username,
            txn=venmo_link.Transaction.PAY if is_send else venmo_link.Transaction.CHARGE,
            amount_cents=payment.cents,
            is_mobile=request.MOBILE,
            note=get_venmo_note(payment),
        )

    return render_template(
        'payment/view.html',
        player=player,
        payment=payment,
        other=other,
        is_send=is_send,
        venmo_url=venmo_url,
        amount=f'{payment.cents // 100}.{payment.cents % 100:02d}',
        zelle_display=zelle_utils.display,
    )
