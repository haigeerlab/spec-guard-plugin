"""rules-at-nodes: the phase hint attaches the stop rules of the node the current module is at. No network."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import module_stage
from module_stage import describe, node_rules, stop_node
from test_checkout_role import View

SCRIPT = str(Path(__file__).with_name("module_stage.py"))
MAP = ("# Capability Map\n| Module id | Responsibility | Depends on |\n|---|---|---|\n"
       "| alpha | x | — |\n\nBuild order: alpha\n")
APPROVED_PLAN = "# Plan\n\n<!-- spec-guard: review approved -->\n"


class Project:
    """A one-module project; `files` maps relative paths to text."""

    def __init__(self, files, zh=True):
        self.files, self.zh = files, zh

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        files = {"spec/CAPABILITY-MAP.md": MAP, **self.files}
        if self.zh:
            config = json.loads(files.get(".agent/config.json", '{"version": 1}'))
            files[".agent/config.json"] = json.dumps(dict(config, artifactLanguage="zh-CN"))
        for rel, text in files.items():
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_text(text, encoding="utf-8")
        return self

    def __exit__(self, *exc):
        self.tmp.cleanup()


def building(todo, spec="# alpha\n", plan=APPROVED_PLAN):
    return {"spec/alpha.md": spec, "tasks/alpha/plan.md": plan, "tasks/alpha/todo.md": todo}


class StopNode(unittest.TestCase):
    def node(self, files, stage):
        with Project(files) as p:
            spec = module_stage.file_review_state(p.root / "spec/alpha.md", "spec")
            plan = module_stage.file_review_state(p.root / "tasks/alpha/plan.md", "plan")
            return stop_node(p.root, "alpha", stage, spec, plan)

    def test_needs_spec_is_the_spec_review(self):
        self.assertEqual(self.node({}, "NEEDS_SPEC"), "spec-review")

    def test_pending_spec_is_the_spec_review(self):
        pending = "# a\n\n<!-- spec-guard: review pending -->\n"
        self.assertEqual(self.node({"spec/alpha.md": pending}, "NEEDS_PLAN"), "spec-review")  # separate: the Plan waits
        combined = {"spec/alpha.md": pending, ".agent/config.json": json.dumps({"version": 1, "reviewCadence": "combined"})}
        self.assertEqual(self.node(combined, "NEEDS_PLAN"), "plan-review")  # combined: both go in one review
        files = building("- [ ] t\n- [ ] 最终验收（gate）\n", spec="# a\n\n<!-- spec-guard: review pending -->\n")
        self.assertEqual(self.node(files, "BUILDING"), "spec-review")

    def test_needs_plan_and_pending_plan_are_the_plan_review(self):
        self.assertEqual(self.node({"spec/alpha.md": "# a\n"}, "NEEDS_PLAN"), "plan-review")
        files = building("- [ ] t\n- [ ] 最终验收（gate）\n", plan="# Plan\n\n<!-- spec-guard: review pending -->\n")
        self.assertEqual(self.node(files, "BUILDING"), "plan-review")

    def test_a_middle_gate(self):
        files = building("- [x] t\n- [ ] 检查点 1（gate）：中途\n- [ ] t2\n- [ ] 最终验收（gate）\n")
        self.assertEqual(self.node(files, "BUILDING"), "mid-gate")

    def test_the_final_gate(self):
        files = building("- [x] t\n- [ ] 最终验收（gate）\n- [ ] 发版后的核对\n")
        self.assertEqual(self.node(files, "BUILDING"), "final-gate")

    def test_on_the_way_there_is_no_node(self):
        files = building("- [ ] t\n- [ ] 检查点 1（report）\n- [ ] 最终验收（gate）\n")
        self.assertIsNone(self.node(files, "BUILDING"))
        self.assertIsNone(self.node(files, "MODULE_DONE"))
        self.assertIsNone(self.node(files, "DONE"))

    def test_unreadable_todo_is_no_gate(self):
        files = building("- [ ] t\n")
        with Project(files) as p:
            (p.root / "tasks/alpha/todo.md").unlink()
            (p.root / "tasks/alpha/todo.md").mkdir()
            self.assertIsNone(stop_node(p.root, "alpha", "BUILDING", "none", "approved"))


class NodeRules(unittest.TestCase):
    def test_each_kind_reads_its_section(self):
        for kind, title in (("map-review", "## 能力图审阅"), ("spec-review", "## Spec 交审"), ("plan-review", "## Plan 交审"),
                            ("mid-gate", "## 中途 gate"), ("final-gate", "## 最终验收")):
            with self.subTest(kind=kind):
                text = node_rules(kind)
                self.assertTrue(text.startswith(title + "\n"), text[:40])
                self.assertNotIn("\n## ", text)

    def test_missing_file_section_or_kind_is_empty(self):
        self.assertEqual(node_rules("nonsense"), "")
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(module_stage, "NODE_RULES", Path(tmp) / "node-rules.md"):
                self.assertEqual(node_rules("final-gate"), "")
            (Path(tmp) / "node-rules.md").write_text("# 停点规则\n\n## 能力图审阅\n\n- x\n", encoding="utf-8")
            with mock.patch.object(module_stage, "NODE_RULES", Path(tmp) / "node-rules.md"):
                self.assertEqual(node_rules("final-gate"), "")
                self.assertIn("- x", node_rules("map-review"))

    def test_command_line(self):
        out = subprocess.run([sys.executable, "-B", SCRIPT, ".", "--node-rules", "map-review"], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertTrue(out.stdout.startswith("## 能力图审阅"))
        out = subprocess.run([sys.executable, "-B", SCRIPT, ".", "--node-rules", "nonsense"], capture_output=True, text=True)
        self.assertEqual((out.returncode, out.stdout), (0, ""))


class Describe(unittest.TestCase):
    def test_the_final_gate_carries_its_rules(self):
        with Project(building("- [x] t\n- [ ] 最终验收（gate）\n")) as p:
            out = describe(p.root)
        self.assertIn("\n\n停点规则（最终验收）：\n\n", out)
        self.assertIn("可以原样发送的完整文字", out)
        self.assertLess(out.index("建议下一步"), out.index("停点规则（最终验收）"))

    def test_english_label_with_the_chinese_section(self):
        with Project(building("- [x] t\n- [ ] 最终验收（gate）\n"), zh=False) as p:
            out = describe(p.root)
        self.assertIn("\n\nStop rules (final acceptance):\n\n## 最终验收", out)

    def test_on_the_way_there_is_nothing_attached(self):
        with Project(building("- [ ] t\n- [ ] 最终验收（gate）\n")) as p:
            out = describe(p.root)
        self.assertNotIn("停点规则（", out)

    def test_the_spec_review_when_no_spec_yet(self):
        with Project({}) as p:
            out = describe(p.root)
        self.assertIn("停点规则（Spec 交审）：", out)

    def test_without_the_file_the_output_is_unchanged(self):
        files = building("- [x] t\n- [ ] 最终验收（gate）\n")
        with Project(files) as p:
            with tempfile.TemporaryDirectory() as tmp:
                with mock.patch.object(module_stage, "NODE_RULES", Path(tmp) / "absent.md"):
                    bare = describe(p.root)
            full = describe(p.root)
        self.assertNotIn("停点规则", bare)
        self.assertTrue(full.startswith(bare))

    def test_role_views_attach_nothing(self):
        files = {"tasks/beta/plan.md": APPROVED_PLAN, "tasks/beta/todo.md": "- [x] a\n- [ ] 最终验收（gate）\n"}
        for role_text in ("module beta\n", "coordinator\n"):
            with self.subTest(role=role_text):
                with View(files, role_text) as v:
                    out = v.describe()
                self.assertNotIn("Stop rules", out)
                self.assertNotIn("停点规则", out)


BASELINE = {"docs/DOCUMENTATION-BASELINE.md": "| Concern | Authority | Status | Rationale |\n|---|---|---|---|\n"}


class DocumentationCheckLine(unittest.TestCase):
    """doc-chain (D15): at the final gate a project with a documentation baseline is told to run the check."""

    FINAL = "- [x] t\n- [ ] 最终验收（gate）\n"

    def test_serial_final_gate_in_both_languages_and_hosts(self):
        for zh, host, want in ((True, "claude", "- 文档核验：项目有文档基线，最终验收前跑 `/spec-guard:documentation-verification alpha`"),
                               (True, "codex", "- 文档核验：项目有文档基线，最终验收前跑 `$spec-guard-ops` 的 documentation 核验（模块 `alpha`）"),
                               (False, "claude", "- Documentation check: this project has a documentation baseline; before the "
                                                 "final acceptance run `/spec-guard:documentation-verification alpha`"),
                               (False, "codex", "run `$spec-guard-ops` documentation verification for `alpha`")):
            with self.subTest(zh=zh, host=host):
                with Project(dict(building(self.FINAL), **BASELINE), zh=zh) as p:
                    out = describe(p.root, host=host)
                self.assertIn(want, out)
        with Project(dict(building(self.FINAL), **BASELINE)) as p:
            out = describe(p.root)
        self.assertIn("「验收结果」", out)
        self.assertIn("attention 不卡验收", out)
        self.assertLess(out.index("- 文档核验："), out.index("建议下一步"))

    def test_no_baseline_leaves_the_output_unchanged(self):
        with Project(building(self.FINAL)) as p:
            bare = describe(p.root)
            (p.root / "docs").mkdir()
            (p.root / "docs/DOCUMENTATION-BASELINE.md").write_text(BASELINE["docs/DOCUMENTATION-BASELINE.md"],
                                                                   encoding="utf-8")
            full = describe(p.root)
        self.assertNotIn("- 文档核验：", bare)
        lines = [line for line in full.split("\n") if not line.startswith("- 文档核验：")]
        self.assertEqual("\n".join(lines), bare)

    def test_other_nodes_carry_no_line(self):
        for files in ({}, {"spec/alpha.md": "# a\n"}, building("- [ ] t\n- [ ] 最终验收（gate）\n"),
                      building("- [x] t\n- [ ] 检查点 1（gate）：中途\n- [ ] 最终验收（gate）\n"),
                      building("- [ ] t\n", plan="# Plan\n\n<!-- spec-guard: review pending -->\n")):
            with self.subTest(files=sorted(files)):
                with Project(dict(files, **BASELINE)) as p:
                    self.assertNotIn("- 文档核验：", describe(p.root))

    def test_module_checkout_gets_it_and_the_coordinator_does_not(self):
        files = dict(BASELINE, **{"tasks/beta/plan.md": APPROVED_PLAN, "tasks/beta/todo.md": self.FINAL})
        with View(files, "module beta\n") as v:
            out = v.describe()
        self.assertIn("- Documentation check: this project has a documentation baseline", out)
        self.assertIn("`/spec-guard:documentation-verification beta`", out)
        with View(files, "coordinator\n") as v:
            self.assertNotIn("Documentation check", v.describe())
        with View(dict(files, **{"tasks/beta/todo.md": "- [ ] a\n- [ ] 最终验收（gate）\n"}), "module beta\n") as v:
            self.assertNotIn("Documentation check", v.describe())


if __name__ == "__main__":
    unittest.main()
