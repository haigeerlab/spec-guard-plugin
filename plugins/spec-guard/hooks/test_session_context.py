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
from unittest import mock
from pathlib import Path

import session_context
from session_context import TAIL_LIMIT, context_tokens, context_usage, location_line, transcript_path_from_hook_input


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

    def test_claude_sums_the_last_assistant_usage(self):
        path = self.write(claude_assistant(1, 2, 3), claude_assistant(10, 200000, 300))
        self.assertEqual(context_tokens(path), 200310)

    def test_claude_walks_back_past_user_and_usage_free_lines(self):
        path = self.write(claude_assistant(5, 100, 20),
                          {"type": "user", "message": {"role": "user", "content": "hi"}},
                          {"type": "assistant", "message": {"role": "assistant"}},
                          {"type": "summary"})
        self.assertEqual(context_tokens(path), 125)

    def test_claude_skips_sidechain_assistant_messages(self):
        path = self.write(claude_assistant(1, 300000, 0), claude_assistant(1, 5000, 0, sidechain=True))
        self.assertEqual(context_tokens(path), 300001)

    def test_zero_usage_records_are_not_a_reading(self):
        # Claude writes a "<synthetic>" assistant message with all-zero usage after an interruption.
        synthetic = claude_assistant(0, 0, 0)
        synthetic["message"]["model"] = "<synthetic>"
        path = self.write(claude_assistant(1, 250000, 0), synthetic, codex_token_count(0))
        self.assertEqual(context_tokens(path), 250001)

    def test_codex_takes_the_last_token_count_input(self):
        path = self.write(codex_token_count(1000), {"type": "response_item", "payload": {}},
                          codex_token_count(250000))
        self.assertEqual(context_tokens(path), 250000)

    def test_codex_skips_token_count_without_info(self):
        path = self.write(codex_token_count(7000),
                          {"type": "event_msg", "payload": {"type": "token_count", "info": None}})
        self.assertEqual(context_tokens(path), 7000)

    def test_bad_lines_are_skipped(self):
        path = self.write(claude_assistant(1, 2, 3), "{not json", "[1, 2]", '"text"')
        self.assertEqual(context_tokens(path), 6)

    def test_records_beyond_the_tail_limit_are_not_found(self):
        filler = json.dumps({"type": "user", "pad": "x" * 1000})
        lines = TAIL_LIMIT // len(filler) + 2
        path = self.write(claude_assistant(1, 2, 3), *([filler] * lines))
        self.assertIsNone(context_tokens(path))

    def test_records_inside_the_tail_limit_are_found_in_a_large_file(self):
        filler = json.dumps({"type": "user", "pad": "x" * 1000})
        path = self.write(*([filler] * (TAIL_LIMIT // len(filler) + 2)), claude_assistant(1, 2, 3))
        self.assertEqual(context_tokens(path), 6)

    def test_nothing_to_read(self):
        self.assertIsNone(context_tokens(self.write()))
        self.assertIsNone(context_tokens(str(Path(self.tmp.name) / "missing.jsonl")))
        self.assertIsNone(context_tokens(""))
        self.assertIsNone(context_tokens(None))
        self.assertIsNone(context_tokens(self.tmp.name))  # a directory

    def test_non_integer_usage_is_not_a_reading(self):
        bad = claude_assistant(1, 2, 3)
        bad["message"]["usage"]["input_tokens"] = "lots"
        self.assertIsNone(context_tokens(self.write(bad)))

    # context-after-compact: a compaction newer than the last reading sets the size.

    def test_claude_compaction_gives_the_post_compaction_size(self):
        path = self.write(claude_assistant(1, 601429, 0), claude_compact(13951),
                          {"type": "user", "isCompactSummary": True, "message": {"role": "user", "content": "s"}})
        self.assertEqual(context_usage(path), (13951, None))

    def test_a_reading_after_the_claude_compaction_wins(self):
        path = self.write(claude_assistant(1, 601429, 0), claude_compact(13951), claude_assistant(1, 93434, 0))
        self.assertEqual(context_tokens(path), 93435)

    def test_claude_compaction_without_a_usable_size_counts_as_compacted(self):
        for post in (None, "14k", -1, 1.5, True):
            with self.subTest(post=post):
                record = claude_compact(post)
                if post is None:
                    del record["compactMetadata"]["postTokens"]
                self.assertEqual(context_usage(self.write(claude_assistant(1, 601429, 0), record)), (0, None))

    def test_codex_compaction_counts_as_compacted(self):
        path = self.write(codex_token_count(223005), {"type": "compacted", "payload": {"message": "m"}},
                          codex_token_count(0))
        self.assertEqual(context_usage(path), (0, None))

    def test_a_reading_after_the_codex_compaction_wins(self):
        path = self.write(codex_token_count(223005), {"type": "compacted", "payload": {}}, codex_token_count(0),
                          codex_token_count(37599))
        self.assertEqual(context_usage(path), (37599, 258400))


    # context-hint-thresholds item 3 and 6: the window comes from the same record as the tokens.

    def test_codex_usage_carries_the_model_context_window(self):
        self.assertEqual(context_usage(self.write(codex_token_count(250000))), (250000, 258400))

    def test_codex_window_that_is_not_a_positive_integer_is_none(self):
        for window in (None, 0, -1, "258400", 25.5, True):
            with self.subTest(window=window):
                record = codex_token_count(9000)
                if window is None:
                    del record["payload"]["info"]["model_context_window"]
                else:
                    record["payload"]["info"]["model_context_window"] = window
                self.assertEqual(context_usage(self.write(record)), (9000, None))

    def test_claude_usage_has_no_window(self):
        self.assertEqual(context_usage(self.write(claude_assistant(10, 200000, 300))), (200310, None))

    def test_no_usage_is_none(self):
        self.assertIsNone(context_usage(self.write()))
        self.assertIsNone(context_usage(None))

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

    def test_prints_tokens_then_the_location_line(self):
        out = self.run_cli(json.dumps({"transcript_path": str(self.transcript)}))
        self.assertEqual(out.split("\n")[0], "250610")
        self.assertEqual(out.split("\n")[2], "")  # Claude records carry no window
        self.assertEqual(out.split("\n")[3], "")  # attended (unattended-run-hint)
        self.assertEqual(out.split("\n")[4], "")  # the input does not say Codex (codex-command-wording)
        self.assertEqual(out.count("\n"), 5)

    def test_prints_codex_as_the_fifth_line_for_a_turn_id(self):
        out = self.run_cli(json.dumps({"transcript_path": str(self.transcript), "turn_id": "t1"}))
        self.assertEqual(out.split("\n")[4], "codex")
        self.assertEqual(out.split("\n")[0], "250610")  # the other facts are unchanged

    def test_prints_codex_as_the_fifth_line_for_a_session_meta_rollout(self):
        self.transcript.write_text(json.dumps({"type": "session_meta", "payload": {"source": "vscode"}}) + "\n"
                                   + json.dumps(codex_token_count(120000)) + "\n")
        out = self.run_cli(json.dumps({"transcript_path": str(self.transcript)}))
        self.assertEqual(out.split("\n")[4], "codex")

    def test_unusable_input_does_not_say_codex(self):
        for text in ("not json", "[]", json.dumps({"transcript_path": 3})):
            self.assertEqual(self.run_cli(text).split("\n")[4], "", text)

    def test_prints_unattended_as_the_fourth_line(self):
        out = self.run_cli(json.dumps({"transcript_path": str(self.transcript)}), attended="0")
        self.assertEqual(out.split("\n")[3], "unattended")
        self.assertEqual(out.split("\n")[0], "250610")  # the other facts are unchanged

    def test_prints_the_codex_window_as_the_third_line(self):
        self.transcript.write_text(json.dumps(codex_token_count(120000)) + "\n")
        out = self.run_cli(json.dumps({"transcript_path": str(self.transcript)}))
        self.assertEqual(out.split("\n")[0], "120000")
        self.assertEqual(out.split("\n")[2], "258400")

    def test_prints_zero_right_after_a_codex_compaction(self):
        self.transcript.write_text("\n".join(json.dumps(r) for r in (
            codex_token_count(223005), {"type": "compacted", "payload": {}}, codex_token_count(0))) + "\n")
        out = self.run_cli(json.dumps({"transcript_path": str(self.transcript)}))
        self.assertEqual(out.split("\n")[0], "0")
        self.assertEqual(out.split("\n")[2], "")

    def test_unusable_input_prints_two_empty_lines(self):
        for text in ("", "not json", json.dumps({"transcript_path": "/no/such/file"})):
            with self.subTest(text=text):
                self.assertEqual(self.run_cli(text).split("\n")[0], "")

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
        self.assertEqual(out.split(b"\n")[0], b"")

    def test_input_over_the_limit_is_not_read(self):
        big = json.dumps({"transcript_path": str(self.transcript), "pad": "x" * session_context.INPUT_LIMIT})
        self.assertEqual(self.run_cli(big).split("\n")[0], "")


def git(*args, cwd):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false",
                    *args], cwd=cwd, check=True, capture_output=True)


TELL = "State this location to the user whenever you ask them to review or confirm."


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

    def test_command_line_prints_the_location_second(self):
        self.commit()
        done = subprocess.run([sys.executable, "-B", SCRIPT, str(self.repo)], input="", capture_output=True,
                              text=True, timeout=10)
        self.assertEqual(done.stdout.split("\n")[1], location_line(self.repo))



class Unattended(unittest.TestCase):
    """unattended-run-hint: only an explicit host signal means nobody is there."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "rollout.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, first_line, expected, attended=None):
        if first_line is not None:
            self.path.write_text(first_line + "\n" + json.dumps(codex_token_count(1)) + "\n")
        environment = {} if attended is None else {"CLAUDE_CODE_SESSION_ATTENDED": attended}
        with mock.patch.dict(os.environ, environment, clear=False):
            if attended is None:
                os.environ.pop("CLAUDE_CODE_SESSION_ATTENDED", None)
            self.assertIs(session_context.unattended(str(self.path)), expected)

    def test_claude_unattended_variable(self):
        self.check(None, True, attended="0")
        self.check(None, False, attended="1")
        self.check(None, False, attended="")

    def test_codex_exec_first_record(self):
        meta = '{"type":"session_meta","payload":{"originator":"codex_exec","source":"exec"}}'
        self.check(meta, True)
        self.check(meta.replace('"exec"}', '"vscode"}'), False)
        self.check('{"type":"session_meta","payload":{"source":{"subagent":"x"}}}', False)
        self.check('{"type":"event_msg","payload":{"source":"exec"}}', False)
        self.check("not json", False)

    def test_long_first_record_still_counts(self):
        # unattended-long-first-record: Codex writes its whole base instructions into session_meta (19-24 KB on
        # 2026-10-08); a record past the old 64 KB read must still be recognised.
        meta = json.dumps({"type": "session_meta",
                           "payload": {"source": "exec", "base_instructions": {"text": "x" * 100_000}}})
        self.assertGreater(len(meta), 65536)
        self.check(meta, True)

    def test_first_record_over_the_limit_counts_as_attended(self):
        # A complete JSON object padded past 1 MB: its first 1 MB parses on its own, so only the
        # "no line end within the limit" rule can keep it attended.
        meta = '{"type":"session_meta","payload":{"source":"exec"}}' + " " * (1 << 20)
        self.check(meta, False)

    def test_missing_or_absent_transcript_is_attended(self):
        self.check(None, False)
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_CODE_SESSION_ATTENDED", None)
            self.assertFalse(session_context.unattended(None))


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
