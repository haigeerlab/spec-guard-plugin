"""module-insert preview/validation tests: every negative case leaves no file changed."""
import importlib.util
import os
import tempfile
import unittest
from unittest import mock
from pathlib import Path


_spec = importlib.util.spec_from_file_location(
    "spec_guard_module_insert", Path(__file__).with_name("module-insert.py"))
module_insert = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(module_insert)

InsertError = module_insert.InsertError
preview = module_insert.preview
main = module_insert.main


MAP = """# Capability Map: fixture

## 目标

Keep insertion facts explicit.

## 模块

| Module id | Responsibility | Depends on |
| --- | --- | --- |
| alpha | First module | — |
| beta | Second module | alpha |
| gamma | Third module | beta |

Build order: alpha, beta → gamma
"""


class ModuleInsertTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sg-module-insert-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.map_path = self.root / "spec" / "CAPABILITY-MAP.md"
        self.write("spec/CAPABILITY-MAP.md", MAP)

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def snapshot(self):
        """A file-path -> (mtime_ns, content) snapshot, for a strict no-write check."""
        state = {}
        for path in self.root.rglob("*"):
            if path.is_file():
                stat = path.stat()
                state[str(path)] = (stat.st_mtime_ns, path.read_bytes())
        return state

    def assert_no_write(self, action):
        before = self.snapshot()
        with self.assertRaises(InsertError):
            action()
        self.assertEqual(before, self.snapshot())

    # ---- positive cases ----

    def test_after_anchor_inserts_row_and_build_order_step(self):
        result = preview(self.root, "delta", "Fourth module", "beta", "after:beta")
        self.assertEqual(result["row_text"], "| delta | Fourth module | beta |")
        self.assertIn("delta", result["build_order_line"])
        self.assertTrue(result["build_order_line"].index("beta") <
                        result["build_order_line"].index("delta") <
                        result["build_order_line"].index("gamma"))
        # preview is read-only
        self.assertEqual(self.map_path.read_text(encoding="utf-8"), MAP)

    def test_end_anchor_appends_row_and_build_order_step(self):
        result = preview(self.root, "delta", "Fourth module", "—", "end")
        lines = result["diff"]
        self.assertTrue(any(line.startswith("+| delta |") for line in lines))
        self.assertTrue(result["build_order_line"].endswith("delta"))

    def test_anchor_inside_comma_group_inserts_after_whole_group(self):
        # alpha and beta are declared as a comma group ("alpha, beta → gamma");
        # anchoring on alpha must land the new module after the whole group, not
        # spliced in the middle of it.
        result = preview(self.root, "delta", "Fourth module", "alpha", "after:alpha")
        self.assertEqual(result["build_order_line"],
                         "Build order: alpha, beta → delta → gamma")

    def test_planned_but_not_started_current_module_is_allowed(self):
        self.write("tasks/alpha/todo.md", "- [ ] one\n- [ ] two\n")
        result = preview(self.root, "delta", "Fourth module", "—", "end")
        self.assertEqual(result["old_current"], "alpha")

    def test_fully_done_current_module_is_allowed(self):
        self.write("tasks/alpha/todo.md", "- [x] one\n- [x] two\n")
        result = preview(self.root, "delta", "Fourth module", "—", "end")
        self.assertIsNotNone(result)

    def test_preview_writes_nothing(self):
        before = self.snapshot()
        preview(self.root, "delta", "Fourth module", "—", "end")
        self.assertEqual(before, self.snapshot())

    def test_proposal_same_id_warning(self):
        self.write("spec/proposals/delta.md", "# Proposal: delta\n")
        result = preview(self.root, "delta", "Fourth module", "—", "end")
        self.assertTrue(result["proposal_conflict"])

    def test_no_proposal_conflict_when_absent(self):
        result = preview(self.root, "delta", "Fourth module", "—", "end")
        self.assertFalse(result["proposal_conflict"])

    def test_current_module_is_stable_when_inserted_after_it(self):
        # alpha is NEEDS_SPEC (no spec/plan yet) and stays the first non-DONE
        # module whether or not a new module lands after it.
        result = preview(self.root, "delta", "Fourth module", "—", "after:alpha")
        self.assertEqual(result["old_current"], "alpha")
        self.assertEqual(result["old_current"], result["new_current"])

    def test_current_module_changes_when_new_module_lands_before_it(self):
        # Finish alpha and beta (spec + plan + no open items) so gamma is the
        # current module, then insert a new module right after beta (still
        # before gamma in Build order): the new module has no spec yet, so it
        # becomes the new first non-DONE module ahead of gamma.
        for module_id in ("alpha", "beta"):
            self.write("spec/%s.md" % module_id, "# Spec: %s\n" % module_id)
            self.write("tasks/%s/plan.md" % module_id, "# Plan: %s\n" % module_id)
            self.write("tasks/%s/todo.md" % module_id, "- [x] done\n")
        result = preview(self.root, "delta", "Fourth module", "—", "after:beta")
        self.assertEqual(result["old_current"], "gamma")
        self.assertEqual(result["new_current"], "delta")

    # ---- negative cases: each must leave every file untouched ----

    def test_current_module_half_done_is_refused(self):
        self.write("tasks/alpha/todo.md", "- [x] done\n- [ ] pending\n")
        self.assert_no_write(lambda: preview(self.root, "delta", "Fourth", "—", "end"))

    def test_missing_capability_map_is_refused(self):
        self.map_path.unlink()
        self.assert_no_write(lambda: preview(self.root, "delta", "Fourth", "—", "end"))

    def test_invalid_capability_map_is_refused(self):
        self.write("spec/CAPABILITY-MAP.md", MAP.replace("Build order: alpha, beta → gamma", ""))
        self.assert_no_write(lambda: preview(self.root, "delta", "Fourth", "—", "end"))

    def test_duplicate_id_is_refused(self):
        self.assert_no_write(lambda: preview(self.root, "beta", "Duplicate", "—", "end"))

    def test_invalid_non_kebab_id_is_refused(self):
        self.assert_no_write(lambda: preview(self.root, "Not_Kebab", "Fourth", "—", "end"))

    def test_unknown_dependency_is_refused(self):
        self.assert_no_write(lambda: preview(self.root, "delta", "Fourth", "ghost", "end"))

    def test_dependency_placed_after_anchor_is_refused(self):
        # gamma sits after alpha in Build order; anchoring after alpha but
        # depending on gamma would place the dependency after the new module.
        self.assert_no_write(lambda: preview(self.root, "delta", "Fourth", "gamma", "after:alpha"))

    def test_anchor_id_not_in_map_is_refused(self):
        self.assert_no_write(lambda: preview(self.root, "delta", "Fourth", "—", "after:ghost"))

    def test_empty_responsibility_is_refused(self):
        self.assert_no_write(lambda: preview(self.root, "delta", "   ", "—", "end"))

    def test_multiline_responsibility_is_refused(self):
        self.assert_no_write(lambda: preview(self.root, "delta", "line one\nline two", "—", "end"))

    def test_existing_spec_file_is_refused(self):
        self.write("spec/delta.md", "# Spec: delta\n")
        self.assert_no_write(lambda: preview(self.root, "delta", "Fourth", "—", "end"))

    def test_confirm_is_rejected_in_task_one(self):
        before = self.snapshot()
        exit_code = main(["--project", str(self.root), "--id", "delta",
                          "--responsibility", "Fourth", "--depends-on", "—",
                          "--anchor", "end", "--confirm"])
        self.assertNotEqual(exit_code, 0)
        self.assertEqual(before, self.snapshot())

    def test_duplicate_depends_on_is_refused(self):
        self.assert_no_write(lambda: preview(self.root, "delta", "Fourth", "alpha,alpha", "end"))

    def test_reordering_existing_build_order_is_refused(self):
        # 表格行序不变、只打乱 Build order 的插入必须被拒：Proposal 评审按 Build order 判断先后。
        self.write("spec/CAPABILITY-MAP.md", MAP.replace("| beta | Second module | alpha |", "| beta | Second module | — |")
                   .replace("| gamma | Third module | beta |", "| gamma | Third module | — |")
                   .replace("Build order: alpha, beta → gamma", "Build order: alpha → beta → gamma"))
        real = module_insert._build_order_segments
        with mock.patch.object(module_insert, "_build_order_segments", lambda line: list(reversed(real(line)))):
            with self.assertRaisesRegex(InsertError, "Build order 中的相对顺序"):
                preview(self.root, "delta", "Fourth module", "—", "end")

    def test_main_reports_failure_without_raising(self):
        before = self.snapshot()
        exit_code = main(["--project", str(self.root), "--id", "beta",
                          "--responsibility", "Dup", "--depends-on", "—",
                          "--anchor", "end"])
        self.assertNotEqual(exit_code, 0)
        self.assertEqual(before, self.snapshot())


if __name__ == "__main__":
    unittest.main()
