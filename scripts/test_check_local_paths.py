#!/usr/bin/env python3
"""在临时 Git 仓库里验证本机用户名路径检查。"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check-local-paths.py"
USER_ROOT = "/Users" + "/"
ENCODED_ROOT = "-Users" + "-"


class LocalPathsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="sg-local-paths-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        self.git("init", "-q")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, env=self.env,
                              check=True, capture_output=True)

    def write(self, name, content, tracked=True):
        path = self.root / name
        path.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
        if tracked:
            self.git("add", "--", name)

    def check(self, root=None):
        return subprocess.run([sys.executable, str(SCRIPT)], cwd=root or self.root,
                              env=self.env, text=True, capture_output=True)

    def test_real_names_report_both_forms_and_line_numbers(self):
        absolute = USER_ROOT + "alice/x"
        encoded = ENCODED_ROOT + "alice-repo"
        self.write("paths.txt", "safe\n" + absolute + "\n" + encoded + "\n")
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("❌", result.stdout)
        self.assertIn("paths.txt:2:", result.stdout)
        self.assertIn(absolute.rsplit("/", 1)[0] + "/", result.stdout)
        self.assertIn("paths.txt:3:", result.stdout)
        self.assertIn(ENCODED_ROOT + "alice-", result.stdout)

    def test_all_placeholders_are_allowed_case_insensitively(self):
        names = ("someone", "user", "username", "name", "me", "you", "example",
                 "<name>", "<用户名>", "<user-name>", "...", "$USER", "${USER}")
        paths = []
        for name in names:
            for variant in (name, name.upper(), name.lower()):
                paths.extend((USER_ROOT + variant + "/x", ENCODED_ROOT + variant + "-x"))
        self.write("placeholders.txt", "\n".join(paths))
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("✅", result.stdout)

    def test_real_names_are_not_placeholder_prefixes(self):
        self.write("names.txt", USER_ROOT + "someone_else/x\n" + ENCODED_ROOT + "username2-repo\n")
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("names.txt:1:", result.stdout)
        self.assertIn("names.txt:2:", result.stdout)

    def test_untracked_files_are_ignored(self):
        self.write("tracked.txt", "safe\n")
        self.write("untracked.txt", USER_ROOT + "alice/x\n", tracked=False)
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_binary_and_non_utf8_files_are_ignored(self):
        path = (USER_ROOT + "alice/x\n").encode("utf-8")
        self.write("binary.bin", b"\x00" + path)
        self.write("non-utf8.txt", b"\xff" + path)
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_worktree_content_is_checked_instead_of_index_content(self):
        self.write("edited.txt", "safe\n")
        self.write("edited.txt", USER_ROOT + "alice/x\n", tracked=False)
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("edited.txt:1:", result.stdout)

    def test_checker_and_tests_need_no_file_exemptions(self):
        self.write("check-local-paths.py", SCRIPT.read_bytes())
        self.write("test_check_local_paths.py", Path(__file__).read_bytes())
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_current_repository_passes(self):
        result = self.check(ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("✅", result.stdout)


if __name__ == "__main__":
    unittest.main()
