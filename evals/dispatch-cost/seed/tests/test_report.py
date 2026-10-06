import unittest

from ledgerlite.ledger import Ledger
from ledgerlite.models import Entry
from ledgerlite.report import format_cents, monthly_report


def ledger_of(*rows):
    return Ledger([Entry(d, a, c, "") for d, a, c in rows])


class FormatCentsTests(unittest.TestCase):
    def test_positive(self):
        self.assertEqual(format_cents(1234), "12.34")

    def test_small(self):
        self.assertEqual(format_cents(5), "0.05")

    def test_negative(self):
        self.assertEqual(format_cents(-5), "-0.05")
        self.assertEqual(format_cents(-1234), "-12.34")

    def test_zero(self):
        self.assertEqual(format_cents(0), "0.00")


class MonthlyReportTests(unittest.TestCase):
    def test_basic_report(self):
        ledger = ledger_of(
            ("2026-01-05T12:00:00Z", "cash", 1234),
            ("2026-01-06T12:00:00Z", "bank", -500),
        )
        self.assertEqual(
            monthly_report(ledger, 2026, 1),
            "Report 2026-01\nbank: -5.00\ncash: 12.34\nTOTAL: 7.34",
        )

    def test_accounts_sorted(self):
        ledger = ledger_of(
            ("2026-01-05T12:00:00Z", "zeta", 100),
            ("2026-01-05T12:00:00Z", "alpha", 200),
        )
        lines = monthly_report(ledger, 2026, 1).splitlines()
        self.assertEqual(lines[1:3], ["alpha: 2.00", "zeta: 1.00"])

    def test_empty_month(self):
        self.assertEqual(
            monthly_report(Ledger(), 2026, 1), "Report 2026-01\nTOTAL: 0.00"
        )

    def test_other_months_excluded(self):
        ledger = ledger_of(
            ("2026-01-15T12:00:00Z", "cash", 100),
            ("2026-02-15T12:00:00Z", "cash", 900),
        )
        self.assertIn("TOTAL: 1.00", monthly_report(ledger, 2026, 1))

    def test_multiple_entries_same_account(self):
        ledger = ledger_of(
            ("2026-01-15T12:00:00Z", "cash", 250),
            ("2026-01-16T12:00:00Z", "cash", 750),
        )
        self.assertEqual(
            monthly_report(ledger, 2026, 1), "Report 2026-01\ncash: 10.00\nTOTAL: 10.00"
        )

    def test_zero_total_has_no_sign(self):
        ledger = ledger_of(
            ("2026-01-15T12:00:00Z", "cash", 250),
            ("2026-01-16T12:00:00Z", "cash", -250),
        )
        self.assertIn("cash: 0.00", monthly_report(ledger, 2026, 1))

    def test_two_decimals_always(self):
        ledger = ledger_of(("2026-01-15T12:00:00Z", "cash", 1000))
        self.assertIn("cash: 10.00", monthly_report(ledger, 2026, 1))


if __name__ == "__main__":
    unittest.main()
