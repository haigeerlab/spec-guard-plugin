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


class ValueSets(unittest.TestCase):
    """plugin-interface: interface.json publishes these sets, so every state the code returns must be in them."""

    def test_review_states(self):
        self.assertEqual(REVIEW_STATES, ("none", "pending", "approved", "revised", "invalid"))
        seen = {review_state(SPEC, "spec"), review_state(with_marker(REVIEW_PENDING), "spec"),
                review_state(approved(), "spec"), review_state(approved() + "改\n", "spec"),
                review_state(with_marker(REVIEW_APPROVED), "spec")}
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

    def test_approving_names_both_sources(self):
        # hub-relayed-approval: the user's words in this conversation, or relayed by a registered decision hub.
        with Project() as project:
            code, out = project.run("--module", "alpha", "--target", "spec", "--state", "approved")
            self.assertEqual(code, 0, out)
            self.assertIn("decision hub", out)
            self.assertIn("item number", out)
            self.assertIn("the message sent to the hub", out)
            self.assertNotIn("an approval the user gave in this conversation.", out)

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


if __name__ == "__main__":
    unittest.main()
