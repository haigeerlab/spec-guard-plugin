import unittest

from ledgerlite import currency


class ConvertTests(unittest.TestCase):
    def test_identity(self):
        for code in currency.supported():
            self.assertEqual(currency.convert(12345, code, code), 12345)

    def test_usd_to_eur(self):
        # 1 EUR = 1.08 USD, so 108 USD cents = 100 EUR cents
        self.assertEqual(currency.convert(108, "USD", "EUR"), 100)

    def test_eur_to_usd(self):
        self.assertEqual(currency.convert(100, "EUR", "USD"), 108)

    def test_usd_to_gbp(self):
        self.assertEqual(currency.convert(12700, "USD", "GBP"), 10000)

    def test_usd_to_jpy(self):
        # 1 JPY = 0.67 USD cents, so 100 USD cents = 149.25... -> 149 yen
        self.assertEqual(currency.convert(100, "USD", "JPY"), 149)

    def test_jpy_to_usd(self):
        self.assertEqual(currency.convert(1000, "JPY", "USD"), 670)

    def test_negative_symmetry(self):
        self.assertEqual(
            currency.convert(-100, "USD", "JPY"), -currency.convert(100, "USD", "JPY")
        )

    def test_rounds_half_away_from_zero(self):
        # 1 USD cent -> 0.925... EUR cent rounds to 1
        self.assertEqual(currency.convert(1, "USD", "EUR"), 1)
        self.assertEqual(currency.convert(-1, "USD", "EUR"), -1)

    def test_zero(self):
        self.assertEqual(currency.convert(0, "USD", "EUR"), 0)

    def test_unknown_code(self):
        with self.assertRaises(ValueError):
            currency.convert(100, "USD", "XXX")
        with self.assertRaises(ValueError):
            currency.convert(100, "ABC", "USD")

    def test_non_int(self):
        with self.assertRaises(TypeError):
            currency.convert(1.5, "USD", "EUR")


class MetadataTests(unittest.TestCase):
    def test_supported_sorted(self):
        self.assertEqual(currency.supported(), ["EUR", "GBP", "JPY", "USD"])

    def test_decimals(self):
        self.assertEqual(currency.decimals("USD"), 2)
        self.assertEqual(currency.decimals("JPY"), 0)

    def test_decimals_unknown(self):
        with self.assertRaises(ValueError):
            currency.decimals("XXX")


if __name__ == "__main__":
    unittest.main()
