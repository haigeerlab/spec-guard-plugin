import os
import tempfile
import unittest

from ledgerlite.parser import parse_amount, parse_file, parse_line, parse_lines


class ParseAmountTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(parse_amount("12.34"), 1234)
        self.assertEqual(parse_amount("10.50"), 1050)
        self.assertEqual(parse_amount("5.00"), 500)

    def test_whole_number(self):
        self.assertEqual(parse_amount("12"), 1200)

    def test_negative(self):
        self.assertEqual(parse_amount("-3.25"), -325)

    def test_whitespace(self):
        self.assertEqual(parse_amount("  7.5 "), 750)

    def test_zero(self):
        self.assertEqual(parse_amount("0.00"), 0)

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            parse_amount("  ")

    def test_garbage_rejected(self):
        with self.assertRaises(ValueError):
            parse_amount("abc")

    def test_nan_rejected(self):
        with self.assertRaises(ValueError):
            parse_amount("nan")


class ParseLineTests(unittest.TestCase):
    def test_basic(self):
        e = parse_line("2026-01-05,cash,12.34,lunch")
        self.assertEqual(e.date, "2026-01-05")
        self.assertEqual(e.account, "cash")
        self.assertEqual(e.amount_cents, 1234)
        self.assertEqual(e.memo, "lunch")

    def test_timestamp_date(self):
        e = parse_line("2026-01-31T23:30:00Z,bank,1.50,x")
        self.assertEqual(e.date, "2026-01-31T23:30:00Z")

    def test_empty_memo(self):
        self.assertEqual(parse_line("2026-01-05,cash,1.00,").memo, "")

    def test_too_few_fields(self):
        with self.assertRaises(ValueError):
            parse_line("2026-01-05,cash,1.00")

    def test_bad_date(self):
        with self.assertRaises(ValueError):
            parse_line("yesterday,cash,1.00,m")

    def test_empty_account(self):
        with self.assertRaises(ValueError):
            parse_line("2026-01-05,,1.00,m")

    def test_bad_amount_mentions_line(self):
        with self.assertRaises(ValueError) as ctx:
            parse_line("2026-01-05,cash,xx,m", 7)
        self.assertIn("line 7", str(ctx.exception))


class ParseLinesTests(unittest.TestCase):
    def test_skips_blank_and_comments(self):
        lines = [
            "# header\n",
            "\n",
            "2026-01-05,cash,1.00,a\n",
            "2026-01-06,bank,2.00,b\n",
        ]
        entries = parse_lines(lines)
        self.assertEqual([e.account for e in entries], ["cash", "bank"])

    def test_error_carries_line_number(self):
        with self.assertRaises(ValueError) as ctx:
            parse_lines(["2026-01-05,cash,1.00,a\n", "bad\n"])
        self.assertIn("line 2", str(ctx.exception))

    def test_empty_input(self):
        self.assertEqual(parse_lines([]), [])


class ParseFileTests(unittest.TestCase):
    def test_reads_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.csv")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("2026-01-05,cash,1.00,a\n2026-01-06,cash,2.00,b\n")
            entries = parse_file(path)
        self.assertEqual(len(entries), 2)
        self.assertEqual(sum(e.amount_cents for e in entries), 300)

    def test_missing_file(self):
        with self.assertRaises(OSError):
            parse_file("/nonexistent/definitely/missing.csv")


if __name__ == "__main__":
    unittest.main()
