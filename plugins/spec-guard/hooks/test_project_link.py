"""The link from a session directory to the project it works on: parsing, validation and the command. No network."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from project_link import LINK_PATH, resolve

SCRIPT = str(Path(__file__).with_name("project_link.py"))


class Dirs:
    """A session directory with no convention and a project directory beside it; names carry a space and CJK."""

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name).resolve()
        self.session = base / "需求 文档"
        self.project = base / "the project"
        self.session.mkdir()
        self.project.mkdir()
        return self

    def link(self, content):
        path = self.session / LINK_PATH
        path.parent.mkdir(exist_ok=True)
        path.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")
        return path

    def __exit__(self, *exc):
        self.tmp.cleanup()


class Resolve(unittest.TestCase):
    def test_no_file_is_none(self):
        with Dirs() as dirs:
            self.assertEqual(resolve(dirs.session), ("none", None))
            (dirs.session / ".agent").mkdir()
            self.assertEqual(resolve(dirs.session), ("none", None))

    def test_absolute_path(self):
        with Dirs() as dirs:
            dirs.link({"version": 1, "project": str(dirs.project)})
            self.assertEqual(resolve(dirs.session), ("ok", dirs.project))

    def test_relative_path_is_relative_to_the_session_directory(self):
        with Dirs() as dirs:
            dirs.link({"version": 1, "project": "../the project"})
            self.assertEqual(resolve(dirs.session), ("ok", dirs.project))
            here = os.getcwd()
            os.chdir(dirs.project)
            try:
                self.assertEqual(resolve(dirs.session), ("ok", dirs.project))
            finally:
                os.chdir(here)

    def test_a_symlinked_target_resolves_to_the_real_directory(self):
        with Dirs() as dirs:
            alias = dirs.session.parent / "alias"
            alias.symlink_to(dirs.project, target_is_directory=True)
            dirs.link({"version": 1, "project": str(alias)})
            self.assertEqual(resolve(dirs.session), ("ok", dirs.project))

    def test_invalid_forms(self):
        with Dirs() as dirs:
            for content in ("{broken", "[]", '"x"', {"project": str(dirs.project)},
                            {"version": 2, "project": str(dirs.project)},
                            {"version": "1", "project": str(dirs.project)},
                            {"version": True, "project": str(dirs.project)},
                            {"version": 1, "project": ""}, {"version": 1, "project": "   "},
                            {"version": 1, "project": 3}, {"version": 1},
                            {"version": 1, "project": str(dirs.project), "extra": 1},
                            {"version": 1, "project": str(dirs.project) + "\nx"}):
                dirs.link(content)
                self.assertEqual(resolve(dirs.session), ("invalid", None), content)

    def test_a_link_that_is_not_a_readable_file_is_invalid(self):
        with Dirs() as dirs:
            (dirs.session / LINK_PATH).mkdir(parents=True)
            self.assertEqual(resolve(dirs.session), ("invalid", None))

    def test_missing_target(self):
        with Dirs() as dirs:
            dirs.link({"version": 1, "project": str(dirs.project / "gone")})
            self.assertEqual(resolve(dirs.session)[0], "missing")
            file_target = dirs.project / "file.txt"
            file_target.write_text("x", encoding="utf-8")
            dirs.link({"version": 1, "project": str(file_target)})
            self.assertEqual(resolve(dirs.session)[0], "missing")


BLOCK = "<!-- BEGIN:agent-skills-convention -->\n"
MAP = ("# Capability Map\n| Module id | Responsibility | Depends on |\n|---|---|---|\n| alpha | x | — |\n\n"
       "Build order: alpha\n")


class Command(unittest.TestCase):
    def setUp(self):
        self.dirs = Dirs().__enter__()
        self.addCleanup(self.dirs.__exit__)
        (self.dirs.project / "CLAUDE.md").write_text(BLOCK, encoding="utf-8")
        (self.dirs.project / "spec").mkdir()
        (self.dirs.project / "spec" / "CAPABILITY-MAP.md").write_text(MAP, encoding="utf-8")
        (self.dirs.project / "spec" / "alpha.md").write_text("# Spec: alpha\n", encoding="utf-8")
        self.file = self.dirs.session / LINK_PATH

    def run_cmd(self, *args, cwd=None):
        done = subprocess.run([sys.executable, "-B", SCRIPT, *args, "--from", str(self.dirs.session)],
                              capture_output=True, text=True, timeout=30, cwd=cwd)
        return done.returncode, done.stdout

    def test_show_without_a_link(self):
        code, out = self.run_cmd("show")
        self.assertEqual(code, 0, out)
        self.assertIn("no link", out)

    def test_set_previews_then_writes_and_reads_back(self):
        code, out = self.run_cmd("set", "--project", str(self.dirs.project))
        self.assertEqual(code, 0, out)
        self.assertFalse(self.file.exists())
        self.assertIn("preview only; nothing was written", out)
        self.assertIn(str(self.dirs.project), out)
        self.assertIn("NEEDS_PLAN", out)                  # the target's current phase
        self.assertIn(".gitignore", out)
        code, out = self.run_cmd("set", "--project", str(self.dirs.project), "--confirm")
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(self.file.read_text(encoding="utf-8")),
                         {"version": 1, "project": str(self.dirs.project)})
        self.assertEqual(resolve(self.dirs.session), ("ok", self.dirs.project))
        first = self.file.read_text(encoding="utf-8")
        code, out = self.run_cmd("set", "--project", str(self.dirs.project), "--confirm")
        self.assertEqual(code, 0, out)
        self.assertIn("already", out)
        self.assertEqual(self.file.read_text(encoding="utf-8"), first)
        code, out = self.run_cmd("show")
        self.assertEqual(code, 0, out)
        self.assertIn("valid", out)
        self.assertIn(str(self.dirs.project), out)

    def test_a_relative_path_is_stored_as_given_and_resolved_from_the_session_directory(self):
        code, out = self.run_cmd("set", "--project", "../the project", "--confirm", cwd=str(self.dirs.project))
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(self.file.read_text(encoding="utf-8"))["project"], "../the project")
        self.assertEqual(resolve(self.dirs.session), ("ok", self.dirs.project))

    def test_set_replaces_an_existing_valid_link(self):
        second = self.dirs.project.parent / "second"
        second.mkdir()
        (second / "AGENTS.md").write_text("<!-- BEGIN:spec-guard-codex-convention -->\n", encoding="utf-8")
        self.run_cmd("set", "--project", str(self.dirs.project), "--confirm")
        code, out = self.run_cmd("set", "--project", str(second), "--confirm")
        self.assertEqual(code, 0, out)
        self.assertEqual(resolve(self.dirs.session), ("ok", second))

    def test_show_reports_why_a_link_is_broken(self):
        self.dirs.link({"version": 1, "project": str(self.dirs.project / "gone")})
        self.assertIn("missing", self.run_cmd("show")[1])
        self.dirs.link("{broken")
        self.assertIn("invalid", self.run_cmd("show")[1])
        bare = self.dirs.project.parent / "bare"
        bare.mkdir()
        self.dirs.link({"version": 1, "project": str(bare)})
        self.assertIn("not-enabled", self.run_cmd("show")[1])

    def test_unset(self):
        self.run_cmd("set", "--project", str(self.dirs.project), "--confirm")
        (self.file.parent / "keep.txt").write_text("x", encoding="utf-8")
        code, out = self.run_cmd("unset")
        self.assertEqual(code, 0, out)
        self.assertTrue(self.file.exists())
        code, out = self.run_cmd("unset", "--confirm")
        self.assertEqual(code, 0, out)
        self.assertFalse(self.file.exists())
        self.assertTrue((self.file.parent / "keep.txt").exists())
        code, out = self.run_cmd("unset", "--confirm")
        self.assertEqual((code, "no-link" in out), (2, True), out)

    def test_unset_leaves_an_empty_agent_directory(self):
        self.run_cmd("set", "--project", str(self.dirs.project), "--confirm")
        self.run_cmd("unset", "--confirm")
        self.assertTrue(self.file.parent.is_dir())

    def test_unset_removes_a_broken_link(self):
        self.dirs.link("{broken")
        code, out = self.run_cmd("unset", "--confirm")
        self.assertEqual(code, 0, out)
        self.assertFalse(self.file.exists())

    def test_refusals(self):
        bare = self.dirs.project.parent / "bare"
        bare.mkdir()
        for target, word in ((self.dirs.project / "gone", "target-missing"), (bare, "target-not-enabled"),
                             (self.dirs.session, "target-is-session")):
            code, out = self.run_cmd("set", "--project", str(target), "--confirm")
            self.assertEqual((code, word in out), (2, True), out)
            self.assertFalse(self.file.exists())
        self.dirs.link("{broken")
        code, out = self.run_cmd("set", "--project", str(self.dirs.project), "--confirm")
        self.assertEqual((code, "link-invalid" in out), (2, True), out)
        self.assertEqual(self.file.read_text(encoding="utf-8"), "{broken")
        self.file.unlink()
        (self.dirs.session / "AGENTS.md").write_text("<!-- BEGIN:spec-guard-codex-convention -->\n", encoding="utf-8")
        code, out = self.run_cmd("set", "--project", str(self.dirs.project), "--confirm")
        self.assertEqual((code, "session-enabled" in out), (2, True), out)
        self.assertFalse(self.file.exists())

    def test_resolve_prints_a_long_path_whole_and_strips_structure_characters(self):
        deep = self.dirs.project
        for part in ("a" * 60, "b" * 60, "c" * 60, "d" * 60, "has`tick"):
            deep = deep / part
        deep.mkdir(parents=True)
        self.dirs.link({"version": 1, "project": str(deep)})
        code, out = self.run_cmd("resolve")
        status, raw, shown, session = out.split("\n")[:4]
        self.assertEqual((code, status, raw), (0, "ok", str(deep)))
        self.assertGreater(len(str(deep)), 260)
        self.assertEqual(shown, str(deep).replace("`", ""))       # whole, minus what could forge Markdown
        self.assertEqual(session, str(self.dirs.session))

    def test_the_command_and_the_hook_agree_on_what_counts_as_enabled(self):
        from project_link import enabled
        hook = str(Path(__file__).with_name("phase-guard.sh"))
        cases = {
            "claude-block": ("CLAUDE.md", BLOCK),
            "codex-block": ("AGENTS.md", "  <!-- BEGIN:spec-guard-codex-convention -->  \n"),
            "state": (".agent/state.json", '{"activeModule": "alpha"}\n'),
            "prose-mention": ("CLAUDE.md", "本项目不用 `<!-- BEGIN:agent-skills-convention -->` 这个块。\n"),
            "other-state": (".agent/state.json", '{"session": "x"}\n'),
            "empty": (None, None),
        }
        for name, (relative, content) in cases.items():
            target = self.dirs.project.parent / name
            target.mkdir()
            if relative:
                (target / relative).parent.mkdir(parents=True, exist_ok=True)
                (target / relative).write_text(content, encoding="utf-8")
            env = {key: value for key, value in os.environ.items()
                   if key not in ("PLUGIN_ROOT", "SPEC_GUARD_HOST", "CLAUDE_CODE_SESSION_ATTENDED")}
            env["CLAUDE_PROJECT_DIR"] = str(target)
            done = subprocess.run(["/bin/bash", hook], stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                  timeout=30, env=env)
            self.assertEqual(enabled(target), bool(done.stdout.strip()), name)


if __name__ == "__main__":
    unittest.main()
