"""gate-tick: gate_tick.py ticks a module's final acceptance checkbox, by module_stage's gate criterion. No network."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from module_stage import at_final_gate

SCRIPT = str(Path(__file__).with_name("gate_tick.py"))
MAP = ("# Capability Map\n| Module id | Responsibility | Depends on |\n|---|---|---|\n"
       "| alpha | x | — |\n| beta | y | alpha |\n\nBuild order: alpha → beta\n")


class GateTick(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "spec").mkdir()
        (self.root / "spec" / "CAPABILITY-MAP.md").write_text(MAP, encoding="utf-8")
        (self.root / "tasks" / "alpha").mkdir(parents=True)
        self.todo = self.root / "tasks" / "alpha" / "todo.md"

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, text):
        self.todo.write_bytes(text.encode("utf-8"))

    def run_tick(self, *extra, module="alpha"):
        return subprocess.run([sys.executable, "-B", SCRIPT, "--project", str(self.root), "--module", module, *extra],
                              capture_output=True, text=True)

    def text(self):
        return self.todo.read_bytes().decode("utf-8")

    def test_preview_changes_nothing(self):
        todo = "# Todo\n\n- [x] Task 1\n- [ ] Checkpoint 1（gate）：最终验收\n"
        self.write(todo)
        done = self.run_tick()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("Checkpoint 1（gate）：最终验收", done.stdout)
        self.assertIn("0 unchecked item(s) left", done.stdout)
        self.assertEqual(self.text(), todo)

    def test_preview_shows_the_line_as_it_is_and_what_it_becomes(self):
        # Rework 1: the preview prints the unchanged line, and the ticked form only as what it would become.
        self.write("- [x] Task 1\n- [ ] 最终验收（gate）\n")
        out = self.run_tick().stdout.splitlines()
        self.assertEqual(out[0], "tasks/alpha/todo.md line 2: - [ ] 最终验收（gate）")
        self.assertIn("would become: - [x] 最终验收（gate）", out[1])
        done = self.run_tick("--confirm").stdout.splitlines()
        self.assertEqual(done[0], "tasks/alpha/todo.md line 2: - [x] 最终验收（gate）")

    def test_confirm_ticks_only_that_box(self):
        self.write("# Todo\n\n- [x] Task 1\n- [ ] Checkpoint 1（gate）：最终验收 — 记 [ ] 原样\n")
        done = self.run_tick("--confirm")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.text(), "# Todo\n\n- [x] Task 1\n- [x] Checkpoint 1（gate）：最终验收 — 记 [ ] 原样\n")

    def test_items_after_the_final_gate_stay_and_are_counted(self):
        self.write("- [x] Task 1\n- [ ] Checkpoint 2（gate）：最终验收\n- [ ] 发版后的核对\n")
        done = self.run_tick("--confirm")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("1 unchecked item(s) left", done.stdout)
        self.assertEqual(self.text(), "- [x] Task 1\n- [x] Checkpoint 2（gate）：最终验收\n- [ ] 发版后的核对\n")

    def test_chinese_forms(self):
        for todo, ticked in (("- [x] G1（gate）\n- [ ] 最终验收（gate）\n", "- [x] G1（gate）\n- [x] 最终验收（gate）\n"),
                             ("- [x] 检查点 1：中途\n* [ ] 检查点 2：最终验收\n", "- [x] 检查点 1：中途\n* [x] 检查点 2：最终验收\n"),
                             ("+ [ ] 最终验收（Gate）\n", "+ [x] 最终验收（Gate）\n")):
            with self.subTest(todo=todo):
                self.write(todo)
                done = self.run_tick("--confirm")
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                self.assertEqual(self.text(), ticked)

    def test_crlf_is_kept(self):
        self.write("- [x] Task 1\r\n- [ ] Checkpoint（gate）：验收\r\n")
        self.assertEqual(self.run_tick("--confirm").returncode, 0)
        self.assertEqual(self.text(), "- [x] Task 1\r\n- [x] Checkpoint（gate）：验收\r\n")

    def test_already_ticked_is_a_no_op(self):
        todo = "- [x] Task 1\n- [x] Checkpoint 1（gate）：最终验收\n- [ ] 发版后的核对\n"
        self.write(todo)
        done = self.run_tick("--confirm")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("already ticked", done.stdout)
        self.assertEqual(self.text(), todo)

    def test_refusals_change_nothing(self):
        cases = (("- [ ] Task 1\n- [ ] Checkpoint 1（gate）：最终验收\n", "not-at-final-gate"),
                 ("- [ ] G1（gate）\n- [ ] Task\n- [ ] 最终验收（gate）\n", "not-at-final-gate"),
                 ("- [ ] Task 1\n- [ ] 最终验收\n", "no-gate"))
        for todo, code in cases:
            with self.subTest(code=code, todo=todo):
                self.write(todo)
                done = self.run_tick("--confirm")
                self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
                self.assertTrue(done.stdout.startswith(code + ":"), done.stdout)
                self.assertEqual(self.text(), todo)

    def test_not_at_final_gate_names_the_first_open_item(self):
        self.write("- [ ] Task 1：先做\n- [ ] Checkpoint 1（gate）：最终验收\n")
        self.assertIn("Task 1：先做", self.run_tick().stdout)

    def test_project_level_refusals(self):
        self.assertTrue(self.run_tick(module="Alpha").stdout.startswith("not-a-module-id:"))
        self.assertTrue(self.run_tick(module="gamma").stdout.startswith("not-in-map:"))
        missing = self.run_tick()
        self.assertEqual(missing.returncode, 2)
        self.assertTrue(missing.stdout.startswith("todo-missing:"), missing.stdout)
        self.todo.write_bytes(b"\xff\xfe not utf-8\n")
        self.assertTrue(self.run_tick().stdout.startswith("todo-unreadable:"))
        (self.root / "spec" / "CAPABILITY-MAP.md").write_text("not a map\n", encoding="utf-8")
        self.assertTrue(self.run_tick().stdout.startswith("map-unreadable:"))

    def test_tickable_exactly_when_the_stage_hint_says_final_gate(self):
        todos = ("- [x] a\n- [ ] Checkpoint：验收\n", "- [ ] a\n- [ ] Checkpoint：验收\n",
                 "- [x] a\n- [ ] Checkpoint 1（gate）：x\n- [ ] Checkpoint 2（gate）：y\n",
                 "- [x] a\n- [ ] Checkpoint 1：中途\n- [ ] 检查点 2：最终验收\n",
                 "- [x] a\n- [ ] 最终验收（gate）\n- [ ] 发版后的核对\n", "- [ ] a\n")
        for todo in todos:
            with self.subTest(todo=todo):
                self.write(todo)
                self.assertEqual(self.run_tick().returncode == 0, at_final_gate(self.root, "alpha"))


if __name__ == "__main__":
    unittest.main()
