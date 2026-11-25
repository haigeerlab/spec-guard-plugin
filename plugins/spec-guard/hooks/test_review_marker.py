"""Review markers on a module's Spec and Plan: the five states, the Spec fingerprint and review_mark.py. No network."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from module_stage import (EXTERNAL_REVIEW_DECLINED, EXTERNAL_REVIEW_STATES, REVIEW_APPROVED, REVIEW_PENDING,
                          REVIEW_STATES, external_review_state, review_approved_line, review_body, review_digest,
                          review_state)

SCRIPT = str(Path(__file__).with_name("review_mark.py"))
MAP = ("# Capability Map\n| Module id | Responsibility | Depends on |\n|---|---|---|\n"
       "| alpha | x | — |\n| beta | y | alpha |\n\nBuild order: alpha → beta\n")
SPEC = "# Spec: alpha\n\n## Objective\n\n正文\n"


def with_marker(marker, text=SPEC):
    head, _, rest = text.partition("\n")
    return "%s\n\n%s\n%s" % (head, marker, rest)


def approved(text=SPEC):
    # The digest covers everything but the marker line, so take it from the text with a marker in place.
    return with_marker(review_approved_line(review_digest(with_marker(REVIEW_PENDING, text))), text)


class States(unittest.TestCase):
    def test_no_marker_is_none(self):
        self.assertEqual(review_state(SPEC, "spec"), "none")
        self.assertEqual(review_state("# Plan\n", "plan"), "none")

    def test_pending(self):
        self.assertEqual(review_state(with_marker(REVIEW_PENDING), "spec"), "pending")
        self.assertEqual(review_state(with_marker("  " + REVIEW_PENDING + "  ", "# Plan\n"), "plan"), "pending")

    def test_spec_approved_needs_the_current_digest(self):
        self.assertEqual(review_state(approved(), "spec"), "approved")

    def test_spec_changed_after_approval_is_revised(self):
        self.assertEqual(review_state(approved().replace("正文", "正文。"), "spec"), "revised")
        self.assertEqual(review_state(approved() + "\n新增一节\n", "spec"), "revised")

    def test_plan_approved_carries_no_digest(self):
        self.assertEqual(review_state(with_marker(REVIEW_APPROVED, "# Plan\n"), "plan"), "approved")
        self.assertEqual(review_state(with_marker(REVIEW_APPROVED, "# Plan\n") + "改动\n", "plan"), "approved")

    def test_invalid_forms(self):
        digest = review_approved_line(review_digest(SPEC))
        for text, kind in (
                (with_marker(REVIEW_APPROVED), "spec"),                      # Spec approval without a digest
                (with_marker(digest, "# Plan\n"), "plan"),                   # Plan approval with a digest
                (with_marker(REVIEW_PENDING + "\n" + REVIEW_PENDING), "spec"),  # more than one line
                (with_marker(REVIEW_PENDING + "\n" + digest), "spec"),
                (with_marker("<!-- spec-guard: review done -->"), "spec"),   # unknown word
                (with_marker("<!-- spec-guard: review approved XYZ -->"), "spec"),
                (with_marker("<!-- spec-guard: review pending --> trailing"), "spec"),
        ):
            self.assertEqual(review_state(text, kind), "invalid", text)

    def test_a_mention_is_not_a_marker(self):
        mention = SPEC + "标记写作 `%s`，独占一行才算。\n" % REVIEW_PENDING
        self.assertEqual(review_state(mention, "spec"), "none")

    def test_fenced_examples_are_not_markers(self):
        fenced = SPEC + "```text\n%s\n<!-- spec-guard: review approved -->   ← 示例\n```\n" % REVIEW_PENDING
        self.assertEqual(review_state(fenced, "spec"), "none")
        self.assertEqual(review_state(with_marker(REVIEW_PENDING, fenced), "spec"), "pending")
        tilde = SPEC + "~~~\n%s\n~~~\n" % REVIEW_PENDING
        self.assertEqual(review_state(tilde, "spec"), "none")

    def test_fence_closes_only_on_a_matching_bare_fence(self):
        for name, fenced in (("shorter fence inside a longer one", "````text\n```\n%s\n````\n"),
                             ("info string is not a closing fence", "```text\n```python\n%s\n```\n")):
            with self.subTest(name):
                text = SPEC + fenced % REVIEW_PENDING
                self.assertEqual(review_state(text, "spec"), "none")
                self.assertEqual(review_state(with_marker(REVIEW_PENDING, text), "spec"), "pending")


class ValueSets(unittest.TestCase):
    """plugin-interface: interface.json publishes these sets, so every state the code returns must be in them."""

    def test_review_states(self):
        self.assertEqual(REVIEW_STATES, ("none", "pending", "approved", "codex-approved", "revised", "invalid"))
        from module_stage import review_codex_line
        codex = with_marker(review_codex_line(review_digest(with_marker(REVIEW_PENDING))))
        seen = {review_state(SPEC, "spec"), review_state(with_marker(REVIEW_PENDING), "spec"),
                review_state(approved(), "spec"), review_state(approved() + "改\n", "spec"),
                review_state(with_marker(REVIEW_APPROVED), "spec"), review_state(codex, "spec")}
        self.assertEqual(seen, set(REVIEW_STATES))

    def test_external_review_states(self):
        self.assertEqual(EXTERNAL_REVIEW_STATES, ("none", "recorded", "declined"))
        seen = set()
        for todo in ("- [ ] a\n", "## 外部审查意见\n- delegate：completed\n", EXTERNAL_REVIEW_DECLINED + "\n"):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / "tasks" / "alpha").mkdir(parents=True)
                (root / "tasks" / "alpha" / "todo.md").write_text(todo, encoding="utf-8")
                seen.add(external_review_state(root, "alpha"))
        self.assertEqual(seen, set(EXTERNAL_REVIEW_STATES))


class Digest(unittest.TestCase):
    def test_marker_line_does_not_change_the_digest(self):
        base = review_digest(SPEC)
        self.assertEqual(review_digest(with_marker(REVIEW_PENDING)), review_digest(approved()))
        self.assertEqual(review_digest(approved()), review_digest(with_marker(review_approved_line("0" * 12))))
        self.assertEqual(len(base), 12)

    def test_any_other_character_changes_it(self):
        base = review_digest(with_marker(REVIEW_PENDING))
        for changed in (SPEC.replace("正文", "正文 "), SPEC + "\n", SPEC.replace("alpha", "alphb"),
                        SPEC.rstrip("\n")):
            self.assertNotEqual(review_digest(with_marker(REVIEW_PENDING, changed)), base, repr(changed))

    def test_fenced_marker_text_is_part_of_the_body(self):
        fenced = SPEC + "```\n%s\n```\n" % REVIEW_PENDING
        self.assertIn(REVIEW_PENDING, review_body(fenced))
        self.assertNotEqual(review_digest(fenced), review_digest(fenced.replace("pending", "approved")))


class Project:
    """alpha has a Spec and a Plan, beta has neither."""

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "spec").mkdir()
        (self.root / "tasks" / "alpha").mkdir(parents=True)
        (self.root / "spec" / "CAPABILITY-MAP.md").write_text(MAP, encoding="utf-8")
        self.spec = self.root / "spec" / "alpha.md"
        self.plan = self.root / "tasks" / "alpha" / "plan.md"
        self.spec.write_text(SPEC, encoding="utf-8")
        self.plan.write_text("# Plan: alpha\n\n步骤\n", encoding="utf-8")
        return self

    def run(self, *args):
        done = subprocess.run([sys.executable, "-B", SCRIPT, "--project", str(self.root), *args],
                              capture_output=True, text=True, timeout=20)
        return done.returncode, done.stdout

    def states(self):
        return (review_state(self.spec.read_text(encoding="utf-8"), "spec"),
                review_state(self.plan.read_text(encoding="utf-8"), "plan"))

    def __exit__(self, *exc):
        self.tmp.cleanup()


class Mark(unittest.TestCase):
    def test_preview_writes_nothing(self):
        with Project() as project:
            before = project.spec.read_text(encoding="utf-8")
            code, out = project.run("--module", "alpha", "--target", "spec", "--state", "pending")
            self.assertEqual(code, 0, out)
            self.assertIn("+" + REVIEW_PENDING, out)
            self.assertIn("preview only; nothing was written", out)
            self.assertEqual(project.spec.read_text(encoding="utf-8"), before)

    def test_confirm_inserts_after_the_title_and_changes_nothing_else(self):
        with Project() as project:
            code, out = project.run("--module", "alpha", "--target", "spec", "--state", "pending", "--confirm")
            self.assertEqual(code, 0, out)
            text = project.spec.read_text(encoding="utf-8")
            self.assertEqual(text, "# Spec: alpha\n\n%s\n\n## Objective\n\n正文\n" % REVIEW_PENDING)
            self.assertEqual(project.states(), ("pending", "none"))

    def test_approving_replaces_the_marker_in_place_and_is_repeatable(self):
        with Project() as project:
            project.run("--module", "alpha", "--target", "spec", "--state", "pending", "--confirm")
            pending = project.spec.read_text(encoding="utf-8")
            code, out = project.run("--module", "alpha", "--target", "spec", "--state", "approved", "--confirm")
            self.assertEqual(code, 0, out)
            first = project.spec.read_text(encoding="utf-8")
            self.assertEqual(first, pending.replace(REVIEW_PENDING, review_approved_line(review_digest(pending))))
            self.assertIn(review_digest(pending), out)
            code, out = project.run("--module", "alpha", "--target", "spec", "--state", "approved", "--confirm")
            self.assertEqual(code, 0, out)
            self.assertIn("already", out)
            self.assertEqual(project.spec.read_text(encoding="utf-8"), first)

    def test_reapproving_a_revised_spec_takes_the_new_digest(self):
        with Project() as project:
            project.run("--module", "alpha", "--target", "spec", "--state", "approved", "--confirm")
            project.spec.write_text(project.spec.read_text(encoding="utf-8") + "补一条\n", encoding="utf-8")
            self.assertEqual(project.states()[0], "revised")
            code, out = project.run("--module", "alpha", "--target", "spec", "--state", "approved", "--confirm")
            self.assertEqual(code, 0, out)
            self.assertEqual(project.states()[0], "approved")
            self.assertTrue(project.spec.read_text(encoding="utf-8").endswith("补一条\n"))

    def test_both_marks_spec_and_plan(self):
        with Project() as project:
            code, out = project.run("--module", "alpha", "--target", "both", "--state", "approved", "--confirm")
            self.assertEqual(code, 0, out)
            self.assertEqual(project.states(), ("approved", "approved"))
            self.assertIn(REVIEW_APPROVED + "\n", project.plan.read_text(encoding="utf-8"))

    def test_a_plan_can_be_approved_when_the_spec_has_no_marker(self):
        with Project() as project:
            before = project.spec.read_text(encoding="utf-8")
            code, out = project.run("--module", "alpha", "--target", "plan", "--state", "approved", "--confirm")
            self.assertEqual(code, 0, out)
            self.assertEqual(project.states(), ("none", "approved"))
            self.assertEqual(project.spec.read_text(encoding="utf-8"), before)
            self.assertIn("has no review marker; this records the Plan's approval only", out)

    def test_a_plan_can_be_approved_when_there_is_no_spec_file(self):
        with Project() as project:
            project.spec.unlink()
            code, out = project.run("--module", "alpha", "--target", "plan", "--state", "approved", "--confirm")
            self.assertEqual(code, 0, out)
            self.assertEqual(review_state(project.plan.read_text(encoding="utf-8"), "plan"), "approved")

    def test_plan_cannot_be_approved_while_the_spec_is_pending_revised_or_invalid(self):
        def pending(project):
            project.run("--module", "alpha", "--target", "spec", "--state", "pending", "--confirm")

        def revised(project):
            project.run("--module", "alpha", "--target", "spec", "--state", "approved", "--confirm")
            project.spec.write_text(project.spec.read_text(encoding="utf-8") + "补一条\n", encoding="utf-8")

        def invalid(project):
            project.spec.write_text(with_marker(REVIEW_PENDING + "\n" + REVIEW_PENDING), encoding="utf-8")

        for prepare, state in ((pending, "pending"), (revised, "revised"), (invalid, "invalid")):
            with Project() as project:
                prepare(project)
                spec_before = project.spec.read_text(encoding="utf-8")
                code, out = project.run("--module", "alpha", "--target", "plan", "--state", "approved", "--confirm")
                self.assertEqual(code, 2, out)
                self.assertIn("spec-not-approved", out)
                self.assertIn("reads as %s" % state, out)
                self.assertIn("needs the user's own explicit approval of that Spec", out)
                self.assertEqual(review_state(project.plan.read_text(encoding="utf-8"), "plan"), "none")
                self.assertEqual(project.spec.read_text(encoding="utf-8"), spec_before)

    def test_plan_is_approved_normally_after_the_spec(self):
        with Project() as project:
            project.run("--module", "alpha", "--target", "spec", "--state", "approved", "--confirm")
            code, out = project.run("--module", "alpha", "--target", "plan", "--state", "approved", "--confirm")
            self.assertEqual(code, 0, out)
            self.assertEqual(project.states(), ("approved", "approved"))
            self.assertNotIn("has no review marker", out)

    def test_approving_reminds_that_the_user_must_have_seen_the_content(self):
        with Project() as project:
            reminder = "Before --confirm, make sure the user has seen the content of"
            code, out = project.run("--module", "alpha", "--target", "both", "--state", "approved")
            self.assertEqual(code, 0, out)
            self.assertIn("spec/alpha.md: %d line(s)" % len(SPEC.splitlines()), out)
            self.assertIn("tasks/alpha/plan.md: 3 line(s)", out)
            self.assertIn(reminder, out)
            self.assertIn("only a link or a one-line summary, that is not a review", out)
            self.assertIn("Spec digest: ", out)
            self.assertEqual(project.states(), ("none", "none"))          # still only a preview
            code, out = project.run("--module", "alpha", "--target", "both", "--state", "approved", "--confirm")
            self.assertEqual(code, 0, out)
            self.assertIn(reminder, out)
            self.assertEqual(project.states(), ("approved", "approved"))  # a reminder, not a gate

    def test_approving_names_the_generic_source(self):
        # review-residual-fixes (C1): the approval source follows the installed collaboration plugin, else this
        # conversation -- the same sentence as commands/review-mark.md; no decision hub or session-protocol wording.
        with Project() as project:
            code, out = project.run("--module", "alpha", "--target", "spec", "--state", "approved")
            self.assertEqual(code, 0, out)
            self.assertIn("installed collaboration plugin", out)
            self.assertIn("current conversation", out)
            for stale in ("decision hub", "session-protocol", "item number", "sent to the hub"):
                self.assertNotIn(stale, out)
        source = (Path(__file__).resolve().parent / "review_mark.py").read_text(encoding="utf-8")
        for stale in ("decision hub", "session-protocol", "item number"):
            self.assertNotIn(stale, source)

    def test_marking_pending_carries_no_reminder(self):
        with Project() as project:
            code, out = project.run("--module", "alpha", "--target", "both", "--state", "pending", "--confirm")
            self.assertEqual(code, 0, out)
            self.assertNotIn("line(s)", out)
            self.assertNotIn("has seen the content", out)

    def test_refusals(self):
        with Project() as project:
            code, out = project.run("--module", "gamma", "--target", "spec", "--state", "pending", "--confirm")
            self.assertEqual((code, "not-in-map" in out), (2, True), out)
            code, out = project.run("--module", "beta", "--target", "spec", "--state", "pending", "--confirm")
            self.assertEqual((code, "file-missing" in out), (2, True), out)
            code, out = project.run("--module", "alpha/../x", "--target", "spec", "--state", "pending", "--confirm")
            self.assertEqual((code, "not-a-module-id" in out), (2, True), out)
            broken = with_marker(REVIEW_PENDING + "\n" + REVIEW_PENDING)
            project.spec.write_text(broken, encoding="utf-8")
            code, out = project.run("--module", "alpha", "--target", "spec", "--state", "approved", "--confirm")
            self.assertEqual((code, "marker-invalid" in out), (2, True), out)
            self.assertEqual(project.spec.read_text(encoding="utf-8"), broken)

    def test_a_file_without_a_title_gets_the_marker_first(self):
        with Project() as project:
            project.plan.write_text("步骤\n", encoding="utf-8")
            code, out = project.run("--module", "alpha", "--target", "plan", "--state", "pending", "--confirm")
            self.assertEqual(code, 0, out)
            self.assertEqual(project.plan.read_text(encoding="utf-8"), "%s\n\n步骤\n" % REVIEW_PENDING)

    def test_fenced_examples_are_left_alone(self):
        with Project() as project:
            fenced = SPEC + "```\n%s\n```\n" % REVIEW_PENDING
            project.spec.write_text(fenced, encoding="utf-8")
            code, out = project.run("--module", "alpha", "--target", "spec", "--state", "approved", "--confirm")
            self.assertEqual(code, 0, out)
            self.assertEqual(project.states()[0], "approved")
            self.assertIn("```\n%s\n```\n" % REVIEW_PENDING, project.spec.read_text(encoding="utf-8"))


class PreBuildBatch(unittest.TestCase):
    """pre-build-spec-batch: approving both shows the revised Spec's cumulative diff against the approved baseline."""
    GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "core.hooksPath=/dev/null",
           "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main"]

    def git(self, project, *args):
        done = subprocess.run(self.GIT + list(args), cwd=project.root, check=True, capture_output=True, text=True,
                              timeout=30)
        return done.stdout.strip()

    def revised(self, project, commit=True):
        self.git(project, "init", "-q")
        if not commit:
            self.git(project, "add", "-A")
            self.git(project, "commit", "-q", "-m", "draft")
        project.run("--module", "alpha", "--target", "spec", "--state", "approved", "--confirm")
        sha = None
        if commit:
            self.git(project, "add", "-A")
            self.git(project, "commit", "-q", "-m", "approved")
            sha = self.git(project, "rev-parse", "HEAD")
        project.spec.write_text(project.spec.read_text(encoding="utf-8") + "补一条\n", encoding="utf-8")
        return sha

    def test_both_shows_the_cumulative_diff_and_approves_both(self):
        with Project() as project:
            sha = self.revised(project)
            code, out = project.run("--module", "alpha", "--target", "both", "--state", "approved")
            self.assertEqual(code, 0, out)
            self.assertIn("spec/alpha.md (approved %s)" % sha[:7], out)
            self.assertIn("+补一条", out)
            self.assertEqual(project.states(), ("revised", "none"))
            code, out = project.run("--module", "alpha", "--target", "both", "--state", "approved", "--confirm")
            self.assertEqual(code, 0, out)
            self.assertEqual(project.states(), ("approved", "approved"))

    def test_without_a_baseline_the_whole_spec_must_be_shown(self):
        with Project() as project:
            self.revised(project, commit=False)
            code, out = project.run("--module", "alpha", "--target", "both", "--state", "approved")
            self.assertEqual(code, 0, out)
            self.assertIn("no approved baseline in git", out)
            self.assertNotIn("(approved ", out)

    def test_plan_alone_still_refuses_and_names_both(self):
        with Project() as project:
            self.revised(project)
            code, out = project.run("--module", "alpha", "--target", "plan", "--state", "approved", "--confirm")
            self.assertEqual(code, 2, out)
            self.assertIn("--target both", out)
            self.assertIn("cumulative diff", out)


def not_important(project):
    """important-requirement: a Spec with a boundary and a readable, non-matching risk list is not important by rule."""
    import json
    project.spec.write_text(project.spec.read_text(encoding="utf-8") + "\n## 并行边界\n\n- 独占：`src/alpha/`\n", encoding="utf-8")
    folder = project.root / ".github" / "autopr"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "risk-paths.json").write_text(json.dumps({"schema": "autopilot.risk-paths/v1", "T4": [], "T3": []}),
                                            encoding="utf-8")


class CodexMarks(unittest.TestCase):
    """codex-approval (C1, assumptions 2-6): rounds are recorded from a report; approval needs a clean last round."""

    def report(self, project, kind="spec", severities=(), outcome=None):
        import hashlib
        import json
        path = project.spec if kind == "spec" else project.plan
        relative = "spec/alpha.md" if kind == "spec" else "tasks/alpha/plan.md"
        findings = [{"title": "t", "file": relative, "line": None, "trigger": "x", "impact": "y", "evidence": "z",
                     "suggestion": "w", "unverified": [], "severity": severity} for severity in severities]
        document = {"schema_version": 1, "execution_status": "completed",
                    "review_outcome": outcome or ("findings" if findings else "no_findings_in_scope"),
                    "backend": "codex", "scope": {"files": {relative: hashlib.sha256(path.read_bytes()).hexdigest()}},
                    "reviewed": [relative], "findings": findings, "limitations": []}
        out = project.root / ("report-%d.json" % len(list(project.root.glob("report-*.json"))))
        out.write_text(json.dumps(document), encoding="utf-8")
        return str(out)

    def mark(self, project, state, report, kind="spec"):
        return project.run("--module", "alpha", "--target", kind, "--state", state, "--review", report, "--confirm")

    def allow_codex(self, project, kind="spec"):
        import json
        (project.root / ".agent").mkdir()
        (project.root / ".agent" / "config.json").write_text(
            json.dumps({"version": 1, "takeover": {kind: "codex"}}), encoding="utf-8")
        if kind == "spec":
            not_important(project)

    def test_codex_approval_without_takeover_refuses_before_reading_report(self):
        for kind in ("spec", "plan"):
            with self.subTest(kind=kind), Project() as project:
                before = (project.spec.read_bytes(), project.plan.read_bytes())
                for report in (self.report(project, kind=kind), str(project.root / "missing.json")):
                    for confirm in ((), ("--confirm",)):
                        code, out = project.run("--module", "alpha", "--target", kind, "--state", "codex-approved",
                                                "--review", report, *confirm)
                        self.assertEqual(code, 2, out)
                        self.assertTrue(out.startswith("codex-route-takeover: "), out)
                        self.assertEqual(len(out.splitlines()), 1, out)
                        self.assertIn("--state codex-reviewed", out)
                        self.assertIn("--state approved", out)
                        self.assertEqual((project.spec.read_bytes(), project.plan.read_bytes()), before)

    def test_codex_approval_of_important_spec_refuses(self):
        with Project() as project:
            self.allow_codex(project)
            project.spec.write_text(SPEC, encoding="utf-8")  # no boundary: important-requirement
            before = project.spec.read_bytes()
            for confirm in ((), ("--confirm",)):
                code, out = project.run("--module", "alpha", "--target", "spec", "--state", "codex-approved",
                                        "--review", self.report(project), *confirm)
                self.assertEqual(code, 2, out)
                self.assertTrue(out.startswith("codex-route-important: "), out)
                self.assertEqual(project.spec.read_bytes(), before)

    def test_codex_approval_of_pre_declared_plan_refuses(self):
        with Project() as project:
            self.allow_codex(project, "plan")
            project.plan.write_text("# Plan: alpha\n\n## 预先声明\n\n- 公共路径：`package.json`\n", encoding="utf-8")
            before = project.plan.read_bytes()
            for confirm in ((), ("--confirm",)):
                code, out = project.run("--module", "alpha", "--target", "plan", "--state", "codex-approved",
                                        "--review", self.report(project, kind="plan"), *confirm)
                self.assertEqual(code, 2, out)
                self.assertTrue(out.startswith("codex-route-pre-declared: "), out)
                self.assertEqual(project.plan.read_bytes(), before)

    def test_codex_review_without_takeover_still_records_a_round(self):
        for kind in ("spec", "plan"):
            with self.subTest(kind=kind), Project() as project:
                code, out = self.mark(project, "codex-reviewed", self.report(project, kind=kind), kind=kind)
                self.assertEqual(code, 0, out)
                text = (project.spec if kind == "spec" else project.plan).read_text(encoding="utf-8")
                self.assertIn("round=1 blocking=0", text)
                self.assertEqual(review_state(text, kind), "none")

    def test_clean_review_records_round_and_codex_approval(self):
        with Project() as project:
            self.allow_codex(project)
            code, out = self.mark(project, "codex-approved", self.report(project))
            self.assertEqual(code, 0, out)
            text = project.spec.read_text(encoding="utf-8")
            self.assertEqual(review_state(text, "spec"), "codex-approved")
            self.assertIn("## 外部审查意见", text)
            self.assertRegex(text, r"<!-- spec-guard: codex-review round=1 blocking=0 sha256=[0-9a-f]{12} -->")
            project.spec.write_text(text.replace("正文", "正文改动"), encoding="utf-8")
            self.assertEqual(review_state(project.spec.read_text(encoding="utf-8"), "spec"), "revised")

    def test_reasons_under_external_review_keep_the_codex_approval(self):
        # M3 second rework: the rule asks for a reason per suggestion in that section; writing it must not void the approval.
        with Project() as project:
            self.allow_codex(project)
            self.assertEqual(self.mark(project, "codex-approved", self.report(project, severities=("suggestion",)))[0], 0)
            text = project.spec.read_text(encoding="utf-8")
            project.spec.write_text(text + "- 建议一：采纳，已在 Task 1 写明。\n", encoding="utf-8")
            self.assertEqual(review_state(project.spec.read_text(encoding="utf-8"), "spec"), "codex-approved")
            project.spec.write_text(text.replace("正文", "正文改动") + "- 建议一：采纳。\n", encoding="utf-8")
            self.assertEqual(review_state(project.spec.read_text(encoding="utf-8"), "spec"), "revised")

    def test_a_codex_approval_from_0_91_0_still_counts(self):
        # A marker written over the whole text (0.91.0/0.91.1) reads the same as before the upgrade.
        from module_stage import review_codex_line
        text = with_marker(REVIEW_PENDING) + "\n## 外部审查意见\n\n<!-- spec-guard: codex-review round=1 blocking=0 sha256=aaaaaaaaaaaa -->\n"
        old = text.replace(REVIEW_PENDING, review_codex_line(review_digest(text)))
        self.assertEqual(review_state(old, "spec"), "codex-approved")
        self.assertEqual(review_state(old.replace("正文", "正文改动"), "spec"), "revised")

    def test_blocking_round_is_recorded_not_approved(self):
        with Project() as project:
            self.allow_codex(project)
            report = self.report(project, severities=("blocking", "suggestion"))
            code, out = self.mark(project, "codex-approved", report)
            self.assertEqual(code, 2, out)
            self.assertIn("blocking", out)
            code, out = self.mark(project, "codex-reviewed", report)
            self.assertEqual(code, 0, out)
            text = project.spec.read_text(encoding="utf-8")
            self.assertIn("round=1 blocking=1", text)
            self.assertEqual(review_state(text, "spec"), "none")
            code, out = self.mark(project, "codex-approved", self.report(project))
            self.assertEqual(code, 0, out)
            self.assertIn("round=2 blocking=0", project.spec.read_text(encoding="utf-8"))

    def test_two_blocking_rounds_hand_it_to_the_user(self):
        with Project() as project:
            self.allow_codex(project)
            for _ in range(2):
                self.assertEqual(self.mark(project, "codex-reviewed", self.report(project, severities=("blocking",)))[0], 0)
            for state, severities in (("codex-reviewed", ("blocking",)), ("codex-approved", ())):
                code, out = self.mark(project, state, self.report(project, severities=severities))
                self.assertEqual(code, 2, (state, out))
                self.assertIn("two rounds", out)
            code, out = project.run("--module", "alpha", "--target", "spec", "--state", "approved", "--confirm")
            self.assertEqual(code, 0, out)

    def test_bad_reports_write_nothing(self):
        with Project() as project:
            self.allow_codex(project)
            before = project.spec.read_text(encoding="utf-8")
            for report in (self.report(project, outcome="inconclusive"), str(project.root / "missing.json")):
                code, out = self.mark(project, "codex-approved", report)
                self.assertEqual(code, 2, out)
            self.assertEqual(project.run("--module", "alpha", "--target", "spec", "--state", "codex-approved",
                                         "--confirm")[0], 2)  # no --review
            self.assertEqual(project.run("--module", "alpha", "--target", "both", "--state", "codex-approved",
                                         "--review", self.report(project), "--confirm")[0], 2)
            self.assertEqual(project.spec.read_text(encoding="utf-8"), before)

    def test_a_codex_approved_spec_lets_the_plan_be_approved(self):
        import json
        with Project() as project:
            (project.root / ".agent").mkdir()
            (project.root / ".agent" / "config.json").write_text(json.dumps({"version": 1, "takeover": {"spec": "codex"}}),
                                                                 encoding="utf-8")
            not_important(project)
            self.assertEqual(self.mark(project, "codex-approved", self.report(project))[0], 0)
            code, out = project.run("--module", "alpha", "--target", "plan", "--state", "approved", "--confirm")
            self.assertEqual(code, 0, out)

    def test_plan_too(self):
        with Project() as project:
            self.allow_codex(project, "plan")
            code, out = self.mark(project, "codex-approved", self.report(project, kind="plan"), kind="plan")
            self.assertEqual(code, 0, out)
            self.assertEqual(review_state(project.plan.read_text(encoding="utf-8"), "plan"), "codex-approved")


class Effective(unittest.TestCase):
    """codex-approval (C2, assumptions 7, 9, Q6): Codex's approval counts only where the takeover gives it the step."""

    def project(self, config, plan="# Plan: alpha\n\n步骤\n"):
        import json
        project = Project().__enter__()
        self.addCleanup(project.__exit__)
        (project.root / ".agent").mkdir()
        (project.root / ".agent" / "config.json").write_text(json.dumps(dict(version=1, **config)), encoding="utf-8")
        project.plan.write_text(plan, encoding="utf-8")
        not_important(project)
        return project.root

    def test_codex_approval_needs_the_takeover(self):
        from module_stage import effective_review
        root = self.project({"takeover": {"spec": "codex"}})
        self.assertEqual(effective_review(root, "alpha", "spec", "codex-approved"), ("approved", "codex"))
        self.assertEqual(effective_review(root, "alpha", "plan", "codex-approved"), ("pending", None))
        self.assertEqual(effective_review(root, "alpha", "plan", "approved"), ("approved", "user"))
        self.assertEqual(effective_review(root, "alpha", "spec", "revised"), ("revised", None))

    def test_an_important_spec_goes_to_the_user(self):
        # important-requirement (AC2): without a boundary the Spec is important (Q7 A); the Plan still follows the takeover.
        from module_stage import effective_review
        root = self.project({"takeover": {"spec": "codex", "plan": "codex"}})
        spec = root / "spec" / "alpha.md"
        spec.write_text(spec.read_text(encoding="utf-8").split("\n## 并行边界")[0] + "\n", encoding="utf-8")
        self.assertEqual(effective_review(root, "alpha", "spec", "codex-approved"), ("pending", None))
        self.assertEqual(effective_review(root, "alpha", "plan", "codex-approved"), ("approved", "codex"))

    def test_a_plan_that_pre_declares_goes_to_the_user(self):
        from module_stage import codex_route
        listed = "# Plan: alpha\n\n## 预先声明\n\n- 公共路径：`package.json`\n"
        self.assertEqual(codex_route(self.project({"takeover": "plan"}, listed), "alpha", "plan"), "pre-declared")
        empty = "# Plan: alpha\n\n## 预先声明\n\n- 公共路径：无\n"
        self.assertEqual(codex_route(self.project({"takeover": "plan"}, empty), "alpha", "plan"), "")

    def test_a_pending_plan_says_why_it_goes_to_the_user(self):
        # M3 rework: with the Plan given to codex, a pending Plan that pre-declares (or has a malformed section) goes to
        # the user, and the hint now says why instead of only "waiting for the user".
        from module_stage import COMMANDS, COMMANDS_ZH, codex_hint
        raw = {"spec": "approved", "plan": "pending"}
        for plan in ("# Plan: alpha\n\n## 预先声明\n\n- 公共路径：`package.json`\n",
                     "# Plan: alpha\n\n## 预先声明\n\n- 配置：无\n"):
            root = self.project({"takeover": "plan"}, plan)
            line, step = codex_hint(root, "alpha", "BUILDING", COMMANDS["claude"], False, raw)
            self.assertIn("pre-declared section lists shared changes or is malformed", line)
            self.assertIn("have the user review", step)
            line, step = codex_hint(root, "alpha", "BUILDING", COMMANDS_ZH["claude"], True, raw)
            self.assertIn("「预先声明」有内容或格式不对", line)
        root = self.project({}, "# Plan: alpha\n\n## 预先声明\n\n- 公共路径：`package.json`\n")
        self.assertIsNone(codex_hint(root, "alpha", "BUILDING", COMMANDS["claude"], False, raw))

    def test_combined_only_with_one_approver(self):
        from module_stage import cadence_combined
        self.assertTrue(cadence_combined(self.project({"reviewCadence": "combined"}), "alpha"))
        self.assertFalse(cadence_combined(self.project({"reviewCadence": "combined", "takeover": "plan"}), "alpha"))
        self.assertTrue(cadence_combined(self.project({"reviewCadence": "combined", "takeover": "merge"}), "alpha"))


class BlankLinesAroundTheMarker(unittest.TestCase):
    """review-marker-blank-line: whatever review_mark.py writes has a blank line on both sides of the marker line
    (none before it at the start of the file, none after it at the end), and the digest matches the file as written."""

    P = REVIEW_PENDING
    CASES = {  # name: (file before, expected layout with {m} for the marker written)
        "top, title right after": (P + "\n# Spec: alpha\n\n正文\n", "{m}\n\n# Spec: alpha\n\n正文\n"),
        "top, blank then title": (P + "\n\n# Spec: alpha\n\n正文\n", "{m}\n\n# Spec: alpha\n\n正文\n"),
        "right under the title": ("# Spec: alpha\n" + P + "\n\n正文\n", "# Spec: alpha\n\n{m}\n\n正文\n"),
        "text right after it": ("# Spec: alpha\n\n" + P + "\n正文\n", "# Spec: alpha\n\n{m}\n\n正文\n"),
        "already spaced": ("# Spec: alpha\n\n" + P + "\n\n正文\n", "# Spec: alpha\n\n{m}\n\n正文\n"),
        "no marker, text right under the title": ("# Spec: alpha\n正文\n", "# Spec: alpha\n\n{m}\n\n正文\n"),
        "at the end": ("# Spec: alpha\n\n正文\n" + P + "\n", "# Spec: alpha\n\n正文\n\n{m}\n"),
        # review_mark.py reads with universal newlines and writes "\n" (unchanged behaviour): CRLF comes back as LF, spaced.
        "crlf": ("# Spec: alpha\r\n" + P + "\r\n正文\r\n", "# Spec: alpha\n\n{m}\n\n正文\n"),
    }

    def test_pending_is_spaced(self):
        for name, (before, layout) in self.CASES.items():
            with self.subTest(case=name), Project() as project:
                project.spec.write_bytes(before.encode("utf-8"))
                code, out = project.run("--module", "alpha", "--target", "spec", "--state", "pending", "--confirm")
                self.assertEqual(code, 0, out)
                self.assertEqual(project.spec.read_bytes().decode("utf-8"), layout.format(m=REVIEW_PENDING))

    def test_approved_is_spaced_and_its_digest_matches_the_file(self):
        for name, (before, layout) in self.CASES.items():
            with self.subTest(case=name), Project() as project:
                project.spec.write_bytes(before.encode("utf-8"))
                code, out = project.run("--module", "alpha", "--target", "spec", "--state", "approved", "--confirm")
                self.assertEqual(code, 0, out)
                text = project.spec.read_bytes().decode("utf-8")
                self.assertEqual(text, layout.format(m=review_approved_line(review_digest(text))))
                self.assertEqual(project.states()[0], "approved")

    def test_a_plan_is_spaced_too(self):
        with Project() as project:
            project.plan.write_text(self.P + "\n# Plan: alpha\n\n步骤\n", encoding="utf-8")
            code, out = project.run("--module", "alpha", "--target", "plan", "--state", "approved", "--confirm")
            self.assertEqual(code, 0, out)
            self.assertEqual(project.plan.read_text(encoding="utf-8"), "%s\n\n# Plan: alpha\n\n步骤\n" % REVIEW_APPROVED)


class AcceptanceFixture(unittest.TestCase):
    """codex-final-acceptance (C2): three pieces of evidence on HEAD, recorded in the git directory, never committed."""

    BASE_TAKEOVER = {"merge": "auto"}  # the takeover in the commit before the module started
    BOUNDARY = "\n## 并行边界\n\n- 独占：`spec/alpha.md`、`tasks/alpha/`、`src/alpha.py`\n- 公共：无\n"

    def setUp(self):
        import json
        import os
        self.json = json
        self.project = Project().__enter__()
        self.addCleanup(self.project.__exit__)
        self.root = self.project.root
        self.home = self.root.parent / (self.root.name + "-home")
        self.home.mkdir()
        self.addCleanup(lambda: __import__("shutil").rmtree(self.home, ignore_errors=True))
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        self.env.update(HOME=str(self.home), GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
                        GIT_COMMITTER_EMAIL="t@t")
        self.project.spec.unlink()
        self.project.plan.unlink()
        self.config(self.BASE_TAKEOVER)
        self.git("init", "-q")
        self.git("remote", "add", "origin", "https://github.com/acme/widget.git")
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        self.project.spec.write_text(SPEC + self.BOUNDARY, encoding="utf-8")
        self.project.plan.write_text("# Plan: alpha\n\n步骤\n", encoding="utf-8")
        (self.root / "src").mkdir()
        (self.root / "src" / "alpha.py").write_text("x = 1\n", encoding="utf-8")
        self.commit("alpha")

    def config(self, takeover):
        (self.root / ".agent").mkdir(exist_ok=True)
        (self.root / ".agent" / "config.json").write_text(self.json.dumps({"version": 1, "takeover": takeover}),
                                                          encoding="utf-8")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True, text=True,
                              env=self.env).stdout.strip()

    def commit(self, message):
        self.git("add", ".")
        self.git("commit", "-qm", message)
        self.head = self.git("rev-parse", "HEAD")

    def report(self, **changes):
        import hashlib
        document = {"schema_version": 1, "execution_status": "completed", "review_outcome": "no_findings_in_scope",
                    "backend": "codex", "findings": [], "limitations": [], "reviewed": ["spec/alpha.md"],
                    "scope": {"files": {"spec/alpha.md": hashlib.sha256(self.project.spec.read_bytes()).hexdigest()},
                              "baseline": {"mode": "commits", "from": "HEAD~1", "to": self.head}}}
        document.update(changes)
        path = self.home / "final.json"
        path.write_text(self.json.dumps(document), encoding="utf-8")
        return path

    def evidence(self, **changes):
        document = {"schema": "autopilot.check-evidence/v1", "repo": "acme/widget", "head_sha": self.head,
                    "runner": "autopilot-orchestrator", "non_author": True, "clone": "/tmp/c", "ran_at": "2026-11-22T00:00:00Z",
                    "checks": [{"cmd": "make test", "exit": 0, "output_sha256": "0" * 64, "tail": "ok"}]}
        document.update(changes)
        folder = self.home / ".autopilot" / "evidence" / "acme__widget"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / (self.head + ".json")).write_text(self.json.dumps(document), encoding="utf-8")

    def accept(self, report, *extra, state="codex-approved"):
        done = subprocess.run([sys.executable, "-B", SCRIPT, "--project", str(self.root), "--module", "alpha",
                               "--target", "acceptance", "--state", state, "--review", str(report), *extra],
                              capture_output=True, text=True, timeout=30, env=self.env)
        return done.returncode, done.stdout

    def record_path(self):
        return self.root / ".git" / "spec-guard" / "acceptance" / "alpha.json"



class Acceptance(AcceptanceFixture):
    def test_three_pieces_record_in_the_git_directory(self):
        import hashlib
        report = self.report()
        self.evidence()
        code, out = self.accept(report)
        self.assertEqual(code, 0, out)
        self.assertIn("preview only", out)
        self.assertFalse(self.record_path().exists())
        code, out = self.accept(report, "--confirm")
        self.assertEqual(code, 0, out)
        record = self.json.loads(self.record_path().read_text(encoding="utf-8"))
        self.assertEqual((record["marker"], record["sha"], record["module"]), ("codex-approved", self.head, "alpha"))
        self.assertEqual(record["report_sha256"], hashlib.sha256(report.read_bytes()).hexdigest())
        self.assertEqual(record["report"], str(report.resolve()))
        self.assertTrue(Path(record["report"]).is_absolute())
        self.assertRegex(record["at"], r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ")
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertEqual(self.git("rev-parse", "HEAD"), self.head)

    def test_a_relative_report_path_is_recorded_absolute(self):
        report = self.report()
        self.evidence()
        done = subprocess.run([sys.executable, "-B", SCRIPT, "--project", str(self.root), "--module", "alpha",
                               "--target", "acceptance", "--state", "codex-approved", "--review", "final.json",
                               "--confirm"], capture_output=True, text=True, timeout=30, env=self.env, cwd=str(self.home))
        self.assertEqual(done.returncode, 0, done.stdout)
        record = self.json.loads(self.record_path().read_text(encoding="utf-8"))
        self.assertEqual(record["report"], str(report.resolve()))

    def assertRefused(self, code_out, word):
        code, out = code_out
        self.assertEqual(code, 2, out)
        self.assertIn(word, out)
        self.assertFalse(self.record_path().exists())

    def test_only_a_merge_auto_module(self):
        for takeover in ("none", "plan", {"spec": "codex", "plan": "codex"}):
            with self.subTest(takeover=takeover):
                self.config(takeover)
                self.commit("takeover %s" % takeover)
                report = self.report()
                self.evidence()
                self.assertRefused(self.accept(report, "--confirm"), "acceptance-not-auto")

    def test_only_codex_approved_with_a_report(self):
        self.evidence()
        self.assertRefused(self.accept(self.report(), "--confirm", state="approved"), "acceptance-state")
        done = subprocess.run([sys.executable, "-B", SCRIPT, "--project", str(self.root), "--module", "alpha",
                               "--target", "acceptance", "--state", "codex-approved", "--confirm"],
                              capture_output=True, text=True, timeout=30, env=self.env)
        self.assertRefused((done.returncode, done.stdout), "review-missing")

    def test_each_missing_piece_refuses(self):
        report = self.report()
        self.assertRefused(self.accept(report, "--confirm"), "no check evidence")
        self.evidence(non_author=False)
        self.assertRefused(self.accept(report, "--confirm"), "non-author")
        self.evidence()
        self.assertRefused(self.accept(self.report(review_outcome="findings", findings=[{"title": "t"}]), "--confirm"),
                           "blocking")
        self.assertRefused(self.accept(self.report(scope={"files": {}, "baseline": {}}), "--confirm"), "scope.files")

    def test_uncommitted_changes_refuse(self):
        report = self.report()
        self.evidence()
        (self.root / "src" / "alpha.py").write_text("x = 2\n", encoding="utf-8")
        self.assertRefused(self.accept(report, "--confirm"), "uncommitted")
        (self.root / "src" / "alpha.py").write_text("x = 1\n", encoding="utf-8")
        (self.root / "loose.txt").write_text("x\n", encoding="utf-8")
        self.assertRefused(self.accept(report, "--confirm"), "uncommitted")

    def test_a_config_change_after_the_start_is_not_out_of_scope(self):
        # M3 rework: narrowing and restoring the takeover rewrites the config; merge was auto before the start too.
        self.config({"merge": "auto", "plan": "codex"})
        self.commit("restored after a narrow")
        report = self.report()
        self.evidence()
        code, out = self.accept(report, "--confirm")
        self.assertEqual(code, 0, out)

    def test_out_of_scope_changes_refuse(self):
        (self.root / "README.md").write_text("x\n", encoding="utf-8")
        self.commit("outside")
        report = self.report()
        self.evidence()
        self.assertRefused(self.accept(report, "--confirm"), "out-of-scope")


class AcceptanceFlowScope(AcceptanceFixture):
    """plan-auto-approve: a merge=auto v2 module's final acceptance checks its boundary plus its design's impact."""

    BOUNDARY = ""

    def setUp(self):
        super().setUp()
        self.project.spec.write_text(SPEC.replace("\n\n", "\n\n<!-- spec-guard: flow v2 tier=normal -->\n\n", 1),
                                     encoding="utf-8")
        (self.root / "tasks" / "alpha" / "design.md").write_text("# d\n\n## 影响面\n\n- 改 `src/alpha.py`\n",
                                                                 encoding="utf-8")
        self.commit("v2 docs")

    def test_impact_only_is_accepted(self):
        report = self.report()
        self.evidence()
        code, out = self.accept(report)
        self.assertEqual(code, 0, out)
        self.assertIn("nothing out of scope", out)

    def test_outside_the_impact_still_refuses(self):
        (self.root / "README.md").write_text("x\n", encoding="utf-8")
        self.commit("outside")
        report = self.report()
        self.evidence()
        code, out = self.accept(report, "--confirm")
        self.assertEqual(code, 2, out)
        self.assertIn("acceptance-out-of-scope", out)
        self.assertIn("README.md", out)


class AcceptanceT4(unittest.TestCase):
    """plan-auto-approve: the final acceptance's scope check stops on T4 also where the scope itself is not checked."""

    def test_a_bug_without_a_boundary_changing_t4(self):
        import json
        import os
        from review_mark import _outside
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
            env.update(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")

            def git(*args):
                subprocess.run(["git", "-C", folder, *args], check=True, capture_output=True, env=env)

            def write(relative, text):
                (root / relative).parent.mkdir(parents=True, exist_ok=True)
                (root / relative).write_text(text, encoding="utf-8")
            write("spec/CAPABILITY-MAP.md", MAP.replace("| beta | y | alpha |\n", "").replace(" → beta", ""))
            write("src/secret.py", "x\n")
            write(".github/autopr/risk-paths.json", json.dumps({"schema": "autopilot.risk-paths/v1", "T4": ["src/*.py"],
                                                                "T3": []}))
            git("init", "-q")
            git("add", "-A")
            git("commit", "-qm", "base")
            write("spec/alpha.md", "# a\n\n<!-- spec-guard: flow v2 tier=bug -->\n")
            git("add", "-A")
            git("commit", "-qm", "spec")
            self.assertIsNone(_outside(root, "alpha"))
            write("src/secret.py", "changed\n")
            self.assertIn("T4 file(s) changed", _outside(root, "alpha"))


class AcceptanceWorktrees(AcceptanceFixture):
    """codex-route-guard (AC4, AC5): shared records, legacy fallback and unchanged ancestry checks."""

    def setUp(self):
        super().setUp()
        self.main = self.root.resolve()
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        linked = Path(folder.name) / "linked"
        self.git("worktree", "add", "--detach", str(linked))
        self.root = linked
        self.common_record = self.main / ".git" / "spec-guard" / "acceptance" / "alpha.json"
        self.legacy_record = Path(self.git("rev-parse", "--git-path", "spec-guard/acceptance/alpha.json"))
        self.assertNotEqual(self.common_record, self.legacy_record)

    def write_record(self, path, sha):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.json.dumps({"marker": "codex-approved", "sha": sha, "module": "alpha"}),
                        encoding="utf-8")

    def test_linked_acceptance_is_shared_and_gate_still_requires_ancestry(self):
        from module_stage import acceptance_path, acceptance_record, final_gate_accepted
        self.git("commit", "--allow-empty", "-qm", "linked acceptance")
        self.head = self.git("rev-parse", "HEAD")
        self.evidence()
        code, out = self.accept(self.report(), "--confirm")
        self.assertEqual(code, 0, out)
        expected = {"marker": "codex-approved", "sha": self.head}
        self.assertEqual(acceptance_record(self.main, "alpha"), expected)
        self.assertEqual(acceptance_path(self.main, "alpha"), self.common_record)
        self.assertEqual(acceptance_path(self.root, "alpha"), self.common_record)
        self.assertIn("recorded codex-approved acceptance: %s" % self.common_record, out)
        self.assertFalse(self.legacy_record.exists())
        self.assertEqual(self.json.loads(self.common_record.read_text(encoding="utf-8"))["sha"], self.head)
        done = subprocess.run([sys.executable, "-B", str(Path(SCRIPT).with_name("map_view.py")),
                               "--project", str(self.main), "--json"], capture_output=True, text=True,
                              timeout=30, env=self.env)
        self.assertEqual(done.returncode, 0, done.stderr)
        module = next(item for item in self.json.loads(done.stdout)["modules"] if item["id"] == "alpha")
        self.assertEqual(module["acceptance"], expected)
        todo = "- [x] implementation\n- [ ] Checkpoint 1（gate）：最终验收\n"
        self.assertFalse(final_gate_accepted(self.main, "alpha", todo))
        self.git("-C", str(self.main), "merge", "--ff-only", self.head)
        self.assertTrue(final_gate_accepted(self.main, "alpha", todo))
        self.git("-C", str(self.main), "commit", "--allow-empty", "-qm", "after acceptance")
        self.assertNotEqual(self.git("-C", str(self.main), "rev-parse", "HEAD"), self.head)
        self.assertTrue(final_gate_accepted(self.main, "alpha", todo))

    def test_legacy_record_is_read_without_migration(self):
        from module_stage import acceptance_record
        self.write_record(self.legacy_record, self.head)
        self.assertEqual(acceptance_record(self.root, "alpha"), {"marker": "codex-approved", "sha": self.head})
        self.assertFalse(self.common_record.exists())

    def test_common_record_takes_priority_and_writing_preserves_legacy(self):
        from module_stage import acceptance_record
        legacy_sha = self.git("rev-parse", "HEAD~1")
        self.write_record(self.legacy_record, legacy_sha)
        legacy = self.legacy_record.read_bytes()
        self.write_record(self.common_record, self.head)
        self.assertEqual(acceptance_record(self.root, "alpha"), {"marker": "codex-approved", "sha": self.head})
        self.evidence()
        code, out = self.accept(self.report(), "--confirm")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.legacy_record.read_bytes(), legacy)

    def test_invalid_common_records_fall_back_to_legacy(self):
        from module_stage import acceptance_record
        self.write_record(self.legacy_record, self.head)
        self.common_record.parent.mkdir(parents=True)
        for text in ("{", "[]", "\ufffd", self.json.dumps({"marker": "approved", "sha": self.head, "module": "alpha"}),
                     self.json.dumps({"marker": "codex-approved", "sha": "invalid", "module": "alpha"}),
                     self.json.dumps({"marker": "codex-approved", "sha": self.head, "module": "beta"})):
            with self.subTest(text=text):
                self.common_record.write_text(text, encoding="utf-8")
                self.assertEqual(acceptance_record(self.root, "alpha"),
                                 {"marker": "codex-approved", "sha": self.head})
        self.common_record.write_bytes(b"\xff")
        self.assertEqual(acceptance_record(self.root, "alpha"), {"marker": "codex-approved", "sha": self.head})


class AcceptanceWidenedLater(AcceptanceFixture):
    """M3 rework (Q14 A): merge must have been auto before the module started, so a patch cannot grant it to itself."""

    BASE_TAKEOVER = {"plan": "codex"}

    def test_merge_auto_only_after_the_start_refuses(self):
        self.config({"merge": "auto"})
        self.commit("widened during the module")
        report = self.report()
        self.evidence()
        code, out = self.accept(report, "--confirm")
        self.assertEqual(code, 2, out)
        self.assertIn("acceptance-not-auto-at-base", out)
        self.assertFalse(self.record_path().exists())



DESIGN = ("# 技术方案：alpha\n\n## 现状调研\n\n现状\n\n## 影响面\n\n- `src/alpha/new.py`\n\n## 实现方案\n\n做法\n\n"
          "## 接口和数据改动\n\n无\n\n## 风险与回滚\n\n无\n\n## 方案取舍\n\n无\n")
DESIGN_LINE = (r"<!-- spec-guard: design-review round=(\d+) blocking=(\d+) sha256=[0-9a-f]{12} vendor=(\S+) "
               r"same-vendor=(true|false) criteria=design-v1 report=([0-9a-f]{64}) -->")


class DesignMarks(unittest.TestCase):
    """design-review C2 (assumptions 5, 6): rounds of a second reviewer on tasks/<id>/design.md."""

    def setUp(self):
        self.project = Project().__enter__()
        self.addCleanup(self.project.__exit__, None, None, None)
        spec = self.project.spec
        spec.write_text(SPEC.replace("\n\n", "\n\n<!-- spec-guard: flow v2 tier=normal -->\n\n", 1), encoding="utf-8")
        not_important(self.project)
        self.design = self.project.root / "tasks" / "alpha" / "design.md"
        self.design.write_text(DESIGN, encoding="utf-8")

    def report(self, severities=(), recheck=None, selection="cross_vendor", criteria="design-v1", vendor="openai",
               same=False, **changes):
        import hashlib
        import json
        relative = "tasks/alpha/design.md"
        findings = [{"title": "t", "file": relative, "line": None, "trigger": "x", "impact": "y", "evidence": "z",
                     "suggestion": "w", "unverified": [], "severity": severity} for severity in severities]
        none = selection == "none"
        document = {"schema_version": 1, "execution_status": "conditions_missing" if none else "completed",
                    "review_outcome": "inconclusive" if none else ("findings" if findings else "no_findings_in_scope"),
                    "backend": None if none else "codex", "criteria": criteria,
                    "reviewer": {"vendor": None if none else vendor, "backend": None if none else "codex",
                                 "same_vendor": None if none else same, "selection": selection},
                    "scope": {"files": {relative: hashlib.sha256(self.design.read_bytes()).hexdigest()}},
                    "findings": findings, "diagnostics": ["no_reviewer_available"] if none else [],
                    "recheck": None if recheck is None else {"items": [{"index": index, "status": status}
                                                                      for index, status in enumerate(recheck)]}}
        document.update(changes)
        out = self.project.root / ("design-report-%d.json" % len(list(self.project.root.glob("design-report-*.json"))))
        out.write_text(json.dumps(document), encoding="utf-8")
        return str(out)

    def mark(self, state, report=None, confirm=True):
        args = ["--module", "alpha", "--target", "design", "--state", state]
        if report is not None:
            args += ["--review", report]
        return self.project.run(*args, *(["--confirm"] if confirm else []))

    def text(self):
        return self.design.read_text(encoding="utf-8")

    def rounds(self):
        import re
        return [match.groups() for match in re.finditer(DESIGN_LINE, self.text())]

    def test_clean_round_is_approved_by_the_reviewer(self):
        import hashlib
        report = self.report(severities=("suggestion",), same=True)
        code, out = self.mark("reviewer-approved", report)
        self.assertEqual(code, 0, out)
        self.assertEqual(review_state(self.text(), "design"), "reviewer-approved")
        self.assertEqual(self.rounds(), [("1", "0", "openai", "true",
                                          hashlib.sha256(Path(report).read_bytes()).hexdigest())])
        self.design.write_text(self.text() + "- 建议一：采纳。\n", encoding="utf-8")  # a reason keeps the approval
        self.assertEqual(review_state(self.text(), "design"), "reviewer-approved")
        self.design.write_text(self.text().replace("做法", "新做法"), encoding="utf-8")
        self.assertEqual(review_state(self.text(), "design"), "revised")

    def test_only_unresolved_recheck_items_still_block(self):
        # AC5: the old codex rounds counted findings only and would record this second round as blocking=0.
        self.assertEqual(self.mark("reviewer-reviewed", self.report(severities=("blocking",)))[0], 0)
        report = self.report(recheck=("unresolved", "resolved"))
        code, out = self.mark("reviewer-approved", report)
        self.assertEqual(code, 2, out)
        self.assertIn("design-blocking", out)
        code, out = self.mark("reviewer-reviewed", report)
        self.assertEqual(code, 0, out)
        self.assertEqual([item[:2] for item in self.rounds()], [("1", "1"), ("2", "1")])
        self.assertEqual(review_state(self.text(), "design"), "pending")

    def test_a_second_round_must_recheck_the_first(self):
        self.assertEqual(self.mark("reviewer-reviewed", self.report(severities=("blocking",)))[0], 0)
        before = self.text()
        code, out = self.mark("reviewer-approved", self.report())
        self.assertEqual(code, 2, out)
        self.assertIn("design-recheck-missing", out)
        self.assertEqual(self.text(), before)
        code, out = self.mark("reviewer-approved", self.report(recheck=("resolved",)))
        self.assertEqual(code, 0, out)
        self.assertEqual(review_state(self.text(), "design"), "reviewer-approved")

    def test_two_blocking_rounds_go_to_the_user(self):
        self.assertEqual(self.mark("reviewer-reviewed", self.report(severities=("blocking",)))[0], 0)
        self.assertEqual(self.mark("reviewer-reviewed", self.report(recheck=("unresolved",)))[0], 0)
        for state in ("reviewer-reviewed", "reviewer-approved"):
            code, out = self.mark(state, self.report(recheck=("resolved",)))
            self.assertEqual(code, 2, (state, out))
            self.assertIn("design-rounds-exhausted", out)
        code, out = self.mark("approved")
        self.assertEqual(code, 0, out)
        self.assertEqual(review_state(self.text(), "design"), "approved")
        self.assertEqual(len(self.rounds()), 2)

    def test_criteria_must_not_change_between_rounds(self):
        self.assertEqual(self.mark("reviewer-reviewed", self.report(severities=("blocking",)))[0], 0)
        self.design.write_text(self.text().replace("criteria=design-v1", "criteria=design-v0"), encoding="utf-8")
        before = self.text()
        code, out = self.mark("reviewer-approved", self.report(recheck=("resolved",)))
        self.assertEqual(code, 2, out)
        self.assertIn("design-criteria-changed", out)
        self.assertEqual(self.text(), before)
        code, out = self.mark("reviewer-reviewed", self.report(criteria="severity-v1"))
        self.assertEqual(code, 2, out)
        self.assertIn("report-invalid", out)

    def test_no_reviewer_is_recorded_as_unreviewed(self):
        # AC7 / Q1 A: not a failure; the design goes to the user.
        for state in ("reviewer-approved", "reviewer-reviewed"):
            with self.subTest(state=state):
                self.design.write_text(DESIGN, encoding="utf-8")
                code, out = self.mark(state, self.report(selection="none"))
                self.assertEqual(code, 0, out)
                self.assertIn("unreviewed", out)
                self.assertEqual([item[:4] for item in self.rounds()], [("1", "0", "none", "false")])
                self.assertEqual(review_state(self.text(), "design"), "pending")
        code, out = self.mark("approved")
        self.assertEqual(code, 0, out)
        self.assertEqual(review_state(self.text(), "design"), "approved")

    def test_any_backend_counts(self):
        report = self.report(backend="claude-code", vendor="anthropic", same=True)
        self.assertEqual(self.mark("reviewer-approved", report)[0], 0)
        self.assertEqual(self.rounds()[0][2:4], ("anthropic", "true"))

    def test_bad_reports_and_targets_write_nothing(self):
        import json
        before = self.text()
        bad = [self.report(execution_status="failed"), self.report(review_outcome="inconclusive"),
               self.report(reviewer={"vendor": "openai", "backend": "codex", "same_vendor": None,
                                     "selection": "cross_vendor"}),
               self.report(reviewer={"vendor": "openai", "backend": "codex", "same_vendor": False,
                                     "selection": "guess"}),
               self.report(scope={"files": {"tasks/alpha/design.md": "0" * 64}}),
               self.report(recheck={"items": [{"index": 0, "status": "maybe"}]}),
               str(self.project.root / "missing.json")]
        for report in bad:
            code, out = self.mark("reviewer-reviewed", report)
            self.assertEqual(code, 2, (json.dumps(report), out))
            self.assertIn("report-invalid", out)
        self.assertEqual(self.mark("reviewer-approved")[0], 2)  # no --review
        for state in ("codex-approved", "codex-reviewed"):
            code, out = self.mark(state, self.report())
            self.assertEqual(code, 2, out)
            self.assertIn("design-state", out)
        code, out = self.project.run("--module", "alpha", "--target", "spec", "--state", "reviewer-approved",
                                     "--review", self.report(), "--confirm")
        self.assertEqual(code, 2, out)
        self.assertEqual(self.text(), before)

    def test_only_a_new_flow_module_with_a_design(self):
        self.project.spec.write_text(SPEC, encoding="utf-8")
        code, out = self.mark("reviewer-approved", self.report())
        self.assertEqual(code, 2, out)
        self.assertIn("design-not-v2", out)
        self.project.spec.write_text(SPEC.replace("\n\n", "\n\n<!-- spec-guard: flow v2 tier=small -->\n\n", 1),
                                     encoding="utf-8")
        code, out = self.mark("pending")
        self.assertEqual(code, 2, out)
        self.assertIn("design-not-v2", out)
        self.project.spec.write_text(SPEC.replace("\n\n", "\n\n<!-- spec-guard: flow v2 tier=normal -->\n\n", 1),
                                     encoding="utf-8")
        self.design.unlink()
        code, out = self.mark("pending")
        self.assertEqual(code, 2, out)
        self.assertIn("file-missing", out)

    def test_the_user_approves_with_a_preview_first(self):
        code, out = self.mark("approved", confirm=False)
        self.assertEqual(code, 0, out)
        self.assertIn("preview only", out)
        self.assertEqual(self.text(), DESIGN)
        self.assertEqual(self.mark("approved")[0], 0)
        self.assertEqual(review_state(self.text(), "design"), "approved")
        self.design.write_text(self.text().replace("做法", "新做法"), encoding="utf-8")
        self.assertEqual(review_state(self.text(), "design"), "revised")

    def test_an_important_design_is_still_the_users(self):
        self.project.spec.write_text(self.project.spec.read_text(encoding="utf-8").replace("tier=normal", "tier=important"),
                                     encoding="utf-8")
        code, out = self.mark("reviewer-approved", self.report())
        self.assertEqual(code, 0, out)
        self.assertIn("important", out)

    def test_design_human_records_the_round_and_waits_for_the_user(self):
        # takeover-redefine (C4 as revised, AC3): the clean round is recorded; it does not let the design through.
        import json
        from module_stage import design_approval
        cfg = self.project.root / ".agent" / "config.json"
        cfg.parent.mkdir(exist_ok=True)
        for takeover, says in (("none", True), ("design", False)):
            with self.subTest(takeover=takeover):
                cfg.write_text(json.dumps({"version": 1, "takeover": takeover}), encoding="utf-8")
                self.design.write_text(DESIGN, encoding="utf-8")
                code, out = self.mark("reviewer-approved", self.report())
                self.assertEqual(code, 0, out)
                self.assertEqual(review_state(self.text(), "design"), "reviewer-approved")
                self.assertEqual("design=human" in out, says, out)
                status = design_approval(self.project.root, "alpha")["status"]
                self.assertEqual(status, "pending-user" if says else "approved")
        cfg.write_text(json.dumps({"version": 1, "takeover": "none"}), encoding="utf-8")
        self.assertEqual(self.mark("approved")[0], 0)
        self.assertEqual(design_approval(self.project.root, "alpha")["approvedBy"], "user")



class PlanAutoRefusal(unittest.TestCase):
    """plan-auto-approve AC3: review-mark refuses --target plan / both on a v2 module before reading any file."""

    def test_every_state_and_shape_refuses_and_writes_nothing(self):
        for plan in (None, "# Plan: alpha\n\n步骤\n", "# Plan\n\n<!-- spec-guard: review bogus -->\n"):
            for target in ("plan", "both"):
                for state in ("pending", "approved", "codex-approved", "codex-reviewed"):
                    with self.subTest(plan=plan, target=target, state=state), Project() as project:
                        project.spec.write_text(SPEC.replace("\n\n", "\n\n<!-- spec-guard: flow v2 tier=normal -->\n\n", 1),
                                                encoding="utf-8")
                        if plan is None:
                            project.plan.unlink()
                        else:
                            project.plan.write_text(plan, encoding="utf-8")
                        before = (project.spec.read_bytes(), project.plan.read_bytes() if plan is not None else None)
                        code, out = project.run("--module", "alpha", "--target", target, "--state", state,
                                                "--review", str(project.root / "missing.json"), "--confirm")
                        self.assertEqual(code, 2, out)
                        self.assertTrue(out.startswith("plan-auto: "), out)
                        self.assertEqual((project.spec.read_bytes(),
                                          project.plan.read_bytes() if plan is not None else None), before)
                        self.assertEqual(plan is None, not project.plan.exists())

    def test_old_module_is_unchanged(self):
        with Project() as project:
            code, out = project.run("--module", "alpha", "--target", "plan", "--state", "pending", "--confirm")
            self.assertEqual(code, 0, out)
            self.assertEqual(project.states()[1], "pending")


if __name__ == "__main__":
    unittest.main()
