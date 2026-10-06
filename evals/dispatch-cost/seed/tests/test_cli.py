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
    "2026-01-05T12:00:00Z,cash,12.34,lunch\n"
    "2026-01-06T12:00:00Z,bank,-5.00,fee\n"
    "2026-02-10T12:00:00Z,cash,1.00,later\n"
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
        self.assertEqual(out, "Report 2026-01\nbank: -5.00\ncash: 12.34\nTOTAL: 7.34\n")

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
