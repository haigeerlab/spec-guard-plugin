import unittest

from ledgerlite.models import Account, Entry


class AccountTests(unittest.TestCase):
    def test_name_is_stripped(self):
        self.assertEqual(Account("  cash ").name, "cash")

    def test_equality_and_hash(self):
        self.assertEqual(Account("cash"), Account("cash"))
        self.assertEqual(len({Account("cash"), Account("cash")}), 1)
        self.assertNotEqual(Account("cash"), Account("bank"))

    def test_str_and_repr(self):
        self.assertEqual(str(Account("cash")), "cash")
        self.assertEqual(repr(Account("cash")), "Account('cash')")

    def test_rejects_empty_name(self):
        with self.assertRaises(ValueError):
            Account("   ")

    def test_rejects_comma(self):
        with self.assertRaises(ValueError):
            Account("a,b")

    def test_rejects_non_string(self):
        with self.assertRaises(TypeError):
            Account(5)

    def test_not_equal_to_other_types(self):
        self.assertNotEqual(Account("cash"), "cash")


class EntryTests(unittest.TestCase):
    def test_fields(self):
        e = Entry("2026-01-05", "cash", 1234, "lunch")
        self.assertEqual(e.date, "2026-01-05")
        self.assertEqual(e.account, "cash")
        self.assertEqual(e.amount_cents, 1234)
        self.assertEqual(e.memo, "lunch")

    def test_memo_defaults_to_empty(self):
        self.assertEqual(Entry("2026-01-05", "cash", 1).memo, "")

    def test_equality(self):
        a = Entry("2026-01-05", "cash", 100, "x")
        b = Entry("2026-01-05", "cash", 100, "x")
        self.assertEqual(a, b)
        self.assertEqual(hash(a), hash(b))
        self.assertNotEqual(a, Entry("2026-01-05", "cash", 101, "x"))

    def test_strips_whitespace(self):
        e = Entry(" 2026-01-05 ", " cash ", 5, " m ")
        self.assertEqual(e.as_tuple(), ("2026-01-05", "cash", 5, "m"))

    def test_amount_must_be_int(self):
        with self.assertRaises(TypeError):
            Entry("2026-01-05", "cash", 1.5, "")
        with self.assertRaises(TypeError):
            Entry("2026-01-05", "cash", True, "")

    def test_requires_date_and_account(self):
        with self.assertRaises(ValueError):
            Entry("", "cash", 1, "")
        with self.assertRaises(ValueError):
            Entry("2026-01-05", " ", 1, "")

    def test_negative_amounts_allowed(self):
        self.assertEqual(Entry("2026-01-05", "cash", -250, "").amount_cents, -250)

    def test_repr_mentions_fields(self):
        text = repr(Entry("2026-01-05", "cash", 7, "m"))
        self.assertIn("amount_cents=7", text)
        self.assertIn("account='cash'", text)


if __name__ == "__main__":
    unittest.main()
