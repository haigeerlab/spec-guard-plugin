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
    """R7: without a readable risk-path list the design stage says risk-path was not checked."""

    def run_hint(self, risk):
        with tfv.Project() as project:
            tfv.approved_spec(project)
            if risk:
                project.write(".github/autopr/risk-paths.json", json.dumps(RISK))
            project.write("tasks/a/design.md", design("- 改 `src/secret/key.py`"))
            need = module_stage.design_requirement(project.root, "a")
            fact, _step = module_stage.design_hint(project.root, "a", "NEEDS_REGRESSION", CMD, True)
            en, _step = module_stage.design_hint(project.root, "a", "NEEDS_REGRESSION", CMD, False)
        return need, fact, en

    def test_no_list(self):
        need, fact, en = self.run_hint(False)
        self.assertEqual((need["riskList"], need["reasons"]), ("no-list", []))
        self.assertIn("T4 路径：没有可读的风险路径清单，`risk-path` 未检查", fact)
        self.assertIn("no readable risk-path list, `risk-path` not checked", en)

    def test_list(self):
        need, fact, _en = self.run_hint(True)
        self.assertEqual((need["riskList"], need["reasons"]), ("ok", ["risk-path"]))
        self.assertNotIn("没有可读的风险路径清单", fact)


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
        self.project.write("tasks/a/design.md", design(interface="- 新字段 `x`"))

    def text(self):
        return (self.project.root / "tasks" / "a" / "design.md").read_text(encoding="utf-8")

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


if __name__ == "__main__":
    unittest.main()
