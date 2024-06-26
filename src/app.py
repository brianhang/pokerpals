import gevent.monkey

from game.qr_code import handle_game_join_qr_code
from migrations.add_payout_type import migrate_add_payout_type
from payment.route import handle_payment_dismiss  # nopep8

gevent.monkey.patch_all()  # nopep8

from flask import Flask, redirect, request, url_for
from flask_mobility import Mobility
from flask_socketio import SocketIO

import db.app_connection
from game.route import (handle_buyin, handle_buyin_form, handle_cashout,
                        handle_cashout_form, handle_create_game,
                        handle_create_game_form, handle_edit_player,
                        handle_edit_player_form, handle_end_game,
                        handle_end_game_form, handle_game_list, handle_history,
                        handle_join_game, handle_join_game_form,
                        handle_view_game)
from player.route import (fetch_player, handle_login, handle_login_page,
                          handle_logout)

app = Flask(__name__)
socketio = SocketIO(app)
Mobility(app)


@app.teardown_appcontext
def teardown_db(_ex):
    db.app_connection.close()


@app.route('/', strict_slashes=False)
def home():
    with fetch_player() as player:
        if player:
            return handle_game_list(player)
    return handle_login_page()


@app.route('/history', strict_slashes=False)
def history():
    with fetch_player() as player:
        if player:
            return handle_history(player)
    return handle_login_page(return_endpoint='history')


@app.route('/game/create', strict_slashes=False)
def game_create_form():
    with fetch_player() as player:
        if player:
            return handle_create_game_form(player)
    return handle_login_page()


@app.post('/game/create', strict_slashes=False)
def game_create():
    with fetch_player() as player:
        if player:
            return handle_create_game(player, socketio=socketio)
    return redirect(url_for('home'))


@app.route('/game/buyin', strict_slashes=False)
def game_buyin_form():
    with fetch_player() as player:
        if player:
            return handle_buyin_form(player)
    return redirect(url_for('home'))


@app.post('/game/buyin', strict_slashes=False)
def game_buyin():
    with fetch_player() as player:
        if player:
            return handle_buyin(player, socketio=socketio)
    return redirect(url_for('home'))


@app.route('/game/cashout', strict_slashes=False)
def game_cashout_form():
    with fetch_player() as player:
        if player:
            return handle_cashout_form(player)
    return redirect(url_for('home'))


@app.post('/game/cashout', strict_slashes=False)
def game_cashout():
    with fetch_player() as player:
        if player:
            return handle_cashout(player, socketio=socketio)
    return redirect(url_for('home'))


@app.route('/g/<game_id>', strict_slashes=False)
def game_view(game_id):
    game_id = int(game_id) if game_id.isdigit() else 0
    with fetch_player() as player:
        return handle_view_game(player=player, game_id=game_id)


@app.route('/game/join/<game_id>', strict_slashes=False)
def game_join_form(game_id):
    with fetch_player() as player:
        if player:
            game_id = int(game_id) if game_id.isdigit() else 0
            return handle_join_game_form(player, game_id)

    entry_code = request.args.get('code', '')
    return handle_login_page(return_endpoint='game_join_form', return_game_id=game_id, return_game_code=entry_code)


@app.post('/game/join/<game_id>', strict_slashes=False)
def game_join(game_id):
    with fetch_player() as player:
        if player:
            game_id = int(game_id) if game_id.isdigit() else 0
            return handle_join_game(player, game_id, socketio=socketio)
    return redirect(url_for('home'))


@app.route('/game/end/<game_id>', strict_slashes=False)
def game_end_form(game_id):
    with fetch_player() as player:
        if player:
            game_id = int(game_id) if game_id.isdigit() else 0
            return handle_end_game_form(player, game_id)
    return redirect(url_for('home'))


@app.post('/game/end/<game_id>', strict_slashes=False)
def game_end(game_id):
    with fetch_player() as player:
        if player:
            game_id = int(game_id) if game_id.isdigit() else 0
            return handle_end_game(player, game_id, socketio=socketio)
    return redirect(url_for('home'))


@app.route('/game/edit/<game_id>/<target_player_id>', strict_slashes=False)
def game_edit_player_form(game_id, target_player_id):
    with fetch_player() as player:
        if player:
            game_id = int(game_id) if game_id.isdigit() else 0
            return handle_edit_player_form(player, game_id, target_player_id)
    return redirect(url_for('home'))


@app.post('/game/edit/<game_id>/<target_player_id>', strict_slashes=False)
def game_edit_player(game_id, target_player_id):
    with fetch_player() as player:
        if player:
            game_id = int(game_id) if game_id.isdigit() else 0
            return handle_edit_player(player, game_id, target_player_id, socketio=socketio)
    return redirect(url_for('home'))


@app.route('/game/qrcode/<game_id>', strict_slashes=False)
def game_qr_code(game_id):
    entry_code = request.args.get('code')
    if entry_code and len(entry_code.strip()) < 1:
        entry_code = None

    return handle_game_join_qr_code(game_id, entry_code)


@app.route('/login', strict_slashes=False)
def login_page():
    with fetch_player() as player:
        if player:
            return redirect(url_for('home'))
    return handle_login_page()


@app.post('/login', strict_slashes=False)
def login():
    return handle_login()


@app.post('/logout')
def logout():
    return handle_logout()


@app.post('/payment/dismiss/<payment_id>', strict_slashes=False)
def payment_dismiss(payment_id):
    with fetch_player() as player:
        if player:
            payment_id = int(payment_id) if payment_id.isdigit() else 0
            return handle_payment_dismiss(player, payment_id)
    return handle_login_page()


if __name__ == '__main__':
    migrate_add_payout_type()

    import os

    debug = os.environ.get('APP_DEBUG') is not None
    port = int(os.environ.get('APP_PORT') or 8080)
    socketio.run(app, host='0.0.0.0', port=port, debug=debug)
