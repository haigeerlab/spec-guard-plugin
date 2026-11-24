#!/usr/bin/env python3
"""plugin-spec-compliance: check-frontmatter.py parses skill, agent and command frontmatter as YAML.

Needs PyYAML; the macOS system Python has none, so the whole set is skipped there (CI's plugin job installs it).
"""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().with_name("check-frontmatter.py")
REPO = SCRIPT.parent.parent
HAS_YAML = importlib.util.find_spec("yaml") is not None


@unittest.skipUnless(HAS_YAML, "PyYAML is not installed")
class FrontmatterTest(unittest.TestCase):
    def run_on(self, files):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for relative, text in files.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
            return subprocess.run([sys.executable, "-B", str(SCRIPT), str(root)], capture_output=True, text=True,
                                  timeout=60)

    SKILL = "plugins/p/skills/s/SKILL.md"
    AGENT = "plugins/p/agents/a.md"
    COMMAND = "plugins/p/commands/c.md"

    def test_complete_files_pass(self):
        done = self.run_on({self.SKILL: "---\nname: s\ndescription: does s\n---\n\nbody\n",
                            self.AGENT: "---\nname: a\ndescription: does a\nmodel: sonnet\n---\n",
                            self.COMMAND: "---\ndescription: does c\nallowed-tools: Bash\n---\n"})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_command_needs_no_name(self):
        done = self.run_on({self.COMMAND: "---\ndescription: does c\n---\n"})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_missing_fields(self):
        cases = {
            "skill without name": ({self.SKILL: "---\ndescription: d\n---\n"}, "name"),
            "skill without description": ({self.SKILL: "---\nname: s\n---\n"}, "description"),
            "agent without name": ({self.AGENT: "---\ndescription: d\n---\n"}, "name"),
            "command without description": ({self.COMMAND: "---\nargument-hint: x\n---\n"}, "description"),
            "empty description": ({self.SKILL: "---\nname: s\ndescription: \"\"\n---\n"}, "description"),
        }
        for label, (files, field) in cases.items():
            with self.subTest(label):
                done = self.run_on(files)
                self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
                self.assertIn(field, done.stdout)
                self.assertIn(next(iter(files)), done.stdout)

    def test_broken_or_missing_frontmatter(self):
        cases = {
            "broken yaml": "---\nname: s\ndescription: [unclosed\n---\n",
            "not a mapping": "---\n- a\n- b\n---\n",
            "no frontmatter": "# just a heading\n",
            "unterminated": "---\nname: s\ndescription: d\n",
        }
        for label, text in cases.items():
            with self.subTest(label):
                done = self.run_on({self.SKILL: text})
                self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
                self.assertIn(self.SKILL, done.stdout)

    def test_this_repository_passes(self):
        done = subprocess.run([sys.executable, "-B", str(SCRIPT), str(REPO)], capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("frontmatter", done.stdout)


if __name__ == "__main__":
    unittest.main()
