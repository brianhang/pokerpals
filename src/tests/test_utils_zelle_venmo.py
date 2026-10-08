import unittest

from utils import zelle
from utils.venmo.link import Transaction, get_payment_url


class TestZelle(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual('+14155550123', zelle.normalize('(415) 555-0123'))
        self.assertEqual('a.b+c@example.co', zelle.normalize(' A.B+c@Example.CO '))
        for raw in [None, '', 'nope', 'a@b', '@example.com', 'a b@example.com', '555-0123']:
            self.assertIsNone(zelle.normalize(raw), raw)

    def test_display(self):
        self.assertEqual('(415) 555-0123', zelle.display('+14155550123'))
        self.assertEqual('+447911123456', zelle.display('+447911123456'))
        self.assertEqual('a@example.com', zelle.display('a@example.com'))


class TestVenmoLink(unittest.TestCase):
    def test_desktop(self):
        self.assertEqual(
            'https://venmo.com/?recipients=bob&txn=pay&note=%E2%99%A0%EF%B8%8F%2012&amount=15.00',
            get_payment_url('bob', Transaction.PAY, 1500, note='♠️ 12'),
        )

    def test_mobile(self):
        self.assertEqual(
            'venmo://paycharge?recipients=bob-1&txn=charge&note=Poker&amount=0.50',
            get_payment_url('bob-1', Transaction.CHARGE, 50, is_mobile=True),
        )


if __name__ == '__main__':
    unittest.main()
