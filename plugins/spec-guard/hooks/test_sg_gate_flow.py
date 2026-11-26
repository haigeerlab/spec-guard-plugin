"""sg-gate-flow (autopilot module 4): the autopilot preset, release pre-authorisation, the overall design gate, the
non-blocking milestone and the say-first line.  No network; every project is a temporary git repository."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import project_config  # noqa: E402

CONFIG = str(HERE / "project_config.py")


class Project:
    """A temporary git project with an optional .agent/config.json."""

    def __init__(self, config=None):
        self.config = config

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        if self.config is not None:
            self.write(".agent/config.json", json.dumps(dict({"version": 1}, **self.config)))
        return self

    def __exit__(self, *exc):
        self.tmp.cleanup()

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def run(self, script, *args):
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        done = subprocess.run([sys.executable, "-B", script, *args, "--project", str(self.root)],
                              capture_output=True, text=True, timeout=30, env=env)
        return done.returncode, done.stdout + done.stderr


import module_stage  # noqa: E402
import map_view  # noqa: E402
from module_stage import DOC_SECTIONS, review_approved_line, review_digest  # noqa: E402

CMD = {"review-mark": "/spec-guard:review-mark", "milestone-mark": "/spec-guard:milestone-mark",
       "author-host": "claude-code"}
REVIEW_MARK = str(HERE / "review_mark.py")
OVERALL = "<!-- spec-guard: overall-design spec/overall/x.md -->"


def draft(modules):
    """A usage draft with one milestone of these modules."""
    return ("# Usage draft: demo\n\n## Entry points\n\n| Entry | Does | Module |\n|---|---|---|\n| `/demo` | runs | %s |\n\n"
            "## Typical usage\n\n### U1: run\nRun it.\n\n## Milestones\n\n| Milestone | Usage | Modules |\n|---|---|---|\n"
            "| M1 | U1 | %s |\n" % (modules[0], ", ".join(modules)))
PREAUTH = "<!-- spec-guard: release-preauth yes -->"


def requirement(extra=(), approved=True, tier="normal", body="不涉及"):
    """spec/a.md of a flow v2 module; `extra` are marker lines under the flow marker; approved binds the digest."""
    head = "# a\n\n<!-- spec-guard: flow v2 tier=%s -->\n%s" % (tier, "".join(line + "\n" for line in extra))
    text = head + "\n" + "".join("## %s\n\n%s\n\n" % (name, body) for name in DOC_SECTIONS["requirement"]["zh"])
    if approved:
        text = text.replace("# a\n\n", "# a\n\n%s\n" % review_approved_line(review_digest(text)), 1)
    return text


class MapProject(Project):
    """A project with a capability map of the given modules."""

    def __init__(self, config=None, ids=("a",)):
        super().__init__(config)
        self.ids = ids

    def __enter__(self):
        super().__enter__()
        rows = "".join("| %s | x | — |\n" % module for module in self.ids)
        self.write("spec/CAPABILITY-MAP.md", "# Capability Map: t\n\n| Module id | Responsibility | Depends on |\n"
                   "|---|---|---|\n%s\nBuild order: %s\n" % (rows, " → ".join(self.ids)))
        return self

    def takeover(self, module="a"):
        return next(m for m in map_view.build(self.root)["modules"] if m["id"] == module)["takeover"]


AUTOPILOT = {"design": "reviewer", "merge": "auto", "release": "auto-confirm"}


class PresetConfig(unittest.TestCase):
    """R9: the autopilot preset and an object carrying a preset key."""

    def items(self, config, module="alpha"):
        with Project(config) as project:
            items, source = project_config.module_takeover(project.root, module)
            return {key: items[key] for key in ("design", "merge", "release")}, source, \
                project_config.module_preset(project.root, module)

    def test_autopilot_expands(self):
        self.assertEqual(self.items({"takeover": "autopilot"}), (AUTOPILOT, "takeover", "autopilot"))

    def test_preset_object_overrides_only_what_it_names(self):
        self.assertEqual(self.items({"takeover": {"preset": "autopilot", "release": "human"}}),
                         (dict(AUTOPILOT, release="human"), "takeover", "autopilot"))

    def test_module_entry_wins_and_names_its_preset(self):
        config = {"takeover": "none", "moduleTakeover": {"alpha": {"preset": "autopilot", "merge": "human"}}}
        self.assertEqual(self.items(config), (dict(AUTOPILOT, merge="human"), "moduleTakeover", "autopilot"))
        self.assertEqual(self.items(config, "beta")[2], "none")

    def test_object_without_preset_is_unchanged(self):
        human = {"design": "human", "merge": "human", "release": "human"}
        self.assertEqual(self.items({"takeover": {"merge": "auto"}}), (dict(human, merge="auto"), "takeover", None))

    def test_factory_default_is_still_none(self):
        human = {"design": "human", "merge": "human", "release": "human"}
        self.assertEqual(self.items(None), (human, "default", "none"))

    def test_invalid_preset_key_is_refused(self):
        for value in ({"preset": "plan"}, {"preset": "fast"}, {"preset": 1}):
            with self.subTest(value=value):
                self.assertFalse(project_config.valid_takeover(value))
                with Project() as project:
                    code, out = project.run(CONFIG, "set", "--key", "takeover", "--value", json.dumps(value),
                                            "--confirm")
                    self.assertEqual(code, 2, out)

    def test_set_writes_preset_and_object(self):
        for value in ("autopilot", {"preset": "autopilot", "release": "human"}):
            with self.subTest(value=value):
                with Project() as project:
                    raw = value if isinstance(value, str) else json.dumps(value)
                    code, out = project.run(CONFIG, "set", "--key", "takeover", "--value", raw, "--confirm")
                    self.assertEqual(code, 0, out)
                    stored = json.loads((project.root / ".agent" / "config.json").read_text(encoding="utf-8"))
                    self.assertEqual(stored["takeover"], value)

    def test_old_flow_pair_of_a_preset_object(self):
        # design review 1 #2: what the object writes for spec/plan is read as written
        cases = {json.dumps({"preset": "autopilot"}): {"spec": "codex", "plan": "codex"},
                 json.dumps({"preset": "autopilot", "plan": "human"}): {"spec": "codex", "plan": "human"},
                 json.dumps({"preset": "autopilot", "design": "human"}): {"spec": "codex", "plan": "human"},
                 json.dumps({"preset": "none", "spec": "codex"}): {"spec": "codex", "plan": "human"}}
        for raw, pair in cases.items():
            with self.subTest(value=raw):
                self.assertEqual(project_config.legacy(json.loads(raw)), pair)


class NarrowAndGates(unittest.TestCase):
    """R10: narrowing autopilot one step; the three gates never belong to a preset."""

    def test_autopilot_narrows_to_merge(self):
        self.assertEqual(project_config.narrow_step("autopilot"), "merge")

    def test_preset_object_hands_back_its_outermost_item(self):
        self.assertEqual(project_config.narrow_step({"preset": "autopilot", "merge": "human"}),
                         {"design": "reviewer"})
        self.assertEqual(project_config.narrow_step({"preset": "autopilot"}),
                         {"design": "reviewer", "merge": "auto"})

    def test_autopilot_is_wider_than_merge(self):
        self.assertTrue(project_config.takeover_wider(project_config.expand("autopilot"),
                                                      project_config.expand("merge")))
        self.assertEqual(project_config.widen_steps("merge", "autopilot"), 1)

    def test_no_gate_item_in_any_preset(self):
        for name, items in project_config.PRESETS.items():
            with self.subTest(preset=name):
                self.assertEqual(set(items), {"design", "merge", "release"})


class ReleaseQuestion(unittest.TestCase):
    """R1: the release question is asked only where the takeover lets autopilot release."""

    def hint(self, config):
        with MapProject(config) as project:
            project.write("spec/a.md", requirement(approved=False))
            return module_stage.requirement_hint(project.root, "a", "pending", CMD, True)[1], \
                module_stage.requirement_hint(project.root, "a", "pending", CMD, False)[1]

    def test_asked_under_autopilot(self):
        for config in ({"takeover": "autopilot"}, {"takeover": {"release": "auto"}}):
            with self.subTest(config=config):
                zh, en = self.hint(config)
                self.assertIn("做完自动发版吗？", zh)
                self.assertIn("release-preauth yes", zh)
                self.assertIn("release-preauth yes", en)

    def test_not_asked_otherwise_and_unchanged(self):
        base = self.hint(None)
        for config in ({"takeover": {"preset": "autopilot", "release": "human"}}, {"takeover": "merge"},
                       {"takeover": {"release": "prepare"}}):
            with self.subTest(config=config):
                self.assertEqual(self.hint(config), base)
                self.assertNotIn("做完自动发版吗", base[0])


class ReleasePreauth(unittest.TestCase):
    """R2: /map --json takeover.releasePreauth."""

    def value(self, spec, config=None):
        with MapProject(config if config is not None else {"takeover": "autopilot"}) as project:
            project.write("spec/a.md", spec)
            return project.takeover()["releasePreauth"]

    def test_true_when_confirmed_and_allowed(self):
        self.assertIs(self.value(requirement([PREAUTH])), True)

    def test_false_after_an_edit_or_without_the_line(self):
        edited = requirement([PREAUTH]).replace("不涉及", "改过", 1)
        self.assertIs(self.value(edited), False)
        self.assertIs(self.value(requirement()), False)
        self.assertIs(self.value(requirement([PREAUTH], approved=False)), False)
        self.assertIs(self.value(requirement(["<!-- spec-guard: release-preauth maybe -->"])), False)

    def test_null_when_not_allowed_or_old_flow(self):
        self.assertIsNone(self.value(requirement([PREAUTH]), {"takeover": {"preset": "autopilot", "release": "human"}}))
        self.assertIsNone(self.value(requirement([PREAUTH]), {}))
        self.assertIsNone(self.value("# a\n\n" + PREAUTH + "\n"))

    def test_preset_field(self):
        with MapProject({"takeover": {"merge": "auto"}, "moduleTakeover": {"b": "autopilot"}}, ids=("a", "b")) as project:
            project.write("spec/a.md", requirement())
            project.write("spec/b.md", requirement())
            self.assertIsNone(project.takeover("a")["preset"])
            self.assertEqual(project.takeover("b")["preset"], "autopilot")


def overall_text(state="approved", body="内容"):
    """spec/overall/x.md with a user approval bound to its text, a pending marker, or a Codex marker."""
    text = "# 总体技术方案\n\n%s\n" % body
    if state == "approved":
        return text.replace("\n\n", "\n\n%s\n" % review_approved_line(review_digest(text)), 1)
    if state == "pending":
        return text.replace("\n\n", "\n\n<!-- spec-guard: review pending -->\n", 1)
    if state == "codex":
        return text.replace("\n\n", "\n\n%s\n" % module_stage.review_codex_line(module_stage.review_codex_digest(text)), 1)
    return text


class OverallDesign(unittest.TestCase):
    """R3: the overall design holds a confirmed requirement until the user approves it."""

    def look(self, overall=None, line=OVERALL, confirmed=True):
        with MapProject() as project:
            project.write("spec/a.md", requirement([line] if line else [], approved=confirmed))
            if overall is not None:
                project.write("spec/overall/x.md", overall)
            line_, step, _s, _p = module_stage.review_hint(project.root, "a", "NEEDS_DESIGN", CMD, True)
            data = next(m for m in map_view.build(project.root)["modules"] if m["id"] == "a")
            return line_, step, data["overallDesign"], module_stage.overall_problems(project.root, "a")

    def test_approved_lets_it_through(self):
        line, step, found, problems = self.look(overall_text())
        self.assertEqual(found, {"path": "spec/overall/x.md", "status": "approved"})
        self.assertNotIn("总体技术方案", line)
        self.assertEqual(problems, [])

    def test_every_other_state_holds(self):
        cases = {"missing": (None, "missing", "fail"), "pending": (overall_text("pending"), "pending", "fail"),
                 "revised": (overall_text().replace("内容", "改过"), "revised", "fail"),
                 "codex": (overall_text("codex"), "pending", "fail"), "none": (overall_text(None), "pending", "fail"),
                 "codex-edited": (overall_text("codex").replace("内容", "改过"), "pending", "fail")}
        for name, (text, status, level) in cases.items():
            with self.subTest(case=name):
                line, step, found, problems = self.look(text)
                self.assertEqual(found["status"], status)
                self.assertIn("总体技术方案", line)
                self.assertIn("先不要写技术方案", step)
                self.assertIn("--target overall", step)
                self.assertEqual(problems[0][0], level)

    def test_bad_path_is_invalid(self):
        for path in ("docs/x.md", "spec/overall/X.md", "spec/overall/../a.md"):
            with self.subTest(path=path):
                line, _step, found, problems = self.look(overall_text(), "<!-- spec-guard: overall-design %s -->" % path)
                self.assertEqual(found, {"path": None, "status": "invalid"})
                self.assertEqual(problems[0][0], "fail")

    def test_unconfirmed_requirement_comes_first_and_only_warns(self):
        line, _step, found, problems = self.look(overall_text("pending"), confirmed=False)
        self.assertIn("需求文档", line)
        self.assertEqual(problems[0][0], "warn")

    def test_no_line_no_gate(self):
        line, _step, found, problems = self.look(None, line=None)
        self.assertIsNone(found)
        self.assertNotIn("总体技术方案", line)
        self.assertEqual(problems, [])

    def test_holds_under_autopilot_too(self):
        # R10: the gate never belongs to a preset
        with MapProject({"takeover": "autopilot"}) as project:
            project.write("spec/a.md", requirement([OVERALL]))
            project.write("spec/overall/x.md", overall_text("codex"))
            self.assertIn("总体技术方案", module_stage.review_hint(project.root, "a", "NEEDS_DESIGN", CMD, True)[0])


class OverallReviewMark(unittest.TestCase):
    """R4: review-mark --target overall writes only the user's states."""

    def run_mark(self, state, line=OVERALL):
        with MapProject() as project:
            project.write("spec/a.md", requirement([line] if line else []))
            project.write("spec/overall/x.md", overall_text(None))
            code, out = project.run(REVIEW_MARK, "--module", "a", "--target", "overall", "--state", state, "--confirm")
            return code, out, (project.root / "spec" / "overall" / "x.md").read_text(encoding="utf-8")

    def test_user_states_are_written(self):
        code, out, text = self.run_mark("approved")
        self.assertEqual(code, 0, out)
        self.assertEqual(module_stage.review_state(text, "spec"), "approved")
        code, out, text = self.run_mark("pending")
        self.assertEqual((code, module_stage.review_state(text, "spec")), (0, "pending"), out)

    def test_other_states_are_refused(self):
        for state in ("codex-approved", "codex-reviewed", "reviewer-approved", "reviewer-reviewed"):
            with self.subTest(state=state):
                code, out, text = self.run_mark(state)
                self.assertEqual(code, 2)
                self.assertIn("overall-user-only", out)
                self.assertEqual(text, overall_text(None))

    def test_no_line_is_refused(self):
        code, out, text = self.run_mark("approved", line=None)
        self.assertEqual(code, 2)
        self.assertIn("overall-none", out)
        self.assertEqual(text, overall_text(None))


class OverallConsistency(unittest.TestCase):
    """R5: modules of one usage draft point to the same overall design."""

    def problems(self, second):
        with MapProject(ids=("a", "b")) as project:
            project.write("spec/usage/demo.md", draft(["a", "b"]))
            project.write("spec/a.md", requirement([OVERALL]))
            project.write("spec/b.md", requirement(["<!-- spec-guard: overall-design %s -->" % second]))
            for name in ("x", "y"):
                project.write("spec/overall/%s.md" % name, overall_text())
            return module_stage.overall_problems(project.root, "a")

    def test_different_files_warn(self):
        problems = self.problems("spec/overall/y.md")
        self.assertEqual([level for level, _ in problems], ["warn"])
        self.assertIn("spec/overall/y.md", problems[0][1])

    def test_same_file_is_quiet(self):
        self.assertEqual(self.problems("spec/overall/x.md"), [])


class MilestoneBlocking(unittest.TestCase):
    """R6: a finished, unconfirmed milestone does not hold autopilot modules back."""

    def look(self, config):
        with MapProject(config, ids=("a", "b", "c")) as project:
            project.write("spec/usage/demo.md", draft(["a", "b"]))
            for module in ("a", "b"):
                project.write("spec/%s.md" % module, "# %s\n" % module)
                project.write("tasks/%s/plan.md" % module, "# Plan\n")
                project.write("tasks/%s/todo.md" % module, "- [x] done\n")
            project.write("spec/c.md", "# c\n")
            states = [module_stage.module_state(project.root, m) for m in ("a", "b", "c")]
            fact, line, step = module_stage.milestone_stop(project.root, states, CMD, True)
            stop = map_view.build(project.root)["milestoneStop"]
            return line, step, stop

    def test_autopilot_reports_without_stopping(self):
        for config in ({"takeover": "autopilot"},
                       {"takeover": {"preset": "autopilot", "release": "human"}},
                       {"takeover": "none", "moduleTakeover": {"a": "autopilot", "b": "autopilot"}}):
            with self.subTest(config=config):
                line, step, stop = self.look(config)
                self.assertIn("不阻塞", line)
                self.assertEqual(step, "")
                self.assertIs(stop["blocking"], False)

    def test_anything_else_stops_as_before(self):
        base = self.look(None)
        self.assertIs(base[2]["blocking"], True)
        self.assertIn("先不开下一个模块", base[1])
        for config in ({"takeover": "merge"}, {"takeover": {"merge": "auto", "release": "auto-confirm"}},
                       {"takeover": "autopilot", "moduleTakeover": {"b": "merge"}}):
            with self.subTest(config=config):
                self.assertEqual(self.look(config), base)


SAY_FIRST = ("先用一句话告诉用户", "tell the user in one sentence")


def approved_design(body="`src/a.py`"):
    """tasks/a/design.md with every design section and the user's approval bound to it."""
    text = "# 技术方案\n\n" + "".join("## %s\n\n%s\n\n" % (name, body) for name in DOC_SECTIONS["design"]["zh"])
    return text.replace("\n\n", "\n\n%s\n" % review_approved_line(module_stage.review_codex_digest(
        text.replace("\n\n", "\n\n<!-- spec-guard: review pending -->\n", 1))), 1)


class SayFirst(unittest.TestCase):
    """R11: before going on through several steps without a stop, say what comes next."""

    def hint(self, files, spec=None):
        with MapProject() as project:
            project.write("spec/a.md", spec if spec is not None else requirement())
            for path, text in files.items():
                project.write(path, text)
            return module_stage.describe(project.root)

    def says(self, text):
        return any(phrase in text for phrase in SAY_FIRST)

    def test_said_when_the_next_steps_do_not_stop(self):
        regression = "# r\n\n## 用例清单\n\n不涉及\n\n## 成功标准对照\n\n不涉及\n\n## 受影响的老功能\n\n不涉及\n"
        cases = {"NEEDS_REGRESSION": {"tasks/a/design.md": approved_design()},
                 "NEEDS_PLAN": {"tasks/a/design.md": approved_design(), "tasks/a/regression.md": regression},
                 "BUILDING": {"tasks/a/design.md": approved_design(), "tasks/a/regression.md": regression,
                              "tasks/a/plan.md": "# Plan\n\n## 任务\n\n- one\n\n## 检查点\n\n不涉及\n",
                              "tasks/a/todo.md": "- [ ] one\n- [ ] 最终验收（gate）\n"}}
        for stage, files in cases.items():
            with self.subTest(stage=stage):
                text = self.hint(files)
                self.assertIn(stage, text)
                self.assertTrue(self.says(text), text)

    def test_not_said_while_a_gate_waits_or_for_old_flow(self):
        self.assertFalse(self.says(self.hint({}, requirement(approved=False))))
        self.assertFalse(self.says(self.hint({}, "# a\n\n<!-- spec-guard: review pending -->\n")))
        self.assertFalse(self.says(self.hint({"tasks/a/design.md": approved_design().replace("`src/a.py`", "`src/b.py`", 1)})))


if __name__ == "__main__":
    unittest.main()
