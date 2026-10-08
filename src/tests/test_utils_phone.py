import unittest

from utils.phone import mask, normalize


class TestPhoneNormalize(unittest.TestCase):
    def test_us_formats(self):
        for raw in [
            '4155550123',
            '(415) 555-0123',
            '415.555.0123',
            '415 555 0123',
            '1-415-555-0123',
            '+1 415 555 0123',
            '001 415 555 0123',
            '  +14155550123  ',
        ]:
            self.assertEqual('+14155550123', normalize(raw), raw)

    def test_international(self):
        self.assertEqual('+447911123456', normalize('+44 7911 123456'))
        self.assertEqual('+447911123456', normalize('0044 7911 123456'))

    def test_invalid(self):
        for raw in [
            None,
            '',
            '555-0123',
            '0155550123',  # area code can't start with 0
            '4151550123',  # exchange can't start with 1
            '415555012',
            '+0123456789',
            '+1234',
            'call me',
            '415-555-01ab',
            '+1 (415) 555-0123 ext 4',
        ]:
            self.assertIsNone(normalize(raw), raw)

    def test_mask(self):
        self.assertEqual('+1 •••-•••-0123', mask('+14155550123'))
        self.assertEqual('•••3456', mask('+447911123456'))


if __name__ == '__main__':
    unittest.main()
