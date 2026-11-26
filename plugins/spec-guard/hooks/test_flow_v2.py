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


# takeover-redefine: the design-review cases were written for the route where a second reviewer's pass lets a design
# through, which is now takeover design=reviewer; the default (none) sends every design to the user.
REVIEWER_ROUTE = {"takeover": "design"}


def hint(project, zh=True, route=None):
    config = {"version": 1, **(REVIEWER_ROUTE if route is None else route)}
    if zh:
        config["artifactLanguage"] = "zh-CN"
    project.write(".agent/config.json", json.dumps(config))
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
                if tier == "small":  # regression-doc-check: a small module's cases are checked before the build
                    body = body.replace("## 回归用例\n\n不涉及\n", "## 回归用例\n\n### R1: x\n- 步骤：a\n- 预期：b\n"
                                                              "- 执行方式：manual\n- 证据：用户原话\n")
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


class TakeoverImportantTest(unittest.TestCase):
    """takeover-redefine (R2-1): the takeover never makes a flow v2 requirement important; old modules unchanged."""

    def test_unknowns_do_not_count_for_v2(self):
        values = ("none", "design", "merge", "plan", {"spec": "codex", "plan": "codex", "merge": "auto"})
        with Project() as project:
            approved_spec(project, boundary=None)  # no boundary, no risk list: both unknowns would apply
            for value in values:
                with self.subTest(value=value):
                    configure(project, takeover=value)
                    self.assertEqual(module_stage.important(project.root, "a"), [])
            configure(project, takeover="design")
            project.write("tasks/a/design.md", design_text())
            self.assertEqual(module_stage.design_approver(project.root, "a"), "reviewer")
            configure(project, takeover="none")
            self.assertEqual(module_stage.design_approver(project.root, "a"), "user")

    def test_old_module_keeps_the_unknowns(self):
        with Project() as project:
            project.write("spec/a.md", "# a\n")
            for value, expected in (("merge", ["cross-unknown", "risk-unknown"]),
                                    ({"spec": "codex"}, ["cross-unknown", "risk-unknown"]),
                                    ("design", []), ("plan", []), ("none", [])):
                with self.subTest(value=value):
                    configure(project, takeover=value)
                    self.assertEqual(module_stage.important(project.root, "a"), expected)


class DesignApprovalTest(unittest.TestCase):
    """design-review AC3, AC4, AC6-AC8: the designApproval status, the phase hint and the stop node."""

    def setUp(self):
        self.project = Project().__enter__()
        self.addCleanup(self.project.__exit__, None, None, None)
        self.project.write(".agent/config.json", json.dumps({"version": 1, **REVIEWER_ROUTE}))

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
        self.assertIn("技术方案 `tasks/a/design.md` 待审（第二审查者；影响面列了已有文件；接管档位 design=reviewer（项目的 takeover））", text)
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
        self.assertIn("待用户批（两轮审查仍有阻断；接管档位 design=reviewer（项目的 takeover））", hint(self.project))
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
        self.assertIn("the design `tasks/a/design.md` awaits a second reviewer (its impact section lists existing files; takeover design=reviewer (the project's takeover))",
                      text)
        self.assertIn("Until it passes, do not write the regression document yet.", text)



class HumanDesignRouteTest(unittest.TestCase):
    """takeover-redefine AC3, AC4 (assumptions 2, 8; Q2 A): under design=human the user approves every design."""

    round = DesignApprovalTest.round
    design = DesignApprovalTest.design
    approval = DesignApprovalTest.approval
    stop = DesignApprovalTest.stop

    def setUp(self):
        self.project = Project().__enter__()
        self.addCleanup(self.project.__exit__, None, None, None)
        approved_spec(self.project)
        self.project.write("src/a/old.py", "x\n")

    def human(self, **config):
        return hint(self.project, route=config)

    def test_reviewed_then_the_user_approves(self):
        self.design()
        self.assertEqual(self.approval()["status"], "pending-review")
        text = self.human()
        self.assertIn("待审（第二审查者；影响面列了已有文件；接管档位 design=human（默认，没设 takeover））", text)
        self.assertIn("这不算放行，接着交用户批", text)
        self.design(marker="reviewer-approved", rounds=[self.round(1, 0)])
        self.assertEqual((self.approval()["status"], self.approval()["approvedBy"]), ("pending-user", None))
        self.assertEqual(self.stop(), "design-review")
        self.assertIn("待用户批（第二审查者已审完；接管档位 design=human（默认，没设 takeover））", self.human())
        self.design(marker="approved", rounds=[self.round(1, 0)])
        self.assertEqual((self.approval()["status"], self.approval()["approvedBy"]), ("approved", "user"))
        # the reviewer route is unchanged: the same pass lets it through
        self.design(marker="reviewer-approved", rounds=[self.round(1, 0)])
        self.human(takeover="design")
        self.assertEqual((self.approval()["status"], self.approval()["approvedBy"]), ("approved", "reviewer"))

    def test_an_edit_before_the_user_approves_is_reviewed_again(self):
        self.design(marker="reviewer-approved", rounds=[self.round(1, 0)])
        self.human()
        self.assertEqual(self.approval()["status"], "pending-user")
        path = self.project.root / "tasks" / "a" / "design.md"
        path.write_text(path.read_text(encoding="utf-8").replace("不涉及", "补一句", 1), encoding="utf-8")
        self.assertEqual(self.approval()["status"], "revised")
        self.assertNotEqual(self.stop(), "design-review")
        text = self.human()
        self.assertIn("放行后又改过，要重新审", text)
        self.assertIn("审完交用户批", text)

    def test_no_review_needed_goes_to_the_user(self):
        self.design("- 新增 `src/a/new.py`")
        self.assertEqual(self.approval()["status"], "pending-user")
        self.assertEqual(self.stop(), "design-review")
        self.assertIn("待用户批（不需要第二审查者；接管档位 design=human（默认，没设 takeover））", self.human())
        self.assertIn("待用户批（不需要第二审查者；接管档位 design=human（模块的 moduleTakeover））",
                      self.human(takeover="design", moduleTakeover={"a": "none"}))
        self.assertIn("接管档位 design=human（继承项目的 takeover，模块的 moduleTakeover 无效）",
                      self.human(takeover="none", moduleTakeover={"a": "fast"}))
        self.assertIn("no second reviewer is needed; takeover design=human (the project's takeover)",
                      hint(self.project, zh=False, route={"takeover": "none"}))
        self.human(takeover="design")
        self.assertEqual(self.approval()["status"], "not-required")

    def test_a_lapsed_reviewer_pass_holds_the_build(self):
        # R1-5: the takeover went from design=reviewer to human after the reviewer's pass
        self.design(marker="reviewer-approved", rounds=[self.round(1, 0)])
        self.human(takeover="design")
        self.assertIsNone(module_stage.design_waits(self.project.root, "a", "BUILDING"))
        self.human()
        self.assertEqual(module_stage.design_waits(self.project.root, "a", "BUILDING")["status"], "pending-user")
        self.assertEqual(self.stop("BUILDING"), "design-review")

    def test_the_state_code_follows_the_review(self):
        # R2-3: pending-review -> in-review keeps the stage and the stop node, so the code must carry the design
        def code():
            self.human(takeover="design")
            return module_stage.describe(self.project.root, state_extra="x").rsplit("spec-guard-state: ", 1)[1][:8]
        self.design()
        first = code()
        self.design(rounds=[self.round(1, 2)])
        self.assertEqual(self.approval()["status"], "in-review")
        self.assertNotEqual(code(), first)

    def test_module_checkout_follows_the_route(self):
        # R2-4
        cmd = module_stage.commands(None, True)
        self.design()
        by_id = {"a": module_state(self.project.root, "a")}
        self.human(takeover="design")
        step = module_stage.role_view(self.project.root, "module", "a", by_id, cmd, "", True)[1]
        self.assertIn("第二审查者", step)
        self.assertNotIn("请用户审", step)
        self.design("- 新增 `src/a/new.py`")
        self.human()
        step = module_stage.role_view(self.project.root, "module", "a", by_id, cmd, "", True)[1]
        self.assertIn("交给协调会话请用户审", step)


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
        self.assertIn("Plan `tasks/a/plan.md` 正在等用户批准", hint(self.project, route={}))



class FlowOverreachTest(unittest.TestCase):
    """plan-auto-approve AC4, AC5: a v2 build is checked against its boundary plus its design's impact, any takeover."""

    def setUp(self):
        self.project = Project().__enter__()
        self.addCleanup(self.project.__exit__, None, None, None)
        self.project.write("src/a/old.py", "x\n")
        self.project.write("src/other.py", "x\n")
        self.project.write(".agent/config.json", json.dumps({"version": 1, **REVIEWER_ROUTE}))
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



class T4Test(FlowOverreachTest):
    """plan-auto-approve AC6: a T4 change stops a module that is not important; the check stands apart from scope."""

    RISK = {"schema": "autopilot.risk-paths/v1", "T4": ["src/secret/**"], "T3": []}

    def setUp(self):
        super().setUp()
        self.project.write("src/secret/k.py", "x\n")
        self.project.write(".github/autopr/risk-paths.json", json.dumps(self.RISK))
        self.commit("risk list")

    def test_a_t4_change_stops_a_normal_module(self):
        self.build(impact="- 改 `src/a/old.py`")
        self.project.write("src/secret/k.py", "changed\n")
        text = hint(self.project)
        self.assertIn("T4 路径：改到 1 个 T4 文件（`src/secret/k.py`）", text)
        self.assertIn("停点规则（中途 gate）", text)
        self.assertIn("高风险文件", module_stage.scope_overreach(self.project.root, "a", "BUILDING", True)[2])

    def test_a_bug_without_a_boundary_is_still_stopped(self):
        self.build("bug")
        self.project.write("src/secret/k.py", "changed\n")
        text = hint(self.project)
        self.assertIn("越界：没有并行边界，未检查。", text)
        self.assertIn("T4 路径：改到 1 个 T4 文件", text)
        self.assertIn("停点规则（中途 gate）", text)

    def test_an_important_module_changing_its_listed_t4_path_goes_on(self):
        from module_stage import REVIEW_PENDING, review_approved_line, review_codex_digest
        self.build("important", impact="- 改 `src/a/old.py`、`src/secret/k.py`")
        path = self.project.root / "tasks" / "a" / "design.md"
        text = path.read_text(encoding="utf-8").replace("\n", "\n\n%s\n" % REVIEW_PENDING, 1)
        path.write_text(text.replace(REVIEW_PENDING, review_approved_line(review_codex_digest(text))), encoding="utf-8")
        self.commit("design approved")
        self.project.write("src/secret/k.py", "changed\n")
        text = hint(self.project)
        self.assertNotIn("T4 路径", text)
        self.assertNotIn("停点规则（中途 gate）", text)

    def test_listing_the_path_makes_the_module_important(self):
        self.build(impact="- 改 `src/a/old.py`")
        self.project.write("src/secret/k.py", "changed\n")
        self.project.write("tasks/a/design.md", design_text("- 改 `src/a/old.py`、`src/secret/k.py`"))
        self.assertIn("risk-path", module_stage.important(self.project.root, "a"))
        self.assertEqual(module_stage.design_approval(self.project.root, "a")["status"], "pending-user")

    def test_an_unreadable_list_is_reported_not_stopped(self):
        (self.project.root / ".github" / "autopr" / "risk-paths.json").write_text("{", encoding="utf-8")
        self.commit("broken list, before the module")
        self.build()
        text = hint(self.project)
        self.assertIn("T4 路径：没有可读的风险路径清单，未检查。", text)
        self.assertNotIn("停点规则（中途 gate）", text)

    def test_no_baseline_is_not_taken_for_no_change(self):
        approved_spec(self.project, "bug")
        self.project.write("tasks/a/plan.md", "# Plan\n")
        self.project.write("tasks/a/todo.md", "- [ ] t\n")  # nothing committed: no baseline
        self.project.write("src/secret/k.py", "changed\n")
        self.assertIn("T4 路径：没有开工基线可比", hint(self.project))



# regression-doc-check: the case format, its parser and the per-case sha256 (Task 1).
CASES_ZH = """# 回归

## 用例清单

### R1: 正常保存
- 步骤：打开页面，
  点保存
- 预期：提示已保存
- 执行方式：command
- 命令：
  ```bash
  python3 -m pytest tests/test_save.py
  ```
- 证据：运行输出

### R2：手工核对
- 步骤：看一眼
- 预期：没变
- 执行方式：manual
- 证据：用户原话

## 成功标准对照

| 成功标准 | 用例 |
|---|---|
| S1 | R1、R2 |
| S2 | R3 |

## 受影响的老功能

### R3: 老的导出
- 步骤：导出
- 预期：同以前
- 执行方式：script
- 命令：`./scripts/export.sh`
- 证据：运行输出
"""

CASES_EN = """# Regression

## Cases

### R1: save
- Steps: open, save
- Expected: saved
- Method: ai-operate
- Evidence: screenshot

## Success criteria coverage

| Criterion | Cases |
|---|---|
| S1 | R1 |

## Affected existing features

不涉及
"""


def criteria_requirement(*ids, tier="normal"):
    body = "".join("- **%s** 能做到 %s\n" % (sid, sid) for sid in ids)
    return requirement(tier).replace("## 成功标准\n\n不涉及\n", "## 成功标准\n\n%s" % body)


class RegressionParseTest(unittest.TestCase):
    def parse(self, text, criteria=("S1", "S2")):
        import regression_view
        return regression_view.parse_regression(text, "module", list(criteria))

    def test_chinese_document_parses_every_field(self):
        result = self.parse(CASES_ZH)
        self.assertEqual(result["problems"], [])
        r1, r2, r3 = result["cases"]
        self.assertEqual((r1["id"], r1["title"], r1["method"]), ("R1", "正常保存", "command"))
        self.assertEqual(r1["steps"], "打开页面，\n点保存")
        self.assertEqual(r1["command"], "python3 -m pytest tests/test_save.py")
        self.assertEqual((r1["criteria"], r1["affectedExisting"]), (["S1"], False))
        self.assertEqual((r2["command"], r2["criteria"]), (None, ["S1"]))
        self.assertEqual((r3["command"], r3["criteria"], r3["affectedExisting"]), ("./scripts/export.sh", ["S2"], True))
        self.assertTrue(all(len(case["sha256"]) == 64 for case in result["cases"]))

    def test_english_document_parses(self):
        result = self.parse(CASES_EN, criteria=("S1",))
        self.assertEqual(result["problems"], [])
        self.assertEqual([(c["id"], c["method"], c["evidence"]) for c in result["cases"]], [("R1", "ai-operate", "screenshot")])

    def test_fenced_heading_is_not_a_case(self):
        text = CASES_EN.replace("## Success criteria coverage", "```\n### R9: no\n```\n\n## Success criteria coverage")
        self.assertEqual([c["id"] for c in self.parse(text, ("S1",))["cases"]], ["R1"])

    def test_criteria_ids_come_from_the_requirement(self):
        import regression_view
        self.assertEqual(regression_view.criteria_ids(criteria_requirement("S1", "S2", "S3")), ["S1", "S2", "S3"])
        self.assertEqual(regression_view.criteria_ids(requirement()), [])

    def test_sha256_ignores_whitespace_and_title_not_content(self):
        base = {c["id"]: c["sha256"] for c in self.parse(CASES_ZH)["cases"]}
        spaced = (CASES_ZH.replace("- 预期：提示已保存", "- 预期：  提示已保存  ").replace("### R1: 正常保存", "### R1: 别的标题")
                  .replace("- 步骤：打开页面，\n  点保存", "- 步骤：打开页面，   点保存"))  # one line vs two: same words
        self.assertEqual({c["id"]: c["sha256"] for c in self.parse(spaced)["cases"]}, base)
        for old, new in (("提示已保存", "提示失败"), ("tests/test_save.py", "tests/other.py"), ("- 证据：用户原话", "- 证据：截图")):
            changed = {c["id"]: c["sha256"] for c in self.parse(CASES_ZH.replace(old, new))["cases"]}
            with self.subTest(old=old):
                self.assertNotEqual(changed, base)

    def test_each_problem_code(self):
        cases = [
            ("case-field-missing", CASES_EN.replace("- Expected: saved\n", "")),
            ("case-method-invalid", CASES_EN.replace("Method: ai-operate", "Method: eyeball")),
            ("case-command-missing", CASES_EN.replace("Method: ai-operate", "Method: command")),
            ("case-command-unexpected", CASES_EN.replace("- Evidence: screenshot", "- Command: ls\n- Evidence: screenshot")),
            ("case-id-duplicate", CASES_EN.replace("## Success criteria coverage", CASES_EN.split("## Cases\n\n")[1].split("## Success")[0] + "## Success criteria coverage")),
            ("criterion-uncovered", CASES_EN),
            ("criterion-unknown", CASES_EN.replace("| S1 | R1 |", "| S1 | R1 |\n| S9 | R1 |")),
            ("case-unknown", CASES_EN.replace("| S1 | R1 |", "| S1 | R1, R7 |")),
            ("no-cases", CASES_EN.split("### R1")[0] + "## Success criteria coverage\n\n不涉及\n\n## Affected existing features\n\n不涉及\n"),
        ]
        for code, text in cases:
            with self.subTest(code=code):
                criteria = ("S1", "S2") if code == "criterion-uncovered" else ("S1",)
                codes = [p["code"] for p in self.parse(text, criteria)["problems"]]
                self.assertIn(code, codes)



def git(root, *args):
    return subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                          capture_output=True, text=True, check=True).stdout.strip()


def commit_all(root, message="c"):
    git(root, "add", "-A")
    git(root, "commit", "-qm", message, "--allow-empty")
    return git(root, "rev-parse", "HEAD")


class RegressionViewCliTest(unittest.TestCase):
    """regression-doc-check Task 2: the CLI, its exit codes and --ref."""

    def view(self, root, *args):
        done = subprocess.run([sys.executable, "-B", str(HERE / "regression_view.py"), "--json", "--project", str(root),
                               *args], capture_output=True, text=True)
        return done.returncode, (json.loads(done.stdout) if done.stdout.strip() else None)

    def setUp(self):
        self.ctx = Project()
        self.project = self.ctx.__enter__()
        self.addCleanup(self.ctx.__exit__)
        git(self.project.root, "init", "-q")

    def normal(self, cases=CASES_EN):
        self.project.write("spec/a.md", criteria_requirement("S1"))
        self.project.write("tasks/a/design.md", "## 影响面\n\n- `src/new.py`\n")
        self.project.write("tasks/a/regression.md", cases)

    def test_tiers_read_their_document(self):
        self.normal()
        code, out = self.view(self.project.root, "--module", "a")
        self.assertEqual((code, out["document"], out["tier"], out["problems"]), (0, "tasks/a/regression.md", "normal", []))
        self.assertEqual(out["sha256"], __import__("hashlib").sha256(CASES_EN.encode()).hexdigest())
        short = CASES_EN.split("## Cases\n\n")[1].split("## Success")[0]
        for tier in ("small", "bug"):
            with self.subTest(tier=tier):
                spec = (criteria_requirement("S1", tier=tier) if tier == "small" else requirement(tier))
                spec += "## 回归用例\n\n" + short + ("| 成功标准 | 用例 |\n|---|---|\n| S1 | R1 |\n" if tier == "small" else "")
                self.project.write("spec/a.md", spec)
                code, out = self.view(self.project.root, "--module", "a")
                self.assertEqual((code, out["document"], [c["id"] for c in out["cases"]], out["problems"]),
                                 (0, "spec/a.md", ["R1"], []))

    def test_errors(self):
        self.assertEqual(self.view(self.project.root, "--module", "zz")[0], 2)
        self.project.write("spec/a.md", "# a\n")
        self.assertEqual(self.view(self.project.root, "--module", "a"), (3, {"schemaVersion": 1, "error": "not-flow-v2"}))
        self.project.write("spec/a.md", criteria_requirement("S1"))
        self.assertEqual(self.view(self.project.root, "--module", "a"), (3, {"schemaVersion": 1, "error": "no-document"}))
        self.assertEqual(self.view(self.project.root, "--usage", "../x")[0], 2)

    def test_ref_reads_that_commit(self):
        self.normal()
        first = commit_all(self.project.root)
        self.normal(CASES_EN.replace("- Expected: saved", "- Expected: changed"))
        code, old = self.view(self.project.root, "--module", "a", "--ref", first)
        _code, new = self.view(self.project.root, "--module", "a")
        self.assertEqual((code, old["ref"], old["cases"][0]["expected"], new["cases"][0]["expected"]),
                         (0, first, "saved", "changed"))
        self.assertNotEqual(old["cases"][0]["sha256"], new["cases"][0]["sha256"])
        self.assertEqual(self.view(self.project.root, "--module", "a", "--ref", "no-such-ref"),
                         (4, {"schemaVersion": 1, "error": "unreadable"}))

    def test_ref_without_the_document(self):
        self.project.write("spec/a.md", criteria_requirement("S1"))
        first = commit_all(self.project.root)
        self.normal()
        self.assertEqual(self.view(self.project.root, "--module", "a", "--ref", first),
                         (3, {"schemaVersion": 1, "error": "not-at-ref"}))

    def test_ref_tier_comes_from_that_commit(self):
        short = CASES_EN.split("## Cases\n\n")[1].split("## Success")[0]
        self.project.write("spec/a.md", criteria_requirement("S1", tier="small") + "## 回归用例\n\n" + short
                           + "| 成功标准 | 用例 |\n|---|---|\n| S1 | R1 |\n")
        first = commit_all(self.project.root)
        self.normal()
        code, out = self.view(self.project.root, "--module", "a", "--ref", first)
        self.assertEqual((code, out["tier"], out["document"]), (0, "small", "spec/a.md"))

    def test_ref_sees_a_batch_insert_as_important(self):
        self.project.write("spec/CAPABILITY-MAP.md", "# Capability Map: t\n\n| Module id | Responsibility | Depends on |\n"
                           "|---|---|---|\n| z | x | — |\n\nBuild order: z\n")
        commit_all(self.project.root)
        self.project.write("spec/CAPABILITY-MAP.md", "# Capability Map: t\n\n| Module id | Responsibility | Depends on |\n"
                           "|---|---|---|\n| z | x | — |\n| a | x | — |\n| b | x | — |\n\nBuild order: z → a → b\n")
        self.project.write("spec/a.md", criteria_requirement("S1", tier="small"))
        self.project.write("tasks/a/regression.md", CASES_EN)
        first = commit_all(self.project.root)
        code, out = self.view(self.project.root, "--module", "a", "--ref", first)
        self.assertEqual((code, out["tier"], out["document"]), (0, "important", "tasks/a/regression.md"))

    def test_ref_bytes_are_the_raw_blob(self):
        crlf = CASES_EN.replace("\n", "\r\n")
        self.project.write("spec/a.md", criteria_requirement("S1"))
        (self.project.root / "tasks" / "a").mkdir(parents=True)
        (self.project.root / "tasks" / "a" / "regression.md").write_bytes(crlf.encode())
        # text eol=crlf: the blob is stored with LF, a checkout writes CRLF -- only the raw blob gives the blob's digest
        self.project.write(".gitattributes", "tasks/a/regression.md text eol=crlf export-ignore export-subst\n")
        first = commit_all(self.project.root)
        blob = subprocess.run(["git", "-C", str(self.project.root), "cat-file", "blob", first + ":tasks/a/regression.md"],
                              capture_output=True, check=True).stdout
        sha = __import__("hashlib").sha256
        self.assertNotEqual(blob, crlf.encode())
        for args, digest in (((), sha(crlf.encode()).hexdigest()), (("--ref", first), sha(blob).hexdigest())):
            with self.subTest(args=args):
                code, out = self.view(self.project.root, "--module", "a", *args)
                self.assertEqual((code, out["sha256"], out["problems"]), (0, digest, []))



SHORT_CASE = CASES_EN.split("## Cases\n\n")[1].split("## Success")[0]


def flow_problems(project):
    return module_stage.flow_doc_problems(project.root, "a")


class RegressionProblemsTest(unittest.TestCase):
    """regression-doc-check Task 3: regression problems in flow_doc_problems (verify-artifacts and the hint)."""

    def setUp(self):
        self.ctx = Project()
        self.project = self.ctx.__enter__()
        self.addCleanup(self.ctx.__exit__)

    def write(self, cases, impact="- `src/new.py`", criteria=("S1",)):
        approved_spec(self.project)
        self.project.write("spec/a.md", criteria_requirement(*criteria))
        self.project.write("tasks/a/design.md", "".join("## %s\n\n%s\n\n" % (n, impact if n == "影响面" else "不涉及")
                                                        for n in DOC_SECTIONS["design"]["zh"]))
        self.project.write("tasks/a/regression.md", cases)

    def test_valid_document_has_no_problem(self):
        self.write(CASES_EN)
        self.assertEqual(flow_problems(self.project), [])

    def test_problem_is_a_failure_with_code_and_place(self):
        self.write(CASES_EN.replace("Method: ai-operate", "Method: command"))
        self.assertEqual(flow_problems(self.project),
                         [("fail", "`tasks/a/regression.md` 回归问题：case-command-missing（R1）")])

    def test_every_criterion_needs_a_case(self):
        self.write(CASES_EN, criteria=("S1", "S2", "S3"))
        found = [m for _l, m in flow_problems(self.project)]
        self.assertIn("`tasks/a/regression.md` 回归问题：criterion-uncovered（S2）", found)
        self.write(CASES_EN.replace("| S1 | R1 |", "| S1 | R1 |\n| S9 | R1 |"))
        self.assertIn("criterion-unknown", " ".join(m for _l, m in flow_problems(self.project)))

    def test_old_files_in_the_impact_need_an_affected_case(self):
        self.project.write("src/old.py", "x = 1\n")
        self.write(CASES_EN, impact="- `src/old.py`")
        self.assertEqual(flow_problems(self.project),
                         [("fail", "`tasks/a/regression.md` 回归问题：affected-existing-empty（tasks/a/regression.md）")])
        self.write(CASES_EN.replace("## Affected existing features\n\n不涉及\n",
                                    "## Affected existing features\n\n" + SHORT_CASE.replace("R1", "R2")), impact="- `src/old.py`")
        self.assertEqual(flow_problems(self.project), [])

    def test_old_module_is_untouched(self):
        self.project.write("spec/a.md", "# a\n")
        self.project.write("tasks/a/regression.md", "nothing\n")
        self.assertEqual(flow_problems(self.project), [])


class ShortTierCasesTest(unittest.TestCase):
    """regression-doc-check Task 3: bug and small cases live in spec/<id>.md (R1-3, R2-3)."""

    def setUp(self):
        self.ctx = Project()
        self.project = self.ctx.__enter__()
        self.addCleanup(self.ctx.__exit__)

    def spec(self, tier, cases=""):
        own = DOC_SECTIONS["bug"]["zh"] if tier == "bug" else DOC_SECTIONS["requirement"]["zh"] + DOC_SECTIONS["small"]["zh"]
        body = "# a\n\n%s\n\n" % marker(tier)
        for name in own:
            if name == "回归用例":
                body += "## 回归用例\n\n%s\n\n" % (cases or "不涉及")
            elif name == "成功标准" and tier == "small":
                body += "## 成功标准\n\n- **S1** 能做到\n\n"
            else:
                body += "## %s\n\n不涉及\n\n" % name
        self.project.write("spec/a.md", body)

    def test_small_cases_are_checked_like_normal(self):
        self.spec("small")
        self.assertIn(("fail", "`spec/a.md` 回归问题：no-cases（spec/a.md）"), flow_problems(self.project))
        self.spec("small", SHORT_CASE + "| 成功标准 | 用例 |\n|---|---|\n| S1 | R1 |\n")
        self.assertEqual(flow_problems(self.project), [])
        self.spec("small", SHORT_CASE)
        self.assertEqual(flow_problems(self.project), [("fail", "`spec/a.md` 回归问题：criterion-uncovered（S1）")])

    def test_bug_without_a_case_by_stage(self):
        self.spec("bug")
        self.assertEqual(flow_problems(self.project), [])  # only the Spec
        self.project.write("tasks/a/plan.md", "# Plan\n\n## 任务\n\n- fix\n\n## 检查点\n\n不涉及\n")
        self.assertEqual([l for l, _m in flow_problems(self.project)], ["warn"])  # a Plan and no todo
        self.project.write("tasks/a/todo.md", "# Todo\n")
        self.assertEqual([l for l, _m in flow_problems(self.project)], ["warn"])  # an empty todo
        self.project.write("tasks/a/todo.md", "- [x] fix\n- [ ] Checkpoint（gate）：验收\n")
        self.assertEqual([l for l, _m in flow_problems(self.project)], ["warn"])  # building, final gate open
        self.project.write("tasks/a/todo.md", "- [x] fix\n- [x] Checkpoint（gate）：验收\n")
        self.assertEqual(flow_problems(self.project), [("fail", "`spec/a.md` 回归问题：no-cases（spec/a.md）")])
        self.project.write("tasks/a/todo.md", "- [x] fix\n- [ ] 延期：调研；恢复条件：有人要\n")
        self.assertEqual([l for l, _m in flow_problems(self.project)], ["fail"])  # only a formal deferral left
        self.spec("bug", SHORT_CASE)
        self.assertEqual(flow_problems(self.project), [])

    def test_bug_case_format_is_checked(self):
        self.spec("bug", SHORT_CASE.replace("Method: ai-operate", "Method: guess"))
        self.assertEqual(flow_problems(self.project), [("fail", "`spec/a.md` 回归问题：case-method-invalid（R1）")])


class ProjectSectionContentTest(unittest.TestCase):
    """regression-doc-check Task 3: a declared project section needs content or 不涉及 (Q2 A: only those)."""

    def test_heading_only_fails_and_skeleton_sections_are_not_checked(self):
        with Project() as project:
            project.write(".agent/config.json", json.dumps({"version": 1, "projectSections": {"design": ["浏览器兼容"]}}))
            approved_spec(project)
            skeleton = "".join("## %s\n\n" % n for n in DOC_SECTIONS["design"]["zh"])  # skeleton sections left empty
            for body, expected in (("## 浏览器兼容\n\n<!-- 待写 -->\n", [("fail", "`tasks/a/design.md` 章节没有内容（section-empty）：浏览器兼容")]),
                                   ("## 浏览器兼容\n", [("fail", "`tasks/a/design.md` 章节没有内容（section-empty）：浏览器兼容")]),
                                   ("## 浏览器兼容\n\n不涉及\n", []),
                                   ("## 浏览器兼容\n\n```\nie11\n```\n", [])):
                with self.subTest(body=body):
                    project.write("tasks/a/design.md", skeleton + body)
                    self.assertEqual(flow_problems(project), expected)



class RegressionHintTest(unittest.TestCase):
    """regression-doc-check Task 4: the stage hint names regression problems while the Plan or the build is on."""

    def setUp(self):
        self.ctx = Project()
        self.project = self.ctx.__enter__()
        self.addCleanup(self.ctx.__exit__)

    def building(self, cases):
        approved_spec(self.project)
        self.project.write("tasks/a/design.md", "## 影响面\n\n- `src/new.py`\n")
        self.project.write("tasks/a/regression.md", cases.replace("| S1 | R1 |\n", ""))  # requirement() has no S<n>
        self.project.write("tasks/a/plan.md", "# Plan\n\n## 任务\n\n- t\n\n## 检查点\n\n- c\n")
        self.project.write("tasks/a/todo.md", "- [ ] t\n")

    def test_problems_are_named_and_go_away(self):
        bad = CASES_EN.replace("Method: ai-operate", "Method: command")
        self.building(bad)
        self.assertIn("- 回归文档：`tasks/a/regression.md` 有 1 处问题：case-command-missing（R1）；完整列表跑 verify-artifacts。",
                      hint(self.project))
        self.building(CASES_EN)
        self.assertNotIn("- 回归文档：", hint(self.project))
        self.building(bad)
        self.assertIn("- Regression: `tasks/a/regression.md` has 1 problem(s): case-command-missing (R1); run verify-artifacts "
                      "for the full list.", hint(self.project, zh=False))

    def test_state_code_follows_the_problem_count(self):
        self.building(CASES_EN.replace("Method: ai-operate", "Method: command"))
        hint(self.project)
        one = module_stage.describe(self.project.root, state_extra="x").rsplit("spec-guard-state: ", 1)[1]
        self.building(CASES_EN.replace("Method: ai-operate", "Method: command").replace("- Expected: saved\n", ""))
        two = module_stage.describe(self.project.root, state_extra="x").rsplit("spec-guard-state: ", 1)[1]
        self.assertNotEqual(one, two)

    def test_bug_without_a_case_is_reminded_while_building(self):
        self.project.write("spec/a.md", "# a\n\n%s\n\n" % marker("bug")
                           + "".join("## %s\n\n不涉及\n\n" % n for n in DOC_SECTIONS["bug"]["zh"]))
        self.project.write("tasks/a/plan.md", "# Plan\n\n## 任务\n\n- t\n\n## 检查点\n\n- c\n")
        self.project.write("tasks/a/todo.md", "- [ ] t\n")
        self.assertIn("- 回归用例：修完在 `spec/a.md` 的回归用例一节补一条用例。", hint(self.project))

    def test_old_module_has_no_line(self):
        self.project.write("spec/a.md", "# a\n")
        self.project.write("tasks/a/plan.md", "# Plan\n")
        self.project.write("tasks/a/todo.md", "- [ ] t\n")
        self.assertNotIn("回归", hint(self.project))



USAGE_REGRESSION = """# 联调回归

## 用例清单

### R1: 两个模块一起用
- 步骤：先 a 后 b
- 预期：b 读到 a 的结果
- 执行方式：script
- 命令：`./scripts/e2e.sh`
- 证据：运行输出

## 成功标准 → 联调用例

| 成功标准 | 用例 |
|---|---|
| S2 | R1 |

## 涉及的模块

- `a`
- `b`
"""


class UsageRegressionTest(unittest.TestCase):
    """regression-doc-check Task 5 (Q1 A): spec/usage/<name>.regression.md."""

    def report(self, project):
        import regression_view
        return regression_view.usage_report(project.root, "demo")

    def test_parses_and_checks(self):
        with Project(("a", "b")) as project:
            project.write("spec/usage/demo.md", "# Usage draft: demo\n\n## 成功标准\n\n- **S1** x\n- **S2** y\n")
            project.write("spec/usage/demo.regression.md", USAGE_REGRESSION)
            out = self.report(project)
            self.assertEqual((out["problems"], out["modules"], out["usage"], out["module"]), ([], ["a", "b"], "demo", None))
            self.assertEqual(out["cases"][0]["criteria"], ["S2"])
            project.write("spec/usage/demo.regression.md", USAGE_REGRESSION.replace("- `b`", "- `zz`").replace("| S2 |", "| S7 |"))
            self.assertEqual(sorted(p["code"] for p in self.report(project)["problems"]), ["criterion-unknown", "module-unknown"])

    def test_draft_without_criteria_and_table_without_ids(self):
        with Project(("a", "b")) as project:
            project.write("spec/usage/demo.md", "# Usage draft: demo\n\n## Entry points\n\nx\n")
            project.write("spec/usage/demo.regression.md", USAGE_REGRESSION.replace("| S2 | R1 |\n", ""))
            self.assertEqual(self.report(project)["problems"], [])
            project.write("spec/usage/demo.regression.md", USAGE_REGRESSION)
            self.assertEqual([p["code"] for p in self.report(project)["problems"]], ["criterion-unknown"])

    def test_cli(self):
        with Project(("a", "b")) as project:
            project.write("spec/usage/demo.regression.md", USAGE_REGRESSION.replace("| S2 | R1 |\n", ""))
            done = subprocess.run([sys.executable, "-B", str(HERE / "regression_view.py"), "--json", "--project",
                                   str(project.root), "--usage", "demo"], capture_output=True, text=True)
            self.assertEqual((done.returncode, json.loads(done.stdout)["document"]), (0, "spec/usage/demo.regression.md"))



class RegressionInterfaceTest(unittest.TestCase):
    """regression-doc-check Task 6: interface.json's regressionView runs as written and describes the output."""

    def test_command_template_runs_and_matches_the_fields(self):
        entry = json.loads((HERE.parent / "interface.json").read_text(encoding="utf-8"))["regressionView"]
        with Project() as project:
            git(project.root, "init", "-q")
            project.write("spec/a.md", criteria_requirement("S1"))
            project.write("tasks/a/regression.md", CASES_EN)
            first = commit_all(project.root)
            fill = {"<project-root>": str(project.root), "<module-id>": "a", "<git ref>": first}
            for extra in ([], entry["refArgs"]):
                with self.subTest(ref=bool(extra)):
                    command = [fill.get(arg, arg) for arg in entry["command"] + extra]
                    done = subprocess.run(command, cwd=HERE.parent, capture_output=True, text=True)
                    self.assertEqual(done.returncode, 0, done.stderr)
                    out = json.loads(done.stdout)
                    self.assertEqual(out["schemaVersion"], entry["schemaVersion"])
                    self.assertEqual(set(out), {"schemaVersion", "module", "usage", "tier", "document", "sha256", "ref",
                                                "criteria", "cases", "problems"})
                    self.assertEqual(set(out["cases"][0]), {"id", "title", "steps", "expected", "method", "command",
                                                            "evidence", "criteria", "affectedExisting", "sha256"})
                    self.assertIn(out["cases"][0]["method"], entry["values"]["method"])



class VerificationHintTest(unittest.TestCase):
    """verification-criteria Task 4: the author line, the four verification states and the final gate (AC7, AC8)."""

    GATE = "- [x] t\n- [ ] Checkpoint 2（gate）：最终验收\n"

    def setUp(self):
        import os
        self.ctx = Project()
        self.project = self.ctx.__enter__()
        self.addCleanup(self.ctx.__exit__)
        self.root = self.project.root
        git(self.root, "init", "-q", "-b", "main")
        approved_spec(self.project)
        self.project.write("tasks/a/design.md", "## 影响面\n\n- `src/new.py`\n")
        self.project.write("tasks/a/regression.md", CASES_EN.replace("| S1 | R1 |\n", ""))
        self.project.write("tasks/a/plan.md", "# Plan\n\n## 任务\n\n- t\n\n## 检查点\n\n- c\n")
        self.project.write("tasks/a/todo.md", "- [ ] t\n")
        commit_all(self.root, "base")
        git(self.root, "switch", "-q", "-c", "feature")
        self.project.write("src/new.py", "x = 1\n")
        commit_all(self.root, "change")
        self.env = {k: os.environ.pop(k) for k in ("CLAUDE_CODE_SESSION_ID", "CODEX_THREAD_ID") if k in os.environ}
        self.addCleanup(os.environ.update, self.env)

    def author(self):
        import os
        import verification
        os.environ["CLAUDE_CODE_SESSION_ID"] = "author-1"
        try:
            verification.add_author(self.root, "a")
        finally:
            os.environ.pop("CLAUDE_CODE_SESSION_ID")

    def put(self, verdict, patch=None):
        import hashlib
        import verification
        path = verification._record_path(self.root, verification.RECORDS_DIR, "a")
        sha = hashlib.sha256((self.root / "tasks" / "a" / "regression.md").read_bytes()).hexdigest()
        verification._write_atomic(path, {"schema": verification.SCHEMA, "module": "a", "usage": None, "verdict": verdict,
                                          "patchId": patch or verification.current_patch_id(self.root),
                                          "regressionSha256": sha, "notes": ["n"], "reportSha256": "0" * 64})

    def at_gate(self):
        self.project.write("tasks/a/todo.md", self.GATE)

    def test_author_line_until_recorded(self):
        text = hint(self.project)
        self.assertIn("- 作者记录：", text)
        self.assertIn("verification.py author --project", text)
        self.author()
        self.assertNotIn("- 作者记录：", hint(self.project))

    def test_four_states_at_the_final_gate(self):
        self.author()
        self.at_gate()
        self.assertIn("- 合并前验证：还没有结论", hint(self.project))
        self.put("pass-with-notes")
        self.assertIn("- 合并前验证：通过但附意见（1 条）", hint(self.project))
        self.put("fail")
        self.assertIn("- 合并前验证：不通过", hint(self.project))
        self.put("pass", patch="0" * 40)
        self.assertIn("- 合并前验证：结论已过期", hint(self.project))

    def test_state_code_follows_the_verification(self):
        self.author()
        self.at_gate()
        hint(self.project)
        none = module_stage.describe(self.root, state_extra="x").rsplit("spec-guard-state: ", 1)[1]
        self.put("fail")
        self.assertNotEqual(module_stage.describe(self.root, state_extra="x").rsplit("spec-guard-state: ", 1)[1], none)

    def test_merge_auto_passes_the_final_gate_only_with_a_current_passing_verdict(self):
        self.author()
        self.at_gate()
        route = {"takeover": "merge"}
        hint(self.project, route=route)
        self.assertEqual(module_state(self.root, "a")["stage"], "BUILDING")
        self.put("fail")
        self.assertEqual(module_state(self.root, "a")["stage"], "BUILDING")
        self.put("pass", patch="0" * 40)
        self.assertEqual(module_state(self.root, "a")["stage"], "BUILDING")
        self.put("pass")
        self.assertEqual(module_state(self.root, "a")["stage"], "DONE")

    def test_codex_acceptance_record_does_not_count_for_flow_v2(self):
        self.author()
        self.at_gate()
        hint(self.project, route={"takeover": "merge"})
        path = module_stage.acceptance_path(self.root, "a")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"marker": "codex-approved", "module": "a",
                                    "sha": git(self.root, "rev-parse", "HEAD")}), encoding="utf-8")
        self.assertIsNone(module_stage.acceptance_record(self.root, "a"))
        self.assertEqual(module_state(self.root, "a")["stage"], "BUILDING")
        self.assertNotIn("本模块合并是自动的，最终验收交 Codex", hint(self.project, route={"takeover": "merge"}))

    def test_merge_human_still_stops_for_the_user(self):
        self.author()
        self.at_gate()
        self.put("pass")
        text = hint(self.project, route={})
        self.assertEqual(module_state(self.root, "a")["stage"], "BUILDING")
        self.assertIn("- 合并前验证：通过", text)



class BugCaseNoReconfirmTest(unittest.TestCase):
    """regression-doc-check Task 8 (M3 run, user "M3 A"): adding a case to a confirmed bug requirement keeps it confirmed."""

    CASE = "### R1: 修复后不报错\n- 步骤：运行\n- 预期：不报错\n- 执行方式：command\n- 命令：`make t`\n- 证据：运行输出\n"

    def spec(self, tier):
        own = DOC_SECTIONS["bug"]["zh"] if tier == "bug" else DOC_SECTIONS["requirement"]["zh"] + DOC_SECTIONS["small"]["zh"]
        return ("# a\n\n<!-- spec-guard: review pending -->\n%s\n\n" % marker(tier)
                + "".join("## %s\n\n不涉及\n\n" % name for name in own))

    def confirm(self, project, text):
        from module_stage import review_approved_line, review_digest
        project.write("spec/a.md", text.replace("<!-- spec-guard: review pending -->", review_approved_line(review_digest(text))))

    def edit(self, project, old, new):
        text = (project.root / "spec" / "a.md").read_text(encoding="utf-8")
        project.write("spec/a.md", text.replace(old, new, 1))

    def test_a_bug_case_added_after_confirmation_keeps_it_confirmed(self):
        with Project() as project:
            self.confirm(project, self.spec("bug"))
            self.edit(project, "## 回归用例\n\n不涉及\n", "## 回归用例\n\n" + self.CASE)
            self.assertIsNone(module_stage.requirement_wait(project.root, "a"))
            self.assertEqual(module_stage.requirement_confirm(project.root, "a")["status"], "confirmed")
            self.edit(project, "## 复现步骤\n\n不涉及\n", "## 复现步骤\n\n点保存\n")
            self.assertEqual(module_stage.requirement_wait(project.root, "a"), "revised")

    def test_a_small_case_still_counts(self):
        with Project() as project:
            self.confirm(project, self.spec("small"))
            self.edit(project, "## 回归用例\n\n不涉及\n", "## 回归用例\n\n" + self.CASE)
            self.assertEqual(module_stage.requirement_wait(project.root, "a"), "revised")

    def test_an_approval_written_by_the_old_algorithm_still_stands(self):
        from module_stage import review_approved_line, review_body
        with Project() as project:
            text = self.spec("bug").replace("## 回归用例\n\n不涉及\n", "## 回归用例\n\n" + self.CASE)
            whole = module_stage._text_digest(review_body(text))  # 0.96.0 and earlier: the whole body
            project.write("spec/a.md", text.replace("<!-- spec-guard: review pending -->", review_approved_line(whole)))
            self.assertIsNone(module_stage.requirement_wait(project.root, "a"))

    def test_a_fenced_heading_does_not_open_the_section(self):
        with Project() as project:
            text = self.spec("bug").replace("## 预期结果\n\n不涉及\n", "## 预期结果\n\n```\n## 回归用例\n```\n不涉及\n")
            self.confirm(project, text)
            self.edit(project, "```\n不涉及\n", "```\n不报错\n")
            self.assertEqual(module_stage.requirement_wait(project.root, "a"), "revised")



class ReworkOverreachTest(FlowOverreachTest):
    """rework-scope-baseline Task 2: a rework is checked from its first commit; the hint names it (AC2, AC6, AC7)."""

    def rework(self, commit=True):
        self.build()
        self.project.write("src/a/old.py", "built\n")
        self.project.write("tasks/a/todo.md", "- [x] t\n- [x] 最终验收（gate）\n")
        self.commit("done")
        self.project.write("src/later.py", "another module\n")
        self.commit("another module merges")
        self.project.write("tasks/a/todo.md", "- [x] t\n- [x] 最终验收（gate）\n- [ ] 返工\n- [ ] 返工验收（gate）\n")
        if commit:
            self.commit("rework")
        return git(self.project.root, "rev-parse", "HEAD")

    def test_another_modules_files_are_not_counted(self):
        start = self.rework()
        self.project.write("src/a/old.py", "reworked\n")
        self.assertNotIn("越界", hint(self.project))
        self.project.write("src/other.py", "changed\n")
        text = hint(self.project)
        self.assertIn("越界：1 个文件超出需求文档的并行边界与技术方案影响面（`src/other.py`）；返工：从提交 `%s` 起算。"
                      % start[:12], text)
        self.assertNotIn("src/later.py", text)

    def test_a_rework_not_committed_yet_compares_with_head(self):
        self.rework(commit=False)
        self.project.write("src/other.py", "changed\n")
        self.assertIn("（`src/other.py`）；返工：还没提交，与 HEAD 比较。", hint(self.project))

    def test_first_build_wording_is_unchanged(self):
        self.build()
        self.project.write("src/other.py", "changed\n")
        self.assertIn("越界：1 个文件超出需求文档的并行边界与技术方案影响面（`src/other.py`）。", hint(self.project))

    def test_start_of_the_module_stays_the_old_base(self):
        import module_scope
        self.rework()
        self.assertEqual(module_stage.module_baseline(self.project.root, "a"),
                         module_scope.default_base(self.project.root, "a"))
        self.assertNotEqual(module_scope.scope_base(self.project.root, "a"), module_scope.default_base(self.project.root, "a"))

    def test_merge_at_base_reads_the_start_of_the_module(self):
        import module_scope
        import review_mark
        self.build()
        self.project.write("tasks/a/todo.md", "- [x] t\n- [x] 最终验收（gate）\n")
        self.commit("done")
        # widened after the module was done and before the rework: the rework base sees merge=auto, the start does not
        self.project.write(".agent/config.json", json.dumps({"version": 1, "takeover": "merge"}))
        self.commit("widen")
        self.project.write("tasks/a/todo.md", "- [x] t\n- [x] 最终验收（gate）\n- [ ] 返工\n")
        self.commit("rework")
        self.assertIsNotNone(module_scope.rework_info(self.project.root, "a"))
        self.assertEqual(review_mark._merge_at_base(self.project.root, "a"), "human")


if __name__ == "__main__":
    unittest.main()
