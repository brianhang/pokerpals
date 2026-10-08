"""
User profiles: how to pay someone, and editing your own name and payment
methods.
"""
from typing import Optional

from flask import Response, abort, redirect, render_template, request, url_for

from player.player import Player
from utils import zelle as zelle_utils
from utils.venmo.username import is_valid_venmo_username
from . import repository as player_repository
from .route import MAX_DISPLAY_NAME_LENGTH


def can_see_zelle(viewer: Player, user: Player) -> bool:
    """
    Zelle handles are phone numbers or emails, so they are only shown to the
    user and people they have played with.
    """
    return viewer.id == user.id or player_repository.shares_game(viewer.id, user.id)


def handle_profile(viewer: Player, user_id: int) -> Response:
    user = player_repository.fetch(user_id)
    if not user:
        return abort(404)

    return render_template(
        'user/profile.html',
        player=viewer,
        user=user,
        is_self=viewer.id == user.id,
        zelle_handle=user.zelle_handle if can_see_zelle(viewer, user) else None,
        zelle_display=zelle_utils.display,
    )


def render_edit(player: Player, err: Optional[str] = None, status: int = 200, **values):
    values = {
        'display_name': player.display_name,
        'venmo_username': player.venmo_username or '',
        'zelle_handle': zelle_utils.display(player.zelle_handle) if player.zelle_handle else '',
        **values,
    }
    return render_template(
        'user/edit.html',
        player=player,
        err=err,
        values=values,
        saved=request.args.get('saved') is not None,
    ), status


def handle_edit_form(player: Player) -> Response:
    return render_edit(player)


def handle_edit(player: Player) -> Response:
    display_name = ' '.join(request.form.get('display-name', '').split())
    venmo_username = request.form.get('venmo-username', '').strip().removeprefix('@')
    raw_zelle_handle = request.form.get('zelle-handle', '').strip()
    values = {
        'display_name': display_name,
        'venmo_username': venmo_username,
        'zelle_handle': raw_zelle_handle,
    }

    def error(message: str):
        return render_edit(player, err=message, status=400, **values)

    if not display_name:
        return error('Please enter your name')
    if len(display_name) > MAX_DISPLAY_NAME_LENGTH:
        return error(f'Please use a name with at most {MAX_DISPLAY_NAME_LENGTH} characters')

    venmo_changed = venmo_username.lower() != (player.venmo_username or '').lower()
    if venmo_username and venmo_changed:
        if player_repository.is_handle_taken(player_repository.VENMO, venmo_username, player.id):
            return error(f'@{venmo_username} is already used by someone else')
        if not is_valid_venmo_username(venmo_username):
            return error(f'Could not find @{venmo_username} on Venmo, please check it')

    zelle_handle = None
    if raw_zelle_handle:
        zelle_handle = zelle_utils.normalize(raw_zelle_handle)
        if not zelle_handle:
            return error('Please enter the phone number or email you use with Zelle')
        if player_repository.is_handle_taken(player_repository.ZELLE, zelle_handle, player.id):
            return error('That Zelle phone number or email is already used by someone else')

    try:
        if venmo_changed or venmo_username != player.venmo_username:
            player_repository.set_payment_method(
                player.id, player_repository.VENMO, venmo_username or None)
        if zelle_handle != player.zelle_handle:
            player_repository.set_payment_method(
                player.id, player_repository.ZELLE, zelle_handle)
    except player_repository.PaymentMethodTakenError:
        return error('That payment method is already used by someone else')

    if display_name != player.display_name:
        player_repository.update_display_name(player.id, display_name)

    return redirect(url_for('account', saved=1), code=303)
