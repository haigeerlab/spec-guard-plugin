"""flow-doc-skeletons: the flow v2 marker, its tier, and the stages of a v2 module.  No network."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import module_stage  # noqa: E402
from module_stage import DOC_SECTIONS, effective_tier, flow_marker, module_state  # noqa: E402

SKELETONS = HERE.parent / "references" / "doc-skeletons.md"


def marker(tier):
    return "<!-- spec-guard: flow v2 tier=%s -->" % tier


def requirement(tier="normal", boundary="`src/a/`", shared=None, extra=""):
    text = "# a\n\n<!-- spec-guard: review approved -->\n%s\n\n" % marker(tier)
    text += "".join("## %s\n\n不涉及\n\n" % name for name in DOC_SECTIONS["requirement"]["zh"])
    text += extra
    if boundary:
        text += "## 并行边界\n\n- 独占：%s\n%s" % (boundary, "- 公共：%s\n" % shared if shared else "")
    return text


class Project:
    def __init__(self, ids=("a",)):
        self.ids = ids

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "spec").mkdir()
        rows = "".join("| %s | x | — |\n" % module for module in self.ids)
        (self.root / "spec" / "CAPABILITY-MAP.md").write_text(
            "# Capability Map: t\n\n| Module id | Responsibility | Depends on |\n|---|---|---|\n%s\nBuild order: %s\n"
            % (rows, " → ".join(self.ids)), encoding="utf-8")
        return self

    def __exit__(self, *exc):
        self.tmp.cleanup()

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


class SkeletonTest(unittest.TestCase):
    def test_every_section_is_in_the_reference_in_both_languages(self):
        text = SKELETONS.read_text(encoding="utf-8")
        for doc, names in DOC_SECTIONS.items():
            self.assertEqual(len(names["zh"]), len(names["en"]), doc)
            for zh, en in zip(names["zh"], names["en"]):
                with self.subTest(doc=doc, section=zh):
                    self.assertIn("| %s | %s |" % (zh, en), text)


class MarkerTest(unittest.TestCase):
    def marker(self, spec):
        with Project() as project:
            if spec is not None:
                project.write("spec/a.md", spec)
            return flow_marker(project.root, "a")

    def test_no_marker_or_no_file_is_the_old_flow(self):
        self.assertEqual(self.marker("# a\n\nbody\n"), {"v2": False, "tier": None, "problems": []})
        self.assertEqual(self.marker(None), {"v2": False, "tier": None, "problems": []})

    def test_four_tiers(self):
        for tier in ("bug", "small", "normal", "important"):
            with self.subTest(tier=tier):
                self.assertEqual(self.marker("# a\n\n%s\n" % marker(tier)), {"v2": True, "tier": tier, "problems": []})

    def test_invalid_tier_reads_as_normal(self):
        self.assertEqual(self.marker("# a\n\n%s\n" % marker("huge")),
                         {"v2": True, "tier": "normal", "problems": ["tier-invalid"]})

    def test_fenced_marker_does_not_count(self):
        self.assertEqual(self.marker("# a\n\n```\n%s\n```\n" % marker("bug"))["v2"], False)


class EffectiveTierTest(unittest.TestCase):
    def test_rule_lifts_a_lower_tier_to_important(self):
        with Project() as project:
            project.write("spec/a.md", requirement("small", shared="全局配置"))
            self.assertEqual(effective_tier(project.root, "a"),
                             {"v2": True, "tier": "important", "problems": ["tier-below-rule"]})

    def test_ordinary_module_keeps_its_tier(self):
        with Project() as project:
            project.write("spec/a.md", requirement("small"))
            self.assertEqual(effective_tier(project.root, "a"), {"v2": True, "tier": "small", "problems": []})

    def test_old_module_has_no_tier(self):
        with Project() as project:
            project.write("spec/a.md", "# a\n")
            self.assertEqual(effective_tier(project.root, "a"), {"v2": False, "tier": None, "problems": []})


def approved_spec(project, tier="normal", **kw):
    """A v2 requirement approved with the real digest marker."""
    from module_stage import review_approved_line, review_digest
    text = requirement(tier, **kw).replace("<!-- spec-guard: review approved -->", "<!-- spec-guard: review pending -->")
    project.write("spec/a.md", text.replace("<!-- spec-guard: review pending -->", review_approved_line(review_digest(text))))


def hint(project, zh=True):
    if zh:
        project.write(".agent/config.json", json.dumps({"version": 1, "artifactLanguage": "zh-CN"}))
    else:
        (project.root / ".agent" / "config.json").unlink(missing_ok=True)
    project.write(".agent/state.json", json.dumps({"activeModule": "a"}))
    return module_stage.describe(project.root)


class StageTest(unittest.TestCase):
    def stages(self, tier, **kw):
        seen = []
        with Project() as project:
            approved_spec(project, tier, **kw)
            seen.append(module_state(project.root, "a")["stage"])
            for relative, text in (("tasks/a/design.md", "# d\n"), ("tasks/a/regression.md", "# r\n"),
                                   ("tasks/a/plan.md", "# p\n"), ("tasks/a/todo.md", "- [ ] t\n"),
                                   ("tasks/a/todo.md", "- [x] t\n")):
                project.write(relative, text)
                seen.append(module_state(project.root, "a")["stage"])
        return seen

    def test_normal_and_important_walk_every_document(self):
        for tier in ("normal", "important"):
            with self.subTest(tier=tier):
                self.assertEqual(self.stages(tier), ["NEEDS_DESIGN", "NEEDS_REGRESSION", "NEEDS_PLAN", "DONE",
                                                     "BUILDING", "DONE"])  # a Plan with no todo counts as done (unchanged)

    def test_bug_and_small_skip_design_and_regression(self):
        for tier in ("bug", "small"):
            with self.subTest(tier=tier), Project() as project:
                approved_spec(project, tier)
                self.assertEqual(module_state(project.root, "a")["stage"], "NEEDS_PLAN")

    def test_small_judged_important_needs_every_document(self):
        with Project() as project:
            approved_spec(project, "small", shared="全局配置")
            self.assertEqual(module_state(project.root, "a")["stage"], "NEEDS_DESIGN")

    def test_old_module_never_sees_the_new_stages(self):
        with Project() as project:
            project.write("spec/a.md", "# a\n")
            self.assertEqual(module_state(project.root, "a")["stage"], "NEEDS_PLAN")

    def test_overlapping_v2_modules_do_not_recurse(self):
        with Project(("a", "b")) as project:
            project.write("spec/a.md", requirement("small", boundary="`src/x/`"))
            project.write("spec/b.md", requirement("small", boundary="`src/x/`").replace("# a", "# b"))
            self.assertEqual(module_state(project.root, "a")["stage"], "NEEDS_DESIGN")
            self.assertEqual(module_state(project.root, "b")["stage"], "NEEDS_DESIGN")
            self.assertIn("NEEDS_DESIGN", hint(project))

    def test_stop_node_is_not_plan_review_before_the_plan(self):
        with Project() as project:
            approved_spec(project)
            for stage in ("NEEDS_DESIGN", "NEEDS_REGRESSION"):
                self.assertNotEqual(module_stage.stop_node(project.root, "a", stage, "approved", "none"), "plan-review")
            self.assertEqual(module_stage.stop_node(project.root, "a", "NEEDS_PLAN", "approved", "none"), "plan-review")


class HintTest(unittest.TestCase):
    def test_new_stages_name_the_document_and_the_skeleton(self):
        with Project() as project:
            approved_spec(project)
            for zh, design, regression in ((True, "写技术方案 `tasks/a/design.md`", "写回归测试文档 `tasks/a/regression.md`"),
                                           (False, "write the design `tasks/a/design.md`",
                                            "write the regression document `tasks/a/regression.md`")):
                text = hint(project, zh)
                self.assertIn(design, text)
                self.assertIn("references/doc-skeletons.md", text)
                project.write("tasks/a/design.md", "# d\n")
                self.assertIn(regression, hint(project, zh))
                project.write("tasks/a/regression.md", "# r\n")
                plan = hint(project, zh)
                self.assertIn("tasks/a/plan.md", plan)
                self.assertIn("references/doc-skeletons.md", plan)
                (project.root / "tasks" / "a" / "design.md").unlink()
                (project.root / "tasks" / "a" / "regression.md").unlink()

    def test_pending_requirement_holds_the_design(self):
        with Project() as project:
            project.write("spec/a.md", requirement().replace("<!-- spec-guard: review approved -->",
                                                             "<!-- spec-guard: review pending -->"))
            text = hint(project)
            self.assertIn("正在等用户批准", text)
            self.assertIn("先不要写技术方案", text)
            self.assertIn("do not write the design yet", hint(project, zh=False))

    def test_combined_cadence_points_at_the_missing_document(self):
        with Project() as project:
            project.write("spec/a.md", requirement().replace("<!-- spec-guard: review approved -->",
                                                             "<!-- spec-guard: review pending -->"))
            project.write(".agent/config.json", json.dumps({"version": 1, "artifactLanguage": "zh-CN",
                                                            "reviewCadence": "combined"}))
            project.write(".agent/state.json", json.dumps({"activeModule": "a"}))
            text = module_stage.describe(project.root)
            self.assertIn("写技术方案 `tasks/a/design.md`", text)
            self.assertIn("连同 Spec 一起交给用户一次批准", text)
            project.write(".agent/config.json", json.dumps({"version": 1, "reviewCadence": "combined"}))
            self.assertIn("present them with the Spec together", module_stage.describe(project.root))

    def test_module_checkout_follows_the_current_rule(self):
        cmd = module_stage.commands(None, True)
        with Project() as project:
            approved_spec(project)
            by_id = {"a": module_state(project.root, "a")}
            _lines, step = module_stage.role_view(project.root, "module", "a", by_id, cmd, "", True)
            self.assertIn("写技术方案 `tasks/a/design.md`", step)
            project.write("spec/a.md", requirement().replace("<!-- spec-guard: review approved -->",
                                                             "<!-- spec-guard: review pending -->"))
            _lines, step = module_stage.role_view(project.root, "module", "a", by_id, cmd, "", True)
            self.assertIn("交给协调会话请用户审", step)

    def test_tier_problem_line(self):
        with Project() as project:
            approved_spec(project, "small", shared="全局配置")
            self.assertIn("规则判为重要需求，按 `important` 处理", hint(project))
            project.write("spec/a.md", requirement("huge"))
            self.assertIn("treated as `normal`", hint(project, zh=False))


class ProjectSectionsTest(unittest.TestCase):
    """project-sections: the declared extra sections join the skeleton for flow v2 modules only."""
    SECTIONS = {"requirement": ["数据来源"], "design": ["浏览器兼容"], "regression": ["视觉回归"]}

    def config(self, project, sections=None, zh=True):
        payload = {"version": 1}
        if zh:
            payload["artifactLanguage"] = "zh-CN"
        if sections is not None:
            payload["projectSections"] = sections
        project.write(".agent/config.json", json.dumps(payload))

    def problems(self, project):
        return [message for _level, message in module_stage.flow_doc_problems(project.root, "a")]

    def test_normal_design_needs_the_declared_section(self):
        with Project() as project:
            self.config(project, {"design": ["浏览器兼容"]})
            approved_spec(project)
            project.write("tasks/a/design.md", "".join("## %s\n\n不涉及\n\n" % n for n in DOC_SECTIONS["design"]["zh"]))
            self.assertIn("`tasks/a/design.md` 缺章节：浏览器兼容", self.problems(project))
            with open(project.root / "tasks" / "a" / "design.md", "a", encoding="utf-8") as handle:
                handle.write("## 浏览器兼容\n\n不涉及\n")
            self.assertEqual(self.problems(project), [])

    def test_bug_and_small_ignore_design_and_regression_sections_but_not_requirement(self):
        for tier, own in (("bug", DOC_SECTIONS["bug"]["zh"]),
                          ("small", DOC_SECTIONS["requirement"]["zh"] + DOC_SECTIONS["small"]["zh"])):
            with self.subTest(tier=tier), Project() as project:
                self.config(project, self.SECTIONS)
                body = "# a\n\n%s\n\n" % marker(tier) + "".join("## %s\n\n不涉及\n\n" % n for n in own)
                project.write("spec/a.md", body)
                self.assertEqual(self.problems(project), ["`spec/a.md` 缺章节：数据来源"])
                project.write("spec/a.md", body + "## 数据来源\n\n不涉及\n")
                self.assertEqual(self.problems(project), [])

    def test_old_module_and_invalid_setting_are_untouched(self):
        with Project() as project:
            self.config(project, self.SECTIONS)
            project.write("spec/a.md", "# a\n")
            self.assertEqual(self.problems(project), [])
            self.config(project, {"design": ["影响面"]})  # invalid: same as a skeleton section
            approved_spec(project)
            project.write("tasks/a/design.md", "".join("## %s\n\n不涉及\n\n" % n for n in DOC_SECTIONS["design"]["zh"]))
            self.assertEqual(self.problems(project), [])

    def test_hint_lists_the_sections_and_is_unchanged_without_them(self):
        with Project() as project:
            approved_spec(project)
            self.config(project)
            project.write(".agent/state.json", json.dumps({"activeModule": "a"}))
            plain = module_stage.describe(project.root)
            self.assertNotIn("另加本项目要求的章节", plain)
            self.config(project, {"design": ["浏览器兼容", "无障碍"]})
            self.assertIn("另加本项目要求的章节：浏览器兼容、无障碍。", module_stage.describe(project.root))
            self.config(project, {"design": ["浏览器兼容"]}, zh=False)
            self.assertIn("Also add this project's sections: 浏览器兼容.", module_stage.describe(project.root))
            self.config(project, {"design": ["影响面"]})
            self.assertNotIn("另加本项目要求的章节", module_stage.describe(project.root))  # invalid: ignored

    def test_needs_spec_says_when_a_requirement_section_is_declared(self):
        with Project() as project:
            self.config(project)
            project.write(".agent/state.json", json.dumps({"activeModule": "a"}))
            plain = module_stage.describe(project.root)
            self.config(project, {"design": ["浏览器兼容"]})
            self.assertNotIn("按新流程写需求文档时", module_stage.describe(project.root))
            self.config(project, {"requirement": ["数据来源"]})
            self.assertIn("按新流程写需求文档时，另加本项目要求的章节：数据来源。", module_stage.describe(project.root))
            self.config(project)
            self.assertEqual(module_stage.describe(project.root), plain)

    def test_state_code_changes_with_the_sections(self):
        with Project() as project:
            approved_spec(project)
            self.config(project)
            project.write(".agent/state.json", json.dumps({"activeModule": "a"}))
            full = module_stage.describe(project.root, state_extra="x")
            code = full.rsplit("spec-guard-state: ", 1)[1][:8]
            self.assertNotIn("\n", module_stage.describe(project.root, state_extra="x", last_state=code).strip())
            self.config(project, {"design": ["浏览器兼容"]})
            again = module_stage.describe(project.root, state_extra="x", last_state=code)
            self.assertIn("另加本项目要求的章节：浏览器兼容。", again)


if __name__ == "__main__":
    unittest.main()
