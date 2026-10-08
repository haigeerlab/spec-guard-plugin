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


PYTHON3_TEXTS = (
    "spec-guard: 本项目已启用约定，但 python3 不可用，本轮没有阶段注入。这不是「未启用」；安装 python3 后恢复。",
    "spec-guard: 本项目已启用约定，但 python3 无法运行，本轮没有阶段注入。这不是「未启用」；修复 python3 后恢复。",
)


class Python3FailureReadTests(Fixture):
    def test_both_python3_failure_texts_are_events(self):
        self.claude_session("s1.jsonl", [claude_attachment("2026-10-01T10:00:00Z", self.real, "s", list(PYTHON3_TEXTS))])
        events, _ = sr.read_claude(self.claude, SINCE)
        self.assertEqual([e["stage"] for e in events], ["python3 故障", "python3 故障"])

    def test_other_spec_guard_prefixed_text_is_not_an_event(self):
        self.claude_session("s1.jsonl", [claude_attachment("2026-10-01T10:00:00Z", self.real, "s",
                                                           ["spec-guard: something else entirely"])])
        self.assertEqual(sr.read_claude(self.claude, SINCE), ([], 0))


def event(when, stage, suggestion="Suggested next step: continue `/build` on `alpha`: 3 unchecked item(s).",
          project="/p/one", session="session-aaaaaa", line=1, host="claude"):
    return {"time": sr.parse_iso(when), "host": host, "project": project, "session": session,
            "line": line, "stage": stage, "suggestion": suggestion}


def repeated(n, stage="DONE", days=2, project="/p/one", suggestion=None):
    """n events spread over `days` calendar days, one minute apart within each day."""
    out = []
    for i in range(n):
        day = 1 + (i * days) // n
        kwargs = {"project": project, "line": i + 1}
        if suggestion is not None:
            kwargs["suggestion"] = suggestion
        out.append(event("2026-10-%02dT10:%02d:%02dZ" % (day, (i // 60) % 60, i % 60), stage, **kwargs))
    return out


def by_signal(found, signal):
    return [f for f in found if f["signal"] == signal]


class S1Tests(unittest.TestCase):
    def test_twenty_one_unchanged_over_two_days_is_one_finding(self):
        found = sr.findings(repeated(21))
        s1 = by_signal(found, "S1")
        self.assertEqual(len(s1), 1)
        self.assertEqual((s1[0]["stage"], s1[0]["count"]), ("DONE", 21))

    def test_nineteen_is_below_threshold(self):
        self.assertEqual(by_signal(sr.findings(repeated(19)), "S1"), [])

    def test_threshold_is_configurable(self):
        self.assertEqual(len(by_signal(sr.findings(repeated(19), min_repeat=10), "S1")), 1)

    def test_all_on_one_day_is_not_a_finding(self):
        self.assertEqual(by_signal(sr.findings(repeated(21, days=1)), "S1"), [])

    def test_suggestion_change_resets_the_run(self):
        events = repeated(12) + [dict(e, time=e["time"].replace(day=e["time"].day + 2),
                                      suggestion="Suggested next step: something else.")
                                 for e in repeated(12)]
        self.assertEqual(by_signal(sr.findings(events), "S1"), [])

    def test_events_are_ordered_by_time_before_counting(self):
        events = repeated(21)
        events.reverse()
        self.assertEqual(len(by_signal(sr.findings(events), "S1")), 1)

    def test_s2_events_do_not_count_toward_s1(self):
        self.assertEqual(by_signal(sr.findings(repeated(25, stage="MAP_INVALID")), "S1"), [])


class S2Tests(unittest.TestCase):
    def test_single_map_invalid_is_reported(self):
        s2 = by_signal(sr.findings([event("2026-10-01T10:00:00Z", "MAP_INVALID")]), "S2")
        self.assertEqual((len(s2), s2[0]["count"]), (1, 1))

    def test_every_diagnostic_stage_is_s2(self):
        stages = ["UNKNOWN", "MAP_INVALID", "?", "python3 故障"]
        found = sr.findings([event("2026-10-01T10:00:00Z", s, suggestion="") for s in stages])
        self.assertEqual(sorted(f["stage"] for f in by_signal(found, "S2")), sorted(stages))

    def test_normal_stage_once_is_nothing(self):
        self.assertEqual(sr.findings([event("2026-10-01T10:00:00Z", "BUILDING")]), [])


class FingerprintTests(unittest.TestCase):
    def test_same_problem_in_two_projects_merges(self):
        found = sr.findings(repeated(21, project="/p/one") + repeated(21, project="/p/two"))
        s1 = by_signal(found, "S1")
        self.assertEqual(len(s1), 1)
        self.assertEqual((s1[0]["count"], len(s1[0]["projects"])), (42, 2))

    def test_module_ids_and_numbers_normalise_to_one_fingerprint(self):
        a = event("2026-10-01T10:00:00Z", "MAP_INVALID", suggestion="Fix `alpha`: 3 left.")
        b = event("2026-10-02T10:00:00Z", "MAP_INVALID", suggestion="Fix `beta`: 7 left.", project="/p/two")
        s2 = by_signal(sr.findings([a, b]), "S2")
        self.assertEqual(len(s2), 1)
        self.assertEqual(s2[0]["suggestion"], "Fix <id>: <n> left.")

    def test_fingerprint_is_stable_and_shaped(self):
        first = sr.findings(repeated(21))[0]["fingerprint"]
        self.assertEqual(first, sr.findings(repeated(21))[0]["fingerprint"])
        self.assertRegex(first, r"^F-[0-9a-f]{4}$")

    def test_examples_are_capped_and_findings_sorted_by_count(self):
        found = sr.findings(repeated(30) + [event("2026-10-01T10:00:00Z", "UNKNOWN", suggestion="")])
        self.assertEqual([f["count"] for f in found], [30, 1])
        self.assertEqual(len(found[0]["examples"]), 3)
        self.assertEqual((found[0]["first"], found[0]["last"]),
                         (min(e["time"] for e in repeated(30)), max(e["time"] for e in repeated(30))))


class CliTests(Fixture):
    def run_cli(self, *extra):
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = sr.main(["--claude-home", str(self.claude), "--codex-home", str(self.codex),
                            "--since", "3650d", *extra])
        return code, out.getvalue()

    def seed(self):
        self.claude_session("s1.jsonl", [
            {"type": "user", "timestamp": "2026-10-01T09:00:00Z", "cwd": self.real,
             "message": {"role": "user", "content": "PROMPT-SECRET-TEXT"}},
            claude_attachment("2026-10-01T10:00:00Z", self.real, "sess-123456789", [segment("MAP_INVALID")]),
        ])

    def test_text_output_is_redacted(self):
        self.seed()
        code, out = self.run_cli()
        self.assertEqual(code, 0)
        self.assertIn("MAP_INVALID", out)
        self.assertIn("project#" + sr.project_hash(self.real), out)
        self.assertIn("sess-1", out)
        self.assertIn("无法观测", out)
        for secret in (self.real, "secret-project", "PROMPT-SECRET-TEXT", "sess-123456789"):
            self.assertNotIn(secret, out)

    def test_json_output_is_redacted_and_parses(self):
        self.seed()
        code, out = self.run_cli("--json")
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(data["findings"][0]["stage"], "MAP_INVALID")
        self.assertIn("unobservable", data)
        for secret in (self.real, "secret-project", "PROMPT-SECRET-TEXT"):
            self.assertNotIn(secret, out)

    def test_reveal_shows_paths(self):
        self.seed()
        _, out = self.run_cli("--reveal")
        self.assertIn(self.real, out)

    def test_no_data_is_success(self):
        code, out = self.run_cli()
        self.assertEqual(code, 0)
        self.assertIn("没有发现", out)

    def test_bad_since_exits_2(self):
        import contextlib
        import io
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                sr.main(["--since", "two weeks"])
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main(verbosity=1)
