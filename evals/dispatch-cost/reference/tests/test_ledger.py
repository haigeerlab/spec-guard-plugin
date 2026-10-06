import unittest

from ledgerlite.ledger import Ledger
from ledgerlite.models import Entry


def make():
    ledger = Ledger()
    ledger.add(Entry("2026-01-05T12:00:00Z", "cash", 1234, "a", "c1"))
    ledger.add(Entry("2026-01-15T12:00:00Z", "cash", -234, "b", "c1"))
    ledger.add(Entry("2026-01-20T12:00:00Z", "bank", 500, "c", "c2"))
    ledger.add(Entry("2026-02-10T12:00:00Z", "cash", 1000, "d", "c1"))
    return ledger


class LedgerTests(unittest.TestCase):
    def test_len_and_entries(self):
        ledger = make()
        self.assertEqual(len(ledger), 4)
        self.assertEqual(len(ledger.entries()), 4)

    def test_entries_by_account(self):
        ledger = make()
        self.assertEqual([e.memo for e in ledger.entries("cash")], ["a", "b", "d"])
        self.assertEqual(ledger.entries("nobody"), [])

    def test_entries_returns_copy(self):
        ledger = make()
        ledger.entries().clear()
        self.assertEqual(len(ledger), 4)

    def test_balance(self):
        ledger = make()
        self.assertEqual(ledger.balance("cash"), 2000)
        self.assertEqual(ledger.balance("bank"), 500)

    def test_balance_unknown_account(self):
        self.assertEqual(make().balance("nobody"), 0)

    def test_category_filters(self):
        ledger = make()
        self.assertEqual(ledger.categories(), ["c1", "c2"])
        self.assertEqual(ledger.balance("cash", "c1"), 2000)
        self.assertEqual(ledger.balance("cash", "c2"), 0)
        self.assertEqual([e.memo for e in ledger.entries(category="c2")], ["c"])
        self.assertEqual(ledger.entries("bank", "c1"), [])

    def test_utc_month_in_other_tz(self):
        ledger = Ledger([Entry("2026-01-31T23:30:00Z", "cash", 1, "", "x")])
        self.assertEqual(len(ledger.entries_in_month(2026, 1)), 1)

    def test_total(self):
        self.assertEqual(make().total(), 2500)

    def test_accounts_sorted(self):
        self.assertEqual(make().accounts(), ["bank", "cash"])

    def test_entries_in_month(self):
        ledger = make()
        jan = ledger.entries_in_month(2026, 1)
        self.assertEqual([e.memo for e in jan], ["a", "b", "c"])
        feb = ledger.entries_in_month(2026, 2)
        self.assertEqual([e.memo for e in feb], ["d"])

    def test_entries_in_empty_month(self):
        self.assertEqual(make().entries_in_month(2025, 12), [])

    def test_add_rejects_non_entry(self):
        with self.assertRaises(TypeError):
            Ledger().add(("2026-01-05", "cash", 1, ""))

    def test_constructor_accepts_entries(self):
        ledger = Ledger([Entry("2026-01-05T12:00:00Z", "cash", 1, "", "c1")])
        self.assertEqual(len(ledger), 1)

    def test_extend(self):
        ledger = Ledger()
        ledger.extend([Entry("2026-01-05T12:00:00Z", "cash", 1, "", "c1"),
                       Entry("2026-01-06T12:00:00Z", "cash", 2, "", "c1")])
        self.assertEqual(ledger.balance("cash"), 3)


if __name__ == "__main__":
    unittest.main()
