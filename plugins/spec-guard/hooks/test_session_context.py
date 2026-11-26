"""Reading the main-session context size from a host transcript, for the phase hint.

Fixtures are built here; nothing reads this machine's real transcripts or rollouts.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import session_context
from session_context import TAIL_LIMIT, location_line, transcript_path_from_hook_input


def claude_assistant(inp, read, write, sidechain=False):
    return {"type": "assistant", "isSidechain": sidechain, "message": {
        "role": "assistant", "usage": {"input_tokens": inp, "cache_read_input_tokens": read,
                                       "cache_creation_input_tokens": write, "output_tokens": 9}}}


def codex_token_count(inp):
    return {"type": "event_msg", "payload": {"type": "token_count", "info": {
        "last_token_usage": {"input_tokens": inp, "cached_input_tokens": inp - 1, "output_tokens": 5},
        "total_token_usage": {"input_tokens": inp * 10}, "model_context_window": 258400}}}


def claude_compact(post):
    return {"type": "system", "subtype": "compact_boundary",
            "compactMetadata": {"trigger": "manual", "preTokens": 601658, "postTokens": post}}


class Transcript(unittest.TestCase):
    """Only the tail reader and the compaction predicate remain: the size itself is no longer read."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "session.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, *records, raw=""):
        with self.path.open("w") as handle:
            handle.write(raw)
            for record in records:
                handle.write((record if isinstance(record, str) else json.dumps(record)) + "\n")
        return str(self.path)

    def test_tail_lines_of_a_small_file_are_all_its_lines(self):
        lines = session_context.tail_lines(self.write(claude_assistant(1, 2, 3), {"type": "user"}))
        self.assertEqual([json.loads(line)["type"] for line in lines if line], ["assistant", "user"])

    def test_tail_lines_drop_the_line_cut_by_the_window(self):
        filler = json.dumps({"type": "user", "pad": "x" * 1000})
        lines = session_context.tail_lines(self.write(claude_assistant(1, 2, 3),
                                                      *([filler] * (TAIL_LIMIT // len(filler) + 2))))
        self.assertTrue(all(not line or json.loads(line)["type"] == "user" for line in lines))

    def test_nothing_to_read(self):
        self.assertEqual(session_context.tail_lines(self.write()), [b""])
        self.assertIsNone(session_context.tail_lines(str(Path(self.tmp.name) / "missing.jsonl")))
        self.assertIsNone(session_context.tail_lines(""))
        self.assertIsNone(session_context.tail_lines(None))
        self.assertIsNone(session_context.tail_lines(self.tmp.name))  # a directory

    # context-after-compact: a compaction record is recognised without reading any size from it.

    def test_claude_compaction_is_a_compaction_whatever_its_size_field_holds(self):
        for post in (13951, None, "14k", -1, 1.5, True):
            with self.subTest(post=post):
                record = claude_compact(post)
                if post is None:
                    del record["compactMetadata"]["postTokens"]
                self.assertTrue(session_context._is_compaction(record))

    def test_codex_compaction_is_a_compaction(self):
        self.assertTrue(session_context._is_compaction({"type": "compacted", "payload": {"message": "m"}}))

    def test_other_records_are_not_compactions(self):
        for record in (claude_assistant(1, 2, 3), codex_token_count(5), {"type": "system", "subtype": "other"},
                       {"type": "user"}, "text", None, [1]):
            with self.subTest(record=record):
                self.assertFalse(session_context._is_compaction(record))

    def test_last_state_is_none_when_a_compaction_is_newer_than_the_injection(self):
        injected = {"type": "attachment", "attachment": {"type": "hook_additional_context", "content": [
            "## spec-guard local workflow\n<!-- spec-guard-state: 0123abcd -->"]}}
        lines = session_context.tail_lines(self.write(injected))
        self.assertEqual(session_context.last_state(lines), "0123abcd")
        lines = session_context.tail_lines(self.write(injected, claude_compact(1)))
        self.assertIsNone(session_context.last_state(lines))
        lines = session_context.tail_lines(self.write(injected, {"type": "compacted", "payload": {}}))
        self.assertIsNone(session_context.last_state(lines))


class HookInput(unittest.TestCase):
    def test_reads_transcript_path(self):
        self.assertEqual(transcript_path_from_hook_input(
            json.dumps({"session_id": "s", "transcript_path": "/x/y.jsonl", "prompt": "p"})), "/x/y.jsonl")

    def test_unusable_input(self):
        for text in ("", "not json", "[]", json.dumps({"prompt": "p"}),
                     json.dumps({"transcript_path": None}), json.dumps({"transcript_path": ""}),
                     json.dumps({"transcript_path": 3})):
            with self.subTest(text=text):
                self.assertIsNone(transcript_path_from_hook_input(text))


SCRIPT = str(Path(__file__).resolve().parent / "session_context.py")


class CommandLine(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.transcript = Path(self.tmp.name) / "t.jsonl"
        self.transcript.write_text(json.dumps(claude_assistant(10, 250000, 600)) + "\n")

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, stdin_text, attended=None):
        env = {key: value for key, value in os.environ.items() if key != "CLAUDE_CODE_SESSION_ATTENDED"}
        if attended is not None:
            env["CLAUDE_CODE_SESSION_ATTENDED"] = attended
        done = subprocess.run([sys.executable, "-B", SCRIPT, self.tmp.name], input=stdin_text,
                              capture_output=True, text=True, timeout=10, env=env)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout

    def test_prints_exactly_three_lines_location_host_state_code(self):
        repo = Path(self.tmp.name, "repo")
        repo.mkdir()
        git("init", "-q", "-b", "main", cwd=repo)
        stdin_text = json.dumps({"transcript_path": str(self.transcript)})
        done = subprocess.run([sys.executable, "-B", SCRIPT, str(repo)], input=stdin_text, capture_output=True,
                              text=True, timeout=10)
        self.assertEqual(done.returncode, 0, done.stderr)
        lines = done.stdout.split("\n")
        self.assertEqual(lines[0], location_line(repo))
        self.assertEqual(lines[1], "")  # Claude: the input does not say Codex
        self.assertEqual(lines[2], "")  # no spec-guard injection recorded yet
        self.assertEqual(done.stdout.count("\n"), 3)

    def test_prints_the_state_code_as_the_third_line(self):
        self.transcript.write_text(json.dumps({"type": "attachment", "attachment": {
            "type": "hook_additional_context", "content": [
                "## spec-guard local workflow\n<!-- spec-guard-state: 0123abcd -->"]}}) + "\n"
            + json.dumps(claude_assistant(10, 250000, 600)) + "\n")
        out = self.run_cli(json.dumps({"transcript_path": str(self.transcript)}))
        self.assertEqual(out.split("\n")[2], "0123abcd")
        self.assertEqual(out.count("\n"), 3)

    def test_prints_codex_as_the_second_line_for_a_turn_id(self):
        out = self.run_cli(json.dumps({"transcript_path": str(self.transcript), "turn_id": "t1"}))
        self.assertEqual(out.split("\n")[1], "codex")
        self.assertEqual(out.count("\n"), 3)

    def test_prints_codex_as_the_second_line_for_a_session_meta_rollout(self):
        self.transcript.write_text(json.dumps({"type": "session_meta", "payload": {"source": "vscode"}}) + "\n"
                                   + json.dumps(codex_token_count(120000)) + "\n")
        out = self.run_cli(json.dumps({"transcript_path": str(self.transcript)}))
        self.assertEqual(out.split("\n")[1], "codex")

    def test_unusable_input_does_not_say_codex(self):
        for text in ("not json", "[]", json.dumps({"transcript_path": 3})):
            self.assertEqual(self.run_cli(text).split("\n")[1], "", text)

    def test_attended_variable_and_high_readings_change_nothing(self):
        stdin_text = json.dumps({"transcript_path": str(self.transcript)})
        self.assertEqual(self.run_cli(stdin_text, attended="0"), self.run_cli(stdin_text, attended="1"))
        self.transcript.write_text(json.dumps(claude_assistant(10, 900000, 600)) + "\n")
        self.assertEqual(self.run_cli(stdin_text, attended="0"), self.run_cli(stdin_text))

    def test_unusable_input_prints_empty_host_and_state_lines(self):
        for text in ("", "not json", json.dumps({"transcript_path": "/no/such/file"})):
            with self.subTest(text=text):
                lines = self.run_cli(text).split("\n")
                self.assertEqual(lines[1:3], ["", ""])

    def test_an_open_stdin_does_not_hang(self):
        started = time.monotonic()
        proc = subprocess.Popen([sys.executable, "-B", SCRIPT, self.tmp.name], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            proc.stdin.write(b'{"transcript_path": ')
            proc.stdin.flush()
            out = proc.stdout.read()  # returns once the script exits; stdin stays open
            proc.wait(timeout=5)
        finally:
            proc.stdin.close()
            proc.kill()
        self.assertLess(time.monotonic() - started, 3)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(out.split(b"\n")[1:3], [b"", b""])

    def test_input_over_the_limit_is_not_read(self):
        big = json.dumps({"transcript_path": str(self.transcript), "pad": "x" * session_context.INPUT_LIMIT})
        self.assertEqual(self.run_cli(big).split("\n")[1:3], ["", ""])


def git(*args, cwd):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false",
                    *args], cwd=cwd, check=True, capture_output=True)


TELL = "State this location to the user whenever you ask them to review or confirm."
TELL_ZH = "请用户审阅或确认时，向用户说明这个位置。"


class Location(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name, "repo")
        self.repo.mkdir()
        git("init", "-q", "-b", "main", cwd=self.repo)
        self.top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=self.repo,
                                  capture_output=True, text=True).stdout.strip()

    def tearDown(self):
        self.tmp.cleanup()

    def commit(self):
        (self.repo / "f").write_text("x")
        git("add", "f", cwd=self.repo)
        git("commit", "-q", "-m", "c", cwd=self.repo)

    def test_branch_and_worktree(self):
        self.commit()
        self.assertEqual(location_line(self.repo), "Location: branch `main` · worktree `%s`. %s" % (self.top, TELL))

    def test_unborn_branch_still_has_a_name(self):
        self.assertEqual(location_line(self.repo), "Location: branch `main` · worktree `%s`. %s" % (self.top, TELL))

    def test_subdirectory_reports_the_worktree_root(self):
        self.commit()
        (self.repo / "sub").mkdir()
        self.assertIn("worktree `%s`." % self.top, location_line(self.repo / "sub"))

    def test_detached_head(self):
        self.commit()
        git("checkout", "-q", "--detach", cwd=self.repo)
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=self.repo,
                             capture_output=True, text=True).stdout.strip()
        self.assertEqual(location_line(self.repo), "Location: detached at `%s` · worktree `%s`. %s" % (sha, self.top, TELL))

    def test_linked_worktree_reports_its_own_root(self):
        self.commit()
        linked = Path(self.tmp.name, "linked")
        git("worktree", "add", "-q", "-b", "side", str(linked), cwd=self.repo)
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=linked,
                             capture_output=True, text=True).stdout.strip()
        self.assertEqual(location_line(linked), "Location: branch `side` · worktree `%s`. %s" % (top, TELL))

    def test_not_a_repository(self):
        plain = Path(self.tmp.name, "plain")
        plain.mkdir()
        self.assertIsNone(location_line(plain))

    def test_branch_name_cannot_forge_structure(self):
        self.commit()
        git("checkout", "-q", "-b", "x`y", cwd=self.repo)
        line = location_line(self.repo)
        self.assertIn("branch `xy`", line)
        self.assertEqual(line.count("`"), 4)

    def test_command_line_prints_the_location_first(self):
        self.commit()
        done = subprocess.run([sys.executable, "-B", SCRIPT, str(self.repo)], input="", capture_output=True,
                              text=True, timeout=10)
        self.assertEqual(done.stdout.split("\n")[0], location_line(self.repo))

    # hint-language-follow: zh-CN gives the Chinese line; any other value keeps the English one.
    def test_chinese_branch(self):
        self.commit()
        self.assertEqual(location_line(self.repo, "zh-CN"),
                         "位置: 分支 `main` · worktree `%s`。%s" % (self.top, TELL_ZH))

    def test_chinese_detached_head(self):
        self.commit()
        git("checkout", "-q", "--detach", cwd=self.repo)
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=self.repo,
                             capture_output=True, text=True).stdout.strip()
        self.assertEqual(location_line(self.repo, "zh-CN"),
                         "位置: 分离于 `%s` · worktree `%s`。%s" % (sha, self.top, TELL_ZH))

    def test_other_languages_keep_english(self):
        self.commit()
        for lang in ("en", "zh-TW", ""):
            self.assertEqual(location_line(self.repo, lang), location_line(self.repo))

    def test_command_line_language(self):
        self.commit()
        done = subprocess.run([sys.executable, "-B", SCRIPT, str(self.repo), "--lang", "zh-CN"], input="",
                              capture_output=True, text=True, timeout=10)
        self.assertEqual(done.stdout.split("\n")[0], location_line(self.repo, "zh-CN"))



class RootFromHookInput(unittest.TestCase):
    """原 session-handoff 第 12 条（该模块已退役，此规则保留）：项目根以 hook 输入的 cwd 所在 git 仓库为准，取不到才用调用方的默认根。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name).resolve()
        self.main = base / "main"
        (self.main / "src").mkdir(parents=True)
        git("init", "-q", "-b", "main", cwd=self.main)
        (self.main / "f").write_text("x\n")
        git("add", "f", cwd=self.main)
        git("commit", "-q", "-m", "init", cwd=self.main)
        self.linked = base / "linked"
        git("worktree", "add", "-q", "-b", "feat", str(self.linked), cwd=self.main)
        self.plain = base / "plain"
        self.plain.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def root(self, payload, fallback=None):
        text = payload if isinstance(payload, str) else json.dumps(payload)
        return session_context.root_from_hook_input(text, str(fallback or self.main))

    def test_cwd_in_a_linked_worktree_wins_over_the_fallback(self):
        self.assertEqual(self.root({"cwd": str(self.linked)}), str(self.linked))

    def test_cwd_in_a_subdirectory_resolves_to_the_repository_root(self):
        self.assertEqual(self.root({"cwd": str(self.main / "src")}), str(self.main))

    def test_unusable_cwd_keeps_the_fallback(self):
        for payload in ("", "not json", "null", {}, {"cwd": None}, {"cwd": ""}, {"cwd": 3},
                        {"cwd": str(self.plain)}, {"cwd": str(self.main / "missing")}):
            with self.subTest(payload=payload):
                self.assertEqual(self.root(payload), str(self.main))

    def test_command_line_prints_the_root_then_the_input_on_one_line(self):
        payload = {"cwd": str(self.linked), "prompt": "a\nb", "transcript_path": "/t"}
        done = subprocess.run([sys.executable, "-B", SCRIPT, "--resolve-root", str(self.main)],
                              input=json.dumps(payload), capture_output=True, text=True, timeout=10)
        self.assertEqual(done.returncode, 0, done.stderr)
        lines = done.stdout.split("\n")
        self.assertEqual(lines[0], str(self.linked))
        self.assertEqual(json.loads(lines[1]), payload)
        self.assertEqual(done.stdout.count("\n"), 2)

    def test_command_line_without_usable_input_prints_the_fallback_and_an_empty_line(self):
        for text in ("", "not json", "[1]"):
            with self.subTest(text=text):
                done = subprocess.run([sys.executable, "-B", SCRIPT, "--resolve-root", str(self.main)],
                                      input=text, capture_output=True, text=True, timeout=10)
                self.assertEqual(done.stdout, "%s\n\n" % self.main)


if __name__ == "__main__":
    unittest.main()
