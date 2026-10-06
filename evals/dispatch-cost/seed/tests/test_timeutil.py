import unittest
from datetime import timezone

from ledgerlite import timeutil


class ParseTimestampTests(unittest.TestCase):
    def test_full_timestamp(self):
        dt = timeutil.parse_timestamp("2026-01-31T23:30:00Z")
        self.assertEqual((dt.year, dt.month, dt.day), (2026, 1, 31))
        self.assertEqual((dt.hour, dt.minute, dt.second), (23, 30, 0))
        self.assertEqual(dt.utcoffset().total_seconds(), 0)
        self.assertIs(dt.tzinfo, timezone.utc)

    def test_plain_date_is_midnight_utc(self):
        dt = timeutil.parse_timestamp("2026-03-04")
        self.assertEqual((dt.hour, dt.minute), (0, 0))

    def test_invalid_shapes(self):
        for bad in ["", "2026-1-5", "2026-01-31 10:00:00", "2026-01-31T10:00:00",
                    "tomorrow", "2026-01-31T10:00:00+08:00"]:
            with self.assertRaises(ValueError, msg=bad):
                timeutil.parse_timestamp(bad)

    def test_invalid_calendar_values(self):
        with self.assertRaises(ValueError):
            timeutil.parse_timestamp("2026-13-01")
        with self.assertRaises(ValueError):
            timeutil.parse_timestamp("2026-02-30")
        with self.assertRaises(ValueError):
            timeutil.parse_timestamp("2026-01-01T25:00:00Z")

    def test_non_string(self):
        with self.assertRaises(ValueError):
            timeutil.parse_timestamp(None)


class MonthKeyTests(unittest.TestCase):
    # Mid-month noon UTC stays in the same month in every real time zone.
    def test_mid_month(self):
        self.assertEqual(timeutil.month_key("2026-01-15T12:00:00Z"), "2026-01")

    def test_other_months(self):
        self.assertEqual(timeutil.month_key("2026-07-15T12:00:00Z"), "2026-07")
        self.assertEqual(timeutil.month_key("2025-12-15T12:00:00Z"), "2025-12")

    def test_zero_padded(self):
        self.assertEqual(timeutil.month_key("2026-03-15T12:00:00Z"), "2026-03")


class MiscTests(unittest.TestCase):
    def test_days_in_month(self):
        self.assertEqual(timeutil.days_in_month(2026, 2), 28)
        self.assertEqual(timeutil.days_in_month(2024, 2), 29)
        self.assertEqual(timeutil.days_in_month(2026, 12), 31)

    def test_to_iso_roundtrip(self):
        text = "2026-01-31T23:30:00Z"
        self.assertEqual(timeutil.to_iso(timeutil.parse_timestamp(text)), text)


if __name__ == "__main__":
    unittest.main()
