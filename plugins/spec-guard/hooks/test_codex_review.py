"""codex-approval (C1): a delegate review report is read, never trusted blindly; it must match the file on disk."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from codex_review import inspect  # noqa: E402

SPEC = "# Spec: alpha\n\n## Objective\n\nDo the thing.\n"


def report(**changes):
    base = {"schema_version": 1, "execution_status": "completed", "review_outcome": "no_findings_in_scope",
            "backend": "codex", "scope": {"files": {"spec/alpha.md": hashlib.sha256(SPEC.encode()).hexdigest()}},
            "reviewed": ["spec/alpha.md"], "findings": [], "limitations": ["Review does not authorize merge or delivery."]}
    base.update(changes)
    return base


def finding(severity=None):
    item = {"title": "t", "file": "spec/alpha.md", "line": None, "trigger": "x", "impact": "y", "evidence": "z",
            "suggestion": "w", "unverified": []}
    if severity is not None:
        item["severity"] = severity
    return item


class Inspect(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "spec").mkdir()
        (self.root / "spec" / "alpha.md").write_text(SPEC, encoding="utf-8")

    def run_with(self, document, raw=None):
        path = self.root / "report.json"
        path.write_text(raw if raw is not None else json.dumps(document), encoding="utf-8")
        return inspect(path, self.root, "spec/alpha.md")

    def test_a_clean_codex_review_passes(self):
        found = self.run_with(report())
        self.assertEqual((found["status"], found["blocking"]), ("ok", 0), found)
        self.assertEqual(found["sha256"], hashlib.sha256(SPEC.encode()).hexdigest())

    def test_blocking_is_counted_and_missing_severity_blocks(self):
        found = self.run_with(report(review_outcome="findings",
                                     findings=[finding("blocking"), finding("suggestion"), finding()]))
        self.assertEqual((found["status"], found["blocking"], found["suggestions"]), ("ok", 2, 1), found)

    def test_reports_without_a_conclusion_are_invalid(self):
        for changes in ({"execution_status": "timed_out"}, {"review_outcome": "inconclusive"}, {"backend": "claude-code"},
                        {"schema_version": 2}, {"findings": "none"}):
            with self.subTest(changes=changes):
                found = self.run_with(report(**changes))
                self.assertEqual(found["status"], "invalid", found)
                self.assertTrue(found["reason"])

    def test_the_file_must_be_the_one_on_disk(self):
        self.assertEqual(self.run_with(report(scope={"files": {}}))["status"], "invalid")
        (self.root / "spec" / "alpha.md").write_text(SPEC + "\nChanged.\n", encoding="utf-8")
        found = self.run_with(report())
        self.assertEqual(found["status"], "invalid")
        self.assertIn("sha256", found["reason"])

    def test_unreadable_reports_are_invalid(self):
        self.assertEqual(self.run_with(None, raw="{not json")["status"], "invalid")
        self.assertEqual(inspect(self.root / "missing.json", self.root, "spec/alpha.md")["status"], "invalid")


if __name__ == "__main__":
    unittest.main()
