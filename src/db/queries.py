
def get_sum_buyins(game_id):
    return r'SELECT sum(total_chips) * game.buyin_cents' \
            'FROM players, ' \
            '  (' \
            f'    select * from games where id = {game_id}' \
            r'  ) game' \
            r'WHERE players.game_id = game.id'
