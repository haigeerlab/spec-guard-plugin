"""Reading the main-session context size from a host transcript, for the phase hint.

Fixtures are built here; nothing reads this machine's real transcripts or rollouts.
"""
import json
import tempfile
import unittest
from pathlib import Path

import session_context
from session_context import TAIL_LIMIT, context_tokens, transcript_path_from_hook_input


def claude_assistant(inp, read, write, sidechain=False):
    return {"type": "assistant", "isSidechain": sidechain, "message": {
        "role": "assistant", "usage": {"input_tokens": inp, "cache_read_input_tokens": read,
                                       "cache_creation_input_tokens": write, "output_tokens": 9}}}


def codex_token_count(inp):
    return {"type": "event_msg", "payload": {"type": "token_count", "info": {
        "last_token_usage": {"input_tokens": inp, "cached_input_tokens": inp - 1, "output_tokens": 5},
        "total_token_usage": {"input_tokens": inp * 10}, "model_context_window": 258400}}}


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


if __name__ == "__main__":
    unittest.main()
