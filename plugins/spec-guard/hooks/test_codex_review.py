"""codex-approval (C1): a delegate review report is read, never trusted blindly; it must match the file on disk."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from codex_review import inspect, inspect_check, inspect_final  # noqa: E402

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


def git(root, *args):
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True,
                          env=env).stdout.strip()


class FinalAcceptance(unittest.TestCase):
    """codex-final-acceptance (C1): evidence 1 (Codex on the final patch) and evidence 2 (checks by a non-author)."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "repo"
        (self.root / "spec").mkdir(parents=True)
        (self.root / "spec" / "alpha.md").write_text(SPEC, encoding="utf-8")
        git(self.root, "init", "-q")
        git(self.root, "remote", "add", "origin", "git@github.com:acme/widget.git")
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "c")
        self.head = git(self.root, "rev-parse", "HEAD")
        self.evidence = Path(tmp.name) / "evidence"

    def final(self, **changes):
        document = report(scope={"files": {"spec/alpha.md": hashlib.sha256(SPEC.encode()).hexdigest()},
                                 "baseline": {"mode": "commits", "from": "HEAD~1", "to": self.head}})
        document.update(changes)
        path = self.root.parent / "final.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        return inspect_final(path, self.root, "alpha")

    def check(self, raw=None, **changes):
        document = {"schema": "autopilot.check-evidence/v1", "repo": "acme/widget", "head_sha": self.head,
                    "runner": "autopilot-orchestrator", "non_author": True, "clone": "/tmp/x", "ran_at": "2026-11-22T00:00:00Z",
                    "checks": [{"cmd": "make test", "exit": 0, "output_sha256": "0" * 64, "tail": "ok"}]}
        document.update(changes)
        folder = self.evidence / "acme__widget"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / (self.head + ".json")).write_text(raw if raw is not None else json.dumps(document), encoding="utf-8")
        return inspect_check(self.root, evidence_root=self.evidence)

    def test_final_review_of_head_passes(self):
        found = self.final()
        self.assertEqual((found["status"], found["head"]), ("ok", self.head), found)

    def test_final_review_is_refused_for_each_gap(self):
        cases = {
            "blocking": {"review_outcome": "findings", "findings": [finding("blocking")]},
            "no severity": {"review_outcome": "findings", "findings": [finding()]},
            "not codex": {"backend": "claude-code"},
            "not completed": {"execution_status": "failed"},
            "not head": {"scope": {"files": {"spec/alpha.md": hashlib.sha256(SPEC.encode()).hexdigest()},
                                   "baseline": {"mode": "commits", "from": "a", "to": "0" * 40}}},
            "not commits": {"scope": {"files": {"spec/alpha.md": hashlib.sha256(SPEC.encode()).hexdigest()},
                                      "baseline": {"mode": "working-tree", "to": self.head}}},
            "spec missing": {"scope": {"files": {}, "baseline": {"mode": "commits", "to": self.head}}},
        }
        for name, changes in cases.items():
            with self.subTest(name):
                found = self.final(**changes)
                self.assertEqual(found["status"], "invalid", found)
                self.assertTrue(found["reason"])

    def test_final_review_spec_must_match_disk(self):
        (self.root / "spec" / "alpha.md").write_text(SPEC + "x\n", encoding="utf-8")
        found = self.final()
        self.assertEqual(found["status"], "invalid")
        self.assertIn("sha256", found["reason"])

    def test_check_evidence_from_a_non_author_on_head_passes(self):
        found = self.check()
        self.assertEqual(found["status"], "ok", found)
        self.assertEqual(found["head"], self.head)
        self.assertTrue(found["path"].endswith("acme__widget/%s.json" % self.head))

    def test_check_evidence_is_refused_for_each_gap(self):
        cases = {
            "runner": {"runner": "claude"},
            "author": {"non_author": False},
            "author string": {"non_author": "true"},
            "exit": {"checks": [{"cmd": "a", "exit": 0}, {"cmd": "b", "exit": 1}]},
            "no checks": {"checks": []},
            "other head": {"head_sha": "0" * 40},
            "schema": {"schema": "autopilot.check-evidence/v2"},
        }
        for name, changes in cases.items():
            with self.subTest(name):
                found = self.check(**changes)
                self.assertEqual(found["status"], "invalid", found)
                self.assertTrue(found["reason"])

    def test_missing_or_unreadable_evidence_is_no_evidence(self):
        found = inspect_check(self.root, evidence_root=self.evidence)
        self.assertEqual(found["status"], "invalid")
        self.assertIn("no check evidence", found["reason"])
        self.assertEqual(self.check(raw="{oops")["status"], "invalid")

    def test_owner_and_repo_come_from_origin(self):
        for url in ("https://github.com/acme/widget.git", "https://github.com/acme/widget", "ssh://git@github.com/acme/widget.git"):
            with self.subTest(url):
                git(self.root, "remote", "set-url", "origin", url)
                self.assertEqual(self.check()["status"], "ok")
        git(self.root, "remote", "remove", "origin")
        found = inspect_check(self.root, evidence_root=self.evidence)
        self.assertEqual(found["status"], "invalid")
        self.assertIn("origin", found["reason"])


if __name__ == "__main__":
    unittest.main()
