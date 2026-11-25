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
            # plan-auto-approve: a v2 Plan is approved when written, so NEEDS_PLAN is no longer a Plan review stop.
            self.assertIsNone(module_stage.stop_node(project.root, "a", "NEEDS_PLAN", "approved", "none"))


NEW_ONLY_DESIGN = "# d\n\n## 影响面\n\n- 新增 `src/a/new.py`\n"


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
                project.write("tasks/a/design.md", NEW_ONLY_DESIGN)  # design-review: new files only, nothing to review
                self.assertIn(regression, hint(project, zh))
                project.write("tasks/a/regression.md", "# r\n")
                plan = hint(project, zh)
                self.assertIn("tasks/a/plan.md", plan)
                self.assertIn("references/doc-skeletons.md", plan)
                (project.root / "tasks" / "a" / "design.md").unlink()
                (project.root / "tasks" / "a" / "regression.md").unlink()

    def test_pending_requirement_holds_the_design(self):
        # requirement-confirm-gate replaced the Spec wording: a v2 requirement waits for the user's confirmation.
        with Project() as project:
            project.write("spec/a.md", requirement().replace("<!-- spec-guard: review approved -->",
                                                             "<!-- spec-guard: review pending -->"))
            text = hint(project)
            self.assertIn("需求文档 `spec/a.md` 等用户确认", text)
            self.assertIn("确认前不要往下写", text)
            self.assertIn("Do not write further documents until it is confirmed", hint(project, zh=False))

    def test_combined_cadence_points_at_the_missing_document(self):
        with Project() as project:
            project.write("spec/a.md", requirement().replace("<!-- spec-guard: review approved -->",
                                                             "<!-- spec-guard: review pending -->"))
            project.write(".agent/config.json", json.dumps({"version": 1, "artifactLanguage": "zh-CN",
                                                            "reviewCadence": "combined"}))
            project.write(".agent/state.json", json.dumps({"activeModule": "a"}))
            # requirement-confirm-gate: combined no longer folds a v2 requirement into the Plan's review.
            text = module_stage.describe(project.root)
            self.assertIn("（批准节奏 combined 不适用于需求确认）", text)
            self.assertNotIn("连同 Spec 一起交给用户一次批准", text)
            project.write(".agent/config.json", json.dumps({"version": 1, "reviewCadence": "combined"}))
            self.assertIn("(reviewCadence combined does not apply to it)", module_stage.describe(project.root))

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


def pending_spec(project, tier="normal", module="a", **kw):
    project.write("spec/%s.md" % module, requirement(tier, **kw).replace("# a", "# %s" % module).replace(
        "<!-- spec-guard: review approved -->", "<!-- spec-guard: review pending -->"))


def codex_spec(project, edit=False, old=False):
    """A requirement carrying only Codex's approval; `edit` changes it afterwards, `old` drops the flow marker."""
    from module_stage import review_codex_digest, review_codex_line
    text = requirement().replace("<!-- spec-guard: review approved -->", "<!-- spec-guard: review pending -->")
    if old:
        text = text.replace(marker("normal") + "\n", "")
    text = text.replace("<!-- spec-guard: review pending -->", review_codex_line(review_codex_digest(text)))
    project.write("spec/a.md", text + ("\n补一句。\n" if edit else ""))


def configure(project, zh=True, **extra):
    config = {"version": 1}
    if zh:
        config["artifactLanguage"] = "zh-CN"
    config.update(extra)
    project.write(".agent/config.json", json.dumps(config))
    project.write(".agent/state.json", json.dumps({"activeModule": "a"}))


def finish_docs(project, todo="- [x] t\n", plan_marker="<!-- spec-guard: review approved -->"):
    project.write("tasks/a/design.md", "# d\n")
    project.write("tasks/a/regression.md", "# r\n")
    project.write("tasks/a/plan.md", "# p\n\n%s\n" % plan_marker)
    project.write("tasks/a/todo.md", todo)


WAIT_ZH = "- 批准: 需求文档 `spec/a.md` 等用户确认"
CODEX_ZH = "- 批准: 需求文档 `spec/a.md` 只有 Codex 的批准，需求要用户在对话里确认"
REVISED_ZH = "- 批准: 需求文档 `spec/a.md` 确认后又改过，要用户重新确认"
STEP_ZH = "在对话正文里复述需求（目标、给谁用、使用场景、业务规则和异常情形、不做什么、成功标准、待定问题，加上档位），问用户是否说完"


class RequirementConfirmHintTest(unittest.TestCase):
    """requirement-confirm-gate: a v2 requirement is confirmed by the user only, before anything else moves."""

    def test_codex_approval_does_not_confirm_a_v2_requirement(self):
        for edit in (False, True):
            with self.subTest(edit=edit), Project() as project:
                codex_spec(project, edit=edit)
                configure(project, takeover={"spec": "codex"})
                text = module_stage.describe(project.root)
                self.assertIn(CODEX_ZH, text)
                self.assertIn("Codex 的批准不算", text)
                self.assertEqual(module_stage.codex_route(project.root, "a", "spec"), "requirement")
                self.assertEqual(module_stage.requirement_wait(project.root, "a"), "codex")

    def test_old_module_keeps_codex_approval(self):
        with Project() as project:
            codex_spec(project, old=True)
            configure(project, takeover={"spec": "codex"})
            text = module_stage.describe(project.root)
            self.assertNotIn("需求文档 `spec/a.md`", text)
            # The old route stands (here risk-unknown: the temporary project has no readable T3/T4 list).
            self.assertNotEqual(module_stage.codex_route(project.root, "a", "spec"), "requirement")
            self.assertIsNone(module_stage.requirement_wait(project.root, "a"))

    def test_waiting_requirement_line_and_step(self):
        with Project() as project:
            for write in (lambda: pending_spec(project),
                          lambda: project.write("spec/a.md", requirement().replace("<!-- spec-guard: review approved -->\n", ""))):
                write()
                configure(project)
                text = module_stage.describe(project.root)
                self.assertIn(WAIT_ZH, text)
                self.assertIn(STEP_ZH, text)
                self.assertIn("interview-me", text)
                self.assertIn("/spec-guard:review-mark", text)
                self.assertIn("确认前不要往下写", text)
                self.assertNotIn("正在等用户批准", text)
                self.assertEqual(module_state(project.root, "a")["stage"], "NEEDS_DESIGN")
                configure(project, zh=False)
                text = module_stage.describe(project.root)
                self.assertIn("- Review: the requirement `spec/a.md` is waiting for the user's confirmation", text)
                self.assertIn("restate the requirement in the conversation (Objective, Users, Scenarios", text)

    def test_bug_restates_its_own_sections(self):
        with Project() as project:
            pending_spec(project, "bug")
            configure(project)
            self.assertIn("复述需求（复现步骤、预期结果、回归用例，加上档位）", module_stage.describe(project.root))

    def test_important_requirement_names_the_reasons(self):
        with Project() as project:
            pending_spec(project, shared="全局配置")
            configure(project)
            text = module_stage.describe(project.root)
            self.assertIn(WAIT_ZH, text)
            self.assertIn("本需求是重要需求：cross-module", text)
            self.assertNotIn("Spec `spec/a.md` 是重要需求", text)

    def test_confirmed_and_revised(self):
        with Project() as project:
            approved_spec(project)
            configure(project)
            self.assertNotIn("需求文档 `spec/a.md`", module_stage.describe(project.root))
            self.assertIsNone(module_stage.requirement_wait(project.root, "a"))
            project.write("spec/a.md", (project.root / "spec" / "a.md").read_text(encoding="utf-8") + "\n补一句。\n")
            text = module_stage.describe(project.root)
            self.assertIn(REVISED_ZH, text)
            self.assertIn(STEP_ZH, text)
            self.assertEqual(module_stage.requirement_wait(project.root, "a"), "revised")

    def test_old_module_without_marker_is_quiet(self):
        with Project() as project:
            project.write("spec/a.md", requirement().replace(marker("normal") + "\n", "").replace(
                "<!-- spec-guard: review approved -->\n", ""))
            configure(project)
            text = module_stage.describe(project.root)
            self.assertNotIn("需求文档", text)
            self.assertIsNone(module_stage.requirement_wait(project.root, "a"))

    def test_combined_cadence_does_not_fold_the_requirement(self):
        with Project() as project:
            pending_spec(project)
            configure(project, reviewCadence="combined")
            text = module_stage.describe(project.root)
            self.assertIn(WAIT_ZH + "（批准节奏 combined 不适用于需求确认）。", text)
            self.assertIn(STEP_ZH, text)
            self.assertNotIn("连同 Spec 一起交给用户一次批准", text)

    def test_revised_with_a_baseline_is_not_batched(self):
        with Project() as project:
            git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false"]
            subprocess.run(["git", "init", "-q"], cwd=project.root, check=True)
            approved_spec(project)
            configure(project)
            subprocess.run(git + ["add", "-A"], cwd=project.root, check=True)
            subprocess.run(git + ["commit", "-qm", "base"], cwd=project.root, check=True)
            project.write("spec/a.md", (project.root / "spec" / "a.md").read_text(encoding="utf-8") + "\n补一句。\n")
            text = module_stage.describe(project.root)
            self.assertIn(REVISED_ZH, text)
            self.assertNotIn("批准后又改过（基线", text)

    def test_module_done_and_final_gate_wait_for_the_requirement(self):
        with Project() as project:
            pending_spec(project)
            finish_docs(project)
            configure(project)
            self.assertEqual(module_state(project.root, "a")["stage"], "DONE")
            text = module_stage.describe(project.root)
            self.assertIn(WAIT_ZH, text)
            self.assertIn("建议下一步: " + STEP_ZH, text)
        with Project() as project:
            pending_spec(project)
            finish_docs(project, todo="- [x] t\n- [ ] 最终验收（gate）：交用户\n")
            configure(project, takeover={"merge": "auto"})
            self.assertTrue(module_stage.at_final_gate(project.root, "a"))
            text = module_stage.describe(project.root)
            self.assertIn("建议下一步: " + STEP_ZH, text)
            self.assertEqual(module_stage.stop_node(project.root, "a", "BUILDING", "pending", "approved"), "spec-review")

    def test_project_done_without_active_module(self):
        with Project() as project:
            pending_spec(project)
            finish_docs(project)
            project.write(".agent/config.json", json.dumps({"version": 1, "artifactLanguage": "zh-CN"}))
            text = module_stage.describe(project.root)
            self.assertIn("当前阶段: **DONE**", text)
            self.assertIn(WAIT_ZH, text)
            self.assertIn("建议下一步: " + STEP_ZH, text)

    def test_scope_line_stays_but_the_requirement_comes_first(self):
        with Project() as project:
            pending_spec(project, boundary=None)
            finish_docs(project, todo="- [ ] t\n")
            configure(project, takeover={"merge": "auto"})
            text = module_stage.describe(project.root)
            # plan-auto-approve: a v2 module is checked against its boundary plus its design's impact paths.
            self.assertIn("- 越界：没有并行边界，技术方案影响面也没写出路径", text)
            self.assertIn("建议下一步: " + STEP_ZH, text)

    def test_milestone_stop_comes_before_the_requirement(self):
        draft = ("# Usage draft: demo\n\n## Entry points\n\n| Entry | Does | Module |\n|---|---|---|\n| `x` | y | b, a |\n\n"
                 "## Typical usage\n\n### U1: run\nx\n\n### U2: more\ny\n\n## Milestones\n\n"
                 "| Milestone | Usage | Modules |\n|---|---|---|\n| M1 | U1 | b |\n| M2 | U1, U2 | a |\n")
        with Project(ids=("b", "a")) as project:
            project.write("spec/b.md", "# b\n")
            project.write("tasks/b/plan.md", "# Plan\n")
            project.write("tasks/b/todo.md", "- [x] one\n")
            project.write("spec/usage/demo.md", draft)
            pending_spec(project)
            configure(project)
            text = module_stage.describe(project.root)
            self.assertIn(WAIT_ZH, text)
            self.assertIn("里程碑停点", text)
            self.assertNotIn("建议下一步: " + STEP_ZH, text)

    def test_role_views(self):
        cmd = module_stage.commands(None, True)
        with Project() as project:
            pending_spec(project)
            configure(project)
            by_id = {"a": module_state(project.root, "a")}
            _lines, step = module_stage.role_view(project.root, "module", "a", by_id, cmd, "", True)
            self.assertIn("交给协调会话请用户审", step)
            review_step = module_stage.review_hint(project.root, "a", "NEEDS_DESIGN", cmd, True)[1]
            _lines, step = module_stage.role_view(project.root, "coordinator", None, by_id, cmd, review_step, True)
            self.assertIn(STEP_ZH, step)
            self.assertIn("作为协调会话", step)

    def test_state_code_changes_with_the_kind_of_wait(self):
        with Project() as project:
            pending_spec(project)
            configure(project, takeover={"spec": "codex"})
            full = module_stage.describe(project.root, state_extra="x")
            code = full.rsplit("spec-guard-state: ", 1)[1][:8]
            self.assertNotIn("\n", module_stage.describe(project.root, state_extra="x", last_state=code).strip())
            codex_spec(project)
            again = module_stage.describe(project.root, state_extra="x", last_state=code)
            self.assertIn(CODEX_ZH, again)


class RequirementConfirmFieldTest(unittest.TestCase):
    """requirement-confirm-gate: requirementConfirm's status, by, at and sha256."""
    GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "core.hooksPath=/dev/null",
           "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main"]

    def git(self, project, *args):
        subprocess.run(self.GIT + list(args), cwd=project.root, check=True, capture_output=True, timeout=30)

    def commit(self, project, message="c"):
        self.git(project, "add", "-A")
        self.git(project, "commit", "-qm", message, "--allow-empty")

    def test_four_statuses(self):
        with Project() as project:
            self.assertIsNone(module_stage.requirement_confirm(project.root, "a"))
            project.write("spec/a.md", "# a\n")
            self.assertIsNone(module_stage.requirement_confirm(project.root, "a"))
            pending_spec(project)
            self.assertEqual(module_stage.requirement_confirm(project.root, "a")["status"], "pending")
            codex_spec(project)
            self.assertEqual(module_stage.requirement_confirm(project.root, "a")["status"], "pending")
            approved_spec(project)
            confirm = module_stage.requirement_confirm(project.root, "a")
            self.assertEqual((confirm["status"], confirm["by"], confirm["at"]), ("confirmed", "user", None))
            project.write("spec/a.md", (project.root / "spec" / "a.md").read_text(encoding="utf-8") + "\n补一句。\n")
            confirm = module_stage.requirement_confirm(project.root, "a")
            self.assertEqual((confirm["status"], confirm["by"]), ("revised", None))
            project.write("spec/a.md", requirement().replace("<!-- spec-guard: review approved -->",
                                                             "<!-- spec-guard: review pending -->\n<!-- spec-guard: review pending -->"))
            self.assertEqual(module_stage.requirement_confirm(project.root, "a")["status"], "invalid")

    def test_sha256_is_the_spec_digest(self):
        with Project() as project:
            approved_spec(project)
            path = project.root / "spec" / "a.md"
            done = subprocess.run([sys.executable, "-B", str(HERE / "spec-digest.py"), "text", str(path)],
                                  capture_output=True, text=True, check=True)
            expected = done.stdout.strip()
            self.assertEqual(module_stage.requirement_confirm(project.root, "a")["sha256"], expected)

    def test_at_follows_the_committed_marker(self):
        with Project() as project:
            self.git(project, "init", "-q")
            pending_spec(project)
            self.commit(project, "requirement")
            approved_spec(project)
            self.assertIsNone(module_stage.requirement_confirm(project.root, "a")["at"])  # not committed yet
            self.commit(project, "confirm")
            at = module_stage.requirement_confirm(project.root, "a")["at"]
            confirm_time = subprocess.run(["git", "log", "-1", "--format=%cI"], cwd=project.root, capture_output=True,
                                          text=True, check=True).stdout.strip()
            self.assertEqual(at, confirm_time)
            approved = (project.root / "spec" / "a.md").read_text(encoding="utf-8")
            # Deleted and committed, then written back without a commit: not the old time.
            pending_spec(project)
            self.commit(project, "drop")
            project.write("spec/a.md", approved)
            self.assertIsNone(module_stage.requirement_confirm(project.root, "a")["at"])

    def test_fenced_example_does_not_date_the_marker(self):
        with Project() as project:
            self.git(project, "init", "-q")
            approved_spec(project)
            approved = (project.root / "spec" / "a.md").read_text(encoding="utf-8")
            line = next(l for l in approved.splitlines() if "review approved" in l)
            body = approved.replace(line + "\n", "")
            project.write("spec/a.md", body.replace("<!-- spec-guard: flow v2", "```\n%s\n```\n<!-- spec-guard: flow v2" % line, 1))
            self.commit(project, "example")
            project.write("spec/a.md", approved)
            self.commit(project, "confirm")
            at = module_stage.requirement_confirm(project.root, "a")["at"]
            confirm_time = subprocess.run(["git", "log", "-1", "--format=%cI"], cwd=project.root, capture_output=True,
                                          text=True, check=True).stdout.strip()
            self.assertEqual(at, confirm_time)

    def test_at_outside_git_and_past_the_limit(self):
        with Project() as project:
            approved_spec(project)
            self.assertIsNone(module_stage.requirement_confirm(project.root, "a")["at"])
            self.git(project, "init", "-q")
            self.commit(project, "confirm")
            for index in range(module_stage.REQUIREMENT_AT_LIMIT):
                project.write("spec/a.md", (project.root / "spec" / "a.md").read_text(encoding="utf-8"))
                project.write("tasks/a/n%d.md" % index, "x\n")
                self.git(project, "add", "-A")
                # touch the requirement in each commit without changing the marker
                path = project.root / "spec" / "a.md"
                path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
                self.commit(project, "n%d" % index)
            self.assertIsNone(module_stage.requirement_confirm(project.root, "a")["at"])

    def test_review_mark_refuses_codex_on_a_v2_requirement(self):
        with Project() as project:
            pending_spec(project)
            project.write(".agent/config.json", json.dumps({"version": 1, "takeover": {"spec": "codex"}}))
            report = project.root / "r.json"
            report.write_text("{}", encoding="utf-8")
            done = subprocess.run([sys.executable, "-B", str(HERE / "review_mark.py"), "--project", str(project.root),
                                   "--module", "a", "--target", "spec", "--state", "codex-approved", "--review",
                                   str(report)], capture_output=True, text=True)
            self.assertEqual(done.returncode, 2)
            self.assertTrue(done.stdout.startswith("codex-route-requirement: "), done.stdout + done.stderr)


class RequirementConfirmRuleTest(unittest.TestCase):
    """requirement-confirm-gate (assumption 5): the shared rule says what the hint enforces."""

    def test_rule_text(self):
        text = (HERE.parent / "references" / "workflow-checkpoints.md").read_text(encoding="utf-8")
        section = text[text.index("## 需求确认"):text.index("## 阶段交接")]
        for phrase in ("接管档位不能代替", "Codex 的批准不算", "只跳过拷问、不跳过确认", "重要需求不能跳过拷问",
                       "经所装协作插件转来的用户原话"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, section)



def git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def design_text(impact="- 新增 `src/a/new.py`"):
    return "# 技术方案：a\n\n" + "".join("## %s\n\n%s\n\n" % (name, impact if name == "影响面" else "不涉及")
                                    for name in DOC_SECTIONS["design"]["zh"])


class DesignRequirementTest(unittest.TestCase):
    """design-review AC2: the order in assumption 2, one positive case each, and new files only."""

    def need(self, project):
        return module_stage.design_requirement(project.root, "a")

    def test_important_goes_to_the_user(self):
        with Project() as project:
            approved_spec(project, "important")
            project.write("tasks/a/design.md", design_text())
            self.assertEqual(self.need(project), {"need": "user", "reason": "important"})

    def test_cross_module_is_important_by_rule(self):
        # The cross-module case of assumption 2 reaches the first branch: important() already lifts the tier.
        with Project() as project:
            approved_spec(project, "normal", shared="全局配置")
            project.write("tasks/a/design.md", design_text())
            self.assertEqual(self.need(project), {"need": "user", "reason": "important"})
            self.assertIn("cross-module", module_stage.important(project.root, "a"))

    def test_existing_files_at_the_baseline_are_reviewed(self):
        with Project() as project:
            project.write("src/a/old.py", "x = 1\n")
            git(project.root, "init", "-q")
            git(project.root, "-c", "user.name=t", "-c", "user.email=t@t", "add", "-A")
            git(project.root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")
            approved_spec(project)
            git(project.root, "add", "-A")
            git(project.root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "spec")
            project.write("src/a/new.py", "y = 2\n")  # written by the module: new at the baseline
            git(project.root, "add", "-A")
            git(project.root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "code")
            project.write("tasks/a/design.md", design_text("- 新增 `src/a/new.py`"))
            self.assertEqual(self.need(project), {"need": "none", "reason": None})
            for impact in ("- 改 `src/a/old.py:12`", "- 改 `src/a/` 目录"):
                with self.subTest(impact=impact):
                    project.write("tasks/a/design.md", design_text(impact))
                    self.assertEqual(self.need(project), {"need": "review", "reason": "old-files"})

    def test_outside_git_the_working_tree_stands_in(self):
        with Project() as project:
            approved_spec(project)
            project.write("src/a/old.py", "x = 1\n")
            project.write("tasks/a/design.md", design_text("- 改 `src/a/old.py`，新增 `src/a/new.py`"))
            self.assertEqual(self.need(project), {"need": "review", "reason": "old-files"})

    def test_no_path_counts_as_old_logic(self):
        with Project() as project:
            approved_spec(project)
            project.write("tasks/a/design.md", design_text("不涉及"))
            self.assertEqual(self.need(project), {"need": "review", "reason": "impact-unknown"})

    def test_the_switch_reviews_every_design(self):
        with Project() as project:
            approved_spec(project)
            project.write("tasks/a/design.md", design_text())
            self.assertEqual(self.need(project), {"need": "none", "reason": None})
            project.write(".agent/config.json", json.dumps({"version": 1, "designReview": "on"}))
            self.assertEqual(self.need(project), {"need": "review", "reason": "configured"})
            project.write(".agent/config.json", json.dumps({"version": 1, "designReview": "yes"}))  # AC9: off
            self.assertEqual(self.need(project), {"need": "none", "reason": None})

    def test_no_design_step(self):
        with Project() as project:
            project.write("spec/a.md", "# a\n")
            self.assertIsNone(self.need(project))
            self.assertIsNone(module_stage.design_approval(project.root, "a"))
            for tier in ("bug", "small"):
                approved_spec(project, tier)
                self.assertIsNone(module_stage.design_approval(project.root, "a"))


class DesignApprovalTest(unittest.TestCase):
    """design-review AC3, AC4, AC6-AC8: the designApproval status, the phase hint and the stop node."""

    def setUp(self):
        self.project = Project().__enter__()
        self.addCleanup(self.project.__exit__, None, None, None)

    def round(self, n, blocking, vendor="openai", same="false", report="a" * 64):
        return ("<!-- spec-guard: design-review round=%d blocking=%d sha256=%s vendor=%s same-vendor=%s "
                "criteria=design-v1 report=%s -->" % (n, blocking, "b" * 12, vendor, same, report))

    def design(self, impact="- 改 `src/a/old.py`", marker=None, rounds=()):
        from module_stage import REVIEW_PENDING, review_approved_line, review_codex_digest, review_reviewer_line
        text = design_text(impact)
        if rounds:
            text += "## 外部审查意见\n\n" + "".join(line + "\n" for line in rounds)
        if marker:
            head, _, rest = text.partition("\n")
            pending = "%s\n\n%s\n%s" % (head, REVIEW_PENDING, rest)
            line = {"pending": REVIEW_PENDING,
                    "approved": review_approved_line(review_codex_digest(pending)),
                    "reviewer-approved": review_reviewer_line(review_codex_digest(pending))}[marker]
            text = pending.replace(REVIEW_PENDING, line)
        self.project.write("tasks/a/design.md", text)

    def approval(self):
        return module_stage.design_approval(self.project.root, "a")

    def stop(self, stage="NEEDS_REGRESSION"):
        return module_stage.stop_node(self.project.root, "a", stage, "approved", "none")

    def test_not_required_goes_straight_to_the_regression_document(self):
        # AC3
        approved_spec(self.project)
        self.design("- 新增 `src/a/new.py`")
        self.assertEqual(self.approval()["status"], "not-required")
        self.assertIsNone(self.approval()["approvedBy"])
        text = hint(self.project)
        self.assertIn("写回归测试文档 `tasks/a/regression.md`", text)
        self.assertNotIn("技术方案 `tasks/a/design.md`", text)

    def test_review_needed_then_passed_by_the_reviewer(self):
        # AC4
        approved_spec(self.project)
        self.project.write("src/a/old.py", "x\n")
        self.design()
        self.assertEqual(self.approval()["status"], "pending-review")
        text = hint(self.project)
        self.assertIn("技术方案 `tasks/a/design.md` 待审（第二审查者；影响面列了已有文件）", text)
        self.assertIn("--author-host <claude-code|codex> --paths tasks/a/design.md --spec spec/a.md", text)
        self.assertIn("放行前先不要写回归测试文档", text)
        self.assertNotIn("建议下一步: 写回归测试文档", text)
        claude = module_stage.design_hint(self.project.root, "a", "NEEDS_REGRESSION",
                                          module_stage.commands("claude", True), True)[1]
        self.assertIn("--author-host claude-code ", claude)
        codex = module_stage.design_hint(self.project.root, "a", "NEEDS_REGRESSION",
                                         module_stage.commands("codex", False), False)[1]
        self.assertIn("--author-host codex ", codex)
        self.assertIsNone(self.stop())
        self.design(rounds=[self.round(1, 2)])
        self.assertEqual(self.approval()["status"], "in-review")
        self.assertIn("--previous-report <上一轮报告>", hint(self.project))
        self.assertIsNone(self.stop())
        self.design(marker="reviewer-approved", rounds=[self.round(1, 2), self.round(2, 0, same="true", report="c" * 64)])
        approval = self.approval()
        self.assertEqual((approval["status"], approval["approvedBy"]), ("approved", "reviewer"))
        self.assertEqual((approval["reviewerVendor"], approval["sameVendor"], approval["reportSha256"]),
                         ("openai", True, "c" * 64))
        self.assertEqual([item["round"] for item in approval["rounds"]], [1, 2])
        self.assertIn("写回归测试文档 `tasks/a/regression.md`", hint(self.project))

    def test_two_blocking_rounds_go_to_the_user(self):
        approved_spec(self.project)
        self.project.write("src/a/old.py", "x\n")
        self.design(rounds=[self.round(1, 2), self.round(2, 1)])
        self.assertEqual(self.approval()["status"], "pending-user")
        self.assertIn("待用户批（两轮审查仍有阻断）", hint(self.project))
        self.assertEqual(self.stop(), "design-review")
        self.design(marker="approved", rounds=[self.round(1, 2), self.round(2, 1)])
        self.assertEqual((self.approval()["status"], self.approval()["approvedBy"]), ("approved", "user"))
        self.assertIsNone(self.stop())

    def test_important_is_always_the_users(self):
        # AC6
        approved_spec(self.project, "important")
        self.design("- 新增 `src/a/new.py`")
        self.assertEqual(self.approval()["status"], "pending-user")
        text = hint(self.project)
        self.assertIn("待用户批（重要需求，第二审查者先审一轮）", text)
        self.assertIn("/delegate:review --profile design", text)
        self.assertEqual(self.stop(), "design-review")
        self.design("- 新增 `src/a/new.py`", marker="reviewer-approved", rounds=[self.round(1, 0)])
        self.assertEqual(self.approval()["status"], "pending-user")
        self.assertIn("待用户批（重要需求）", hint(self.project))
        self.design("- 新增 `src/a/new.py`", marker="approved", rounds=[self.round(1, 0)])
        self.assertEqual((self.approval()["status"], self.approval()["approvedBy"]), ("approved", "user"))

    def test_no_reviewer_goes_to_the_user(self):
        # AC7
        approved_spec(self.project)
        self.project.write("src/a/old.py", "x\n")
        self.design(marker="pending", rounds=[self.round(1, 0, vendor="none")])
        approval = self.approval()
        self.assertEqual(approval["status"], "unreviewed")
        self.assertEqual((approval["reviewerVendor"], approval["sameVendor"], approval["reportSha256"]),
                         (None, None, None))
        self.assertEqual(approval["rounds"][0]["vendor"], None)
        self.assertIn("没有可用的第二审查者（未审），交用户批", hint(self.project))
        self.assertEqual(self.stop(), "design-review")
        self.design(marker="approved", rounds=[self.round(1, 0, vendor="none")])
        self.assertEqual((self.approval()["status"], self.approval()["approvedBy"]), ("approved", "user"))

    def test_an_edit_after_passing_is_a_revision(self):
        # AC8: reviewed again, or approved again by the user, also once the later documents exist.
        approved_spec(self.project)
        self.project.write("src/a/old.py", "x\n")
        self.design(marker="reviewer-approved", rounds=[self.round(1, 0)])
        path = self.project.root / "tasks" / "a" / "design.md"
        path.write_text(path.read_text(encoding="utf-8").replace("不涉及", "改过", 1), encoding="utf-8")
        self.assertEqual(self.approval()["status"], "revised")
        self.assertIn("放行后又改过，要重新审", hint(self.project))
        self.assertIsNone(self.stop())
        self.project.write("tasks/a/regression.md", "# r\n")
        self.project.write("tasks/a/plan.md", "# p\n")
        self.project.write("tasks/a/todo.md", "- [ ] t\n")
        self.assertIn("放行后又改过，要重新审", hint(self.project))
        approved_spec(self.project, "important")
        self.design(marker="approved", rounds=[self.round(1, 0)])
        path.write_text(path.read_text(encoding="utf-8").replace("不涉及", "改过", 1), encoding="utf-8")
        self.assertIn("批准后又改过，要用户重新批", hint(self.project))
        self.assertEqual(self.stop("BUILDING"), "design-review")

    def test_a_design_from_before_this_check_is_not_stopped_later(self):
        approved_spec(self.project)
        self.project.write("src/a/old.py", "x\n")
        self.design()
        self.project.write("tasks/a/regression.md", "# r\n")
        self.assertEqual(self.approval()["status"], "pending-review")
        self.assertNotIn("技术方案 `tasks/a/design.md`", hint(self.project))

    def test_english_wording(self):
        approved_spec(self.project)
        self.project.write("src/a/old.py", "x\n")
        self.design()
        text = hint(self.project, zh=False)
        self.assertIn("the design `tasks/a/design.md` awaits a second reviewer (its impact section lists existing files)",
                      text)
        self.assertIn("Until it passes, do not write the regression document yet.", text)



class PlanAutoApproveTest(unittest.TestCase):
    """plan-auto-approve AC2: a v2 Plan is approved by being written; its marker does nothing; old modules unchanged."""

    TODO = "- [ ] t\n- [ ] 最终验收（gate）\n"

    def setUp(self):
        self.project = Project().__enter__()
        self.addCleanup(self.project.__exit__, None, None, None)
        approved_spec(self.project)
        self.project.write("tasks/a/design.md", NEW_ONLY_DESIGN)
        self.project.write("tasks/a/regression.md", "# r\n")

    def effective(self):
        return module_stage.effective_review(self.project.root, "a", "plan", "none")

    def test_without_a_plan(self):
        self.assertEqual(module_state(self.project.root, "a")["stage"], "NEEDS_PLAN")
        self.assertEqual(self.effective(), ("none", None))
        self.assertEqual(module_stage.codex_route(self.project.root, "a", "plan"), "auto")
        self.assertIsNone(module_stage.stop_node(self.project.root, "a", "NEEDS_PLAN", "approved", "none"))
        text = hint(self.project)
        self.assertIn("Plan 写完即自动批准", text)
        self.assertNotIn("停点规则（Plan 交审）", text)
        self.assertIn("approved automatically", hint(self.project, zh=False))

    def test_a_written_plan_is_approved_whatever_its_marker(self):
        for marker in ("", "<!-- spec-guard: review pending -->\n", "<!-- spec-guard: review approved -->\n",
                       "<!-- spec-guard: review codex-approved aaaaaaaaaaaa -->\n", "<!-- spec-guard: review bogus -->\n"):
            with self.subTest(marker=marker):
                self.project.write("tasks/a/plan.md", "# Plan\n\n%s\n## 任务\n\n- t\n" % marker)
                self.project.write("tasks/a/todo.md", self.TODO)
                self.assertEqual(self.effective(), ("approved", "auto"))
                text = hint(self.project)
                self.assertIn("Plan 已自动批准", text)
                self.assertNotIn("先等批准再构建", text)
                self.assertNotIn("Plan `tasks/a/plan.md`", text)
                self.assertNotIn("批准标记无效", text)
                self.assertIn("Plan approved automatically", hint(self.project, zh=False))

    def test_old_module_still_waits(self):
        self.project.write("spec/a.md", "# a\n")
        self.project.write("tasks/a/plan.md", "# Plan\n\n<!-- spec-guard: review pending -->\n")
        self.project.write("tasks/a/todo.md", self.TODO)
        self.assertNotEqual(self.effective()[1], "auto")
        self.assertEqual(module_stage.codex_route(self.project.root, "a", "plan"), "takeover")
        self.assertIn("Plan `tasks/a/plan.md` 正在等用户批准", hint(self.project))



class FlowOverreachTest(unittest.TestCase):
    """plan-auto-approve AC4, AC5: a v2 build is checked against its boundary plus its design's impact, any takeover."""

    def setUp(self):
        self.project = Project().__enter__()
        self.addCleanup(self.project.__exit__, None, None, None)
        self.project.write("src/a/old.py", "x\n")
        self.project.write("src/other.py", "x\n")
        git(self.project.root, "init", "-q")
        self.commit("base")

    def commit(self, message):
        git(self.project.root, "add", "-A")
        git(self.project.root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", message)

    def build(self, tier="normal", boundary=None, impact="- 改 `src/a/old.py`"):
        approved_spec(self.project, tier, boundary=boundary)
        if tier not in ("bug", "small"):
            self.project.write("tasks/a/design.md", design_text(impact))
            self.project.write("tasks/a/regression.md", "# r\n")
        self.project.write("tasks/a/plan.md", "# Plan\n\n## 任务\n\n- t\n")
        self.project.write("tasks/a/todo.md", "- [ ] t\n- [ ] 最终验收（gate）\n")
        self.commit("docs")

    def test_outside_the_impact_stops_and_adding_it_passes(self):
        self.build()
        self.project.write("src/a/old.py", "changed\n")
        self.assertNotIn("越界", hint(self.project))
        self.project.write("src/other.py", "changed\n")
        text = hint(self.project)
        self.assertIn("越界：1 个文件超出需求文档的并行边界与技术方案影响面（`src/other.py`）", text)
        self.assertIn("停点规则（中途 gate）", text)
        self.project.write("tasks/a/design.md", design_text("- 改 `src/a/old.py`、`src/other.py`"))
        self.assertNotIn("越界", hint(self.project))

    def test_a_reviewed_design_is_revised_by_the_addition(self):
        from module_stage import REVIEW_PENDING, review_codex_digest, review_reviewer_line
        self.build()
        path = self.project.root / "tasks" / "a" / "design.md"
        text = path.read_text(encoding="utf-8").replace("\n", "\n\n%s\n" % REVIEW_PENDING, 1)
        path.write_text(text.replace(REVIEW_PENDING, review_reviewer_line(review_codex_digest(text))), encoding="utf-8")
        self.assertEqual(module_stage.design_approval(self.project.root, "a")["status"], "approved")
        path.write_text(path.read_text(encoding="utf-8").replace("`src/a/old.py`", "`src/a/old.py`、`src/other.py`"),
                        encoding="utf-8")
        self.assertEqual(module_stage.design_approval(self.project.root, "a")["status"], "revised")

    def test_a_pre_declared_path_is_not_authorized(self):
        self.build()
        self.project.write("tasks/a/plan.md", "# Plan\n\n<!-- spec-guard: review approved -->\n\n## 任务\n\n- t\n\n"
                                              "## 预先声明\n\n- 公共路径：`src/other.py`\n")
        self.commit("plan")
        self.project.write("src/other.py", "changed\n")
        self.assertIn("越界：1 个文件超出", hint(self.project))

    def test_bug_without_a_boundary_is_not_checked_and_does_not_stop(self):
        self.build("bug")
        self.project.write("src/other.py", "changed\n")
        text = hint(self.project)
        self.assertIn("越界：没有并行边界，未检查。", text)
        self.assertNotIn("停点规则（中途 gate）", text)

    def test_small_with_a_boundary_is_checked(self):
        self.build("small", boundary="`src/a/`")
        self.project.write("src/other.py", "changed\n")
        self.assertIn("越界：1 个文件超出", hint(self.project))

    def test_normal_without_any_path_stops(self):
        self.build(impact="不涉及")
        text = hint(self.project)
        self.assertIn("没有并行边界，技术方案影响面也没写出路径", text)
        self.assertIn("停点规则（中途 gate）", text)


if __name__ == "__main__":
    unittest.main()
