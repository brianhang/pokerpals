
def get_sum_buyins(game_id):
    return 'SELECT sum(players.total_buyin_chips) * game.buyin_amt_cents '\
            f'FROM Players, (SELECT * FROM games WHERE id={game_id}) AS game '\
            'WHERE players.game_id = game.id;'
#      return r'SELECT sum(players.total_chips) * game.buyin_cents ' \
#              'FROM players, ' \
#                '(' \
#               f'  select * from games where id = {game_id} ' \
#               r') as game' \
#              r'WHERE ' \
#              'players.game_id = game.id;'
