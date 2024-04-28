from datetime import datetime
from typing import Optional
import unittest

from game_players.game_players import GamePlayer
from payout.settle import get_transactions, Transaction


class TestSettle(unittest.TestCase):
    def test_empty(self):
        game_players = self.make_players([])
        transactions = get_transactions(game_players)
        self.assertListEqual(
            [],
            transactions,
            'There should be no transactions with no players',
        )

    def test_no_op(self):
        game_players = self.make_players([(0, 0)])
        transactions = get_transactions(game_players)
        self.assertListEqual([], transactions, 'No transactions are necessary')

    def test_no_op_nonzero(self):
        game_players = self.make_players([(10_00, 10_00)])
        transactions = get_transactions(game_players)
        self.assertListEqual([], transactions, 'No transactions are necessary')

    def test_no_op_nonzero_many(self):
        game_players = self.make_players(
            [(10_00, 10_00), (20_00, 20_00), (0, 0)])
        transactions = get_transactions(game_players)
        self.assertListEqual([], transactions, 'No transactions are necessary')

    def test_one_player(self):
        game_players = self.make_players([(10_00, 10_00)])
        transactions = get_transactions(game_players)
        self.assert_transactions_valid(game_players, transactions)

    def test_two_players(self):
        game_players = self.make_players([(10_00, 5_00), (10_00, 15_00)])
        transactions = get_transactions(game_players)
        self.assert_transactions_valid(game_players, transactions)

    def test_two_positive(self):
        game_players = self.make_players(
            [(10_00, 0), (10_00, 15_00), (10_00, 15_00)])
        transactions = get_transactions(game_players)
        self.assert_transactions_valid(game_players, transactions)

    def test_two_negative(self):
        game_players = self.make_players(
            [(10_00, 0), (10_00, 0), (10_00, 30_00)])
        transactions = get_transactions(game_players)
        self.assert_transactions_valid(game_players, transactions)

    def test_many(self):
        game_players = self.make_players(
            [(10_00, 5_00), (10_00, 5_00), (10_00, 30_00), (10_00, 0)])
        transactions = get_transactions(game_players)
        self.assert_transactions_valid(game_players, transactions)

    def make_players(
        self,
        buyin_and_cashouts: list[tuple[int, Optional[int]]],
    ) -> list[GamePlayer]:
        join_time = datetime.now()
        return [
            GamePlayer(
                player_venmo_username=f'Player-{player_idx + 1}',
                join_time=join_time,
                buyin_cents=buyin_cents,
                cashout_cents=cashout_cents
            )
            for player_idx, (buyin_cents, cashout_cents)
            in enumerate(buyin_and_cashouts)
        ]

    def assert_transactions_valid(
        self,
        game_players: list[GamePlayer],
        transactions: list[Transaction],
    ) -> None:
        balances = {
            player.player_venmo_username: player.buyin_cents
            for player in game_players
        }

        for transaction in transactions:
            self.assertIn(transaction.sender_id, balances,
                          f'{transaction} has an invalid from player')
            balances[transaction.sender_id] -= transaction.cents
            self.assertIn(transaction.receiver_id, balances,
                          f'{transaction} has an invalid to player')
            balances[transaction.receiver_id] += transaction.cents

        for player in game_players:
            self.assertEqual(player.cashout_cents,
                             balances[player.player_venmo_username],
                             'Final balance does not match')

        original_sum = sum(player.buyin_cents for player in game_players)
        final_sum = sum(balances.values())
        self.assertEqual(original_sum, final_sum, 'No money should be lost')


if __name__ == '__main__':
    unittest.main()
