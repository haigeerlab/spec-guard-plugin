"""module-insert preview/validation tests: every negative case leaves no file changed."""
import importlib.util
import io
import os
import stat
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock
from pathlib import Path


_spec = importlib.util.spec_from_file_location(
    "spec_guard_module_insert", Path(__file__).with_name("module-insert.py"))
module_insert = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(module_insert)

InsertError = module_insert.InsertError
preview = module_insert.preview
main = module_insert.main


FENCED_EXAMPLE_MAP = """# Capability Map: fixture

## 目标

Keep insertion facts explicit.

## 模块

示例（勿编辑）：

```markdown
| Module id | Responsibility | Depends on |
| --- | --- | --- |
| example-one | Example only | — |
| example-two | Example only | example-one |

Build order: example-one → example-two
```

| Module id | Responsibility | Depends on |
| --- | --- | --- |
| alpha | First module | — |
| beta | Second module | alpha |
| gamma | Third module | beta |

Build order: alpha, beta → gamma
"""


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

    # ---- confirm/write (Task 2) ----

    def fresh_project(self, map_text=None, files=None):
        """A second, independent temp project for confirm scenarios that need
        their own map mutation or missing map, so they don't interfere with
        self.root."""
        tmp = tempfile.TemporaryDirectory(prefix="sg-module-insert-confirm-")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        if map_text is not None:
            path = root / "spec" / "CAPABILITY-MAP.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(map_text, encoding="utf-8")
        for relative, content in (files or {}).items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return root

    def snapshot_of(self, root):
        state = {}
        for path in root.rglob("*"):
            if path.is_file():
                stat = path.stat()
                state[str(path)] = (stat.st_mtime_ns, path.read_bytes())
        return state

    def confirm_main(self, root, id_="delta", responsibility="Fourth",
                     depends_on="—", anchor="end"):
        args = ["--project", str(root), "--id", id_, "--responsibility", responsibility,
                "--depends-on", depends_on, "--anchor", anchor, "--confirm"]
        # Silence the CLI's own stdout/stderr so it doesn't clutter the test run.
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return main(args)

    def test_confirm_changes_only_the_map(self):
        before = self.snapshot()
        outcome = module_insert.write(self.root, "delta", "Fourth module", "—", "end")
        after = self.snapshot()
        self.assertEqual(set(after) - set(before), set())
        self.assertEqual(set(before) - set(after), set())
        self.assertNotEqual(before[str(self.map_path)], after[str(self.map_path)])
        for key, value in before.items():
            if key != str(self.map_path):
                self.assertEqual(after[key], value)
        self.assertEqual(outcome["map_path"], str(self.map_path))

    def test_confirm_via_cli_reports_written_map(self):
        exit_code = self.confirm_main(self.root, id_="delta", responsibility="Fourth module")
        self.assertEqual(exit_code, 0)
        self.assertFalse((self.root / "spec" / "delta.md").exists())
        self.assertIn("delta", self.map_path.read_text(encoding="utf-8"))

    def test_confirm_written_map_parses_strictly_and_preserves_digests(self):
        old_digest = module_insert.compute(str(self.map_path))
        module_insert.write(self.root, "delta", "Fourth module", "beta", "after:beta")
        # parse_map raises MapError if the written map is not strictly valid.
        module_insert.parse_map(self.map_path)
        new_digest = module_insert.compute(str(self.map_path))
        self.assertEqual(old_digest["goalDigest"], new_digest["goalDigest"])
        new_row_digests = dict((row["id"], row["rowDigest"]) for row in new_digest["rows"])
        for row in old_digest["rows"]:
            self.assertEqual(new_row_digests[row["id"]], row["rowDigest"])
        existing_ids = {"alpha", "beta", "gamma"}
        filtered = [module_id for module_id in new_digest["order"] if module_id in existing_ids]
        self.assertEqual(filtered, old_digest["order"])

    def test_confirm_new_current_module_reports_needs_spec(self):
        # Finish alpha and beta so gamma is current, then insert a module right
        # after beta (still before gamma): the new module has no spec, so it
        # becomes the new current module, and since --confirm writes only the
        # map (no spec skeleton), module_stage correctly reports NEEDS_SPEC.
        for module_id in ("alpha", "beta"):
            self.write("spec/%s.md" % module_id, "# Spec: %s\n" % module_id)
            self.write("tasks/%s/plan.md" % module_id, "# Plan: %s\n" % module_id)
            self.write("tasks/%s/todo.md" % module_id, "- [x] done\n")
        outcome = module_insert.write(self.root, "delta", "Fourth module", "—", "after:beta")
        self.assertEqual(outcome["stage_module"], "delta")
        self.assertEqual(outcome["stage_hint"], "NEEDS_SPEC")

    def finish_alpha_active(self, done=("alpha",)):
        for module_id in done:
            self.write("spec/%s.md" % module_id, "# Spec: %s\n" % module_id)
            self.write("tasks/%s/plan.md" % module_id, "# Plan: %s\n" % module_id)
            self.write("tasks/%s/todo.md" % module_id, "- [x] done\n")
        self.write(".agent/state.json", '{"activeModule": "alpha"}\n')

    def test_confirm_reports_module_done_when_active_module_done_and_others_pending(self):
        self.finish_alpha_active()
        outcome = module_insert.write(self.root, "delta", "Fourth module", "—", "end")
        self.assertEqual(outcome["stage_module"], "alpha")
        self.assertEqual(outcome["stage_hint"], "MODULE_DONE")
        # Build order is alpha, beta -> gamma -> delta; beta is the first unfinished.
        self.assertEqual(outcome["stage_pending"], ("beta", "NEEDS_SPEC"))

    def test_confirm_cli_prints_module_done_hint_naming_next_module(self):
        # Every existing module is done; activeModule still points at alpha.
        self.finish_alpha_active(done=("alpha", "beta", "gamma"))
        args = ["--project", str(self.root), "--id", "delta", "--responsibility", "Fourth",
                "--depends-on", "gamma", "--anchor", "end", "--confirm"]
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            self.assertEqual(main(args), 0)
        self.assertIn(
            "当前阶段提示: `alpha` 处于 MODULE_DONE；Build order 中下一个未完成模块是 `delta`（NEEDS_SPEC）",
            out.getvalue())
        self.assertNotIn("`alpha` 处于 DONE", out.getvalue())

    def test_stage_hint_line_all_done_and_plain_stage(self):
        # Insertion always adds an unfinished module, so the all-done path is not
        # reachable through write(); check the formatter directly.
        self.assertEqual(module_insert.format_stage_hint(
            {"stage_module": "alpha", "stage_hint": "DONE", "stage_pending": None}),
            "当前阶段提示: DONE")
        self.assertEqual(module_insert.format_stage_hint(
            {"stage_module": "delta", "stage_hint": "NEEDS_SPEC", "stage_pending": ("delta", "NEEDS_SPEC")}),
            "当前阶段提示: `delta` 处于 NEEDS_SPEC")

    def test_confirm_failed_replace_leaves_map_untouched_and_no_stray_temp_file(self):
        original = self.map_path.read_text(encoding="utf-8")

        with mock.patch.object(module_insert.os, "replace", side_effect=OSError("simulated replace failure")):
            with self.assertRaises(OSError):
                module_insert.write(self.root, "delta", "Fourth module", "—", "end")

        self.assertEqual(self.map_path.read_text(encoding="utf-8"), original)
        leftover = [path for path in self.map_path.parent.iterdir()
                   if path.name not in ("CAPABILITY-MAP.md",)]
        self.assertEqual(leftover, [], "temp file must be cleaned up after a failed os.replace")

    def test_confirm_missing_capability_map_is_refused(self):
        root = self.fresh_project(map_text=None)
        before = self.snapshot_of(root)
        exit_code = self.confirm_main(root)
        self.assertNotEqual(exit_code, 0)
        self.assertEqual(before, self.snapshot_of(root))

    def test_confirm_refuses_every_preview_negative_case(self):
        scenarios = [
            dict(name="half_done_current_module",
                files={"tasks/alpha/todo.md": "- [x] done\n- [ ] pending\n"}),
            dict(name="invalid_map",
                map_text=MAP.replace("Build order: alpha, beta → gamma", "")),
            dict(name="duplicate_id", id_="beta"),
            dict(name="invalid_non_kebab_id", id_="Not_Kebab"),
            dict(name="unknown_dependency", depends_on="ghost"),
            dict(name="dependency_after_anchor", depends_on="gamma", anchor="after:alpha"),
            dict(name="anchor_not_in_map", anchor="after:ghost"),
            dict(name="empty_responsibility", responsibility="   "),
            dict(name="multiline_responsibility", responsibility="line one\nline two"),
            dict(name="existing_spec_file", files={"spec/delta.md": "# Spec: delta\n"}),
            dict(name="duplicate_depends_on", depends_on="alpha,alpha"),
        ]
        for scenario in scenarios:
            with self.subTest(scenario["name"]):
                root = self.fresh_project(map_text=scenario.get("map_text", MAP),
                                          files=scenario.get("files"))
                before = self.snapshot_of(root)
                exit_code = self.confirm_main(
                    root, id_=scenario.get("id_", "delta"),
                    responsibility=scenario.get("responsibility", "Fourth"),
                    depends_on=scenario.get("depends_on", "—"),
                    anchor=scenario.get("anchor", "end"))
                self.assertNotEqual(exit_code, 0, scenario["name"])
                self.assertEqual(before, self.snapshot_of(root), scenario["name"])

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
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            exit_code = main(["--project", str(self.root), "--id", "beta",
                              "--responsibility", "Dup", "--depends-on", "—",
                              "--anchor", "end"])
        self.assertNotEqual(exit_code, 0)
        self.assertEqual(before, self.snapshot())

    # ---- Task 4: fenced examples must be skipped, new id must be present, mode preserved ----

    def test_preview_inserts_into_real_table_and_leaves_fenced_example_untouched(self):
        root = self.fresh_project(map_text=FENCED_EXAMPLE_MAP)
        before_text = (root / "spec" / "CAPABILITY-MAP.md").read_text(encoding="utf-8")
        result = preview(root, "delta", "Fourth module", "beta", "after:beta")
        # The real table gets the new row; the fenced example block is untouched.
        self.assertIn("| delta | Fourth module | beta |", result["new_text"])
        fence_start = before_text.index("```markdown")
        fence_end = before_text.index("```", fence_start + len("```markdown")) + len("```")
        fenced_block = before_text[fence_start:fence_end]
        self.assertIn(fenced_block, result["new_text"])
        self.assertNotIn("| delta | Fourth module | beta |", fenced_block)
        # The real Build order (not the fenced example one) gained the new step.
        self.assertTrue(result["build_order_line"].index("beta") <
                        result["build_order_line"].index("delta") <
                        result["build_order_line"].index("gamma"))

    def test_confirm_with_fenced_example_inserts_into_real_map_and_parses(self):
        root = self.fresh_project(map_text=FENCED_EXAMPLE_MAP)
        map_path = root / "spec" / "CAPABILITY-MAP.md"
        before_text = map_path.read_text(encoding="utf-8")
        outcome = module_insert.write(root, "delta", "Fourth module", "beta", "after:beta")
        after_text = map_path.read_text(encoding="utf-8")
        # capability-map.py / parse_map now lists the new id.
        parsed = module_insert.parse_map(map_path)
        self.assertIn("delta", [row.module_id for row in parsed.rows])
        self.assertIn("delta", parsed.order)
        # The fenced example block is byte-identical to before.
        fence_start = before_text.index("```markdown")
        fence_end = before_text.index("```", fence_start + len("```markdown")) + len("```")
        fenced_block_before = before_text[fence_start:fence_end]
        self.assertIn(fenced_block_before, after_text)
        self.assertNotIn("| delta | Fourth module | beta |", fenced_block_before)
        self.assertEqual(outcome["map_path"], str(map_path))

    def test_assert_new_module_present_rejects_missing_row(self):
        # Unit-test the defensive assertion helper directly: a parsed map that
        # lacks the new id in its module rows must be rejected.
        class FakeRow(object):
            def __init__(self, module_id):
                self.module_id = module_id

        class FakeParsed(object):
            rows = [FakeRow("alpha"), FakeRow("beta")]
            order = ["alpha", "beta"]

        with self.assertRaises(InsertError):
            module_insert._assert_new_module_present(FakeParsed(), "delta")

    def test_assert_new_module_present_rejects_missing_from_build_order(self):
        class FakeRow(object):
            def __init__(self, module_id):
                self.module_id = module_id

        class FakeParsed(object):
            rows = [FakeRow("alpha"), FakeRow("beta"), FakeRow("delta")]
            order = ["alpha", "beta"]  # delta missing from Build order

        with self.assertRaises(InsertError):
            module_insert._assert_new_module_present(FakeParsed(), "delta")

    def test_assert_new_module_present_accepts_when_present(self):
        class FakeRow(object):
            def __init__(self, module_id):
                self.module_id = module_id

        class FakeParsed(object):
            rows = [FakeRow("alpha"), FakeRow("delta")]
            order = ["alpha", "delta"]

        module_insert._assert_new_module_present(FakeParsed(), "delta")

    def test_preview_refuses_and_writes_nothing_when_new_id_would_be_missing(self):
        # Defensive negative: even if the new-map parse somehow omitted the new
        # id, preview (and therefore --confirm, which re-runs preview) must
        # reject rather than reporting success. Simulate this by making the
        # tmp-file parse (the one used to validate the *new* map) return a map
        # without the new id, while the parse of the *old* map on disk behaves
        # normally.
        root = self.fresh_project(map_text=MAP)
        map_path = root / "spec" / "CAPABILITY-MAP.md"
        before = self.snapshot_of(root)
        real_parse_map = module_insert.parse_map

        class FakeRow(object):
            def __init__(self, module_id):
                self.module_id = module_id

        class FakeParsed(object):
            rows = [FakeRow("alpha"), FakeRow("beta"), FakeRow("gamma")]
            order = ["alpha", "beta", "gamma"]  # missing "delta"
            goal = None

        def fake_parse_map(path, *args, **kwargs):
            if str(path) == str(map_path):
                return real_parse_map(path, *args, **kwargs)
            return FakeParsed()

        with mock.patch.object(module_insert, "parse_map", side_effect=fake_parse_map):
            with self.assertRaises(InsertError):
                preview(root, "delta", "Fourth module", "—", "end")
        self.assertEqual(before, self.snapshot_of(root))

    def test_confirm_refuses_and_writes_nothing_when_new_id_would_be_missing(self):
        root = self.fresh_project(map_text=MAP)
        map_path = root / "spec" / "CAPABILITY-MAP.md"
        before = self.snapshot_of(root)
        real_parse_map = module_insert.parse_map

        class FakeRow(object):
            def __init__(self, module_id):
                self.module_id = module_id

        class FakeParsed(object):
            rows = [FakeRow("alpha"), FakeRow("beta"), FakeRow("gamma")]
            order = ["alpha", "beta", "gamma"]  # missing "delta"
            goal = None

        def fake_parse_map(path, *args, **kwargs):
            if str(path) == str(map_path):
                return real_parse_map(path, *args, **kwargs)
            return FakeParsed()

        with mock.patch.object(module_insert, "parse_map", side_effect=fake_parse_map):
            exit_code = self.confirm_main(root, id_="delta", responsibility="Fourth module")
        self.assertNotEqual(exit_code, 0)
        self.assertEqual(before, self.snapshot_of(root))

    def test_confirm_preserves_original_file_mode(self):
        root = self.fresh_project(map_text=MAP)
        map_path = root / "spec" / "CAPABILITY-MAP.md"
        os.chmod(map_path, 0o644)
        before_mode = stat.S_IMODE(os.stat(map_path).st_mode)
        self.assertEqual(before_mode, 0o644)
        exit_code = self.confirm_main(root, id_="delta", responsibility="Fourth module")
        self.assertEqual(exit_code, 0)
        after_mode = stat.S_IMODE(os.stat(map_path).st_mode)
        self.assertEqual(after_mode, 0o644)


if __name__ == "__main__":
    unittest.main()
