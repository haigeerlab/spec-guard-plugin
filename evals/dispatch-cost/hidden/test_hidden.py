"""Grading tests. Target repo path comes from env LEDGERLITE_REPO."""
import os
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal

REPO = os.environ.get("LEDGERLITE_REPO")
HERE = os.path.dirname(os.path.abspath(__file__))
DEFECT_A = os.path.join(os.path.dirname(HERE), "defects", "defect_a.csv")


def run_py(code, *args, tz="UTC"):
    env = dict(os.environ)
    env["TZ"] = tz
    return subprocess.run(
        [sys.executable, "-c", code, *args], cwd=REPO, env=env,
        capture_output=True, text=True,
    )


def run_cli(*args, tz="UTC"):
    env = dict(os.environ)
    env["TZ"] = tz
    return subprocess.run(
        [sys.executable, "-m", "ledgerlite.cli", *args], cwd=REPO, env=env,
        capture_output=True, text=True,
    )


def write_csv(rows, five=True):
    """rows: (date, account, amount, memo, category)."""
    handle = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
    for date, account, amount, memo, category in rows:
        fields = [date, account, amount, memo] + ([category] if five else [])
        handle.write(",".join(fields) + "\n")
    handle.close()
    return handle.name


def cents_str(cents):
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(cents), 100)
    return "%s%d.%02d" % (sign, whole, frac)


def decimal_cents(text):
    return int(Decimal(text) * 100)


def report_lines(path, month="2026-01", tz="UTC", extra=()):
    proc = run_cli("report", "--csv", path, "--month", month, *extra, tz=tz)
    return proc, proc.stdout.splitlines()


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not REPO or not os.path.isdir(REPO):
            raise RuntimeError("set LEDGERLITE_REPO to the target repo")


class Task1FormatAmount(Base):
    def call(self, cents, code):
        proc = run_py(
            "import sys\nfrom ledgerlite.currency import format_amount\n"
            "print(format_amount(int(sys.argv[1]), sys.argv[2]), end='')",
            str(cents), code,
        )
        return proc

    def check(self, cents, code, expected):
        proc = self.call(cents, code)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, expected)

    def test_examples(self):
        self.check(123456, "USD", "$1,234.56")
        self.check(-5, "EUR", "-€0.05")
        self.check(0, "GBP", "£0.00")
        self.check(100000000, "USD", "$1,000,000.00")
        self.check(99, "USD", "$0.99")
        self.check(-123456789, "GBP", "-£1,234,567.89")

    def test_jpy(self):
        self.check(1234567, "JPY", "¥1,234,567")
        self.check(-5, "JPY", "-¥5")
        self.check(0, "JPY", "¥0")

    def test_unknown_code(self):
        proc = run_py(
            "from ledgerlite.currency import format_amount\n"
            "try:\n    format_amount(1, 'XXX')\nexcept ValueError:\n    print('VE')\n"
        )
        self.assertEqual(proc.stdout.strip(), "VE", proc.stderr)

    def test_non_int(self):
        proc = run_py(
            "from ledgerlite.currency import format_amount\n"
            "for v in (1.5, True):\n"
            "    try:\n        format_amount(v, 'USD')\n"
            "    except TypeError:\n        print('TE')\n"
        )
        self.assertEqual(proc.stdout.split(), ["TE", "TE"], proc.stderr)


class Task2CliMonth(Base):
    def setUp(self):
        self.path = write_csv([("2026-01-15T12:00:00Z", "cash", "1.00", "m", "misc")])
        self.addCleanup(os.unlink, self.path)

    def test_invalid_months_exit_2(self):
        for bad in ["2026-13", "2026-00", "26-01", "2026-1", "2026/01", "abc", ""]:
            proc = run_cli("report", "--csv", self.path, "--month", bad)
            self.assertEqual(proc.returncode, 2, "month=%r stderr=%r" % (bad, proc.stderr))
            self.assertTrue(proc.stderr.strip(), "no stderr for %r" % bad)
            self.assertNotIn("Traceback", proc.stderr)
            self.assertEqual(proc.stdout, "")

    def test_check_precedes_file_read(self):
        proc = run_cli("report", "--csv", "/no/such/file.csv", "--month", "2026-13")
        self.assertEqual(proc.returncode, 2, proc.stderr)

    def test_valid_month_ok(self):
        proc = run_cli("report", "--csv", self.path, "--month", "2026-01")
        self.assertEqual(proc.returncode, 0, proc.stderr)


class Task3Rounding(Base):
    def total_line(self, rows):
        path = write_csv([("2026-01-15T12:00:00Z", acct, amt, "m", "misc") for acct, amt in rows])
        self.addCleanup(os.unlink, path)
        proc, lines = report_lines(path)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return lines

    def expected(self, rows):
        by_acct = {}
        for acct, amt in rows:
            by_acct[acct] = by_acct.get(acct, 0) + decimal_cents(amt)
        return by_acct, sum(by_acct.values())

    def check_rows(self, rows):
        lines = self.total_line(rows)
        by_acct, total = self.expected(rows)
        self.assertEqual(lines[-1], "TOTAL: " + cents_str(total))
        for acct, cents in by_acct.items():
            self.assertIn("%s: %s" % (acct, cents_str(cents)), lines)

    def test_defect_a_file(self):
        with open(DEFECT_A, encoding="utf-8") as handle:
            rows = [tuple(l.rstrip("\n").split(",")[:3]) for l in handle if l.strip()]
        rows = [(a, amt) for (_d, a, amt) in rows]
        self.check_rows(rows)
        _, total = self.expected(rows)
        self.assertEqual(total, 3779)

    def test_tricky_set_1(self):
        self.check_rows([("a", "4.35"), ("a", "4.35"), ("a", "4.35"), ("b", "0.07"),
                         ("b", "0.14"), ("a", "33.33"), ("b", "67.89"), ("b", "1.15")])

    def test_tricky_set_2_signs_and_forms(self):
        self.check_rows([("a", "-0.29"), ("a", "-0.57"), ("b", "1.15"), ("b", "19.99"),
                         ("a", "-19.99"), ("b", "0.01"), ("a", "0.29"), ("b", "-1.15"),
                         ("a", "12"), ("b", "7.5"), ("a", "+0.58")])

    def test_tricky_set_3_many_small(self):
        self.check_rows([("a", "0.01")] * 37 + [("b", "0.57")] * 13 + [("a", "1.15")] * 9)

    def test_balance_exact(self):
        path = write_csv([("2026-01-15T12:00:00Z", "a", "0.29", "m", "x"),
                          ("2026-01-16T12:00:00Z", "a", "0.57", "m", "x"),
                          ("2026-01-17T12:00:00Z", "a", "19.99", "m", "x")])
        self.addCleanup(os.unlink, path)
        proc = run_cli("balance", "--csv", path, "--account", "a")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "a: 20.85")

    def test_invalid_amounts_rejected(self):
        for bad in ["1.005", "1e3", "nan", "inf", ".5", "5.", ""]:
            path = write_csv([("2026-01-15T12:00:00Z", "a", bad, "m", "x")])
            self.addCleanup(os.unlink, path)
            proc = run_cli("balance", "--csv", path, "--account", "a")
            self.assertEqual(proc.returncode, 1, "amount=%r out=%r" % (bad, proc.stdout))
            self.assertNotIn("Traceback", proc.stderr)
            self.assertIn("line 1", proc.stderr)


class Task4Category(Base):
    ROWS = [
        ("2026-01-05T12:00:00Z", "cash", "9.54", "a", "food"),
        ("2026-01-06T12:00:00Z", "cash", "8.00", "b", "rent"),
        ("2026-01-12T12:00:00Z", "bank", "19.00", "c", "fees"),
        ("2026-01-18T12:00:00Z", "bank", "1.25", "d", "interest"),
        ("2026-02-03T12:00:00Z", "cash", "100.00", "e", "food"),
    ]

    def setUp(self):
        self.path = write_csv(self.ROWS)
        self.addCleanup(os.unlink, self.path)

    def test_report_format(self):
        proc, _ = report_lines(self.path)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            proc.stdout,
            "Report 2026-01\nbank: 20.25\n  fees: 19.00\n  interest: 1.25\n"
            "cash: 17.54\n  food: 9.54\n  rent: 8.00\nTOTAL: 37.79\n",
        )

    def test_report_category_filter(self):
        proc, _ = report_lines(self.path, extra=("--category", "food"))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "Report 2026-01\ncash: 9.54\n  food: 9.54\nTOTAL: 9.54\n")

    def test_report_category_no_match(self):
        proc, _ = report_lines(self.path, extra=("--category", "Food"))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "Report 2026-01\nTOTAL: 0.00\n")

    def test_balance_filter(self):
        proc = run_cli("balance", "--csv", self.path, "--account", "cash", "--category", "food")
        self.assertEqual(proc.stdout.strip(), "cash: 109.54", proc.stderr)
        proc = run_cli("balance", "--csv", self.path, "--account", "cash")
        self.assertEqual(proc.stdout.strip(), "cash: 117.54", proc.stderr)

    def test_api(self):
        proc = run_py(
            "from ledgerlite.models import Entry\nfrom ledgerlite.ledger import Ledger\n"
            "l = Ledger()\n"
            "l.add(Entry('2026-01-05T12:00:00Z','cash',954,'a','food'))\n"
            "l.add(Entry('2026-01-06T12:00:00Z','cash',800,'b','rent'))\n"
            "print(l.balance('cash','food'), l.balance('cash'), len(l.entries('cash','rent')),"
            " l.categories())\n"
            "try:\n    Entry('2026-01-05T12:00:00Z','cash',1,'m')\nexcept TypeError:\n    print('TE')\n"
        )
        self.assertEqual(proc.stdout.splitlines(), ["954 1754 1 ['food', 'rent']", "TE"], proc.stderr)

    def test_four_field_line_rejected(self):
        path = write_csv([("2026-01-05T12:00:00Z", "cash", "1.00", "m", "x")], five=False)
        self.addCleanup(os.unlink, path)
        proc = run_cli("balance", "--csv", path, "--account", "cash")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("line 1", proc.stderr)


class Task5UtcMonths(Base):
    ZONES = ["Asia/Shanghai", "America/New_York"]
    CASES = [
        ("2026-01-31T23:30:00Z", "2026-01"),
        ("2026-01-31T16:00:00Z", "2026-01"),
        ("2025-12-31T23:59:59Z", "2025-12"),
        ("2025-12-31T16:30:00Z", "2025-12"),
        ("2026-02-01T00:00:00Z", "2026-02"),
        ("2026-03-08T07:30:00Z", "2026-03"),
        ("2026-03-01T03:00:00Z", "2026-03"),
        ("2026-01-31", "2026-01"),
        ("2026-01-01", "2026-01"),
    ]

    def test_month_key(self):
        code = "import sys\nfrom ledgerlite.timeutil import month_key\nprint(month_key(sys.argv[1]))"
        for tz in self.ZONES:
            for ts, want in self.CASES:
                proc = run_py(code, ts, tz=tz)
                self.assertEqual(proc.stdout.strip(), want, "tz=%s ts=%s %s" % (tz, ts, proc.stderr))

    def test_report_assignment(self):
        path = write_csv([("2026-01-31T23:30:00Z", "cash", "5.00", "m", "x"),
                          ("2026-02-01T00:00:00Z", "cash", "7.00", "m", "x")])
        self.addCleanup(os.unlink, path)
        for tz in self.ZONES:
            _, jan = report_lines(path, "2026-01", tz=tz)
            _, feb = report_lines(path, "2026-02", tz=tz)
            self.assertEqual(jan[-1], "TOTAL: 5.00", "tz=" + tz)
            self.assertEqual(feb[-1], "TOTAL: 7.00", "tz=" + tz)

    def test_year_boundary_report(self):
        path = write_csv([("2025-12-31T23:59:59Z", "cash", "3.00", "m", "x")])
        self.addCleanup(os.unlink, path)
        for tz in self.ZONES:
            _, dec = report_lines(path, "2025-12", tz=tz)
            _, jan = report_lines(path, "2026-01", tz=tz)
            self.assertEqual(dec[-1], "TOTAL: 3.00", "tz=" + tz)
            self.assertEqual(jan[-1], "TOTAL: 0.00", "tz=" + tz)


if __name__ == "__main__":
    unittest.main()
