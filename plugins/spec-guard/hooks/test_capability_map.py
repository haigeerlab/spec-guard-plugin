"""map-table-count-diagnostic: the module-table count error names where the tables are."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

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



class DeclaredGroupsTests(unittest.TestCase):
    """map-startable: comma groups survive as declared_groups; order_groups and the CLI output stay serial."""

    def parse(self, order, validate_graph=True):
        handle, path = tempfile.mkstemp(suffix=".md")
        os.close(handle)
        self.addCleanup(os.remove, path)
        with open(path, "w", encoding="utf-8") as out:
            out.write("\n".join(["# Map", ""] + table("a", "b", "c", "d") + ["", order]) + "\n")
        return path, parse_map(path, validate_graph=validate_graph)

    def test_commas_are_kept_in_declared_groups(self):
        _, parsed = self.parse("Build order: a → b, `c` → d")
        self.assertEqual(parsed.declared_groups, [["a"], ["b", "c"], ["d"]])
        self.assertEqual(parsed.order_groups, [["a"], ["b"], ["c"], ["d"]])
        self.assertEqual(parsed.order, ["a", "b", "c", "d"])

    def test_without_commas_each_group_has_one_module(self):
        _, parsed = self.parse("Build order: a -> b -> c -> d")
        self.assertEqual(parsed.declared_groups, [["a"], ["b"], ["c"], ["d"]])

    def test_history_mode_has_none(self):
        _, parsed = self.parse("", validate_graph=False)
        self.assertIsNone(parsed.declared_groups)

    def test_cli_output_is_unchanged(self):
        path, _ = self.parse("Build order: a → b, c → d")
        done = subprocess.run([sys.executable, "-B", str(Path(__file__).with_name("capability-map.py")), path],
                              capture_output=True, text=True, timeout=20)
        result = json.loads(done.stdout)
        self.assertEqual(set(result), {"ok", "modules", "orderGroups", "order"})
        self.assertEqual(result["orderGroups"], [["a"], ["b"], ["c"], ["d"]])

if __name__ == "__main__":
    unittest.main(verbosity=1)
