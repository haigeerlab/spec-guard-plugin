import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from test_usage_draft import GOOD, MAP  # noqa: E402

DRAFT = "spec/usage/demo.md"


class MilestoneMarkTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "spec" / "usage").mkdir(parents=True)
        (self.root / "spec" / "CAPABILITY-MAP.md").write_text(MAP, encoding="utf-8")
        self.write(GOOD)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, text):
        (self.root / DRAFT).write_text(text, encoding="utf-8")

    def text(self):
        return (self.root / DRAFT).read_text(encoding="utf-8")

    def sha(self):
        return hashlib.sha256((self.root / "spec" / "usage" / "demo.md").read_bytes()).hexdigest()

    def done(self, *modules):
        for module in modules:
            (self.root / "spec" / ("%s.md" % module)).write_text("# Spec\n", encoding="utf-8")
            folder = self.root / "tasks" / module
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "plan.md").write_text("# Plan\n", encoding="utf-8")
            (folder / "todo.md").write_text("- [x] Task 1\n", encoding="utf-8")

    def run_mark(self, milestone, *extra, draft=DRAFT):
        return subprocess.run([sys.executable, "-B", str(HERE / "milestone_mark.py"), "--project", str(self.root),
                               "--draft", draft, "--milestone", milestone] + list(extra),
                              capture_output=True, text=True, stdin=subprocess.DEVNULL)

    def test_preview_is_read_only(self):
        self.done("alpha", "beta")
        before = self.sha()
        out = self.run_mark("M1")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("<!-- spec-guard: milestone M1 confirmed alpha, beta -->", out.stdout)
        self.assertIn("U1", out.stdout)
        self.assertIn("--confirm", out.stdout)
        self.assertEqual(self.sha(), before)

    def test_confirm_writes_one_line(self):
        self.done("alpha", "beta")
        out = self.run_mark("M1", "--confirm")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        text = self.text()
        self.assertEqual(text.count("<!-- spec-guard: milestone M1 confirmed alpha, beta -->"), 1)
        self.assertTrue(text.startswith(GOOD.rstrip("\n")), text)
        self.assertEqual(sorted(p.name for p in (self.root / "spec" / "usage").iterdir()), ["demo.md"])

    def test_already_confirmed(self):
        self.done("alpha", "beta")
        self.write(GOOD + "\n<!-- spec-guard: milestone M1 confirmed alpha, beta -->\n")
        before = self.sha()
        out = self.run_mark("M1", "--confirm")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("已确认", out.stdout)
        self.assertEqual(self.sha(), before)

    def test_stale_record_is_replaced(self):
        self.done("alpha", "beta")
        self.write(GOOD + "\n<!-- spec-guard: milestone M1 confirmed alpha -->\n")
        out = self.run_mark("M1", "--confirm")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        text = self.text()
        self.assertNotIn("confirmed alpha -->", text)
        self.assertEqual(text.count("milestone M1 confirmed"), 1)
        self.assertIn("<!-- spec-guard: milestone M1 confirmed alpha, beta -->", text)

    def test_refuse_unknown_milestone(self):
        out = self.run_mark("M9", "--confirm")
        self.assertEqual(out.returncode, 2)
        self.assertIn("M9", out.stdout)

    def test_refuse_incomplete(self):
        self.done("alpha")
        before = self.sha()
        out = self.run_mark("M1", "--confirm")
        self.assertEqual(out.returncode, 2)
        self.assertIn("beta", out.stdout)
        self.assertEqual(self.sha(), before)

    def test_refuse_earlier_unconfirmed(self):
        self.done("alpha", "beta", "gamma", "delta")
        out = self.run_mark("M2", "--confirm")
        self.assertEqual(out.returncode, 2)
        self.assertIn("M1", out.stdout)
        self.assertNotIn("milestone M2 confirmed", self.text())

    def test_refuse_draft_outside_usage(self):
        out = self.run_mark("M1", draft="spec/CAPABILITY-MAP.md")
        self.assertEqual(out.returncode, 2)

    def test_refuse_broken_draft(self):
        self.write("# nothing\n")
        out = self.run_mark("M1")
        self.assertEqual(out.returncode, 2)


if __name__ == "__main__":
    unittest.main()
