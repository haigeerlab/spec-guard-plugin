"""self-observation-report regressions. Every fixture is synthetic: fake Claude and Codex
session directories under a temporary home. Nothing here reads the machine's real sessions."""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import self_report as sr  # noqa: E402

SINCE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def segment(stage, suggestion="Suggested next step: run `/spec-guard:verify-artifacts`.", title="## spec-guard local workflow"):
    lines = [title, ""]
    if stage is not None:
        lines.append("当前阶段: **%s**" % stage)
    lines += ["", "- Capability map: present", ""]
    if suggestion:
        lines.append(suggestion)
    return "\n".join(lines)


def claude_attachment(when, cwd, session, contents):
    return {"type": "attachment", "timestamp": when, "cwd": cwd, "sessionId": session,
            "attachment": {"type": "hook_additional_context", "content": contents}}


def codex_meta(cwd, thread, source="cli"):
    return {"timestamp": "2026-10-01T00:00:00Z", "type": "session_meta",
            "payload": {"id": thread, "cwd": cwd, "source": source}}


def codex_developer(when, text):
    return {"timestamp": when, "type": "response_item",
            "payload": {"type": "message", "role": "developer", "content": [{"type": "input_text", "text": text}]}}


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sg-self-report-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.claude = self.root / "claude"
        self.codex = self.root / "codex"
        self.project = self.root / "work" / "secret-project"
        self.project.mkdir(parents=True)
        self.real = os.path.realpath(str(self.project))

    def write_jsonl(self, path, rows):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write((row if isinstance(row, str) else json.dumps(row, ensure_ascii=False)) + "\n")

    def claude_session(self, name, rows):
        self.write_jsonl(self.claude / "projects" / "-encoded" / name, rows)

    def codex_rollout(self, name, rows):
        self.write_jsonl(self.codex / "sessions" / "2026" / "10" / "01" / name, rows)


class ClaudeReadTests(Fixture):
    def test_only_spec_guard_segments_are_events(self):
        self.claude_session("s1.jsonl", [
            claude_attachment("2026-10-01T10:00:00.123Z", self.real, "sess-1",
                              ["agent-skills loaded. other hook", segment("MAP_INVALID")]),
        ])
        events, unparsed = sr.read_claude(self.claude, SINCE)
        self.assertEqual(unparsed, 0)
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event["host"], "claude")
        self.assertEqual(event["stage"], "MAP_INVALID")
        self.assertEqual(event["suggestion"], "Suggested next step: run `/spec-guard:verify-artifacts`.")
        self.assertEqual(event["project"], self.real)
        self.assertEqual(event["session"], "sess-1")
        self.assertEqual(event["line"], 1)

    def test_line_numbers_count_every_row(self):
        self.claude_session("s1.jsonl", [
            {"type": "user", "timestamp": "2026-10-01T09:00:00Z"},
            "not json",
            claude_attachment("2026-10-01T10:00:00Z", self.real, "sess-1", [segment("DONE")]),
        ])
        events, _ = sr.read_claude(self.claude, SINCE)
        self.assertEqual(events[0]["line"], 3)

    def test_subagent_transcripts_are_not_read(self):
        sub = self.claude / "projects" / "-encoded" / "sess-1" / "subagents" / "agent-a.jsonl"
        self.write_jsonl(sub, [claude_attachment("2026-10-01T10:00:00Z", self.real, "sess-1", [segment("DONE")])])
        events, _ = sr.read_claude(self.claude, SINCE)
        self.assertEqual(events, [])

    def test_legacy_format_stage_is_taken_whole(self):
        legacy = segment("IDLE (已归档)", "建议下一步: 当前没有活跃 initiative；/spec 开始新的一轮",
                         title="## agent-skills 链路状态（自动探测，非用户输入）")
        self.claude_session("s1.jsonl", [claude_attachment("2026-10-01T10:00:00Z", self.real, "s", [legacy])])
        events, _ = sr.read_claude(self.claude, SINCE)
        self.assertEqual(events[0]["stage"], "IDLE (已归档)")
        self.assertEqual(events[0]["suggestion"], "建议下一步: 当前没有活跃 initiative；/spec 开始新的一轮")

    def test_missing_stage_line_is_question_mark(self):
        self.claude_session("s1.jsonl", [claude_attachment("2026-10-01T10:00:00Z", self.real, "s",
                                                           [segment(None, suggestion="")])])
        events, _ = sr.read_claude(self.claude, SINCE)
        self.assertEqual((events[0]["stage"], events[0]["suggestion"]), ("?", ""))

    def test_since_filters_and_bad_timestamps_are_counted(self):
        self.claude_session("s1.jsonl", [
            claude_attachment("2025-12-31T23:59:59Z", self.real, "s", [segment("DONE")]),
            claude_attachment("not-a-time", self.real, "s", [segment("DONE")]),
            claude_attachment("2026-10-01T10:00:00Z", self.real, "s", [segment("BUILDING")]),
        ])
        events, unparsed = sr.read_claude(self.claude, SINCE)
        self.assertEqual([e["stage"] for e in events], ["BUILDING"])
        self.assertEqual(unparsed, 1)

    def test_missing_home_is_empty_not_error(self):
        self.assertEqual(sr.read_claude(self.root / "nowhere", SINCE), ([], 0))


class CodexReadTests(Fixture):
    def test_developer_segment_is_event(self):
        self.codex_rollout("rollout-a.jsonl", [
            codex_meta(self.real, "thread-1"),
            codex_developer("2026-10-01T10:00:00Z", segment("BUILDING")),
            codex_developer("2026-10-01T10:01:00Z", "unrelated developer text"),
        ])
        events, unparsed = sr.read_codex(self.codex, SINCE)
        self.assertEqual(unparsed, 0)
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual((event["host"], event["stage"], event["session"], event["line"]),
                         ("codex", "BUILDING", "thread-1", 2))
        self.assertEqual(event["project"], self.real)

    def test_subagent_threads_are_not_read(self):
        self.codex_rollout("rollout-sub.jsonl", [
            codex_meta(self.real, "thread-2", source={"subagent": {"thread_spawn": {"parent_thread_id": "thread-1"}}}),
            codex_developer("2026-10-01T10:00:00Z", segment("BUILDING")),
        ])
        self.assertEqual(sr.read_codex(self.codex, SINCE), ([], 0))

    def test_user_messages_are_not_events(self):
        self.codex_rollout("rollout-a.jsonl", [
            codex_meta(self.real, "thread-1"),
            {"timestamp": "2026-10-01T10:00:00Z", "type": "response_item",
             "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": segment("DONE")}]}},
        ])
        self.assertEqual(sr.read_codex(self.codex, SINCE), ([], 0))


if __name__ == "__main__":
    unittest.main(verbosity=1)
