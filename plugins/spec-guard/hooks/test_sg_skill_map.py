"""sg-skill-map (autopilot module 7): the phase hint names the skills at each fixed gate of a flow v2 module, the
todo keeps a Skill log that /map --json parses for the hub's report, and the final gate reminds an empty log.
No network; every project is a temporary directory."""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import module_stage  # noqa: E402
import test_flow_v2 as tfv  # noqa: E402
from module_stage import DOC_SECTIONS  # noqa: E402

OVERALL = "<!-- spec-guard: overall-design spec/overall/x.md -->"
FINAL = "- [ ] 最终验收（gate）：推送、开 PR、验收并同时问合并\n"


def design(interface="不涉及", impact="- 新增 `src/a/new.py`"):
    fill = {"影响面": impact, "接口和数据改动": interface}
    return "# 技术方案：a\n\n" + "".join("## %s\n\n%s\n\n" % (n, fill.get(n, "不涉及")) for n in DOC_SECTIONS["design"]["zh"])


class Stages(unittest.TestCase):
    """Builds module `a` at each position the skill map knows."""

    def setUp(self):
        self.project = tfv.Project().__enter__()
        self.addCleanup(self.project.__exit__, None, None, None)

    def at(self, position):
        p = self.project
        if position == "review-first":
            tfv.pending_spec(p, reviewed=False)
        elif position == "confirm":
            tfv.pending_spec(p)
        elif position == "overall":
            tfv.approved_spec(p, extra=OVERALL + "\n")
        elif position == "design-write":
            tfv.approved_spec(p)
        elif position == "design-wait":
            tfv.approved_spec(p)
            p.write("tasks/a/design.md", design(interface="- 新字段 `x`"))
        elif position == "none":
            tfv.approved_spec(p)
            p.write(".agent/config.json", json.dumps({"version": 1, "takeover": "design"}))
            p.write("tasks/a/design.md", design())
        elif position in ("build", "final"):
            tfv.approved_spec(p)
            p.write(".agent/config.json", json.dumps({"version": 1, "takeover": "design"}))
            p.write("tasks/a/design.md", design())
            p.write("tasks/a/regression.md", "# r\n")
            p.write("tasks/a/plan.md", "# p\n")
            p.write("tasks/a/todo.md", ("- [ ] Task 1：t\n" if position == "build" else "- [x] Task 1：t\n") + FINAL)
        return module_stage.module_state(p.root, "a")["stage"]

    def position(self, stage):
        return module_stage.skill_position(self.project.root, "a", stage)

    def hint(self, zh=True):
        route = json.loads((self.project.root / ".agent" / "config.json").read_text(encoding="utf-8")) \
            if (self.project.root / ".agent" / "config.json").exists() else {"version": 1}
        route.pop("version", None)
        route.pop("artifactLanguage", None)
        return tfv.hint(self.project, zh=zh, route=route)


class Position(Stages):
    """R1: one position at a time, in order; none for an old module or a stage without a fixed gate."""

    def test_positions(self):
        for setup, expected in (("review-first", "review-first"), ("confirm", "confirm"), ("overall", "overall"),
                                ("design-write", "design"), ("design-wait", "design"), ("none", None),
                                ("build", "build"), ("final", "final")):
            with self.subTest(setup=setup):
                self.setUp()
                stage = self.at(setup)
                self.assertEqual(self.position(stage), expected, stage)

    def test_old_module(self):
        self.project.write("spec/a.md", "# a\n")
        self.assertIsNone(self.position("NEEDS_PLAN"))


class SkillLine(Stages):
    """R2: exactly one Skill line where there is a position, naming its skills and when to record them."""

    def test_lines(self):
        for setup, names, record in (
                ("review-first", ("`delegate:review`", "宿主全新子会话"), "写 todo 时补进"),
                ("confirm", ("interview-me", "idea-refine", "spec-driven-development"), "写 todo 时补进"),
                ("overall", ("source-driven-development", "artifact-diagramming"), "写 todo 时补进"),
                ("design-write", ("security-and-hardening", "deprecation-and-migration（涉及数据迁移时）"), "写 todo 时补进"),
                ("build", ("incremental-implementation", "test-driven-development", "先在已装插件里找"), "记进 todo"),
                ("final", ("browser-testing-with-devtools", "git-workflow-and-versioning"), "记进 todo")):
            with self.subTest(setup=setup):
                self.setUp()
                self.at(setup)
                text = self.hint()
                lines = [line for line in text.splitlines() if line.startswith("- Skill：")]
                self.assertEqual(len(lines), 1, text)
                for name in names:
                    self.assertIn(name, lines[0])
                self.assertIn(record, lines[0])
                if setup == "final":
                    self.assertNotIn("incremental-implementation", lines[0])

    def test_english(self):
        self.at("build")
        self.assertEqual(sum(1 for line in self.hint(zh=False).splitlines() if line.startswith("- Skill: ")), 1)

    def test_no_line(self):
        self.at("none")
        self.assertNotIn("- Skill：", self.hint())
        self.setUp()
        self.project.write("spec/a.md", "# a\n")
        self.assertNotIn("- Skill", self.hint())


class RoleView(Stages):
    """R3: a module checkout gets its module's Skill line; review-first -> confirm changes its facts."""

    def facts(self):
        cmd = module_stage.commands(None, True)
        by_id = {"a": module_stage.module_state(self.project.root, "a")}
        return (module_stage.role_view(self.project.root, "module", "a", by_id, cmd, "", True)[0],
                module_stage._role_facts(self.project.root, "module", "a", by_id, cmd, True))

    def test_role(self):
        self.at("review-first")
        lines, first = self.facts()
        self.assertTrue(any(line.startswith("- Skill：") and "delegate:review" in line for line in lines))
        self.setUp()
        self.at("confirm")
        lines, second = self.facts()
        self.assertTrue(any(line.startswith("- Skill：") and "interview-me" in line for line in lines))
        self.assertNotEqual(first, second)
        self.assertEqual(first[-1], "review-first")
        self.assertEqual(second[-1], "confirm")


LOG = """- [ ] Task 1：t

## Skill 使用记录

- 实现：incremental-implementation、test-driven-development
- 审查：delegate:review
- 画图：没有现成的 skill，按常规做法来。
- Diagram: No existing skill, done the usual way
- 混合：a，b,c；d;e、a
- 没有冒号
- ：x
- 空：
```
- 代码块：x
```
  - 缩进：x

## 证据

- 证据里的一行：不算
"""


class SkillLog(Stages):
    """R4: the Skill log is parsed by the first colon, the no-existing-skill phrase first, five separators."""

    def log(self):
        return module_stage.skill_log(self.project.root, "a")

    def test_parse(self):
        self.at("build")
        self.project.write("tasks/a/todo.md", LOG)
        self.assertEqual(self.log(), [
            {"place": "实现", "skills": ["incremental-implementation", "test-driven-development"], "none": False},
            {"place": "审查", "skills": ["delegate:review"], "none": False},
            {"place": "画图", "skills": [], "none": True},
            {"place": "Diagram", "skills": [], "none": True},
            {"place": "混合", "skills": ["a", "b", "c", "d", "e"], "none": False}])

    def test_english_heading_missing_section_and_old_module(self):
        self.at("build")
        self.project.write("tasks/a/todo.md", "- [ ] t\n\n## Skill log\n\n- Build: incremental-implementation\n")
        self.assertEqual(self.log(), [{"place": "Build", "skills": ["incremental-implementation"], "none": False}])
        self.project.write("tasks/a/todo.md", "- [ ] t\n")
        self.assertEqual(self.log(), [])
        self.setUp()
        self.project.write("spec/a.md", "# a\n")
        self.assertIsNone(self.log())

    def test_in_the_map(self):
        self.at("build")
        self.project.write("tasks/a/todo.md", LOG)
        from map_view import build
        row = next(m for m in build(self.project.root)["modules"] if m["id"] == "a")
        self.assertEqual(row["skillLog"], self.log())


class TodoProgress(Stages):
    """R5: the Skill log section does not change the todo's progress, stage or next gate."""

    def test_unchanged(self):
        self.at("build")
        before = (module_stage.module_state(self.project.root, "a"), module_stage.next_gate(self.project.root, "a"))
        path = self.project.root / "tasks" / "a" / "todo.md"
        path.write_text(path.read_text(encoding="utf-8") + "\n## Skill 使用记录\n\n- 实现：tdd\n", encoding="utf-8")
        after = (module_stage.module_state(self.project.root, "a"), module_stage.next_gate(self.project.root, "a"))
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
