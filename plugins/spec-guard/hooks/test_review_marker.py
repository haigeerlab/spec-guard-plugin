"""Review markers on a module's Spec and Plan: the five states and the Spec fingerprint. No network."""
import unittest

from module_stage import (REVIEW_APPROVED, REVIEW_PENDING, review_approved_line, review_body, review_digest,
                          review_state)

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


if __name__ == "__main__":
    unittest.main()
