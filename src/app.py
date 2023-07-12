from flask import Flask, redirect, url_for

import db.app_connection
from game.route import (handle_buyin, handle_buyin_form, handle_cashout,
                        handle_cashout_form, handle_create_game,
                        handle_create_game_form, handle_end_game,
                        handle_end_game_form, handle_game_list,
                        handle_join_game, handle_join_game_form,
                        handle_view_game)
from player.route import (fetch_player, handle_login, handle_login_page,
                          handle_logout)

app = Flask(__name__)


@app.teardown_appcontext
def teardown_db(_ex):
    db.app_connection.close()


@app.route('/', strict_slashes=False)
def home():
    with fetch_player() as player:
        if player:
            return handle_game_list(player)
    return handle_login_page()


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
            return handle_create_game(player)
    return redirect(url_for('home'))


@app.route('/game/buyin', strict_slashes=False)
def game_buyin_form():
    with fetch_player() as player:
        if player:
            return handle_buyin_form(player)
    return redirect(url_for('home')), 403


@app.post('/game/buyin', strict_slashes=False)
def game_buyin():
    with fetch_player() as player:
        if player:
            return handle_buyin(player)
    return redirect(url_for('home')), 403


@app.route('/game/cashout', strict_slashes=False)
def game_cashout_form():
    with fetch_player() as player:
        if player:
            return handle_cashout_form(player)
    return redirect(url_for('home')), 403


@app.post('/game/cashout', strict_slashes=False)
def game_cashout():
    with fetch_player() as player:
        if player:
            return handle_cashout(player)
    return redirect(url_for('home')), 403


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
    return redirect(url_for('home')), 403


@app.post('/game/join/<game_id>', strict_slashes=False)
def game_join(game_id):
    with fetch_player() as player:
        if player:
            game_id = int(game_id) if game_id.isdigit() else 0
            return handle_join_game(player, game_id)
    return redirect(url_for('home')), 403


@app.route('/game/end/<game_id>', strict_slashes=False)
def game_end_form(game_id):
    with fetch_player() as player:
        if player:
            game_id = int(game_id) if game_id.isdigit() else 0
            return handle_end_game_form(player, game_id)
    return redirect(url_for('home')), 403


@app.post('/game/end/<game_id>', strict_slashes=False)
def game_end(game_id):
    with fetch_player() as player:
        if player:
            game_id = int(game_id) if game_id.isdigit() else 0
            return handle_end_game(player, game_id)
    return redirect(url_for('home')), 403


@app.post('/login', strict_slashes=False)
def login():
    return handle_login()


@app.post('/logout')
def logout():
    return handle_logout()


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8080)
