"""sg-design-outline (autopilot module 6): the design outline by case -- a new project or module adds four sections,
an important requirement compares two approaches, a multi-module requirement draws its module interfaces.
No network; every project is a temporary directory, a git repository where batches matter."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import module_stage  # noqa: E402
from module_stage import DOC_SECTIONS  # noqa: E402
import test_flow_v2 as tfv  # noqa: E402
import test_important_requirement as tir  # noqa: E402

OVERALL = "<!-- spec-guard: overall-design spec/overall/x.md -->"


def spec(tier="normal", extra=()):
    return "# a\n\n<!-- spec-guard: flow v2 tier=%s -->\n%s\n## 目标\n\n不涉及\n\n## 并行边界\n\n- 独占：`src/%%s/`\n" % (
        tier, "".join(line + "\n" for line in extra))


class GitProject(unittest.TestCase):
    """A git project with a capability map; `insert` adds modules in one commit like a batch insert."""
    git, config, risk, insert = tir.Important.git, tir.Important.config, tir.Important.risk, tir.Important.insert

    def setUp(self):
        tir.Important.setUp(self)
        self.config({})
        (self.root / ".github" / "autopr" / "risk-paths.json").unlink()
        module_stage._BATCH_CACHE.clear()

    def add(self, *ids, tier="normal", extra=()):
        self.insert(*ids, specs={module: (spec(tier, extra) % module).replace("# a", "# %s" % module) for module in ids})

    def case(self, module="alpha"):
        return module_stage.design_outline_case(self.root, module)


class OutlineCase(GitProject):
    """R1: new only for exactly one valid overall-design line; important by the effective tier; cross by batch."""

    def test_new(self):
        self.add("alpha", extra=(OVERALL,))
        self.assertTrue(self.case()["new"])
        for lines in ((OVERALL, OVERALL), ("<!-- spec-guard: overall-design spec/x.md -->",),
                      ("<!-- spec-guard: overall-design -->",), ()):
            with self.subTest(lines=lines):
                (self.root / "spec" / "alpha.md").write_text(spec(extra=lines) % "alpha", encoding="utf-8")
                self.assertFalse(self.case()["new"])

    def test_broken_prefix_line_is_invalid(self):
        self.add("alpha", extra=("<!-- spec-guard: overall-design -->",))
        self.assertEqual(module_stage.overall_design(self.root, "alpha"), {"path": None, "status": "invalid"})

    def test_important_and_short_tiers(self):
        self.add("alpha", tier="important")
        self.assertTrue(self.case()["important"])
        self.add("beta", tier="small")
        self.assertIsNone(self.case("beta"))
        (self.root / "spec" / "gamma.md").write_text("# gamma\n", encoding="utf-8")
        self.assertIsNone(self.case("gamma"))

    def test_cross(self):
        self.add("alpha", "beta")
        self.add("gamma")
        self.assertEqual((self.case("alpha")["cross"], self.case("beta")["cross"], self.case("gamma")["cross"]),
                         (True, True, False))

    def test_cross_without_git(self):
        self.add("alpha", "beta")
        subprocess.run(["rm", "-rf", str(self.root / ".git")], check=True)
        module_stage._BATCH_CACHE.clear()
        self.assertFalse(self.case()["cross"])


class BatchCache(GitProject):
    """R7: one git batch read per project state; a changed map or HEAD reads again."""

    def test_reuse_and_invalidate(self):
        self.add("alpha")
        calls = []
        real = module_stage.usage_draft.batches

        def counted(project):
            calls.append(project)
            return real(project)
        module_stage.usage_draft.batches = counted
        try:
            self.assertFalse(self.case()["cross"])
            self.assertFalse(self.case()["cross"])
            self.assertEqual(len(calls), 1)
            self.add("beta", "gamma")
            self.assertTrue(self.case("beta")["cross"])
            self.assertEqual(len(calls), 2)
        finally:
            module_stage.usage_draft.batches = real


NEW_ZH, NEW_EN = DOC_SECTIONS["design-new"]["zh"], DOC_SECTIONS["design-new"]["en"]


def design(extra=(), alternatives="不涉及", sections=None):
    """tasks/a/design.md: the six sections plus `extra` section names (each 不涉及); `alternatives` fills 方案取舍."""
    names = list(DOC_SECTIONS["design"]["zh"]) + list(extra)
    fill = {"影响面": "- 新增 `src/a/new.py`", "方案取舍": alternatives}
    fill.update(sections or {})
    return "# 技术方案：a\n\n" + "".join("## %s\n\n%s\n\n" % (name, fill.get(name, "不涉及")) for name in names)


class V2Project(unittest.TestCase):
    """A flow v2 module `a` outside git (no batches); `spec_extra` goes into the requirement."""

    def setUp(self):
        self.project = tfv.Project().__enter__()
        self.addCleanup(self.project.__exit__, None, None, None)
        module_stage._BATCH_CACHE.clear()

    def requirement(self, tier="normal", new=False):
        tfv.approved_spec(self.project, tier, extra=OVERALL + "\n" if new else "")

    def problems(self):
        return module_stage.flow_doc_problems(self.project.root, "a")


class NewDesignSections(V2Project):
    """R2: a new project or module's design without the four sections fails; with them (zh or en, 不涉及) it passes."""

    def test_missing_fails_in_flight_and_done(self):
        self.requirement(new=True)
        self.project.write("tasks/a/design.md", design())
        for done in (False, True):
            with self.subTest(done=done):
                if done:
                    for name, text in (("regression.md", "# r\n"), ("plan.md", "# p\n"), ("todo.md", "- [x] t\n")):
                        self.project.write("tasks/a/%s" % name, text)
                failures = [m for level, m in self.problems() if level == "fail" and "design.md" in m]
                self.assertEqual(len(failures), 1, self.problems())
                for name in NEW_ZH:
                    self.assertIn(name, failures[0])

    def test_present_passes(self):
        self.requirement(new=True)
        for extra in (NEW_ZH, NEW_EN):
            with self.subTest(extra=extra[0]):
                self.project.write("tasks/a/design.md", design(extra))
                self.assertEqual([m for level, m in self.problems() if "design.md" in m], [])


class Unchanged(V2Project):
    """R3: not new -- six sections as before, the same problems as before the change."""

    def test_six_sections_pass(self):
        self.requirement()
        self.project.write("tasks/a/design.md", design())
        self.assertEqual([m for level, m in self.problems() if "design.md" in m], [])

    def test_missing_one_of_six_reads_as_before(self):
        self.requirement()
        self.project.write("tasks/a/design.md", design().replace("## 方案取舍\n\n不涉及\n\n", ""))
        self.assertIn(("fail", "`tasks/a/design.md` 缺章节：方案取舍"), self.problems())


class Alternatives(V2Project):
    """R4: an important requirement's design comparing fewer than two approaches warns, never fails."""

    def warnings(self, text, tier="important"):
        self.requirement(tier)
        self.project.write("tasks/a/design.md", design(alternatives=text))
        return [m for level, m in module_stage.design_outline_problems(self.project.root, "a") if level == "warn"]

    def test_fewer_than_two(self):
        for text, count in (("不涉及", 0), ("- 做法甲", 1), ("只考虑过一种做法，就是甲。", 0), ("1) 甲\n2) 乙", 0),
                            ("- <!-- 甲 -->\n- 乙", 1), ("- 甲\n  - 甲的细节", 1), ("```\n- 甲\n- 乙\n```", 0)):
            with self.subTest(text=text):
                found = self.warnings(text)
                self.assertEqual(len(found), 1)
                self.assertIn("只列了 %d 种做法" % count, found[0])

    def test_two_or_more_and_not_important(self):
        for text in ("- 甲\n- 乙", "1. 甲\n2. 乙", "* 甲\n+ 乙\n- 丙"):
            with self.subTest(text=text):
                self.assertEqual(self.warnings(text), [])
        self.assertEqual(self.warnings("- 甲", tier="normal"), [])

    def test_never_a_failure(self):
        self.warnings("不涉及")
        self.assertFalse([m for level, m in module_stage.design_outline_problems(self.project.root, "a")
                          if level == "fail"])


class ModuleInterfaces(GitProject):
    """R5: a multi-module requirement's design without module interfaces (missing, empty, only a comment) warns."""

    def setUp(self):
        super().setUp()
        self.add("alpha", "beta")
        self.add("gamma")

    def warnings(self, module, extra=None):
        names = list(DOC_SECTIONS["design"]["zh"])
        body = "".join("## %s\n\n不涉及\n\n" % name for name in names) + (extra or "")
        path = self.root / "tasks" / module / "design.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# d\n\n" + body, encoding="utf-8")
        return module_stage.design_outline_problems(self.root, module)

    def test_warns(self):
        for extra, what in ((None, "缺「模块接口」一节"), ("## 模块接口\n\n", "「模块接口」一节没有内容"),
                            ("## 模块接口\n\n- <!-- TODO -->\n", "「模块接口」一节没有内容")):
            with self.subTest(extra=extra):
                found = self.warnings("alpha", extra)
                self.assertEqual([level for level, _m in found], ["warn"])
                self.assertIn(what, found[0][1])

    def test_passes(self):
        for extra in ("## 模块接口\n\n无直接接口，因为 beta 只读 alpha 写的文件。\n",
                      "## 模块接口\n\n```mermaid\ngraph LR\n  alpha --> beta\n```\n",
                      "## Module interfaces\n\n- alpha calls beta\n"):
            with self.subTest(extra=extra):
                self.assertEqual(self.warnings("alpha", extra), [])
        self.assertEqual(self.warnings("gamma"), [])


class OutlineHint(GitProject):
    """R6: the lines show only at NEEDS_REGRESSION, one per finding, and the state code follows the count."""

    def setUp(self):
        super().setUp()
        self.add("alpha", "beta", tier="important")

    def write(self, alternatives):
        path = self.root / "tasks" / "alpha" / "design.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(design(alternatives=alternatives), encoding="utf-8")

    def test_stages_and_lines(self):
        self.assertEqual(module_stage.design_outline_line(self.root, "alpha", "NEEDS_DESIGN", True), (None, ""))
        self.write("不涉及")
        fact, lines = module_stage.design_outline_line(self.root, "alpha", "NEEDS_REGRESSION", True)
        self.assertEqual(len(lines.splitlines()), 2)
        self.assertTrue(all(line.startswith("- 技术方案大纲：") for line in lines.splitlines()))
        for stage in ("NEEDS_PLAN", "BUILDING"):
            self.assertEqual(module_stage.design_outline_line(self.root, "alpha", stage, True), (None, ""))
        self.assertTrue(module_stage.design_outline_line(self.root, "alpha", "NEEDS_REGRESSION", False)[1]
                        .startswith("- Design outline: "))

    def test_fact_follows_the_count(self):
        self.write("不涉及")
        first = module_stage.design_outline_line(self.root, "alpha", "NEEDS_REGRESSION", True)
        self.write("- 甲")
        second = module_stage.design_outline_line(self.root, "alpha", "NEEDS_REGRESSION", True)
        self.assertNotEqual(first[0], second[0])
        self.assertIn("只列了 1 种做法", second[1])

    def test_in_the_phase_hint(self):
        self.write("不涉及")
        (self.root / ".agent" / "config.json").write_text(json.dumps({"version": 1, "artifactLanguage": "zh-CN"}),
                                                         encoding="utf-8")
        (self.root / ".agent" / "state.json").write_text(json.dumps({"activeModule": "alpha"}), encoding="utf-8")
        text = module_stage.describe(self.root)
        self.assertIn("NEEDS_REGRESSION", text)
        self.assertEqual(text.count("- 技术方案大纲："), 2)


class Release(unittest.TestCase):
    """R9: version 0.100.0 or later everywhere (sg-skill-map moved on), the CHANGELOG entry says what upgraders must
    do, the interface at least 1.27."""
    ROOT = HERE.parent.parent.parent

    def test_versions(self):
        for path in ("plugins/spec-guard/.claude-plugin/plugin.json", "plugins/spec-guard/.codex-plugin/plugin.json"):
            with self.subTest(path=path):
                version = json.loads((self.ROOT / path).read_text(encoding="utf-8"))["version"]
                self.assertGreaterEqual(tuple(int(p) for p in version.split(".")), (0, 100, 0))
        for path in ("README.md", "README.en.md"):
            with self.subTest(path=path):
                self.assertRegex((self.ROOT / path).read_text(encoding="utf-8"), r"--ref v0\.1\d\d\.\d+")
        major, minor = (int(p) for p in json.loads((HERE.parent / "interface.json").read_text(encoding="utf-8"))
                        ["interface"].split("."))
        self.assertEqual(major, 1)
        self.assertGreaterEqual(minor, 27)

    def test_changelog(self):
        text = (self.ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        entry = text[text.index("## [0.100.0]"):text.index("## [0.99.0]")]
        for phrase in ("sg-design-outline", "要补这四节", "模块接口", "方案取舍"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, entry)


if __name__ == "__main__":
    unittest.main()
