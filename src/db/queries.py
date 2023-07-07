
def get_sum_buyins(game_id):
    return 'SELECT sum(players.total_buyin_chips) * game.buyin_amt_cents '\
            f'FROM players, (SELECT * FROM games WHERE id={game_id}) AS game '\
            'WHERE players.game_id = game.id;'


def get_payout_query(game_id):
    return 'SELECT players.venmo_username, (final_chips - total_buyin_chips) * buyin_amt_cents/200 '\
            f'FROM players, (SELECT * FROM games WHERE id={game_id}) AS game '\
            'WHERE players.game_id = game.id;'
