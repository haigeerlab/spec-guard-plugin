"""module-cost-report regressions. Every fixture is synthetic: a temporary git repo plus fake
host session directories. Nothing here reads the machine's real Claude or Codex sessions."""
import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import module_cost_report as mcr

MODULE = "demo"
TODO = Path("tasks") / MODULE / "todo.md"


def utc(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)


class Repo:
    """A throwaway git repo whose commits carry exact committer times."""

    def __init__(self, root):
        self.root = Path(root)
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.invalid")
        self.git("config", "user.name", "t")

    def git(self, *args, when=None):
        env = dict(os.environ)
        if when:
            env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = when
        return subprocess.run(["git", "-C", str(self.root), *args], check=True,
                              capture_output=True, text=True, env=env).stdout

    def todo(self, lines, when):
        path = self.root / TODO
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Todo: demo\n\n" + "\n".join(lines) + "\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-qm", "todo", when=when)


class TaskWindowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Repo(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def windows(self, now="2026-10-05T12:00:00Z"):
        return mcr.task_windows(self.repo.root, MODULE, now=utc(now))

    def test_two_ticked_tasks_get_consecutive_windows(self):
        self.repo.todo(["- [ ] Task 1：a", "- [ ] Task 2：b"], "2026-10-05T10:00:00Z")
        self.repo.todo(["- [x] Task 1：a", "- [ ] Task 2：b"], "2026-10-05T10:20:00Z")
        self.repo.todo(["- [x] Task 1：a", "- [x] Task 2：b"], "2026-10-05T10:45:00Z")
        tasks = self.windows()["tasks"]
        self.assertEqual([t["title"] for t in tasks], ["Task 1：a", "Task 2：b"])
        self.assertEqual((tasks[0]["start"], tasks[0]["end"]), (utc("2026-10-05T10:00:00Z"), utc("2026-10-05T10:20:00Z")))
        self.assertEqual((tasks[1]["start"], tasks[1]["end"]), (utc("2026-10-05T10:20:00Z"), utc("2026-10-05T10:45:00Z")))
        self.assertTrue(all(t["done"] for t in tasks))

    def test_unchecked_task_runs_until_now(self):
        self.repo.todo(["- [ ] Task 1：a", "- [ ] Task 2：b"], "2026-10-05T10:00:00Z")
        self.repo.todo(["- [x] Task 1：a", "- [ ] Task 2：b"], "2026-10-05T10:20:00Z")
        task2 = self.windows(now="2026-10-05T11:30:00Z")["tasks"][1]
        self.assertFalse(task2["done"])
        self.assertEqual((task2["start"], task2["end"]), (utc("2026-10-05T10:20:00Z"), utc("2026-10-05T11:30:00Z")))

    def test_first_tick_counts_even_if_unticked_later(self):
        self.repo.todo(["- [ ] Task 1：a"], "2026-10-05T10:00:00Z")
        self.repo.todo(["- [x] Task 1：a"], "2026-10-05T10:10:00Z")
        self.repo.todo(["- [ ] Task 1：a"], "2026-10-05T10:15:00Z")
        self.repo.todo(["- [x] Task 1：a"], "2026-10-05T10:30:00Z")
        task = self.windows()["tasks"][0]
        self.assertEqual(task["end"], utc("2026-10-05T10:10:00Z"))

    def test_uncommitted_todo_cannot_be_attributed(self):
        path = self.repo.root / TODO
        path.parent.mkdir(parents=True)
        path.write_text("- [x] Task 1：a\n", encoding="utf-8")
        with self.assertRaises(mcr.AttributionError) as caught:
            self.windows()
        self.assertIn("没有提交历史", str(caught.exception))

    def test_missing_todo_cannot_be_attributed(self):
        with self.assertRaises(mcr.AttributionError) as caught:
            self.windows()
        self.assertIn("todo.md", str(caught.exception))

    def test_not_a_git_repo_cannot_be_attributed(self):
        with tempfile.TemporaryDirectory() as plain:
            (Path(plain) / TODO).parent.mkdir(parents=True)
            (Path(plain) / TODO).write_text("- [x] Task 1：a\n", encoding="utf-8")
            with self.assertRaises(mcr.AttributionError):
                mcr.task_windows(Path(plain), MODULE, now=utc("2026-10-05T12:00:00Z"))

    def test_cli_exits_2_and_reports_why_instead_of_zero(self):
        result = subprocess.run(["python3", "-B", str(Path(mcr.__file__)), "--project", str(self.repo.root),
                                 "--json", MODULE], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("无法归属", result.stdout + result.stderr)
        self.assertNotIn('"total"', result.stdout)

    def test_cli_json_lists_windows(self):
        self.repo.todo(["- [ ] Task 1：a"], "2026-10-05T10:00:00Z")
        self.repo.todo(["- [x] Task 1：a"], "2026-10-05T10:20:00Z")
        result = subprocess.run(["python3", "-B", str(Path(mcr.__file__)), "--project", str(self.repo.root),
                                 "--json", MODULE], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        task = data["modules"][0]["tasks"][0]
        self.assertEqual((task["start"], task["end"]), ("2026-10-05T10:00:00Z", "2026-10-05T10:20:00Z"))


if __name__ == "__main__":
    unittest.main(verbosity=1)
