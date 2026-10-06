"""Paste-ready session handoff text (session-handoff spec, items 1, 2, 10, 11).

Fixtures are temporary git repositories built here; nothing reads this machine's transcripts.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import session_handoff

SCRIPT = str(Path(__file__).resolve().parent / "session_handoff.py")
MAP = ("# Capability Map\n| Module id | Responsibility | Depends on |\n|---|---|---|\n"
       "| alpha | x | — |\n| beta | y | alpha |\n\nBuild order: alpha → beta\n")


def git(*args, cwd):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com",
                           "-c", "commit.gpgsign=false", *args],
                          cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class Handoff(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve() / "demo-repo"
        self.root.mkdir()
        git("init", "-q", "-b", "main", cwd=self.root)
        (self.root / "README").write_text("x\n")
        self.commit("init")

    def tearDown(self):
        self.tmp.cleanup()

    def commit(self, message):
        git("add", "-A", cwd=self.root)
        git("commit", "-q", "--allow-empty", "-m", message, cwd=self.root)
        return git("rev-parse", "--short", "HEAD", cwd=self.root)

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def module(self, module_id, todo=None):
        self.write("spec/%s.md" % module_id, "# %s\n" % module_id)
        self.write("tasks/%s/plan.md" % module_id, "# Plan\n")
        if todo is not None:
            self.write("tasks/%s/todo.md" % module_id, todo)

    def text(self, root=None):
        return session_handoff.handoff_text(root or self.root)

    def line(self, prefix, root=None):
        lines = [l for l in self.text(root).splitlines() if l.startswith(prefix)]
        self.assertEqual(len(lines), 1, self.text(root))
        return lines[0]

    # Shape

    def test_header_names_repository_worktree_branch_and_head(self):
        head = git("rev-parse", "--short", "HEAD", cwd=self.root)
        self.assertEqual(self.text().splitlines()[0],
                         "demo-repo 仓库（%s，分支 main，HEAD %s）。" % (self.root, head))

    def test_ends_with_the_blank_for_the_user(self):
        text = self.text()
        self.assertTrue(text.endswith("\n## 下一步\n下一步：____"), text)
        self.assertIn("\n## 现状\n", text)

    # Stage line, every stage the hook can report

    def test_idle_without_a_capability_map(self):
        self.assertEqual(self.line("阶段 "), "阶段 IDLE；没有能力图。")

    def test_map_only_without_module_specs(self):
        self.write("spec/CAPABILITY-MAP.md", MAP)
        self.assertEqual(self.line("阶段 "), "阶段 MAP_ONLY；有能力图，没有模块 Spec。")

    def test_needs_spec(self):
        self.write("spec/CAPABILITY-MAP.md", MAP)
        self.write("spec/other.md", "# other\n")
        self.assertEqual(self.line("阶段 "),
                         "阶段 NEEDS_SPEC；模块 2，Spec 0，Plan 0，进行中 0，完成 0；当前模块 alpha。")

    def test_building(self):
        self.write("spec/CAPABILITY-MAP.md", MAP)
        self.module("alpha", "- [x] a\n")
        self.module("beta", "- [x] a\n- [ ] b\n")
        self.assertEqual(self.line("阶段 "),
                         "阶段 BUILDING；模块 2，Spec 2，Plan 2，进行中 1，完成 1；当前模块 beta。")

    def test_done(self):
        self.write("spec/CAPABILITY-MAP.md", MAP)
        self.module("alpha", "- [x] a\n")
        self.module("beta", "- [x] b\n")
        self.assertEqual(self.line("阶段 "),
                         "阶段 DONE；模块 2，Spec 2，Plan 2，进行中 0，完成 2；当前模块 无。")

    def test_invalid_map(self):
        self.write("spec/CAPABILITY-MAP.md", "| alpha | x | — |\n")
        self.write("spec/alpha.md", "# alpha\n")
        self.assertEqual(self.line("阶段 "), "阶段 MAP_INVALID；能力图无法解析，运行 verify-artifacts 查看。")

    # Location

    def test_detached_head(self):
        sha = self.commit("second")
        git("checkout", "-q", "--detach", "HEAD", cwd=self.root)
        self.assertIn("，分离 HEAD，HEAD %s）" % sha, self.text().splitlines()[0])

    def test_linked_worktree_reports_its_own_root_and_the_repository_name(self):
        linked = self.root.parent / "wt-x"
        git("worktree", "add", "-q", "-b", "feat", str(linked), cwd=self.root)
        first = self.text(linked).splitlines()[0]
        self.assertTrue(first.startswith("demo-repo 仓库（%s，分支 feat，HEAD " % linked), first)

    def test_outside_git_everything_git_is_unknown(self):
        plain = self.root.parent / "plain"
        plain.mkdir()
        text = self.text(plain)
        self.assertEqual(text.splitlines()[0], "plain 仓库（%s，分支 未知，HEAD 未知）。" % plain)
        self.assertIn("未合并提交：未知", text)

    # Unmerged commits (done-unmerged-hint's rule: locally known origin default branch, no fetch)

    def test_unmerged_count_against_origin(self):
        git("update-ref", "refs/remotes/origin/main", "HEAD", cwd=self.root)
        self.commit("a")
        self.commit("b")
        self.assertEqual(self.line("未合并提交："), "未合并提交：2 个（相对 origin/main）")

    def test_no_unmerged_commits(self):
        git("update-ref", "refs/remotes/origin/main", "HEAD", cwd=self.root)
        self.assertEqual(self.line("未合并提交："), "未合并提交：无（相对 origin/main）")

    def test_unmerged_unknown_without_a_remote(self):
        self.assertEqual(self.line("未合并提交："), "未合并提交：未知（没有本地已知的远端默认分支）")

    # Release evidence

    def evidence(self, name, statuses):
        records = [{"subject": subject, "status": status} for subject, status in statuses]
        self.write("docs/releases/%s" % name, json.dumps({"schemaVersion": 1, "records": records}))

    def test_latest_version_wins_numerically_and_files_merge(self):
        self.evidence("v0.9.0-claude.json", [("old", "not-verified")])
        self.evidence("v0.10.0-claude.json", [("a", "not-verified"), ("b", "host-verified")])
        self.evidence("v0.10.0-codex.json", [("c", "not-verified")])
        self.assertEqual(self.line("发布证据"), "发布证据 v0.10.0 中 not-verified：a、c")

    def test_latest_version_without_not_verified(self):
        self.evidence("v1.0.0-claude.json", [("a", "host-verified")])
        self.assertEqual(self.line("发布证据"), "发布证据 v1.0.0 中 not-verified：无")

    def test_no_release_evidence(self):
        self.assertEqual(self.line("发布证据"), "发布证据：无")

    def test_unreadable_evidence_file_is_skipped(self):
        self.write("docs/releases/v2.0.0-claude.json", "{not json")
        self.evidence("v2.0.0-codex.json", [("c", "not-verified")])
        self.write("docs/releases/notes.md", "x")
        self.assertEqual(self.line("发布证据"), "发布证据 v2.0.0 中 not-verified：c")

    # Read-only and the command line

    def test_read_only(self):
        self.write("spec/CAPABILITY-MAP.md", MAP)
        self.module("alpha", "- [ ] a\n")

        def snapshot():
            out = {}
            for directory, _, files in os.walk(self.root):
                for name in files:
                    path = os.path.join(directory, name)
                    out[path] = os.stat(path).st_mtime_ns
            return out
        before = snapshot()
        self.text()
        self.assertEqual(before, snapshot())

    def test_command_line_prints_the_text(self):
        done = subprocess.run([sys.executable, "-B", SCRIPT, str(self.root)], capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, timeout=20)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout, self.text() + "\n")


if __name__ == "__main__":
    unittest.main()
