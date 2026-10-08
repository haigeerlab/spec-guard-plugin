"""module-insert preview/validation tests: every negative case leaves no file changed."""
import importlib.util
import io
import os
import stat
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock
from pathlib import Path

import module_stage
import proposal_promotion_proof
import test_proposal_promotion_proof as fixtures


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

    # ---- --interrupt (I2) ----

    def make_done(self, *ids):
        for module_id in ids:
            self.write("spec/%s.md" % module_id, "# Spec: %s\n" % module_id)
            self.write("tasks/%s/plan.md" % module_id, "# Plan: %s\n" % module_id)
            self.write("tasks/%s/todo.md" % module_id, "- [x] done\n")

    def make_half(self, module_id):
        self.write("spec/%s.md" % module_id, "# Spec: %s\n" % module_id)
        self.write("tasks/%s/plan.md" % module_id, "# Plan: %s\n" % module_id)
        self.write("tasks/%s/todo.md" % module_id, "- [x] one\n- [ ] two\n")

    def interrupt_main(self, args_extra, root=None):
        root = root or self.root
        args = ["--project", str(root), "--id", "delta", "--responsibility", "Fourth",
                "--depends-on", "—", "--anchor", "end"] + args_extra
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(args)
        return code, out.getvalue(), err.getvalue()

    def test_without_interrupt_half_done_rejection_mentions_flag(self):
        self.make_done("alpha", "beta")
        self.make_half("gamma")
        before = self.snapshot()
        with self.assertRaises(InsertError) as ctx:
            preview(self.root, "delta", "Fourth", "—", "end")
        self.assertIn("请先完成它", str(ctx.exception))
        self.assertIn("--interrupt", str(ctx.exception))
        self.assertEqual(before, self.snapshot())

    def test_interrupt_allows_half_done_and_reports_progress(self):
        self.make_done("alpha", "beta")
        self.make_half("gamma")
        result = preview(self.root, "delta", "Fourth", "—", "end", interrupt=True)
        self.assertEqual(result["interrupted"], {"id": "gamma", "checked": 1, "total": 2})
        report = module_insert.format_report(result)
        self.assertIn("gamma", report)
        self.assertIn("已勾 1/2", report)

    def test_interrupt_anchor_before_paused_module_new_becomes_current_no_hint(self):
        self.make_done("alpha", "beta")
        self.make_half("gamma")
        result = preview(self.root, "delta", "Fourth", "—", "after:beta", interrupt=True)
        self.assertEqual(result["new_current"], "delta")
        report = module_insert.format_report(result)
        self.assertIn("插入后当前模块将从 gamma 变为 delta", report)
        self.assertNotIn("activeModule", report)

    def test_interrupt_anchor_after_paused_module_hints_active_module(self):
        self.make_done("alpha", "beta")
        self.make_half("gamma")
        result = preview(self.root, "delta", "Fourth", "—", "end", interrupt=True)
        report = module_insert.format_report(result)
        self.assertIn("插入后当前模块仍是 `gamma`；请把 .agent/state.json 的 activeModule "
                      "改为 `delta` 再开始构建", report)

    def test_interrupt_active_module_still_paused_module_hints_active_module(self):
        self.make_done("alpha", "beta")
        self.make_half("gamma")
        self.write(".agent/state.json", '{"activeModule": "gamma"}\n')
        result = preview(self.root, "delta", "Fourth", "—", "after:beta", interrupt=True)
        self.assertEqual(result["new_current"], "gamma")
        self.assertIn("activeModule 改为 `delta`", module_insert.format_report(result))

    def test_interrupt_allowed_while_another_module_is_also_half_done(self):
        # Consumer-project shape: the current module waits on external facts while a later
        # module is being built in parallel; neither blocks an explicit interrupt.
        self.make_half("alpha")
        self.make_half("beta")
        self.write(".agent/state.json", '{"activeModule": "beta"}\n')
        result = preview(self.root, "delta", "Fourth", "—", "end", interrupt=True)
        self.assertEqual(result["interrupted"]["id"], "beta")
        self.assertNotIn("只支持一层插队", module_insert.format_report(result))
        module_insert.write(self.root, "delta", "Fourth", "—", "end", interrupt=True)
        self.assertIn("delta", module_insert.parse_map(self.map_path).order)

    def test_interrupt_does_not_bypass_other_validations(self):
        self.make_done("alpha", "beta")
        self.make_half("gamma")
        self.assert_no_write(lambda: preview(
            self.root, "delta", "Fourth", "ghost", "end", interrupt=True))
        self.assert_no_write(lambda: preview(
            self.root, "delta", "Fourth", "—", "after:ghost", interrupt=True))
        self.assert_no_write(lambda: preview(
            self.root, "Bad_Id", "Fourth", "—", "end", interrupt=True))

    def test_interrupt_is_noop_when_current_module_not_half_done(self):
        plain = preview(self.root, "delta", "Fourth", "—", "end")
        with_flag = preview(self.root, "delta", "Fourth", "—", "end", interrupt=True)
        self.assertIsNone(with_flag["interrupted"])
        self.assertEqual(module_insert.format_report(plain),
                         module_insert.format_report(with_flag))

    def test_cli_interrupt_confirm_writes_only_the_map(self):
        self.make_done("alpha", "beta")
        self.make_half("gamma")
        code, _, err = self.interrupt_main([])
        self.assertEqual(code, 1)
        self.assertIn("--interrupt", err)
        code, out, _ = self.interrupt_main(["--interrupt"])
        self.assertEqual(code, 0)
        self.assertIn("已勾 1/2", out)
        before = self.snapshot()
        code, out, _ = self.interrupt_main(["--interrupt", "--confirm"])
        self.assertEqual(code, 0)
        after = self.snapshot()
        self.assertEqual(set(before), set(after))
        changed = [k for k in before if before[k] != after[k]]
        self.assertEqual(changed, [str(self.map_path)])
        self.assertIn("delta", self.map_path.read_text(encoding="utf-8"))

    def test_interrupt_end_to_end_pause_and_resume(self):
        self.make_done("alpha", "beta")
        self.make_half("gamma")
        outcome = module_insert.write(self.root, "delta", "Urgent", "beta", "after:beta",
                                      interrupt=True)
        self.assertEqual(outcome["stage_module"], "delta")
        self.assertEqual(outcome["stage_hint"], "NEEDS_SPEC")
        self.assertEqual(outcome["stage_paused"], ("gamma", "BUILDING"))
        text = module_stage.describe(self.root)
        self.assertIn("NEEDS_SPEC", text)
        self.assertIn("Paused: `gamma`", text)
        self.make_done("delta")
        self.write(".agent/state.json", '{"activeModule": "delta"}\n')
        text = module_stage.describe(self.root)
        self.assertIn("MODULE_DONE", text)
        self.assertIn("resume paused module `gamma`", text)

    def test_stage_hint_paused_branch(self):
        self.assertEqual(module_insert.format_stage_hint(
            {"stage_module": "delta", "stage_hint": "MODULE_DONE", "stage_pending": ("gamma", "BUILDING"),
             "stage_paused": ("gamma", "BUILDING")}),
            "当前阶段提示: `delta` 处于 MODULE_DONE；被暂停的模块 `gamma`（BUILDING）应先恢复")

    def test_stage_hint_paused_branch_via_confirm(self):
        # alpha (done) is active, gamma is half done and paused: MODULE_DONE names it.
        self.make_done("alpha", "beta")
        self.make_half("gamma")
        self.write(".agent/state.json", '{"activeModule": "alpha"}\n')
        outcome = module_insert.write(self.root, "delta", "Fourth", "—", "end")
        self.assertEqual(outcome["stage_hint"], "MODULE_DONE")
        self.assertEqual(outcome["stage_paused"], ("gamma", "BUILDING"))
        self.assertIn("被暂停的模块 `gamma`（BUILDING）应先恢复",
                      module_insert.format_stage_hint(outcome))

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

    def test_non_separator_second_row_is_refused(self):
        # The strict parser's separator rule had no negative test (2026-10-08 audit F9):
        # an ordinary row under the header must not be accepted as the separator.
        self.write("spec/CAPABILITY-MAP.md",
                   MAP.replace("| --- | --- | --- |\n| alpha |", "| x | y | z |\n| alpha |"))
        before = self.snapshot()
        with self.assertRaises(InsertError) as caught:
            preview(self.root, "delta", "Fourth", "—", "end")
        self.assertIn("表头分隔行", str(caught.exception))
        self.assertEqual(before, self.snapshot())

    def test_current_module_selection_is_module_stage_project_stage(self):
        # 2026-10-08 audit F16: module-insert must not carry its own "current module" rule.
        import inspect
        import module_stage
        source = inspect.getsource(module_insert._current_module)
        self.assertIn("project_stage(", source)
        order = ["alpha", "beta", "gamma"]
        states = [module_stage.module_state(self.root, module_id) for module_id in order]
        expected = module_stage.project_stage(states, module_stage.active_module(self.root))[1]
        self.assertEqual(module_insert._current_module(self.root, order)[0], expected)

    def test_duplicate_id_is_refused(self):
        self.assert_no_write(lambda: preview(self.root, "beta", "Duplicate", "—", "end"))

    def test_invalid_non_kebab_id_is_refused(self):
        self.assert_no_write(lambda: preview(self.root, "Not_Kebab", "Fourth", "—", "end"))

    def test_trailing_newline_id_is_refused_by_the_id_gate(self):
        # `$` matches before a final newline, so the kebab-case gate must use
        # fullmatch; otherwise the id slips through and the downstream strict
        # re-validation blames the capability map instead of the id.
        before = self.snapshot()
        with self.assertRaises(InsertError) as caught:
            preview(self.root, "zeta\n", "Fourth", "—", "end")
        self.assertIn("id 不是合法的 kebab-case", str(caught.exception))
        self.assertEqual(before, self.snapshot())

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

    def run_cli(self, *extra):
        args = ["--project", str(self.root), "--id", "delta", "--responsibility", "Fourth",
                "--depends-on", "—", "--anchor", "end"] + list(extra)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(args)
        return code, out.getvalue(), err.getvalue()

    def test_existing_spec_file_is_allowed_and_previewed_with_a_stage_hint(self):
        self.write("spec/delta.md", "# Spec: delta\n")
        self.assertTrue(preview(self.root, "delta", "Fourth", "—", "end")["existing_spec"])
        before = self.snapshot()
        code, out, err = self.run_cli()
        self.assertEqual((code, err), (0, ""))
        self.assertIn("提示: spec/delta.md 已存在", out)
        self.assertIn("NEEDS_PLAN", out)
        self.assertEqual(before, self.snapshot())

    def test_no_existing_spec_has_no_hint_and_flag_is_false(self):
        self.assertFalse(preview(self.root, "delta", "Fourth", "—", "end")["existing_spec"])
        code, out, err = self.run_cli()
        self.assertNotIn("已存在", out)
        code, out, err = self.run_cli("--confirm")
        self.assertNotIn("已存在", out)

    def test_confirm_over_existing_spec_changes_only_the_map_and_reaches_needs_plan(self):
        self.make_done("alpha", "beta", "gamma")
        spec_text = "# Spec: delta\n\nReviewed elsewhere.\n"
        self.write("spec/delta.md", spec_text)
        before = self.snapshot()
        code, out, err = self.run_cli("--confirm")
        self.assertEqual((code, err), (0, ""))
        after = self.snapshot()
        changed = set(path for path in set(before) | set(after) if before.get(path) != after.get(path))
        self.assertEqual(changed, {str(self.map_path)})
        self.assertEqual((self.root / "spec" / "delta.md").read_text(encoding="utf-8"), spec_text)
        self.assertIn("当前阶段提示: `delta` 处于 NEEDS_PLAN", out)
        self.assertIn("提示: spec/delta.md 已存在", out)
        self.assertIn("NEEDS_PLAN", out.splitlines()[-1])

    def test_verify_artifacts_accepts_the_module_after_insertion_over_an_existing_spec(self):
        hook = Path(__file__).with_name("verify-artifacts.sh")
        self.write("spec/delta.md", "# Spec: delta\n")

        def verify():
            done = subprocess.run(
                ["/bin/bash", str(hook)], env=dict(os.environ, CLAUDE_PROJECT_DIR=str(self.root)),
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                universal_newlines=True)
            return done.stdout

        self.assertIn("能力图上没有的模块 spec: delta", verify())
        code, out, err = self.run_cli("--confirm")
        self.assertEqual(code, 0, err)
        self.assertNotIn("能力图上没有的模块 spec", verify())

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


GROUPED_MAP = fixtures.BASE_MAP.replace(
    "| alpha | Existing capability | — |",
    "| alpha | Existing capability | — |\n| beta | Sibling capability | — |").replace(
        "Build order: alpha", "Build order: alpha, beta")


class ProposalPromotionFixture(fixtures.PromotionFixture):
    """A real temp remote and consumer clone with a published Proposal for `gamma`."""
    skip_promotion = True
    base_map = None
    stage = "proposal-stage:accepted"

    def setUp(self):
        super().setUp()
        self.map_file = self.consumer / "spec" / "CAPABILITY-MAP.md"
        self.git(self.consumer, "config", "user.email", "test@example.invalid")
        self.git(self.consumer, "config", "user.name", "test")

    def write_proposal(self):
        super().write_proposal()
        if self.base_map is None:
            return
        path = self.seed / "spec/proposals/gamma.md"
        text = path.read_text(encoding="utf-8").replace(
            "| Build order | alpha |", "| Build order | alpha, beta |")
        placeholder = "0" * 64
        path.write_text(text.replace(
            text.split("revision=sha256:", 1)[1].split(" ", 1)[0], placeholder),
            encoding="utf-8")
        path.write_text(path.read_text(encoding="utf-8").replace(
            placeholder, fixtures.compute_revision(path)), encoding="utf-8")

    def reader(self, *ignored):
        return self.tracker(self.stage)

    def snapshot(self):
        return dict((str(path), path.read_bytes())
                    for path in self.consumer.rglob("*")
                    if path.is_file() and ".git" not in path.relative_to(self.consumer).parts)

    def run_main(self, *extra, proposal=("--proposal", "gamma"),
                 platform=("--platform", "github", "--target", "octo/spec-guard")):
        argv = ["--project", str(self.consumer)] + list(proposal) + list(platform) + list(extra)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(argv, tracker_reader=self.reader)
        return code, out.getvalue(), err.getvalue()

    def assert_rejected(self, *extra, message=None, **kwargs):
        before = self.snapshot()
        for flags in ((), ("--confirm",)):
            code, out, err = self.run_main(*(extra + flags), **kwargs)
            self.assertNotEqual(code, 0, (out, err))
            if message:
                self.assertIn(message, err)
            self.assertEqual(before, self.snapshot())
        return err


class ProposalPromotionTests(ProposalPromotionFixture):
    def base_commit(self):
        return self.git(self.seed, "rev-parse", "HEAD").strip()

    def test_preview_shows_declared_row_and_identity_without_writing(self):
        before = self.snapshot()
        code, out, err = self.run_main()
        self.assertEqual((code, err), (0, ""))
        self.assertIn("| gamma | Gamma. | alpha |", out)
        self.assertIn("Build order: alpha → gamma", out)
        self.assertIn("gamma", out.splitlines()[0])
        self.assertIn(self.publication.proposal.revision, out)
        self.assertIn(self.base_commit(), out)
        self.assertNotIn("本地存在", out)
        self.assertEqual(before, self.snapshot())

    def test_confirm_changes_only_the_capability_map(self):
        before = self.snapshot()
        code, out, err = self.run_main("--confirm")
        self.assertEqual((code, err), (0, ""))
        after = self.snapshot()
        changed = set(path for path in set(before) | set(after) if before.get(path) != after.get(path))
        self.assertEqual(changed, {str(self.map_file)})
        self.assertIn("| gamma | Gamma. | alpha |", self.map_file.read_text(encoding="utf-8"))

    def test_confirmed_promotion_pushed_to_the_remote_is_proved(self):
        base = self.base_commit()
        self.git(self.consumer, "fetch", "origin")
        self.git(self.consumer, "switch", "-c", "promote-gamma", base)
        code, out, err = self.run_main("--confirm")
        self.assertEqual((code, err), (0, ""))
        self.git(self.consumer, "add", "spec/CAPABILITY-MAP.md")
        self.git(self.consumer, "commit", "-m", "promote gamma")
        self.git(self.consumer, "push", "origin", "HEAD:trunk")
        proof = proposal_promotion_proof.prove_from_remote(
            self.consumer, "gamma", "github", "octo/spec-guard", tracker_reader=self.reader)
        self.assertEqual((proof.state, proof.module_id), ("proved", "gamma"))

    def test_string_proposal_flag_keeps_gitlab_numeric_target_as_int(self):
        seen = []

        def reader(proposal, platform, target):
            seen.append((platform, target))
            return self.tracker(self.stage)

        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            main(["--project", str(self.consumer), "--proposal", "gamma",
                  "--platform", "gitlab", "--target", "123"], tracker_reader=reader)
        self.assertEqual(seen[0], ("gitlab", 123))

    def test_field_flags_are_rejected_with_proposal(self):
        for flags in (("--id", "delta"), ("--responsibility", "Other"),
                      ("--depends-on", "alpha"), ("--anchor", "end")):
            with self.subTest(flags=flags):
                self.assert_rejected(*flags)

    def test_platform_and_target_are_required_with_proposal(self):
        self.assert_rejected(platform=("--target", "octo/spec-guard"))
        self.assert_rejected(platform=("--platform", "github"))
        self.assert_rejected(platform=())

    def test_half_done_current_module_needs_interrupt(self):
        (self.consumer / "tasks/alpha").mkdir(parents=True)
        (self.consumer / "tasks/alpha/todo.md").write_text("- [x] one\n- [ ] two\n",
                                                            encoding="utf-8")
        self.assert_rejected(message="--interrupt")
        code, out, err = self.run_main("--interrupt")
        self.assertEqual((code, err), (0, ""))

    def test_existing_module_spec_is_allowed_and_previewed_with_a_stage_hint(self):
        spec = self.consumer / "spec/gamma.md"
        spec.write_text("# Spec: gamma\n", encoding="utf-8")
        before = self.snapshot()
        code, out, err = self.run_main()
        self.assertEqual((code, err), (0, ""))
        self.assertIn("提示: spec/gamma.md 已存在", out)
        self.assertEqual(before, self.snapshot())
        code, out, err = self.run_main("--confirm")
        self.assertEqual((code, err), (0, ""))
        self.assertIn("spec/gamma.md 已存在", out)
        self.assertEqual(spec.read_text(encoding="utf-8"), "# Spec: gamma\n")

    def test_local_map_differing_from_base_commit_is_rejected_with_the_commit(self):
        self.map_file.write_text(self.map_file.read_text(encoding="utf-8") + "\nExtra.\n",
                                 encoding="utf-8")
        err = self.assert_rejected()
        self.assertIn(self.base_commit(), err)
        self.assertIn("git switch -c", err)

    def test_nothing_local_about_the_proposal_is_needed_or_warned(self):
        code, out, err = self.run_main()
        self.assertEqual(code, 0)
        self.assertNotIn("警告", out)

    def test_unknown_proposal_is_rejected_with_its_state(self):
        err = self.assert_rejected(proposal=("--proposal", "missing"), message="absent")
        self.assertIn("publication-absent", err)


class InReviewProposalPromotionTests(ProposalPromotionFixture):
    stage = "proposal-stage:in-review"

    def test_non_accepted_stage_is_rejected_with_state_and_diagnostic(self):
        err = self.assert_rejected(message="in-review")
        self.assertNotIn("Traceback", err)


class DriftedProposalPromotionTests(ProposalPromotionFixture):
    drift_map = fixtures.DRIFT_MAP

    def test_baseline_drift_is_rejected(self):
        self.assert_rejected(message="proposal-baseline-drifted")


class GroupedSegmentProposalPromotionTests(ProposalPromotionFixture):
    base_map = GROUPED_MAP

    def test_anchor_inside_a_grouped_segment_would_not_be_provable(self):
        self.assertEqual(self.publication.proposal.change.anchor, "after:alpha")
        self.assert_rejected(message="并行段")

    def test_without_proposal_the_same_insertion_is_still_allowed(self):
        result = preview(self.consumer, "gamma", "Gamma.", "alpha", "after:alpha")
        self.assertEqual(result["build_order_line"], "Build order: alpha, beta → gamma")


class ProposalArgumentTests(unittest.TestCase):
    def test_missing_fields_without_proposal_still_fail_in_argparse(self):
        err = io.StringIO()
        with redirect_stderr(err), self.assertRaises(SystemExit) as raised:
            main(["--id", "delta"])
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("the following arguments are required: --responsibility, --depends-on, "
                      "--anchor", err.getvalue())


if __name__ == "__main__":
    unittest.main()
