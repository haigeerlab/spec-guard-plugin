"""map-table-count-diagnostic: the module-table count error names where the tables are."""
import os
import tempfile
import unittest

from capability_map import MapError, parse_map
from module_stage import FRAGMENT_LIMIT

HEADER = ["| Module id | Responsibility | Depends on |", "| --- | --- | --- |"]


def table(*ids):
    return HEADER + ["| %s | x | — |" % module_id for module_id in ids]


class TableCountTests(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".md")
        os.close(handle)
        self.addCleanup(os.remove, self.path)

    def write(self, lines):
        with open(self.path, "w", encoding="utf-8") as out:
            out.write("\n".join(lines) + "\n")

    def error(self, validate_graph=True):
        with self.assertRaises(MapError) as caught:
            parse_map(self.path, validate_graph=validate_graph)
        return str(caught.exception)

    def test_three_tables_are_counted_with_header_lines(self):
        # Headers land on lines 3, 7 and 11.
        self.write(["# Map", ""] + table("alpha") + [""] + table("beta") + [""] + table("gamma")
                   + ["", "Build order: alpha → beta → gamma"])
        self.assertIn("必须恰好有一个模块表，找到 3 张：第 3、7、11 行", self.error())

    def test_more_than_five_tables_lists_five_and_says_more(self):
        lines = []
        for index in range(7):
            lines += table("m%d" % index) + [""]
        self.write(lines + ["Build order: m0"])
        message = self.error()
        self.assertIn("找到 7 张：第 1、5、9、13、17 行等", message)
        self.assertNotIn("21", message)

    def test_no_table_says_so(self):
        self.write(["# Map", "", "| alpha | x | — |", "", "Build order: alpha"])
        self.assertIn("没有模块表（需要恰好一张表头为 Module id 的表）", self.error())

    def test_fenced_table_is_not_counted_and_lines_do_not_shift(self):
        self.write(["# Map", "```", *table("example"), "```"] + table("alpha") + [""] + table("beta")
                   + ["", "Build order: alpha → beta"])
        # Fence occupies lines 2-6; real headers on lines 7 and 11.
        self.assertIn("找到 2 张：第 7、11 行", self.error())

    def test_history_mode_reports_the_same_way(self):
        self.write(table("alpha") + [""] + table("beta"))
        self.assertIn("找到 2 张：第 1、5 行", self.error(validate_graph=False))

    def test_history_mode_still_accepts_no_table(self):
        self.write(["# Map", "", "no table yet"])
        self.assertEqual(parse_map(self.path, validate_graph=False).rows, [])

    def test_worst_case_fits_the_stage_hint_limit(self):
        lines = []
        for index in range(120):
            lines += ["", "", "", "", "", "", "", ""] + table("m%d" % index)
        self.write(lines + ["Build order: m0"])
        self.assertLessEqual(len(self.error()), FRAGMENT_LIMIT)


if __name__ == "__main__":
    unittest.main(verbosity=1)
