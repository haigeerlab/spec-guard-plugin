"""sg-review-rules (autopilot module 5): one review round before the requirement is confirmed, designs reviewed only
on three high-risk reasons, the design approver from the takeover alone, and flow v2 important requirements decided
by risk paths only.  No network; every project is a temporary git repository."""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import module_stage  # noqa: E402
from module_stage import DOC_SECTIONS, important  # noqa: E402
import test_flow_v2 as tfv  # noqa: E402
import test_important_requirement as tir  # noqa: E402

_spec = tir._spec

V2 = "<!-- spec-guard: flow v2 tier=normal -->\n"


class ImportantV2(unittest.TestCase):
    """R11: a flow v2 module is important only on a risk path; an old module keeps all five rules."""
    git, config, risk, insert = tir.Important.git, tir.Important.config, tir.Important.risk, tir.Important.insert

    def setUp(self):
        tir.Important.setUp(self)
        self.config({})

    def test_v2_ignores_multi_and_cross_module(self):
        self.insert("alpha", "beta", specs={"alpha": V2 + _spec(shared="锁文件"), "beta": V2 + _spec()})
        self.assertEqual(important(self.root, "alpha"), [])
        self.insert("gamma", specs={"gamma": V2 + _spec("`src/a/x.py`")})
        self.assertEqual(important(self.root, "gamma"), [])

    def test_v2_risk_path_still_counts(self):
        self.insert("alpha", "beta", specs={"alpha": V2 + _spec("`.github/workflows/`"), "beta": V2 + _spec()})
        self.assertEqual(important(self.root, "alpha"), ["risk-path"])

    def test_old_flow_unchanged(self):
        self.insert("alpha", "beta", specs={"alpha": _spec(shared="锁文件"), "beta": _spec("`.github/x`")})
        self.assertEqual(important(self.root, "alpha"), ["multi-module", "cross-module"])
        self.assertEqual(important(self.root, "beta"), ["multi-module", "risk-path"])


RISK = {"schema": "autopilot.risk-paths/v1", "T4": ["src/secret/**"], "T3": []}
CMD = {"review-mark": "/spec-guard:review-mark", "author-host": "claude-code"}


def design(impact="- 新增 `src/a/new.py`", interface="不涉及"):
    """tasks/a/design.md with every section; `impact` and `interface` fill those two."""
    fill = {"影响面": impact, "接口和数据改动": interface}
    return "# 技术方案：a\n\n" + "".join("## %s\n\n%s\n\n" % (name, fill.get(name, "不涉及"))
                                    for name in DOC_SECTIONS["design"]["zh"])


class DesignRequirement(unittest.TestCase):
    """R6: a design is reviewed on risk-path, irreversible or new-dependency only; designReview: on still reviews."""

    def need(self, impact="- 新增 `src/a/new.py`", interface="不涉及", config=None, risk=True):
        with tfv.Project() as project:
            tfv.approved_spec(project)
            if risk:
                project.write(".github/autopr/risk-paths.json", json.dumps(RISK))
            if config:
                project.write(".agent/config.json", json.dumps(dict(version=1, **config)))
            project.write("tasks/a/design.md", design(impact, interface))
            return module_stage.design_requirement(project.root, "a")

    def test_risk_path(self):
        got = self.need("- 改 `src/secret/key.py`")
        self.assertEqual((got["need"], got["reason"], got["reasons"]), ("review", "risk-path", ["risk-path"]))

    def test_irreversible(self):
        got = self.need(interface="- `/map --json` 新字段 `x`")
        self.assertEqual((got["need"], got["reason"]), ("review", "irreversible"))

    def test_empty_interface_variants(self):
        for text in ("不涉及", "无。", "- 没有", "None", "n/a", "N/A.", "Not applicable", "no changes",
                     "<!-- x -->\n不涉及", "1. 无", ""):
            with self.subTest(text=text):
                self.assertEqual(self.need(interface=text)["reason"], None)
        self.assertEqual(self.need(interface="无\n- 新增表 t")["reason"], "irreversible")

    def test_new_dependency(self):
        for path in ("package.json", "web/package-lock.json", "requirements-dev.txt", "go.sum", "Cargo.lock",
                     "pyproject.toml"):
            with self.subTest(path=path):
                got = self.need("- 改 `%s`" % path)
                self.assertEqual((got["need"], got["reason"]), ("review", "new-dependency"))
        self.assertEqual(self.need("- 改 `docs/requirements.md`")["reason"], None)

    def test_several_reasons_keep_order(self):
        got = self.need("- 改 `src/secret/a.py`、`package.json`", interface="- 新字段")
        self.assertEqual((got["reason"], got["reasons"]), ("risk-path", ["risk-path", "irreversible", "new-dependency"]))

    def test_old_files_and_no_path_are_not_reasons(self):
        self.assertEqual(self.need("- 改 `plugins/x/old.py`")["need"], "none")
        self.assertEqual(self.need("- 改几处老逻辑")["need"], "none")

    def test_important_is_not_a_reason(self):
        with tfv.Project() as project:
            tfv.approved_spec(project, "important")
            project.write("tasks/a/design.md", design())
            got = module_stage.design_requirement(project.root, "a")
        self.assertEqual((got["need"], got["reason"]), ("none", None))

    def test_configured(self):
        got = self.need(config={"designReview": "on"})
        self.assertEqual((got["need"], got["reason"], got["reasons"]), ("review", "configured", ["configured"]))


class RiskListHint(unittest.TestCase):
    """R7: without a readable risk-path list the design stage says risk-path was not checked, waiting or not."""

    def run_hint(self, risk, route=None, impact="- 改 `src/secret/key.py`"):
        with tfv.Project() as project:
            tfv.approved_spec(project)
            if risk:
                project.write(".github/autopr/risk-paths.json", json.dumps(RISK))
            project.write("tasks/a/design.md", design(impact))
            need = module_stage.design_requirement(project.root, "a")
            zh = tfv.hint(project, route=route)
            en = tfv.hint(project, zh=False, route=route)
            stage = module_stage.module_state(project.root, "a")["stage"]
        return need, zh, en, stage

    def test_no_list(self):
        need, zh, en, stage = self.run_hint(False, route={})
        self.assertEqual((need["riskList"], need["reasons"], stage), ("no-list", [], "NEEDS_REGRESSION"))
        self.assertEqual(zh.count("T4 路径：没有可读的风险路径清单，`risk-path` 未检查"), 1)
        self.assertIn("no readable risk-path list, `risk-path` not checked", en)

    def test_no_list_when_the_design_needs_no_review(self):
        # round 2 finding 1: design=reviewer and nothing to review lets the design through, the line still shows
        need, zh, _en, _stage = self.run_hint(False)
        self.assertEqual(need["need"], "none")
        self.assertIn("T4 路径：没有可读的风险路径清单，`risk-path` 未检查", zh)
        self.assertNotIn("技术方案 `tasks/a/design.md`", zh)

    def test_list(self):
        need, zh, _en, _stage = self.run_hint(True)
        self.assertEqual((need["riskList"], need["reasons"]), ("ok", ["risk-path"]))
        self.assertNotIn("没有可读的风险路径清单", zh)


class DesignApprover(unittest.TestCase):
    """R8: under design=reviewer an important requirement's design is let through by the second reviewer too."""

    def setUp(self):
        self.project = tfv.Project().__enter__()
        self.addCleanup(self.project.__exit__, None, None, None)
        tfv.approved_spec(self.project, "important")
        self.project.write(".github/autopr/risk-paths.json", json.dumps(RISK))

    def approval(self, route, rounds=(), marker=None, impact="- 改 `src/secret/key.py`"):
        self.project.write(".agent/config.json", json.dumps(dict(version=1, **route)))
        tfv.DesignApprovalTest.design(self, impact, marker=marker, rounds=rounds)
        return module_stage.design_approval(self.project.root, "a")

    round = tfv.DesignApprovalTest.round

    def test_reviewer_route(self):
        reviewer = {"takeover": "design"}
        got = self.approval(reviewer)
        self.assertEqual((got["status"], got["approver"]), ("pending-review", "reviewer"))
        got = self.approval(reviewer, [self.round(1, 0)], "reviewer-approved")
        self.assertEqual((got["status"], got["approvedBy"]), ("approved", "reviewer"))
        got = self.approval(reviewer, [self.round(1, 2), self.round(2, 0)], "reviewer-approved")
        self.assertEqual((got["status"], got["approvedBy"]), ("approved", "reviewer"))
        got = self.approval(reviewer, [self.round(1, 2), self.round(2, 1)])
        self.assertEqual(got["status"], "pending-user")
        got = self.approval(reviewer, impact="- 新增 `src/a/new.py`")
        self.assertEqual(got["status"], "not-required")
        from map_view import build
        row = next(m for m in build(self.project.root)["modules"] if m["id"] == "a")
        self.assertEqual((row["takeover"]["design"], row["takeover"]["designForcedBy"]), ("reviewer", None))

    def test_human_route_unchanged(self):
        got = self.approval({})
        self.assertEqual((got["status"], got["approver"]), ("pending-review", "user"))
        got = self.approval({}, [self.round(1, 0)], "reviewer-approved")
        self.assertEqual((got["status"], got["approvedBy"]), ("pending-user", None))
        got = self.approval({}, impact="- 新增 `src/a/new.py`")
        self.assertEqual(got["status"], "pending-user")


REVIEW_MARK = str(HERE / "review_mark.py")


def mark(project, *args):
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    done = subprocess.run([sys.executable, "-B", REVIEW_MARK, "--project", str(project.root), "--module", "a", *args],
                          capture_output=True, text=True, timeout=30, env=env)
    return done.returncode, done.stdout + done.stderr


class DesignHostRound(unittest.TestCase):
    """R9: a design round from a host subsession or with no reviewer, written with report=none."""

    def setUp(self):
        self.project = tfv.Project().__enter__()
        self.addCleanup(self.project.__exit__, None, None, None)
        tfv.approved_spec(self.project)
        self.project.write(".agent/config.json", json.dumps({"version": 1, "takeover": "design"}))
        self.project.write("tasks/a/design.md", design(interface="- 新字段 `x`") + FINDINGS)

    def text(self):
        return (self.project.root / "tasks" / "a" / "design.md").read_text(encoding="utf-8")

    def test_host_needs_findings(self):
        self.project.write("tasks/a/design.md", design(interface="- 新字段 `x`"))
        before = self.text()
        code, out = mark(self.project, "--target", "design", "--state", "host-reviewed", "--blocking", "0", "--confirm")
        self.assertEqual(code, 2)
        self.assertIn("review-findings-missing", out)
        self.assertEqual(self.text(), before)

    def test_host_clean_round_lets_it_through(self):
        code, out = mark(self.project, "--target", "design", "--state", "host-reviewed", "--blocking", "0", "--confirm")
        self.assertEqual(code, 0, out)
        self.assertRegex(self.text(), r"design-review round=1 blocking=0 sha256=[0-9a-f]{12} vendor=host "
                                      r"same-vendor=true criteria=host report=none -->")
        got = module_stage.design_approval(self.project.root, "a")
        self.assertEqual((got["status"], got["approvedBy"], got["reviewerVendor"], got["reportSha256"]),
                         ("approved", "reviewer", "host", None))
        self.assertIsNone(got["rounds"][0]["reportSha256"])

    def test_host_blocking_round(self):
        code, out = mark(self.project, "--target", "design", "--state", "host-reviewed", "--blocking", "3", "--confirm")
        self.assertEqual(code, 0, out)
        self.assertEqual(module_stage.design_approval(self.project.root, "a")["status"], "in-review")
        self.assertEqual(module_stage.review_state(self.text(), "design"), "pending")

    def test_host_needs_blocking(self):
        before = self.text()
        code, out = mark(self.project, "--target", "design", "--state", "host-reviewed", "--confirm")
        self.assertEqual(code, 2)
        self.assertIn("blocking-missing", out)
        self.assertEqual(self.text(), before)

    def test_no_reviewer(self):
        code, out = mark(self.project, "--target", "design", "--state", "no-reviewer", "--confirm")
        self.assertEqual(code, 0, out)
        self.assertIn("vendor=none same-vendor=false criteria=none report=none -->", self.text())
        self.assertEqual(module_stage.design_approval(self.project.root, "a")["status"], "unreviewed")

    def test_report_none_with_another_vendor_is_broken(self):
        line = ("<!-- spec-guard: design-review round=1 blocking=0 sha256=%s vendor=openai same-vendor=false "
                "criteria=design-v1 report=none -->" % ("b" * 12))
        self.project.write("tasks/a/design.md", self.text() + "## 外部审查意见\n\n" + line + "\n")
        self.assertEqual(module_stage.design_round_records(self.text()), [])
        problems = module_stage.design_review_problems(self.project.root, "a")
        self.assertIn(("fail", "`tasks/a/design.md` 有 1 行技术方案审查轮次行写坏了"), problems)

    def test_spec_target_refuses_for_now_unless_requirement(self):
        code, out = mark(self.project, "--target", "plan", "--state", "no-reviewer")
        self.assertEqual(code, 2)


class ElevatedTier(unittest.TestCase):
    """R10: a small module the rules lift to important can record its design; an unlifted one cannot."""

    def run_mark(self, lifted):
        with tfv.Project() as project:
            if lifted:
                project.write(".github/autopr/risk-paths.json", json.dumps(RISK))
            tfv.approved_spec(project, "small", boundary="`src/secret/`" if lifted else "`src/a/`")
            project.write("tasks/a/design.md", design())
            return mark(project, "--target", "design", "--state", "no-reviewer")

    def test_lifted(self):
        code, out = self.run_mark(True)
        self.assertEqual(code, 0, out)

    def test_not_lifted(self):
        code, out = self.run_mark(False)
        self.assertEqual(code, 2)
        self.assertIn("design-not-v2", out)


CODEX_LINE = "<!-- spec-guard: codex-review round=1 blocking=2 sha256=%s -->" % ("c" * 12)
FINDINGS = "\n## 外部审查意见\n\n- 子会话：目标一节没写怎样算做成（阻断）\n"


class RequirementProject(unittest.TestCase):
    def setUp(self):
        self.project = tfv.Project().__enter__()
        self.addCleanup(self.project.__exit__, None, None, None)

    def spec(self, tier="normal", old=False, extra=""):
        tfv.pending_spec(self.project, tier, reviewed=False)
        if old:
            self.project.write("spec/a.md", self.text().replace(tfv.marker(tier) + "\n", ""))
        if extra:
            self.project.write("spec/a.md", self.text() + extra)

    def text(self):
        return (self.project.root / "spec" / "a.md").read_text(encoding="utf-8")

    def review(self):
        return module_stage.requirement_review(self.project.root, "a")


class RequirementNotRequired(RequirementProject):
    """R2 (the /map part): bug and small are not reviewed; an old module has no requirementReview."""

    def test_values(self):
        for tier in ("bug", "small"):
            with self.subTest(tier=tier):
                self.spec(tier)
                self.assertEqual(self.review(), {"required": False, "status": "not-required", "records": []})
        self.spec(old=True)
        self.assertIsNone(self.review())
        from map_view import build
        self.spec()
        row = next(m for m in build(self.project.root)["modules"] if m["id"] == "a")
        self.assertEqual(row["requirementReview"], {"required": True, "status": "missing", "records": []})


class RequirementRecords(RequirementProject):
    """R3: the three records, one round only, and the reason rules."""

    def test_host_needs_findings(self):
        self.spec(extra="\n## 外部审查意见\n\n%s\n" % "<!-- spec-guard: something -->")
        before = self.text()
        code, out = mark(self.project, "--target", "spec", "--state", "host-reviewed", "--blocking", "0", "--confirm")
        self.assertEqual(code, 2)
        self.assertIn("review-findings-missing", out)
        self.assertEqual(self.text(), before)

    def test_host_record(self):
        self.spec(extra=FINDINGS)
        digest = module_stage._text_digest(self.text())
        code, out = mark(self.project, "--target", "spec", "--state", "host-reviewed", "--blocking", "2", "--confirm")
        self.assertEqual(code, 0, out)
        self.assertIn("<!-- spec-guard: requirement-review reviewer=host blocking=2 sha256=%s -->" % digest, self.text())
        self.assertEqual(self.review(), {"required": True, "status": "reviewed",
                                         "records": [{"reviewer": "host", "blocking": 2, "sha256": digest, "reason": None}]})
        self.assertEqual(module_stage.review_state(self.text(), "spec"), "pending")

    def test_none_record(self):
        self.spec()
        code, out = mark(self.project, "--target", "spec", "--state", "no-reviewer", "--reason", " 没装 delegate，也开不了子会话 ",
                         "--confirm")
        self.assertEqual(code, 0, out)
        record = self.review()["records"][0]
        self.assertEqual((record["reviewer"], record["reason"]), ("none", "没装 delegate，也开不了子会话"))

    def test_codex_record_counts(self):
        self.spec(extra="\n## 外部审查意见\n\n%s\n" % CODEX_LINE)
        self.assertEqual(self.review()["records"], [{"reviewer": "codex", "blocking": 2, "sha256": "c" * 12, "reason": None}])

    def test_one_round_only(self):
        for first in (("--state", "host-reviewed", "--blocking", "0"), ("--state", "no-reviewer", "--reason", "x"), None):
            for second in (("--state", "host-reviewed", "--blocking", "1"), ("--state", "no-reviewer", "--reason", "y"),
                           ("--state", "codex-reviewed", "--review", "/nonexistent.json")):
                with self.subTest(first=first, second=second):
                    if first is None:
                        self.spec(extra="\n## 外部审查意见\n\n%s\n" % CODEX_LINE)
                    else:
                        self.spec(extra=FINDINGS)
                        self.assertEqual(mark(self.project, "--target", "spec", *first, "--confirm")[0], 0)
                    before = self.text()
                    code, out = mark(self.project, "--target", "spec", *second, "--confirm")
                    self.assertEqual(code, 2)
                    self.assertIn("requirement-review-recorded", out)
                    self.assertEqual(self.text(), before)

    def test_reasons_refused(self):
        self.spec()
        before = self.text()
        for reason in (None, "", "   ", "a -- b", "a > b", "两行\n原因", "长" * 201):
            with self.subTest(reason=reason):
                args = ["--target", "spec", "--state", "no-reviewer", "--confirm"]
                if reason is not None:
                    args[4:4] = ["--reason", reason]
                code, out = mark(self.project, *args)
                self.assertEqual(code, 2)
                self.assertIn("requirement-review-reason", out)
                self.assertEqual(self.text(), before)

    def test_broken_lines(self):
        for line in ("<!-- spec-guard: requirement-review reviewer=none sha256=%s -->" % ("d" * 12),
                     "<!-- spec-guard: requirement-review reviewer=none sha256=%s reason= -->" % ("d" * 12),
                     "<!-- spec-guard: requirement-review reviewer=host sha256=%s -->" % ("d" * 12)):
            with self.subTest(line=line):
                self.spec(extra="\n## 外部审查意见\n\n%s\n" % line)
                self.assertEqual(self.review()["status"], "missing")
                self.assertIn(("fail", "`spec/a.md` 有 1 行需求文档审查记录写坏了"),
                              module_stage.flow_doc_problems(self.project.root, "a"))

    def test_not_required_modules_refuse_the_new_states(self):
        self.spec("bug")
        code, out = mark(self.project, "--target", "spec", "--state", "host-reviewed", "--blocking", "0")
        self.assertEqual(code, 2)
        self.assertIn("no-report-state", out)


GIT = tir.GIT


class RequirementGate(RequirementProject):
    """R1: a required requirement with no review record cannot be confirmed; any record lets it through."""

    def approve(self, target="spec"):
        return mark(self.project, "--target", target, "--state", "approved", "--confirm")

    def test_refused_without_a_record(self):
        for tier in ("normal", "important"):
            for target in ("spec",):  # --target both is refused for a new-flow module (plan-auto) before this
                with self.subTest(tier=tier, target=target):
                    self.spec(tier)
                    before = self.text()
                    code, out = self.approve(target)
                    self.assertEqual(code, 2)
                    self.assertIn("requirement-unreviewed", out)
                    self.assertEqual(self.text(), before)

    def test_lifted_small_is_refused(self):
        self.project.write(".github/autopr/risk-paths.json", json.dumps(RISK))
        tfv.pending_spec(self.project, "small", boundary="`src/secret/`", reviewed=False)
        code, out = self.approve()
        self.assertEqual(code, 2)
        self.assertIn("requirement-unreviewed", out)

    def test_each_record_lets_it_through(self):
        for args in (("--state", "host-reviewed", "--blocking", "1"), ("--state", "no-reviewer", "--reason", "x"), None):
            with self.subTest(args=args):
                if args is None:
                    self.spec(extra="\n## 外部审查意见\n\n%s\n" % CODEX_LINE)
                else:
                    self.spec(extra=FINDINGS)
                    self.assertEqual(mark(self.project, "--target", "spec", *args, "--confirm")[0], 0)
                code, out = self.approve()
                self.assertEqual(code, 0, out)
                self.assertEqual(module_stage.review_state(self.text(), "spec"), "approved")


class GitRequirement(RequirementProject):
    def git(self, *args):
        subprocess.run(GIT + list(args), cwd=self.project.root, check=True, capture_output=True, timeout=30)

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def reviewed(self, commit=True):
        """A pending requirement, committed when `commit`, then recorded as reviewed with no reviewer."""
        self.git("init", "-q")
        self.spec()
        if commit:
            self.commit("requirement")
        self.assertEqual(mark(self.project, "--target", "spec", "--state", "no-reviewer", "--reason", "x",
                              "--confirm")[0], 0)

    def edit(self, lines=1):
        self.project.write("spec/a.md", self.text().replace("## 目标\n\n不涉及", "## 目标\n\n" + "\n".join(
            "改了第 %d 行" % n for n in range(lines)), 1))

    def hint(self, zh=True):
        config = {"version": 1}
        if zh:
            config["artifactLanguage"] = "zh-CN"
        self.project.write(".agent/config.json", json.dumps(config))
        self.project.write(".agent/state.json", json.dumps({"activeModule": "a"}))
        return module_stage.describe(self.project.root)


class RequirementHint(GitRequirement):
    """R4: the confirmation stop asks for the review first, then restates with the changes since it."""

    def test_missing_asks_for_the_review_first(self):
        self.spec()
        text = self.hint()
        self.assertIn("需求文档要先审一轮，再交用户确认", text)
        for way in ("--state codex-reviewed", "全新子会话", "--state host-reviewed --blocking", "--state no-reviewer --reason"):
            self.assertIn(way, text)
        self.assertNotIn("在对话正文里复述需求", text)
        self.assertIn("Review the requirement once before the user confirms it", self.hint(zh=False))

    def test_reviewed_restates_and_discloses(self):
        self.reviewed()
        text = self.hint()
        self.assertIn("在对话正文里复述需求", text)
        self.assertIn("交用户时附上审查提了什么、改了哪些、哪些没采纳及原因", text)

    def test_unchanged_since_the_review(self):
        # the record line and its section are not the requirement: recording the review is not a change
        self.reviewed()
        self.commit("recorded")
        self.assertEqual(module_stage.requirement_review_diff(self.project.root, "a"), {"status": "unchanged"})
        self.assertIn("审查后没有改动", self.hint())

    def test_diff_after_an_edit(self):
        self.reviewed()
        self.edit()
        self.commit("edit")
        text = self.hint()
        self.assertIn("审查以来的改动（照原样给用户看）", text)
        self.assertIn("+改了第 0 行", text)

    def test_not_in_git(self):
        self.reviewed(commit=False)
        self.edit()
        text = self.hint()
        self.assertIn("审查以来的改动取不到", text)

    def test_long_diff_is_cut(self):
        self.reviewed()
        self.edit(80)
        lines = module_stage.requirement_review_diff(self.project.root, "a")["diff"].splitlines()
        text = self.hint()
        self.assertIn("还有 %d 行" % (len(lines) - module_stage.DIFF_HINT_LINES), text)
        self.assertNotIn("+改了第 79 行", text)

    def test_state_code_follows_the_review(self):
        def code():
            self.hint()
            return module_stage.describe(self.project.root, state_extra="x").rsplit("spec-guard-state: ", 1)[1][:8]
        self.git("init", "-q")
        self.spec()
        first = code()
        self.assertEqual(mark(self.project, "--target", "spec", "--state", "no-reviewer", "--reason", "x",
                              "--confirm")[0], 0)
        self.assertNotEqual(code(), first)


class RequirementDiffPreview(GitRequirement):
    """R5: the confirmation preview prints the whole diff since the review, or why it cannot."""

    def preview(self):
        return mark(self.project, "--target", "spec", "--state", "approved")

    def test_whole_diff(self):
        self.reviewed()
        self.edit(80)
        before = self.text()
        code, out = self.preview()
        self.assertEqual(code, 0, out)
        self.assertIn("Changes since the review (show this diff to the user verbatim):", out)
        self.assertIn("+改了第 79 行", out)
        self.assertEqual(self.text(), before)

    def test_unchanged(self):
        self.reviewed()
        code, out = self.preview()
        self.assertEqual(code, 0, out)
        self.assertIn("spec/a.md: nothing changed since the review.", out)

    def test_unavailable(self):
        self.reviewed(commit=False)
        self.edit()
        code, out = self.preview()
        self.assertEqual(code, 0, out)
        self.assertIn("spec/a.md: the changes since the review cannot be shown", out)


class InterfaceFields(unittest.TestCase):
    """R12: interface 1.27 only adds values and fields, each one described."""

    def setUp(self):
        self.data = json.loads((HERE.parent / "interface.json").read_text(encoding="utf-8"))

    def test_version(self):
        self.assertEqual(self.data["interface"], "1.27")

    def test_new_fields_and_values_are_described(self):
        view = self.data["mapView"]
        self.assertIn("since 1.27", view["flow"]["fields"]["requirementReview"])
        for field in ("reason", "reasons", "riskList"):
            with self.subTest(field=field):
                self.assertIn("1.27", view["designApproval"]["fields"][field])
        self.assertIn("reportSha256", view["designApproval"]["fields"]["rounds"])
        self.assertIn("always null since 1.27", view["takeover"]["fields"]["designForcedBy"])
        text = json.dumps(self.data["reviewMark"], ensure_ascii=False)
        for word in ("host-reviewed", "no-reviewer", "--blocking", "--reason", "requirement-unreviewed",
                     "requirement-review-recorded", "requirement-review-reason", "review-findings-missing"):
            with self.subTest(word=word):
                self.assertIn(word, text)
        self.assertIn("old-files and impact-unknown no longer appear", view["designApproval"]["fields"]["reason"])


if __name__ == "__main__":
    unittest.main()
