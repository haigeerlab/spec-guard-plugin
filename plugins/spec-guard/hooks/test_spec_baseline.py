"""pre-build-spec-batch: the approved baseline of a revised Spec comes from git history, never from memory."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from module_stage import pre_build_batch, spec_baseline  # noqa: E402

GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "core.hooksPath=/dev/null",
       "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main"]
MAP = ("# Capability Map\n\n| Module id | Responsibility | Depends on |\n|---|---|---|\n| alpha | x | — |\n\n"
       "Build order: alpha\n")
SPEC = "# Spec: alpha\n\n## Objective\n\nDo the thing.\n"


class Repo:
    def __init__(self, git=True):
        self.git_repo = git

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "spec").mkdir()
        (self.root / "spec" / "CAPABILITY-MAP.md").write_text(MAP, encoding="utf-8")
        self.spec.write_text(SPEC, encoding="utf-8")
        if self.git_repo:
            self.git("init", "-q")
        return self

    def __exit__(self, *exc):
        self.tmp.cleanup()

    @property
    def spec(self):
        return self.root / "spec" / "alpha.md"

    def git(self, *args):
        subprocess.run(GIT + list(args), cwd=self.root, check=True, capture_output=True, timeout=30)

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.root, capture_output=True, text=True,
                              check=True).stdout.strip()

    def approve(self):
        subprocess.run([sys.executable, "-B", str(HERE / "review_mark.py"), "--project", str(self.root), "--module",
                        "alpha", "--target", "spec", "--state", "approved", "--confirm"],
                       check=True, capture_output=True, timeout=30)

    def edit(self, extra="\nAnother line.\n"):
        self.spec.write_text(self.spec.read_text(encoding="utf-8") + extra, encoding="utf-8")


class Baseline(unittest.TestCase):
    def test_found_after_committing_the_approval(self):
        with Repo() as repo:
            repo.approve()
            approved = repo.spec.read_text(encoding="utf-8")
            sha = repo.commit("approved")
            repo.edit()
            repo.commit("revised")
            repo.edit("\nUncommitted line.\n")
            found = spec_baseline(repo.root, "alpha")
            self.assertEqual(found["status"], "found", found)
            self.assertEqual(found["commit"], sha)
            self.assertEqual(found["text"], approved)

    def test_absent_when_the_approval_was_never_committed(self):
        with Repo() as repo:
            repo.commit("draft")
            repo.approve()
            repo.edit()
            self.assertEqual(spec_baseline(repo.root, "alpha"), {"status": "absent"})

    def test_unverified_outside_git(self):
        with Repo(git=False) as repo:
            repo.approve()
            repo.edit()
            found = spec_baseline(repo.root, "alpha")
            self.assertEqual(found["status"], "unverified")
            self.assertTrue(found["reason"])

    def test_only_the_last_fifty_commits(self):
        with Repo() as repo:
            repo.approve()
            repo.commit("approved")
            for n in range(50):
                repo.edit("\nline %d\n" % n)
                repo.commit("edit %d" % n)
            self.assertEqual(spec_baseline(repo.root, "alpha"), {"status": "absent"})

    def test_not_approved_is_absent(self):
        with Repo() as repo:
            repo.commit("draft")
            self.assertEqual(spec_baseline(repo.root, "alpha"), {"status": "absent"})


class PreBuild(unittest.TestCase):
    def test_only_a_revised_spec_before_the_plan_is_approved(self):
        with Repo() as repo:
            repo.approve()
            repo.commit("approved")
            repo.edit()
            self.assertEqual(pre_build_batch(repo.root, "alpha", "NEEDS_PLAN", "revised", "none")["status"], "found")
            self.assertEqual(pre_build_batch(repo.root, "alpha", "BUILDING", "revised", "pending")["status"], "found")
            self.assertIsNone(pre_build_batch(repo.root, "alpha", "BUILDING", "revised", "approved"))
            self.assertIsNone(pre_build_batch(repo.root, "alpha", "BUILDING", "revised", "none"))
            self.assertIsNone(pre_build_batch(repo.root, "alpha", "NEEDS_PLAN", "approved", "none"))
            self.assertIsNone(pre_build_batch(repo.root, "alpha", "NEEDS_SPEC", "revised", "none"))


if __name__ == "__main__":
    unittest.main()
