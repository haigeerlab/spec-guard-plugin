import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest

from ledgerlite import cli

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CSV = (
    "2026-01-05T12:00:00Z,cash,12.34,lunch,food\n"
    "2026-01-06T12:00:00Z,bank,-5.00,fee,fees\n"
    "2026-02-10T12:00:00Z,cash,1.00,later,food\n"
)


def run_main(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = cli.main(argv)
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "data.csv")
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write(CSV)

    def test_report(self):
        code, out, _ = run_main(["report", "--csv", self.path, "--month", "2026-01"])
        self.assertEqual(code, 0)
        self.assertEqual(out, "Report 2026-01\nbank: -5.00\n  fees: -5.00\ncash: 12.34\n  food: 12.34\nTOTAL: 7.34\n")

    def test_balance(self):
        code, out, _ = run_main(["balance", "--csv", self.path, "--account", "cash"])
        self.assertEqual(code, 0)
        self.assertEqual(out, "cash: 13.34\n")

    def test_balance_unknown_account(self):
        code, out, _ = run_main(["balance", "--csv", self.path, "--account", "x"])
        self.assertEqual(code, 0)
        self.assertEqual(out, "x: 0.00\n")

    def test_missing_file(self):
        code, _, err = run_main(["report", "--csv", "/no/such.csv", "--month", "2026-01"])
        self.assertEqual(code, 1)
        self.assertIn("cannot read", err)

    def test_bad_csv_line(self):
        bad = os.path.join(self.tmp.name, "bad.csv")
        with open(bad, "w", encoding="utf-8") as handle:
            handle.write("not,enough\n")
        code, _, err = run_main(["balance", "--csv", bad, "--account", "cash"])
        self.assertEqual(code, 1)
        self.assertIn("line 1", err)

    def test_missing_required_argument_exits_2(self):
        code, _, _ = run_main(["report", "--csv", self.path])
        self.assertEqual(code, 2)

    def test_month_validation_exits_2(self):
        for bad in ["2026-13", "2026-00", "26-01", "2026-1", "2026/01", "abc", ""]:
            code, out, err = run_main(["report", "--csv", "/no/such.csv", "--month", bad])
            self.assertEqual(code, 2, bad)
            self.assertEqual(out, "")
            self.assertNotIn("Traceback", err)
            self.assertIn(repr(bad), err)

    def test_month_valid_boundaries(self):
        for good in ["2026-01", "2026-12"]:
            code, _, _ = run_main(["report", "--csv", self.path, "--month", good])
            self.assertEqual(code, 0)

    def test_report_category_filter(self):
        code, out, _ = run_main(
            ["report", "--csv", self.path, "--month", "2026-01", "--category", "food"])
        self.assertEqual(code, 0)
        self.assertEqual(out, "Report 2026-01\ncash: 12.34\n  food: 12.34\nTOTAL: 12.34\n")

    def test_balance_category_filter(self):
        code, out, _ = run_main(
            ["balance", "--csv", self.path, "--account", "cash", "--category", "Food"])
        self.assertEqual((code, out), (0, "cash: 0.00\n"))
        code, out, _ = run_main(
            ["balance", "--csv", self.path, "--account", "cash", "--category", "food"])
        self.assertEqual((code, out), (0, "cash: 13.34\n"))

    def test_report_empty_category(self):
        code, out, _ = run_main(
            ["report", "--csv", self.path, "--month", "2026-01", "--category", "zzz"])
        self.assertEqual((code, out), (0, "Report 2026-01\nTOTAL: 0.00\n"))

    def test_task3_repro_total(self):
        path = os.path.join(self.tmp.name, "t3.csv")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(
                "2026-01-05T12:00:00Z,cash,0.29,coffee,food\n"
                "2026-01-09T12:00:00Z,cash,12.50,lunch,food\n"
                "2026-01-12T12:00:00Z,bank,19.00,fee,fees\n"
                "2026-01-18T12:00:00Z,bank,1.25,interest,interest\n"
                "2026-01-22T12:00:00Z,cash,7.75,market,rent\n"
                "2026-01-27T12:00:00Z,cash,-3.00,refund,food\n")
        code, out, _ = run_main(["report", "--csv", path, "--month", "2026-01"])
        self.assertEqual(code, 0)
        self.assertEqual(out, "Report 2026-01\nbank: 20.25\n  fees: 19.00\n  interest: 1.25\n"
                              "cash: 17.54\n  food: 9.79\n  rent: 7.75\nTOTAL: 37.79\n")

    def test_bad_amount_exits_1(self):
        path = os.path.join(self.tmp.name, "b.csv")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("2026-01-05,cash,1.005,x,y\n")
        code, _, err = run_main(["balance", "--csv", path, "--account", "cash"])
        self.assertEqual(code, 1)
        self.assertIn("line 1", err)

    def test_month_end_utc_any_tz(self):
        path = os.path.join(self.tmp.name, "m.csv")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("2026-01-31T23:30:00Z,cash,1.00,x,y\n")
        for tz in ["Asia/Shanghai", "America/New_York"]:
            env = dict(os.environ, TZ=tz)
            for month, want in [("2026-01", "TOTAL: 1.00"), ("2026-02", "TOTAL: 0.00")]:
                proc = subprocess.run(
                    [sys.executable, "-m", "ledgerlite.cli", "report", "--csv", path,
                     "--month", month], cwd=ROOT, env=env, capture_output=True, text=True)
                self.assertIn(want, proc.stdout, (tz, month))

    def test_module_entry_point(self):
        proc = subprocess.run(
            [sys.executable, "-m", "ledgerlite.cli", "balance",
             "--csv", self.path, "--account", "bank"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "bank: -5.00\n")


if __name__ == "__main__":
    unittest.main()
