"""Suspending and resuming a started module: preview, confirm, refusals. No network."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from module_stage import SUSPEND_MARKER

SCRIPT = str(Path(__file__).with_name("module_suspend.py"))
MAP = ("# Capability Map\n| Module id | Responsibility | Depends on |\n|---|---|---|\n"
       "| alpha | x | — |\n| beta | y | alpha |\n| gamma | z | beta |\n\nBuild order: alpha → beta → gamma\n")


class Project:
    """alpha half done, beta not started, gamma spec only; todo text per module is overridable."""

    def __init__(self, alpha="- [x] built\n- [ ] review later\n", beta="- [ ] start\n"):
        self.todos = {"alpha": alpha, "beta": beta}

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "spec").mkdir()
        (self.root / "spec" / "CAPABILITY-MAP.md").write_text(MAP, encoding="utf-8")
        for module in ("alpha", "beta", "gamma"):
            (self.root / "spec" / (module + ".md")).write_text("# %s\n" % module, encoding="utf-8")
        for module, todo in self.todos.items():
            (self.root / "tasks" / module).mkdir(parents=True)
            (self.root / "tasks" / module / "plan.md").write_text("# Plan\n", encoding="utf-8")
            if todo is not None:
                (self.root / "tasks" / module / "todo.md").write_text(todo, encoding="utf-8")
        return self

    def todo(self, module):
        return (self.root / "tasks" / module / "todo.md").read_text(encoding="utf-8")

    def run(self, *args):
        done = subprocess.run([sys.executable, "-B", SCRIPT, *args, "--project", str(self.root)],
                              capture_output=True, text=True, timeout=20)
        return done.returncode, done.stdout

    def __exit__(self, *exc):
        self.tmp.cleanup()


class Suspend(unittest.TestCase):
    def test_preview_writes_nothing_and_names_the_next_current_module(self):
        with Project() as project:
            before = project.todo("alpha")
            code, out = project.run("--suspend", "alpha")
            self.assertEqual(code, 0, out)
            self.assertIn("preview only", out)
            self.assertIn("current module after suspending: beta", out)
            self.assertEqual(project.todo("alpha"), before)

    def test_confirm_appends_the_marker_and_reads_back(self):
        with Project() as project:
            code, out = project.run("--suspend", "alpha", "--confirm")
            self.assertEqual(code, 0, out)
            lines = project.todo("alpha").splitlines()
            self.assertEqual(lines[-1], SUSPEND_MARKER)
            self.assertEqual(lines[:2], ["- [x] built", "- [ ] review later"])
            self.assertIn("suspended alpha", out)

    def test_missing_final_newline_is_kept_apart_from_the_marker(self):
        with Project(alpha="- [x] built\n- [ ] review later") as project:
            self.assertEqual(project.run("--suspend", "alpha", "--confirm")[0], 0)
            self.assertEqual(project.todo("alpha").splitlines()[-2:], ["- [ ] review later", SUSPEND_MARKER])

    def test_refusals_write_nothing(self):
        cases = {
            "not-a-module-id": ("Alpha!",),
            "not-in-map": ("delta",),
            "no-plan-or-todo": ("gamma",),
        }
        for reason, (module,) in cases.items():
            with Project() as project:
                code, out = project.run("--suspend", module, "--confirm")
                self.assertEqual(code, 2, reason)
                self.assertIn(reason, out)
        with Project(beta="- [x] start\n") as project:
            code, out = project.run("--suspend", "beta", "--confirm")
            self.assertEqual(code, 2)
            self.assertIn("nothing-open", out)
            self.assertNotIn(SUSPEND_MARKER, project.todo("beta"))
        with Project(alpha="- [ ] a\n%s\n" % SUSPEND_MARKER) as project:
            code, out = project.run("--suspend", "alpha", "--confirm")
            self.assertEqual(code, 2)
            self.assertIn("already-suspended", out)
            self.assertEqual(project.todo("alpha").count(SUSPEND_MARKER), 1)

    def test_exactly_one_action(self):
        with Project() as project:
            self.assertEqual(project.run("--suspend", "alpha", "--resume", "beta")[0], 2)
            self.assertEqual(project.run()[0], 2)


class Resume(unittest.TestCase):
    def test_preview_then_confirm_removes_the_marker(self):
        with Project(alpha="- [x] built\n- [ ] review later\n%s\n" % SUSPEND_MARKER) as project:
            code, out = project.run("--resume", "alpha")
            self.assertEqual(code, 0, out)
            self.assertIn("preview only", out)
            self.assertIn(SUSPEND_MARKER, project.todo("alpha"))
            self.assertIn("current module after resuming: alpha", out)
            code, out = project.run("--resume", "alpha", "--confirm")
            self.assertEqual(code, 0, out)
            self.assertEqual(project.todo("alpha"), "- [x] built\n- [ ] review later\n")

    def test_not_suspended_is_refused(self):
        with Project() as project:
            code, out = project.run("--resume", "alpha", "--confirm")
            self.assertEqual(code, 2)
            self.assertIn("not-suspended", out)

    def test_resuming_while_another_module_is_half_done_explains_the_pause(self):
        todo = "- [x] built\n- [ ] review later\n%s\n" % SUSPEND_MARKER
        with Project(alpha=todo, beta="- [x] one\n- [ ] two\n") as project:
            state = project.root / ".agent"
            state.mkdir()
            (state / "state.json").write_text('{"activeModule":"beta"}\n', encoding="utf-8")
            code, out = project.run("--resume", "alpha")
            self.assertEqual(code, 0, out)
            self.assertIn("beta is half done", out)
            self.assertIn("alpha will show as paused", out)


if __name__ == "__main__":
    unittest.main()
