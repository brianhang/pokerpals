import unittest

from utils.cents import to_numerical_string, to_string, from_string

class TestCents(unittest.TestCase):
    def test_to_numerical_string(self):
        s = to_numerical_string(0)
        self.assertEqual(s, "0.00")

        s = to_numerical_string(1)
        self.assertEqual(s, "0.01")

        s = to_numerical_string(10)
        self.assertEqual(s, "0.10")

        s = to_numerical_string(100)
        self.assertEqual(s, "1.00")

        s = to_numerical_string(99)
        self.assertEqual(s, "0.99")

        s = to_numerical_string(101)
        self.assertEqual(s, "1.01")

        s = to_numerical_string(1234)
        self.assertEqual(s, "12.34")

    def test_to_numerical_string_negative(self):
        s = to_numerical_string(-0)
        self.assertEqual(s, "0.00")

        s = to_numerical_string(-1)
        self.assertEqual(s, "-0.01")

        s = to_numerical_string(-10)
        self.assertEqual(s, "-0.10")

        s = to_numerical_string(-100)
        self.assertEqual(s, "-1.00")

        s = to_numerical_string(-99)
        self.assertEqual(s, "-0.99")

        s = to_numerical_string(-101)
        self.assertEqual(s, "-1.01")

        s = to_numerical_string(-1234)
        self.assertEqual(s, "-12.34")

    def test_to_string(self):
        s = to_string(0)
        self.assertEqual(s, "$0.00")

        s = to_string(1)
        self.assertEqual(s, "$0.01")

        s = to_string(10)
        self.assertEqual(s, "$0.10")

        s = to_string(100)
        self.assertEqual(s, "$1.00")

        s = to_string(99)
        self.assertEqual(s, "$0.99")

        s = to_string(101)
        self.assertEqual(s, "$1.01")

        s = to_string(1234)
        self.assertEqual(s, "$12.34")

    def test_to_string_negative(self):
        s = to_string(-0)
        self.assertEqual(s, "$0.00")

        s = to_string(-1)
        self.assertEqual(s, "-$0.01")

        s = to_string(-10)
        self.assertEqual(s, "-$0.10")

        s = to_string(-100)
        self.assertEqual(s, "-$1.00")

        s = to_string(-99)
        self.assertEqual(s, "-$0.99")

        s = to_string(-101)
        self.assertEqual(s, "-$1.01")

        s = to_string(-1234)
        self.assertEqual(s, "-$12.34")


    def test_from_string(self):
        c = from_string("0")
        self.assertEqual(c, 0)

        c = from_string("0.0")
        self.assertEqual(c, 0)

        c = from_string("0.00")
        self.assertEqual(c, 0)

        c = from_string(".12")
        self.assertEqual(c, 12)

        c = from_string("12.")
        self.assertEqual(c, 1200)

        c = from_string("20.99")
        self.assertEqual(c, 2099)

        c = from_string("20.00")
        self.assertEqual(c, 2000)

        c = from_string("20.01")
        self.assertEqual(c, 2001)

        c = from_string("20.2")
        self.assertEqual(c, 2020)


    def test_from_string_failure(self):
        c = from_string("abcd")
        self.assertEqual(c, None)

        c = from_string("0.a")
        self.assertEqual(c, None)

        c = from_string("a.0")
        self.assertEqual(c, None)

        c = from_string("0.-2")
        self.assertEqual(c, None)

        c = from_string("0.100")
        self.assertEqual(c, None)
