"""
Phone number login.

1. /login: the user enters a phone number and is texted a code.
2. /login/verify: the user enters the code.
3. If a user has that phone number, they are logged in. Otherwise
   /login/welcome lets them either claim a profile from the old Venmo login
   (keeping their game history and payments) or start a new profile.

The logged in user's ID is kept in Flask's signed session cookie.
"""
import time
from contextlib import contextmanager
from typing import Optional

from flask import Response, redirect, render_template, request, session, url_for

from player.player import Player
from utils import phone as phone_utils
from utils import verification
from utils.venmo.username import is_valid_venmo_username
from . import repository as player_repository

ALLOWED_ENDPOINTS = ['home', 'game_view', 'history', 'game_join_form']

SESSION_USER_ID = 'user_id'
SESSION_LOGIN = 'login'

# How long someone has to type the code, and then to finish signing up
PENDING_LOGIN_TTL_SECONDS = 15 * 60
RESEND_COOLDOWN_SECONDS = 30
MAX_DISPLAY_NAME_LENGTH = 40


@contextmanager
def fetch_player() -> Optional[Player]:
    yield player_repository.fetch(session.get(SESSION_USER_ID))


def get_return_params() -> dict:
    return_endpoint = request.values.get('return', '').strip()
    return_game_id = request.values.get('return_game_id', '').strip()
    return_game_code = request.values.get('return_game_code', '').strip()

    return {
        'endpoint': return_endpoint if return_endpoint in ALLOWED_ENDPOINTS else None,
        'game_id': int(return_game_id) if return_game_id.isdigit() else None,
        'code': return_game_code or None,
    }


def get_return_url(return_params: Optional[dict]) -> str:
    return_params = return_params or {}
    params = {}

    if return_params.get('game_id'):
        params['game_id'] = return_params['game_id']
    if return_params.get('code'):
        params['code'] = return_params['code']

    return url_for(return_params.get('endpoint') or 'home', **params)


def get_pending_login() -> Optional[dict]:
    """
    The login in progress, if it has not expired.
    """
    pending = session.get(SESSION_LOGIN)

    if not pending or pending.get('started', 0) + PENDING_LOGIN_TTL_SECONDS < time.time():
        session.pop(SESSION_LOGIN, None)
        return None

    return pending


def log_in(player: Player, return_params: Optional[dict]) -> Response:
    session.pop(SESSION_LOGIN, None)
    session[SESSION_USER_ID] = player.id
    session.permanent = True
    return redirect(get_return_url(return_params), code=303)


def handle_login_page(return_endpoint='', return_game_id=None, return_game_code='') -> str:
    return_endpoint = request.args.get('return', return_endpoint or '').strip()
    return_game_id = request.args.get('return_game_id', return_game_id)
    return_game_code = request.args.get(
        'return_game_code', return_game_code or '').strip()

    return render_login(
        return_endpoint=return_endpoint,
        return_game_id=return_game_id,
        return_game_code=return_game_code,
    )


def handle_login() -> Response:
    raw_phone_number = request.form.get('phone-number', '')
    return_params = get_return_params()
    phone_number = phone_utils.normalize(raw_phone_number)
    err = None

    if not phone_number:
        err = 'Please enter a valid phone number, including the area code'
    elif verification.is_enabled():
        try:
            verification.send_code(phone_number)
        except verification.VerificationError as ex:
            err = str(ex)

    if err:
        return render_login(
            err=err,
            phone_number=raw_phone_number,
            return_endpoint=return_params['endpoint'] or '',
            return_game_id=return_params['game_id'],
            return_game_code=return_params['code'] or '',
        ), 400

    pending = {
        'phone_number': phone_number,
        'verified': False,
        'started': time.time(),
        'sent': time.time(),
        'return': return_params,
    }

    if not verification.is_enabled():
        return finish_verification(pending)

    session[SESSION_LOGIN] = pending
    return redirect(url_for('login_verify_page'), code=303)


def render_verify(pending: dict, err: Optional[str] = None, info: Optional[str] = None, status: int = 200):
    return render_template(
        'login_verify.html',
        err=err,
        info=info,
        masked_phone_number=phone_utils.mask(pending['phone_number']),
    ), status


def render_login(**values) -> str:
    return render_template(
        'login.html',
        sends_code=verification.is_enabled(),
        **values,
    )


def handle_verify_page() -> Response:
    pending = get_pending_login()
    if not pending or pending['verified']:
        return redirect(url_for('login_page'))

    return render_verify(pending)


def handle_verify() -> Response:
    pending = get_pending_login()
    if not pending or pending['verified']:
        return redirect(url_for('login_page'), code=303)

    code = request.form.get('code', '')

    try:
        is_valid = verification.check_code(pending['phone_number'], code)
    except verification.VerificationError as ex:
        return render_verify(pending, err=str(ex), status=400)

    if not is_valid:
        return render_verify(
            pending,
            err='That code is not right or has expired, please try again or send a new code',
            status=400,
        )

    return finish_verification(pending)


def finish_verification(pending: dict) -> Response:
    """
    The phone number in `pending` is verified (or verification is off): log
    in its user, or send a new number to sign up.
    """
    player = player_repository.fetch_by_phone_number(pending['phone_number'])
    if player:
        return log_in(player, pending['return'])

    pending['verified'] = True
    pending['started'] = time.time()
    session[SESSION_LOGIN] = pending
    return redirect(url_for('login_welcome_page'), code=303)


def handle_resend() -> Response:
    pending = get_pending_login()
    if not pending or pending['verified']:
        return redirect(url_for('login_page'), code=303)

    if pending.get('sent', 0) + RESEND_COOLDOWN_SECONDS > time.time():
        return render_verify(pending, err='Please wait a moment before sending another code', status=429)

    try:
        verification.send_code(pending['phone_number'])
    except verification.VerificationError as ex:
        return render_verify(pending, err=str(ex), status=400)

    pending['sent'] = time.time()
    session[SESSION_LOGIN] = pending
    return render_verify(pending, info='A new code is on its way')


def get_verified_phone_number() -> Optional[str]:
    pending = get_pending_login()
    if pending and pending['verified']:
        return pending['phone_number']
    return None


def render_welcome(err: Optional[str] = None, status: int = 200, **values):
    return render_template('login_welcome.html', err=err, values=values), status


def handle_welcome_page() -> Response:
    if not get_verified_phone_number():
        return redirect(url_for('login_page'))
    return render_welcome()


def handle_welcome() -> Response:
    phone_number = get_verified_phone_number()
    if not phone_number:
        return redirect(url_for('login_page'), code=303)

    return_params = session[SESSION_LOGIN]['return']

    # Someone may have finished signing up with this number in another tab
    player = player_repository.fetch_by_phone_number(phone_number)
    if player:
        return log_in(player, return_params)

    action = request.form.get('action')
    venmo_username = request.form.get('venmo-username', '') \
        .strip() \
        .removeprefix('@')

    if action == 'claim':
        return claim_venmo_profile(phone_number, venmo_username, return_params)
    if action == 'create':
        display_name = ' '.join(request.form.get('display-name', '').split())
        return create_profile(phone_number, display_name, venmo_username, return_params)

    return render_welcome()


def claim_venmo_profile(phone_number: str, venmo_username: str, return_params: dict) -> Response:
    if not venmo_username:
        return render_welcome(err='Please enter your Venmo username', status=400)

    player = player_repository.fetch_by_venmo_username(venmo_username)

    if not player:
        return render_welcome(
            err=f'No one has played as @{venmo_username} before, you can start a new profile instead',
            status=400,
            claim_venmo_username=venmo_username,
        )

    if player.phone_number or not player_repository.claim(player.id, phone_number):
        return render_welcome(
            err=f'@{venmo_username} has already been claimed by another phone number',
            status=400,
            claim_venmo_username=venmo_username,
        )

    return log_in(player, return_params)


def create_profile(phone_number: str, display_name: str, venmo_username: str, return_params: dict) -> Response:
    values = {
        'display_name': display_name,
        'create_venmo_username': venmo_username,
    }

    if not display_name:
        return render_welcome(err='Please enter your name', status=400, **values)
    if len(display_name) > MAX_DISPLAY_NAME_LENGTH:
        return render_welcome(
            err=f'Please use a name with at most {MAX_DISPLAY_NAME_LENGTH} characters', status=400, **values)

    if venmo_username:
        existing = player_repository.fetch_by_venmo_username(venmo_username)
        if existing and not existing.phone_number:
            return render_welcome(
                err=f'@{venmo_username} already has a PokerPal history, claim it above to keep it',
                status=400,
                claim_venmo_username=venmo_username,
                **values,
            )
        if existing:
            return render_welcome(
                err=f'@{venmo_username} is already used by someone else', status=400, **values)
        if not is_valid_venmo_username(venmo_username):
            return render_welcome(
                err=f'Could not find @{venmo_username} on Venmo, please check it', status=400, **values)

    try:
        player = player_repository.create(
            phone_number=phone_number,
            display_name=display_name,
            venmo_username=venmo_username or None,
        )
    except player_repository.PhoneNumberTakenError:
        player = player_repository.fetch_by_phone_number(phone_number)
    except player_repository.VenmoUsernameTakenError:
        return render_welcome(
            err=f'@{venmo_username} is already used by someone else', status=400, **values)

    return log_in(player, return_params)


def handle_logout() -> Response:
    session.clear()
    return redirect('/', code=303)
