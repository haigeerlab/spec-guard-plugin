#!/usr/bin/env python3
"""在临时 Git 仓库里验证本机用户名路径检查。"""
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

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
        self.env["SPEC_GUARD_LOGIN_NAME"] = ""
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

    def test_login_name_reports_case_insensitive_matches_and_line_numbers(self):
        self.env["SPEC_GUARD_LOGIN_NAME"] = "alice"
        self.write("names.txt", "safe\n'Alice'\nuserName: alice\nALICE alice\n")
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(result.stdout.splitlines(), [
            "  ❌ names.txt:2: Alice",
            "  ❌ names.txt:3: alice",
            "  ❌ names.txt:4: ALICE",
            "  ❌ names.txt:4: alice",
        ])

    def test_login_name_requires_whole_words(self):
        self.env["SPEC_GUARD_LOGIN_NAME"] = "alice"
        self.write("names.txt", "malice alice_x aliceberg _alice 1alice alice2\n")
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("alice", result.stdout.lower())

    def test_placeholder_generic_empty_and_short_login_names_are_skipped(self):
        names = ("someone", "user", "username", "name", "me", "you", "example",
                 "...", "$user", "${user}", "runner", "root", "ubuntu", "admin",
                 "vagrant", "ci", "RUNNER", "", "ab")
        for name in names:
            with self.subTest(name=name):
                self.env["SPEC_GUARD_LOGIN_NAME"] = name
                self.write("names.txt", name + "\n")
                result = self.check()
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_login_name_is_literal(self):
        self.env["SPEC_GUARD_LOGIN_NAME"] = "a.ce"
        self.write("names.txt", "abce\na.ce\n")
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(result.stdout.splitlines(), ["  ❌ names.txt:2: a.ce"])

    def test_login_name_uses_the_existing_file_filters(self):
        self.env["SPEC_GUARD_LOGIN_NAME"] = "alice"
        self.write("tracked.txt", "safe\n")
        self.write("untracked.txt", "alice\n", tracked=False)
        self.write("binary.bin", b"\x00alice\n")
        self.write("non-utf8.txt", b"\xffalice\n")
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_login_name_is_detected_without_override(self):
        scan = runpy.run_path(str(SCRIPT))["scan"]
        self.write("names.txt", "Alice\n")
        with mock.patch.dict(os.environ):
            os.environ.pop("SPEC_GUARD_LOGIN_NAME", None)
            with mock.patch("getpass.getuser", return_value="alice"):
                self.assertEqual(scan(self.root), ["names.txt:1: Alice"])

    def test_missing_login_name_skips_only_the_new_check(self):
        scan = runpy.run_path(str(SCRIPT))["scan"]
        absolute = USER_ROOT + "alice/"
        self.write("names.txt", "alice\n" + absolute + "\n")
        for outcome in ({"return_value": ""}, {"side_effect": OSError("unavailable")}):
            with self.subTest(outcome=outcome), mock.patch.dict(os.environ):
                os.environ.pop("SPEC_GUARD_LOGIN_NAME", None)
                with mock.patch("getpass.getuser", **outcome):
                    self.assertEqual(scan(self.root), ["names.txt:2: " + absolute])

    def test_checker_and_tests_need_no_file_exemptions(self):
        self.write("check-local-paths.py", SCRIPT.read_bytes())
        self.write("test_check_local_paths.py", Path(__file__).read_bytes())
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_current_repository_passes(self):
        self.env.pop("SPEC_GUARD_LOGIN_NAME", None)
        result = self.check(ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("✅", result.stdout)


if __name__ == "__main__":
    unittest.main()
