from flask import Flask, redirect, url_for

from player.route import fetch_player, handle_login_page, handle_login, handle_logout
from game.route import handle_buyin, handle_buyin_form, handle_create_game, handle_game_list, handle_create_game_form, handle_view_game

import db.app_connection


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
    return redirect(url_for('home'))


@app.post('/game/buyin', strict_slashes=False)
def game_buyin():
    with fetch_player() as player:
        if player:
            return handle_buyin(player)
    return redirect(url_for('home'))


@app.route('/g/<game_id>')
def game_view(game_id):
    game_id = int(game_id) if game_id.isdigit() else 0
    with fetch_player() as player:
        return handle_view_game(player=player, game_id=game_id)


@app.post('/login', strict_slashes=False)
def login():
    return handle_login()


@app.post('/logout')
def logout():
    return handle_logout()


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8080)
