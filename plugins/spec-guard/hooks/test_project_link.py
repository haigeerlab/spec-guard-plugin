"""The link from a session directory to the project it works on: parsing, validation and the command. No network."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from project_link import LINK_PATH, resolve, resolve_for

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


class ResolveForSession(unittest.TestCase):
    """link-per-session: a session's own entry first, then the directory-level link, else nothing."""

    def setUp(self):
        self.dirs = Dirs().__enter__()
        self.addCleanup(self.dirs.__exit__)
        self.other = self.dirs.project.parent / "other project"
        self.other.mkdir()

    def link2(self, sessions, project=None):
        data = {"version": 2, "sessions": sessions}
        if project is not None:
            data["project"] = project
        self.dirs.link(data)

    def test_a_sessions_own_entry_wins_over_the_directory_link(self):
        self.link2({"sess-a": str(self.other)}, project=str(self.dirs.project))
        self.assertEqual(resolve_for(self.dirs.session, ["sess-a"]), ("ok", self.other, "session"))
        self.assertEqual(resolve_for(self.dirs.session, ["nope", "sess-a"]), ("ok", self.other, "session"))

    def test_an_unregistered_session_falls_back_to_the_directory_link(self):
        self.link2({"sess-a": str(self.other)}, project=str(self.dirs.project))
        self.assertEqual(resolve_for(self.dirs.session, ["sess-b"]), ("ok", self.dirs.project, "directory"))
        self.assertEqual(resolve_for(self.dirs.session, []), ("ok", self.dirs.project, "directory"))
        self.assertEqual(resolve(self.dirs.session), ("ok", self.dirs.project))

    def test_only_other_sessions_entries_means_nothing_for_this_session(self):
        self.link2({"sess-a": str(self.other)})
        self.assertEqual(resolve_for(self.dirs.session, ["sess-b"]), ("none", None, None))
        self.assertEqual(resolve_for(self.dirs.session, []), ("none", None, None))
        self.assertEqual(resolve(self.dirs.session), ("none", None))

    def test_a_relative_session_path_and_a_missing_session_target(self):
        self.link2({"sess-a": "../other project", "sess-b": "../gone"})
        self.assertEqual(resolve_for(self.dirs.session, ["sess-a"]), ("ok", self.other, "session"))
        state, target, source = resolve_for(self.dirs.session, ["sess-b"])
        self.assertEqual((state, source), ("missing", "session"))

    def test_version_1_ignores_session_ids(self):
        self.dirs.link({"version": 1, "project": str(self.dirs.project)})
        self.assertEqual(resolve_for(self.dirs.session, ["sess-a"]), ("ok", self.dirs.project, "directory"))

    def test_invalid_version_2_forms(self):
        good = str(self.dirs.project)
        for content in ({"version": 2, "project": good},                       # sessions is required
                        {"version": 2, "sessions": {}},                        # nothing to point at
                        {"version": 2, "sessions": []},
                        {"version": 2, "sessions": {"a": good}, "extra": 1},
                        {"version": 2, "sessions": {"": good}},
                        {"version": 2, "sessions": {"has space": good}},
                        {"version": 2, "sessions": {"a/b": good}},
                        {"version": 2, "sessions": {"x" * 129: good}},
                        {"version": 2, "sessions": {"a": ""}},
                        {"version": 2, "sessions": {"a": 3}},
                        {"version": 2, "sessions": {"a": good}, "project": ""},
                        {"version": 1, "project": good, "sessions": {"a": good}},  # version 1 has no sessions
                        {"version": 3, "sessions": {"a": good}}):
            self.dirs.link(content)
            self.assertEqual(resolve_for(self.dirs.session, ["a"]), ("invalid", None, None), content)

    def test_an_empty_sessions_table_is_fine_beside_a_directory_link(self):
        self.link2({}, project=str(self.dirs.project))
        self.assertEqual(resolve_for(self.dirs.session, ["a"]), ("ok", self.dirs.project, "directory"))


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

    def test_set_and_show_say_the_link_covers_every_session_in_the_directory(self):
        note = "applies to every session that runs in this directory"
        code, out = self.run_cmd("show")
        self.assertNotIn(note, out)                      # no link: nothing to warn about
        code, out = self.run_cmd("set", "--project", str(self.dirs.project))
        self.assertEqual(code, 0, out)
        self.assertIn(note, out)
        self.assertIn("follows it", out)                 # D18: commands follow the link too
        self.assertIn("--session", out)                  # sharing sessions register their own entries
        self.assertNotIn("do not link", out)
        code, out = self.run_cmd("set", "--project", str(self.dirs.project), "--confirm")
        self.assertEqual(code, 0, out)
        self.assertIn(note, out)
        code, out = self.run_cmd("show")
        self.assertIn(note, out)
        self.dirs.link({"version": 1, "project": str(self.dirs.project / "gone")})
        self.assertNotIn(note, self.run_cmd("show")[1])  # a broken link reports why it is broken instead

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

    def second_project(self):
        second = self.dirs.project.parent / "second"
        second.mkdir()
        (second / "AGENTS.md").write_text("<!-- BEGIN:spec-guard-codex-convention -->\n", encoding="utf-8")
        return second

    def stored(self):
        return json.loads(self.file.read_text(encoding="utf-8"))

    def test_a_session_entry_is_previewed_then_written_without_a_directory_link(self):
        code, out = self.run_cmd("set", "--project", str(self.dirs.project), "--session", "sess-a")
        self.assertEqual(code, 0, out)
        self.assertFalse(self.file.exists())
        for phrase in ("session sess-a only", "CLAUDE_CODE_SESSION_ID", "CODEX_THREAD_ID", "preview only"):
            self.assertIn(phrase, out)
        self.assertNotIn("applies to every session", out)
        code, out = self.run_cmd("set", "--project", str(self.dirs.project), "--session", "sess-a", "--confirm")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.stored(), {"version": 2, "sessions": {"sess-a": str(self.dirs.project)}})
        self.assertEqual(resolve_for(self.dirs.session, ["sess-a"]), ("ok", self.dirs.project, "session"))
        self.assertEqual(resolve(self.dirs.session), ("none", None))
        code, out = self.run_cmd("set", "--project", str(self.dirs.project), "--session", "sess-a", "--confirm")
        self.assertEqual((code, "already" in out), (0, True), out)

    def test_session_entries_and_the_directory_link_live_side_by_side(self):
        second = self.second_project()
        self.run_cmd("set", "--project", str(self.dirs.project), "--session", "sess-a", "--confirm")
        self.run_cmd("set", "--project", str(second), "--session", "sess-b", "--confirm")
        code, out = self.run_cmd("set", "--project", str(second), "--confirm")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.stored(), {"version": 2, "project": str(second),
                                         "sessions": {"sess-a": str(self.dirs.project), "sess-b": str(second)}})
        code, out = self.run_cmd("show", "--session", "sess-a")
        self.assertEqual(code, 0, out)
        for phrase in ("sess-a", "sess-b", str(self.dirs.project), str(second), "this session uses its own entry"):
            self.assertIn(phrase, out)
        code, out = self.run_cmd("show", "--session", "sess-x")
        self.assertIn("this session has no entry and uses the directory-level link", out)
        code, out = self.run_cmd("show")
        self.assertIn("2 session entries", out)

    def test_unset_of_one_session_keeps_the_rest_and_shrinks_the_file(self):
        second = self.second_project()
        self.run_cmd("set", "--project", str(second), "--confirm")
        self.run_cmd("set", "--project", str(self.dirs.project), "--session", "sess-a", "--confirm")
        self.run_cmd("set", "--project", str(self.dirs.project), "--session", "sess-b", "--confirm")
        code, out = self.run_cmd("unset", "--session", "sess-a")
        self.assertEqual(code, 0, out)
        self.assertIn("sess-a", self.stored()["sessions"])              # preview only
        code, out = self.run_cmd("unset", "--session", "sess-a", "--confirm")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.stored(), {"version": 2, "project": str(second),
                                         "sessions": {"sess-b": str(self.dirs.project)}})
        self.run_cmd("unset", "--session", "sess-b", "--confirm")
        self.assertEqual(self.stored(), {"version": 1, "project": str(second)})   # back to the plain form
        code, out = self.run_cmd("unset", "--session", "sess-b", "--confirm")
        self.assertEqual((code, "no-session-link" in out), (2, True), out)

    def test_unsetting_the_last_session_entry_removes_the_file(self):
        self.run_cmd("set", "--project", str(self.dirs.project), "--session", "sess-a", "--confirm")
        code, out = self.run_cmd("unset", "--session", "sess-a", "--confirm")
        self.assertEqual(code, 0, out)
        self.assertFalse(self.file.exists())
        self.assertTrue(self.file.parent.is_dir())

    def test_unset_without_a_session_only_drops_the_directory_link(self):
        second = self.second_project()
        self.run_cmd("set", "--project", str(self.dirs.project), "--session", "sess-a", "--confirm")
        code, out = self.run_cmd("unset", "--confirm")
        self.assertEqual((code, "no-directory-link" in out), (2, True), out)
        self.run_cmd("set", "--project", str(second), "--confirm")
        code, out = self.run_cmd("unset", "--confirm")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.stored(), {"version": 2, "sessions": {"sess-a": str(self.dirs.project)}})

    def test_session_refusals(self):
        for bad in ("has space", "a/b", "x" * 129, ""):
            code, out = self.run_cmd("set", "--project", str(self.dirs.project), "--session", bad, "--confirm")
            self.assertEqual((code, "session-id-invalid" in out), (2, True), (bad, out))
            self.assertFalse(self.file.exists())
        bare = self.dirs.project.parent / "bare"
        bare.mkdir()
        code, out = self.run_cmd("set", "--project", str(bare), "--session", "sess-a", "--confirm")
        self.assertEqual((code, "target-not-enabled" in out), (2, True), out)
        self.dirs.link("{broken")
        code, out = self.run_cmd("unset", "--session", "sess-a", "--confirm")
        self.assertEqual((code, "link-invalid" in out), (2, True), out)
        self.assertEqual(self.file.read_text(encoding="utf-8"), "{broken")

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


class Follow(unittest.TestCase):
    """D18: every command resolves its project through `follow`, the same resolution the phase hook uses."""

    def setUp(self):
        self.dirs = Dirs().__enter__()
        self.addCleanup(self.dirs.__exit__)
        (self.dirs.project / "CLAUDE.md").write_text(BLOCK, encoding="utf-8")
        self.other = self.dirs.session.parent / "other project"
        self.other.mkdir()
        (self.other / "CLAUDE.md").write_text(BLOCK, encoding="utf-8")

    def follow(self, *extra):
        done = subprocess.run([sys.executable, "-B", SCRIPT, "follow", "--from", str(self.dirs.session), *extra],
                              capture_output=True, text=True, timeout=30)
        return done.returncode, done.stdout, done.stderr

    def test_no_link_file_operates_on_the_session_directory_quietly(self):
        self.assertEqual(self.follow(), (0, "%s\n" % self.dirs.session, ""))

    def test_directory_link_is_followed_and_said_so(self):
        self.dirs.link({"version": 1, "project": str(self.dirs.project)})
        code, out, err = self.follow("--session", "s-1")
        self.assertEqual((code, out), (0, "%s\n" % self.dirs.project))
        self.assertIn("本次操作的是被指向的项目 `%s`" % self.dirs.project, err)
        self.assertIn("目录级指向", err)
        self.assertIn(str(self.dirs.session / LINK_PATH), err)

    def test_this_sessions_entry_wins_over_the_directory_link(self):
        self.dirs.link({"version": 2, "project": str(self.dirs.project), "sessions": {"s-1": str(self.other)}})
        code, out, err = self.follow("--session", "s-1")
        self.assertEqual((code, out), (0, "%s\n" % self.other))
        self.assertIn("本会话的登记", err)
        code, out, _ = self.follow("--session", "s-2")
        self.assertEqual((code, out), (0, "%s\n" % self.dirs.project))
        code, out, _ = self.follow("--session", "")        # host variable unset: directory level only
        self.assertEqual((code, out), (0, "%s\n" % self.dirs.project))

    def test_only_other_sessions_entries_operate_on_the_session_directory(self):
        self.dirs.link({"version": 2, "sessions": {"s-9": str(self.other)}})
        self.assertEqual(self.follow("--session", "s-1"), (0, "%s\n" % self.dirs.session, ""))

    def test_broken_links_stop_instead_of_falling_back(self):
        plain = self.dirs.session.parent / "plain"
        plain.mkdir()
        cases = {"not-enabled": ({"version": 1, "project": str(plain)}, "没有启用 spec-guard"),
                 "missing": ({"version": 1, "project": str(plain / "gone")}, "不存在或不是目录"),
                 "invalid": ("{not json", "格式无效")}
        for name, (content, words) in cases.items():
            self.dirs.link(content)
            code, out, err = self.follow()
            self.assertEqual((code, out), (2, ""), name)
            self.assertIn(words, err, name)
            self.assertIn("link-project", err, name)
            self.assertNotIn("本次操作的是被指向的项目", err, name)

    def test_broken_session_entry_says_it_is_this_sessions_entry(self):
        self.dirs.link({"version": 2, "project": str(self.dirs.project),
                        "sessions": {"s-1": str(self.dirs.session.parent / "gone")}})
        code, out, err = self.follow("--session", "s-1")
        self.assertEqual((code, out), (2, ""))
        self.assertIn("本会话的登记", err)

    def test_enabled_session_directory_is_not_followed(self):
        (self.dirs.session / "CLAUDE.md").write_text(BLOCK, encoding="utf-8")
        self.dirs.link({"version": 1, "project": str(self.dirs.project)})
        self.assertEqual(self.follow(), (0, "%s\n" % self.dirs.session, ""))


PLUGIN = Path(__file__).resolve().parent.parent
SKILLS = ("spec-guard-ops", "ticket", "local-ticket-ledger-ops", "local-ticket-portability")


class EntryPointsFollow(unittest.TestCase):
    """D18: every entry point except link-project takes its project from `follow`, with its own host's session id."""

    def entries(self):
        files = [path for path in sorted((PLUGIN / "commands").glob("*.md")) if path.name != "link-project.md"]
        files += [PLUGIN / "skills" / name / "SKILL.md" for name in SKILLS]
        return files

    def test_every_entry_point_follows_with_its_hosts_session_id(self):
        for path in self.entries():
            text = path.read_text(encoding="utf-8")
            claude = path.parent.name == "commands"
            mine, other = (("CLAUDE_CODE_SESSION_ID", "CODEX_THREAD_ID") if claude
                           else ("CODEX_THREAD_ID", "CLAUDE_CODE_SESSION_ID"))
            self.assertIn('project_link.py" follow --from "$FROM" --session "${%s:-}"' % mine, text, path.name)
            self.assertNotIn('--session "${%s' % other, text, path.name)
            self.assertNotIn("--project .", text, path.name)
            self.assertNotIn('PROJECT="${CLAUDE_PROJECT_DIR:-', text, path.name)
            self.assertIn("本次操作的是被指向的项目", text, path.name)

    def test_link_project_says_the_other_commands_follow(self):
        text = (PLUGIN / "commands" / "link-project.md").read_text(encoding="utf-8")
        self.assertNotIn("不会自动跟随", text)
        self.assertIn("自动跟随", text)


if __name__ == "__main__":
    unittest.main()
