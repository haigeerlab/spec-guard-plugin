"""module-cost-report regressions. Every fixture is synthetic: a temporary git repo plus fake
host session directories. Nothing here reads the machine's real Claude or Codex sessions."""
import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import module_cost_report as mcr

MODULE = "demo"
TODO = Path("tasks") / MODULE / "todo.md"


def utc(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)


class Repo:
    """A throwaway git repo whose commits carry exact committer times."""

    def __init__(self, root):
        self.root = Path(root)
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.invalid")
        self.git("config", "user.name", "t")

    def git(self, *args, when=None):
        env = dict(os.environ)
        if when:
            env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = when
        return subprocess.run(["git", "-C", str(self.root), *args], check=True,
                              capture_output=True, text=True, env=env).stdout

    def todo(self, lines, when):
        path = self.root / TODO
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Todo: demo\n\n" + "\n".join(lines) + "\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-qm", "todo", when=when)


class TaskWindowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Repo(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def windows(self, now="2026-10-05T12:00:00Z"):
        return mcr.task_windows(self.repo.root, MODULE, now=utc(now))

    def test_two_ticked_tasks_get_consecutive_windows(self):
        self.repo.todo(["- [ ] Task 1：a", "- [ ] Task 2：b"], "2026-10-05T10:00:00Z")
        self.repo.todo(["- [x] Task 1：a", "- [ ] Task 2：b"], "2026-10-05T10:20:00Z")
        self.repo.todo(["- [x] Task 1：a", "- [x] Task 2：b"], "2026-10-05T10:45:00Z")
        tasks = self.windows()["tasks"]
        self.assertEqual([t["title"] for t in tasks], ["Task 1：a", "Task 2：b"])
        self.assertEqual((tasks[0]["start"], tasks[0]["end"]), (utc("2026-10-05T10:00:00Z"), utc("2026-10-05T10:20:00Z")))
        self.assertEqual((tasks[1]["start"], tasks[1]["end"]), (utc("2026-10-05T10:20:00Z"), utc("2026-10-05T10:45:00Z")))
        self.assertTrue(all(t["done"] for t in tasks))

    def test_unchecked_task_runs_until_now(self):
        self.repo.todo(["- [ ] Task 1：a", "- [ ] Task 2：b"], "2026-10-05T10:00:00Z")
        self.repo.todo(["- [x] Task 1：a", "- [ ] Task 2：b"], "2026-10-05T10:20:00Z")
        task2 = self.windows(now="2026-10-05T11:30:00Z")["tasks"][1]
        self.assertFalse(task2["done"])
        self.assertEqual((task2["start"], task2["end"]), (utc("2026-10-05T10:20:00Z"), utc("2026-10-05T11:30:00Z")))

    def test_first_tick_counts_even_if_unticked_later(self):
        self.repo.todo(["- [ ] Task 1：a"], "2026-10-05T10:00:00Z")
        self.repo.todo(["- [x] Task 1：a"], "2026-10-05T10:10:00Z")
        self.repo.todo(["- [ ] Task 1：a"], "2026-10-05T10:15:00Z")
        self.repo.todo(["- [x] Task 1：a"], "2026-10-05T10:30:00Z")
        task = self.windows()["tasks"][0]
        self.assertEqual(task["end"], utc("2026-10-05T10:10:00Z"))

    def test_uncommitted_todo_cannot_be_attributed(self):
        path = self.repo.root / TODO
        path.parent.mkdir(parents=True)
        path.write_text("- [x] Task 1：a\n", encoding="utf-8")
        with self.assertRaises(mcr.AttributionError) as caught:
            self.windows()
        self.assertIn("没有提交历史", str(caught.exception))

    def test_missing_todo_cannot_be_attributed(self):
        with self.assertRaises(mcr.AttributionError) as caught:
            self.windows()
        self.assertIn("todo.md", str(caught.exception))

    def test_not_a_git_repo_cannot_be_attributed(self):
        with tempfile.TemporaryDirectory() as plain:
            (Path(plain) / TODO).parent.mkdir(parents=True)
            (Path(plain) / TODO).write_text("- [x] Task 1：a\n", encoding="utf-8")
            with self.assertRaises(mcr.AttributionError):
                mcr.task_windows(Path(plain), MODULE, now=utc("2026-10-05T12:00:00Z"))

    def test_cli_exits_2_and_reports_why_instead_of_zero(self):
        result = subprocess.run(["python3", "-B", str(Path(mcr.__file__)), "--project", str(self.repo.root),
                                 "--json", MODULE], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("无法归属", result.stdout + result.stderr)
        self.assertNotIn('"total"', result.stdout)

    def test_cli_json_lists_windows(self):
        self.repo.todo(["- [ ] Task 1：a"], "2026-10-05T10:00:00Z")
        self.repo.todo(["- [x] Task 1：a"], "2026-10-05T10:20:00Z")
        result = subprocess.run(["python3", "-B", str(Path(mcr.__file__)), "--project", str(self.repo.root),
                                 "--json", MODULE], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        task = data["modules"][0]["tasks"][0]
        self.assertEqual((task["start"], task["end"]), ("2026-10-05T10:00:00Z", "2026-10-05T10:20:00Z"))


def claude_row(kind, ts, cwd, mid=None, model="claude-opus-5-5", usage=None, content=None, sidechain=False, agent=None):
    row = {"type": kind, "timestamp": ts, "cwd": str(cwd), "isSidechain": sidechain, "sessionId": "s1"}
    if agent:
        row["agentId"] = agent
    message = {"role": kind, "content": content or [{"type": "text", "text": "SECRET-PROMPT-TEXT"}]}
    if kind == "assistant":
        message.update({"model": model, "usage": usage or {}})
        if mid:
            message["id"] = mid
    row["message"] = message
    return row


def usage(inp=0, w5=0, w1=0, read=0, out=0):
    return {"input_tokens": inp, "cache_creation_input_tokens": w5 + w1, "cache_read_input_tokens": read,
            "output_tokens": out, "cache_creation": {"ephemeral_5m_input_tokens": w5, "ephemeral_1h_input_tokens": w1}}


def agent_call(tool_id):
    return [{"type": "tool_use", "id": tool_id, "name": "Agent", "input": {"prompt": "SECRET-TASK-PROMPT"}}]


class ClaudeUsageTests(unittest.TestCase):
    """Two tasks; Task 1 window 10:00-10:20, Task 2 window 10:20-10:45 (UTC)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.project = base / "my.proj_dir"
        self.project.mkdir()
        self.repo = Repo(self.project)
        self.repo.todo(["- [ ] Task 1：a", "- [ ] Task 2：b"], "2026-10-05T10:00:00Z")
        self.repo.todo(["- [x] Task 1：a", "- [ ] Task 2：b"], "2026-10-05T10:20:00Z")
        self.repo.todo(["- [x] Task 1：a", "- [x] Task 2：b"], "2026-10-05T10:45:00Z")
        self.home = base / "claude-home"
        real = os.path.realpath(self.project)
        self.dir = self.home / "projects" / mcr.encode_project_dir(real)
        self.dir.mkdir(parents=True)
        self.real = real

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, rows):
        path = self.dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        return path

    def report(self):
        return mcr.build_report(self.project, MODULE, claude_home=self.home, codex_home=None,
                                now=utc("2026-10-05T12:00:00Z"))

    def test_project_dir_encoding_uses_realpath_and_replaces_dot_and_underscore(self):
        self.assertTrue(mcr.encode_project_dir(self.real).endswith("-my-proj-dir"))
        self.assertNotIn(".", mcr.encode_project_dir(self.real))
        self.assertEqual(mcr.claude_project_dir(self.home, self.project), self.dir)

    def test_message_id_rows_keep_only_the_largest_usage(self):
        cwd = self.real
        self.write("s1.jsonl", [
            claude_row("assistant", "2026-10-05T10:05:00Z", cwd, "m1", usage=usage(inp=2, w1=100, out=5)),
            claude_row("assistant", "2026-10-05T10:05:01Z", cwd, "m1", usage=usage(inp=2, w1=100, out=40)),
            claude_row("assistant", "2026-10-05T10:05:02Z", cwd, "m1", usage=usage(inp=2, w1=100, out=90)),
            claude_row("assistant", "2026-10-05T10:06:00Z", cwd, None, usage=usage(read=7)),
            claude_row("assistant", "2026-10-05T10:07:00Z", cwd, None, usage=usage(read=7)),
        ])
        task1 = self.report()["tasks"][0]
        main = task1["main"]["claude-opus-5-5"]
        self.assertEqual((main["input"], main["cache_write_1h"], main["output"], main["cache_read"]), (2, 100, 90, 14))

    def test_messages_outside_the_window_go_to_their_own_task(self):
        cwd = self.real
        self.write("s1.jsonl", [
            claude_row("assistant", "2026-10-05T10:05:00Z", cwd, "m1", usage=usage(out=10)),
            claude_row("assistant", "2026-10-05T10:30:00Z", cwd, "m2", usage=usage(out=20)),
            claude_row("assistant", "2026-10-05T09:00:00Z", cwd, "m0", usage=usage(out=999)),
        ])
        tasks = self.report()["tasks"]
        self.assertEqual(tasks[0]["main"]["claude-opus-5-5"]["output"], 10)
        self.assertEqual(tasks[1]["main"]["claude-opus-5-5"]["output"], 20)

    def test_model_switch_mid_session_is_split_per_message(self):
        cwd = self.real
        self.write("s1.jsonl", [
            claude_row("assistant", "2026-10-05T10:05:00Z", cwd, "m1", model="claude-opus-5", usage=usage(out=1)),
            claude_row("assistant", "2026-10-05T10:06:00Z", cwd, "m2", model="claude-opus-5-5", usage=usage(out=2)),
        ])
        main = self.report()["tasks"][0]["main"]
        self.assertEqual((main["claude-opus-5"]["output"], main["claude-opus-5-5"]["output"]), (1, 2))

    def test_subagent_file_is_linked_by_tool_use_id_and_counted_once(self):
        cwd = self.real
        self.write("s1.jsonl", [
            claude_row("assistant", "2026-10-05T10:21:00Z", cwd, "m1", usage=usage(out=1), content=agent_call("toolu_A")),
            claude_row("assistant", "2026-10-05T10:21:00Z", cwd, "m1", usage=usage(out=1), content=agent_call("toolu_A")),
        ])
        sub = [claude_row("assistant", "2026-10-05T10:22:00Z", cwd, "x1", model="claude-sonnet-5-5",
                          usage=usage(w1=60000, out=10), sidechain=True, agent="aa"),
               claude_row("assistant", "2026-10-05T10:22:01Z", cwd, "x1", model="claude-sonnet-5-5",
                          usage=usage(w1=60000, out=30), sidechain=True, agent="aa"),
               # a SendMessage continuation appended to the same file, later
               claude_row("assistant", "2026-10-05T10:40:00Z", cwd, "x2", model="claude-sonnet-5-5",
                          usage=usage(read=500, out=5), sidechain=True, agent="aa")]
        self.write("s1/subagents/agent-aa.jsonl", sub)
        (self.dir / "s1/subagents/agent-aa.meta.json").write_text(
            json.dumps({"agentType": "executor", "model": "sonnet", "toolUseId": "toolu_A"}), encoding="utf-8")
        report = self.report()
        task2 = report["tasks"][1]
        self.assertEqual(task2["dispatches"], 1)
        self.assertEqual(task2["dispatches_unrecorded"], 0)
        s = task2["sub"]["claude-sonnet-5-5"]
        self.assertEqual((s["cache_write_1h"], s["output"], s["cache_read"]), (60000, 35, 500))
        self.assertEqual(report["tasks"][0]["sub"], {})

    def test_dispatch_without_subagent_file_is_unrecorded_not_zero(self):
        cwd = self.real
        self.write("s1.jsonl", [
            claude_row("assistant", "2026-10-05T10:21:00Z", cwd, "m1", usage=usage(out=1), content=agent_call("toolu_B")),
        ])
        task2 = self.report()["tasks"][1]
        self.assertEqual((task2["dispatches"], task2["dispatches_unrecorded"]), (1, 1))
        self.assertEqual(task2["coverage"], "0/1")

    def test_cache_write_split_5m_and_1h(self):
        cwd = self.real
        self.write("s1.jsonl", [claude_row("assistant", "2026-10-05T10:05:00Z", cwd, "m1", usage=usage(w5=3, w1=4))])
        main = self.report()["tasks"][0]["main"]["claude-opus-5-5"]
        self.assertEqual((main["cache_write_5m"], main["cache_write_1h"]), (3, 4))

    def test_rows_from_another_cwd_are_ignored(self):
        self.write("s1.jsonl", [
            claude_row("assistant", "2026-10-05T10:05:00Z", "/somewhere/else", "m1", usage=usage(out=50)),
        ])
        self.assertEqual(self.report()["tasks"][0]["main"], {})

    def test_contributing_sessions_are_listed(self):
        cwd = self.real
        self.write("s1.jsonl", [claude_row("assistant", "2026-10-05T10:05:00Z", cwd, "m1", usage=usage(out=5))])
        self.write("s2.jsonl", [claude_row("assistant", "2026-10-05T10:06:00Z", cwd, "m9", usage=usage(out=6))])
        self.assertEqual(sorted(self.report()["tasks"][0]["sessions"]), ["claude:s1", "claude:s2"])


def codex_meta(thread, cwd, ts, parent=None, task=None, guardian=False):
    payload = {"id": thread, "session_id": parent or thread, "cwd": str(cwd), "timestamp": ts}
    if guardian:  # shape copied from a real codex-cli 0.160.0 guardian rollout
        payload["source"] = {"subagent": {"other": "guardian"}}
        payload["parent_thread_id"] = parent
    elif parent:
        payload["source"] = {"subagent": {"thread_spawn": {"parent_thread_id": parent, "depth": 1,
                                                           "agent_path": "/root/" + task}}}
    else:
        payload["source"] = "exec"
    return {"timestamp": ts, "type": "session_meta", "payload": payload}


def codex_model(ts, model, effort="medium"):
    return {"timestamp": ts, "type": "turn_context", "payload": {"model": model, "effort": effort}}


def codex_tokens(ts, inp, cached, out, reasoning=0, write=0):
    total = {"input_tokens": inp, "cached_input_tokens": cached, "cache_write_input_tokens": write,
             "output_tokens": out, "reasoning_output_tokens": reasoning, "total_tokens": inp + out}
    return {"timestamp": ts, "type": "event_msg", "payload": {"type": "token_count", "info": {"total_token_usage": total}}}


def codex_spawn(ts, task, call_id):
    args = {"task_name": task, "model": "gpt-6-luna", "reasoning_effort": "high", "message": "gAAAAAB-ENCRYPTED"}
    return {"timestamp": ts, "type": "response_item",
            "payload": {"type": "function_call", "name": "spawn_agent", "call_id": call_id, "arguments": json.dumps(args)}}


class CodexUsageTests(unittest.TestCase):
    """Same two windows as ClaudeUsageTests: Task 1 10:00-10:20, Task 2 10:20-10:45 (UTC)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.project = base / "proj"
        self.project.mkdir()
        self.repo = Repo(self.project)
        self.repo.todo(["- [ ] Task 1：a", "- [ ] Task 2：b"], "2026-10-05T10:00:00Z")
        self.repo.todo(["- [x] Task 1：a", "- [ ] Task 2：b"], "2026-10-05T10:20:00Z")
        self.repo.todo(["- [x] Task 1：a", "- [x] Task 2：b"], "2026-10-05T10:45:00Z")
        self.home = base / "codex-home"
        self.real = os.path.realpath(self.project)

    def tearDown(self):
        self.tmp.cleanup()

    def rollout(self, thread, rows):
        path = self.home / "sessions" / "2026" / "10" / "05" / ("rollout-2026-10-05T10-00-00-%s.jsonl" % thread)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    def report(self):
        return mcr.build_report(self.project, MODULE, claude_home=None, codex_home=self.home,
                                now=utc("2026-10-05T12:00:00Z"))

    def test_cumulative_totals_are_differenced_not_summed(self):
        self.rollout("main1", [
            codex_meta("main1", self.real, "2026-10-05T09:59:00Z"),
            codex_model("2026-10-05T09:59:00Z", "gpt-6.1-sol"),
            codex_tokens("2026-10-05T09:59:30Z", 1000, 0, 10),        # before Task 1: not counted
            codex_tokens("2026-10-05T10:05:00Z", 5000, 3000, 50, reasoning=20),
            codex_tokens("2026-10-05T10:10:00Z", 9000, 6000, 90, reasoning=30),
            codex_tokens("2026-10-05T10:30:00Z", 12000, 8000, 100, reasoning=35),
        ])
        tasks = self.report()["tasks"]
        t1 = tasks[0]["main"]["gpt-6.1-sol"]
        # Task 1 = 10:10 total minus 09:59:30 total: input 8000 of which cached 6000 -> uncached 2000
        self.assertEqual((t1["input"], t1["cache_read"], t1["output"], t1["reasoning_output"]), (2000, 6000, 80, 30))
        t2 = tasks[1]["main"]["gpt-6.1-sol"]
        self.assertEqual((t2["input"], t2["cache_read"], t2["output"]), (1000, 2000, 10))

    def test_reasoning_is_reference_only_not_added_to_session_total(self):
        self.rollout("main1", [
            codex_meta("main1", self.real, "2026-10-05T10:01:00Z"),
            codex_model("2026-10-05T10:01:00Z", "gpt-6.1-sol"),
            codex_tokens("2026-10-05T10:05:00Z", 100, 40, 30, reasoning=25),
        ])
        task1 = self.report()["tasks"][0]
        self.assertEqual(task1["sessions"]["codex:main1"], 130)  # input 100 + output 30; reasoning not added

    def test_child_rollout_counts_whole_thread_to_spawning_task(self):
        self.rollout("main1", [
            codex_meta("main1", self.real, "2026-10-05T10:01:00Z"),
            codex_model("2026-10-05T10:01:00Z", "gpt-6.1-sol"),
            codex_spawn("2026-10-05T10:21:00Z", "word_count", "call_1"),
            codex_tokens("2026-10-05T10:22:00Z", 100, 0, 10),
        ])
        self.rollout("child1", [
            codex_meta("child1", self.real, "2026-10-05T10:21:01Z", parent="main1", task="word_count"),
            codex_model("2026-10-05T10:21:01Z", "gpt-6-luna", "high"),
            codex_tokens("2026-10-05T10:23:00Z", 4000, 1000, 200),
            codex_tokens("2026-10-05T10:50:00Z", 6000, 2000, 300),   # after the window: still this child
        ])
        task2 = self.report()["tasks"][1]
        self.assertEqual((task2["dispatches"], task2["dispatches_unrecorded"], task2["coverage"]), (1, 0, "1/1"))
        child = task2["sub"]["gpt-6-luna"]
        self.assertEqual((child["input"], child["cache_read"], child["output"]), (4000, 2000, 300))
        self.assertEqual(self.report()["tasks"][0]["sub"], {})

    def test_spawn_without_child_rollout_is_unrecorded(self):
        self.rollout("main1", [
            codex_meta("main1", self.real, "2026-10-05T10:01:00Z"),
            codex_model("2026-10-05T10:01:00Z", "gpt-6.1-sol"),
            codex_spawn("2026-10-05T10:05:00Z", "slugify", "call_1"),
        ])
        task1 = self.report()["tasks"][0]
        self.assertEqual((task1["dispatches"], task1["dispatches_unrecorded"]), (1, 1))

    def test_guardian_thread_is_listed_apart_and_not_a_dispatch(self):
        self.rollout("main1", [codex_meta("main1", self.real, "2026-10-05T10:01:00Z"),
                               codex_model("2026-10-05T10:01:00Z", "gpt-6.1-sol")])
        self.rollout("guard1", [
            codex_meta("guard1", self.real, "2026-10-05T10:02:00Z", parent="main1", guardian=True),
            codex_model("2026-10-05T10:02:00Z", "gpt-6.1-sol"),
            codex_tokens("2026-10-05T10:03:00Z", 500, 100, 5),
        ])
        task1 = self.report()["tasks"][0]
        self.assertEqual(task1["dispatches"], 0)
        self.assertEqual(task1["sub"], {})
        self.assertEqual(task1["guardian"]["gpt-6.1-sol"]["input"], 400)

    def test_rollouts_of_another_project_are_ignored(self):
        self.rollout("other", [
            codex_meta("other", "/somewhere/else", "2026-10-05T10:01:00Z"),
            codex_model("2026-10-05T10:01:00Z", "gpt-6.1-sol"),
            codex_tokens("2026-10-05T10:05:00Z", 999, 0, 9),
        ])
        self.assertEqual(self.report()["tasks"][0]["main"], {})

    def test_repeated_identical_totals_are_not_extra_turns(self):
        self.rollout("main1", [
            codex_meta("main1", self.real, "2026-10-05T10:01:00Z"),
            codex_model("2026-10-05T10:01:00Z", "gpt-6.1-sol"),
            codex_tokens("2026-10-05T10:05:00Z", 100, 0, 10),
            codex_tokens("2026-10-05T10:05:01Z", 100, 0, 10),   # the host re-emits the same total
            codex_tokens("2026-10-05T10:06:00Z", 300, 100, 20),
        ])
        self.assertEqual(self.report()["tasks"][0]["main_turns"], 2)

    def test_encrypted_spawn_message_never_reaches_output(self):
        self.rollout("main1", [
            codex_meta("main1", self.real, "2026-10-05T10:01:00Z"),
            codex_model("2026-10-05T10:01:00Z", "gpt-6.1-sol"),
            codex_spawn("2026-10-05T10:05:00Z", "slugify", "call_1"),
        ])
        self.assertNotIn("ENCRYPTED", json.dumps(mcr._jsonable(self.report()), ensure_ascii=False))


def tool_result(ts, cwd, tool_id, text, error=False):
    row = {"type": "user", "timestamp": ts, "cwd": str(cwd), "isSidechain": False, "sessionId": "s1",
           "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_id,
                                                     "is_error": error, "content": text}]}}
    return row


def edit_call(tool_id, name, path):
    return [{"type": "tool_use", "id": tool_id, "name": name, "input": {"file_path": path, "new_string": "SECRET-CODE"}}]


RECLAIM = "PreToolUse:Agent hook error: tier-guard：这是 L2 任务第二次失败后的收回（上游报告连续失败 2 次）。"


class ReworkSignalTests(ClaudeUsageTests):
    """Rework signals on the Claude side; inherits the two-task fixture."""

    def subagent(self, name, tool_id, ts):
        self.write("s1/subagents/agent-%s.jsonl" % name, [
            claude_row("assistant", ts, self.real, "sub-" + name, model="claude-sonnet-5-5", usage=usage(out=3),
                       sidechain=True, agent=name)])
        (self.dir / ("s1/subagents/agent-%s.meta.json" % name)).write_text(json.dumps({"toolUseId": tool_id}), encoding="utf-8")

    def test_two_dispatches_of_one_task_count_one_redispatch(self):
        cwd = self.real
        self.write("s1.jsonl", [
            claude_row("assistant", "2026-10-05T10:21:00Z", cwd, "m1", usage=usage(out=1), content=agent_call("t1")),
            tool_result("2026-10-05T10:25:00Z", cwd, "t1", "done"),
            claude_row("assistant", "2026-10-05T10:26:00Z", cwd, "m2", usage=usage(out=1), content=agent_call("t2")),
            tool_result("2026-10-05T10:30:00Z", cwd, "t2", "done"),
        ])
        self.subagent("a1", "t1", "2026-10-05T10:22:00Z")
        self.subagent("a2", "t2", "2026-10-05T10:27:00Z")
        task2 = self.report()["tasks"][1]
        self.assertEqual((task2["dispatches"], task2["redispatches"]), (2, 1))

    def test_reclaimed_call_is_a_reclaim_not_a_dispatch(self):
        cwd = self.real
        self.write("s1.jsonl", [
            claude_row("assistant", "2026-10-05T10:21:00Z", cwd, "m1", usage=usage(out=1), content=agent_call("t1")),
            tool_result("2026-10-05T10:21:01Z", cwd, "t1", RECLAIM, error=True),
        ])
        task2 = self.report()["tasks"][1]
        self.assertEqual((task2["dispatches"], task2["dispatches_unrecorded"], task2["reclaims"]), (0, 0, 1))

    def test_other_hook_denials_are_not_dispatches_either(self):
        cwd = self.real
        self.write("s1.jsonl", [
            claude_row("assistant", "2026-10-05T10:21:00Z", cwd, "m1", usage=usage(out=1), content=agent_call("t1")),
            tool_result("2026-10-05T10:21:01Z", cwd, "t1", "PreToolUse:Agent hook error: tier-guard：本会话第一次未 pin 的派活已被拦下。", error=True),
        ])
        task2 = self.report()["tasks"][1]
        self.assertEqual((task2["dispatches"], task2["reclaims"], task2["coverage"]), (0, 0, "0/0"))

    def test_main_edits_after_handback_count_distinct_files_except_todo(self):
        cwd = self.real
        todo = os.path.join(self.real, "tasks", MODULE, "todo.md")
        self.write("s1.jsonl", [
            claude_row("assistant", "2026-10-05T10:21:00Z", cwd, "m1", usage=usage(out=1), content=agent_call("t1")),
            claude_row("assistant", "2026-10-05T10:21:30Z", cwd, "m0", usage=usage(out=1),
                       content=edit_call("e0", "Edit", os.path.join(self.real, "before.py"))),
            tool_result("2026-10-05T10:25:00Z", cwd, "t1", "done"),
            claude_row("assistant", "2026-10-05T10:26:00Z", cwd, "m2", usage=usage(out=1),
                       content=edit_call("e1", "Edit", os.path.join(self.real, "src.py"))),
            claude_row("assistant", "2026-10-05T10:27:00Z", cwd, "m3", usage=usage(out=1),
                       content=edit_call("e2", "Write", os.path.join(self.real, "src.py"))),
            claude_row("assistant", "2026-10-05T10:28:00Z", cwd, "m4", usage=usage(out=1),
                       content=edit_call("e3", "MultiEdit", os.path.join(self.real, "test_src.py"))),
            claude_row("assistant", "2026-10-05T10:29:00Z", cwd, "m5", usage=usage(out=1), content=edit_call("e4", "Edit", todo)),
        ])
        self.subagent("a1", "t1", "2026-10-05T10:22:00Z")
        task2 = self.report()["tasks"][1]
        self.assertEqual(task2["edits_after_handback"], 2)

    def test_no_dispatch_means_no_edits_after_handback(self):
        cwd = self.real
        self.write("s1.jsonl", [claude_row("assistant", "2026-10-05T10:26:00Z", cwd, "m2", usage=usage(out=1),
                                           content=edit_call("e1", "Edit", os.path.join(self.real, "src.py")))])
        self.assertEqual(self.report()["tasks"][1]["edits_after_handback"], 0)

    def test_report_never_carries_prompts_or_code(self):
        cwd = self.real
        self.write("s1.jsonl", [
            claude_row("assistant", "2026-10-05T10:21:00Z", cwd, "m1", usage=usage(out=1), content=agent_call("t1")),
            tool_result("2026-10-05T10:25:00Z", cwd, "t1", "SECRET-RESULT"),
            claude_row("assistant", "2026-10-05T10:26:00Z", cwd, "m2", usage=usage(out=1),
                       content=edit_call("e1", "Edit", os.path.join(self.real, "src.py"))),
        ])
        self.subagent("a1", "t1", "2026-10-05T10:22:00Z")
        dumped = json.dumps(mcr._jsonable(self.report()), ensure_ascii=False)
        for secret in ("SECRET-PROMPT-TEXT", "SECRET-TASK-PROMPT", "SECRET-RESULT", "SECRET-CODE", "src.py"):
            self.assertNotIn(secret, dumped)


class CodexReworkTests(CodexUsageTests):
    def test_main_apply_patch_after_child_finishes_counts_files(self):
        patch = ("*** Begin Patch\n*** Update File: %s/textkit/slug.py\n@@\n-SECRET\n+SECRET\n"
                 "*** Add File: %s/tests/test_slug.py\n+x\n*** Update File: %s/tasks/demo/todo.md\n*** End Patch") % (
                     self.real, self.real, self.real)
        self.rollout("main1", [
            codex_meta("main1", self.real, "2026-10-05T10:01:00Z"),
            codex_model("2026-10-05T10:01:00Z", "gpt-6.1-sol"),
            codex_spawn("2026-10-05T10:21:00Z", "word_count", "call_1"),
            {"timestamp": "2026-10-05T10:30:00Z", "type": "response_item",
             "payload": {"type": "custom_tool_call", "name": "exec",
                         "input": "text(await tools.apply_patch(%s));" % json.dumps(patch)}},
        ])
        self.rollout("child1", [
            codex_meta("child1", self.real, "2026-10-05T10:21:01Z", parent="main1", task="word_count"),
            codex_model("2026-10-05T10:21:01Z", "gpt-6-luna", "high"),
            codex_tokens("2026-10-05T10:25:00Z", 10, 0, 1),
        ])
        task2 = self.report()["tasks"][1]
        self.assertEqual((task2["dispatches"], task2["edits_after_handback"]), (1, 2))


PRICES = {"currency": "USD", "per": "1M", "models": {
    "claude-opus-5-5": {"input": 5, "cache_write_5m": 6.25, "cache_write_1h": 10, "cache_read": 0.5, "output": 25},
    "claude-sonnet-5-5": {"input": 2, "cache_read": 0.2, "output": 10}}}


class OutputTests(ClaudeUsageTests):
    def run_cli(self, *extra, prices=None):
        args = ["python3", "-B", str(Path(mcr.__file__)), "--project", str(self.project),
                "--claude-home", str(self.home), "--codex-home", str(Path(self.tmp.name) / "no-codex")]
        if prices is not None:
            price_file = Path(self.tmp.name) / "prices.json"
            price_file.write_text(json.dumps(prices), encoding="utf-8")
            args += ["--prices", str(price_file)]
        result = subprocess.run(args + list(extra) + [MODULE], capture_output=True, text=True,
                                env=dict(os.environ, SPEC_GUARD_COST_REPORT_NOW="2026-10-05T12:00:00Z"))
        return result

    def seed(self):
        cwd = self.real
        self.write("s1.jsonl", [
            claude_row("assistant", "2026-10-05T10:05:00Z", cwd, "m1", usage=usage(inp=1000, w1=1000, read=2000000, out=1000)),
            claude_row("assistant", "2026-10-05T10:06:00Z", cwd, "m2", usage=usage(read=1000000, out=1000)),
            claude_row("assistant", "2026-10-05T10:21:00Z", cwd, "m3", usage=usage(out=1), content=agent_call("t1")),
            tool_result("2026-10-05T10:25:00Z", cwd, "t1", "SECRET-RESULT"),
        ])
        self.write("s1/subagents/agent-a1.jsonl", [
            claude_row("assistant", "2026-10-05T10:22:00Z", cwd, "x1", model="claude-sonnet-5-5",
                       usage=usage(w1=50000, out=2000), sidechain=True, agent="a1")])
        (self.dir / "s1/subagents/agent-a1.meta.json").write_text(json.dumps({"toolUseId": "t1"}), encoding="utf-8")

    def test_main_turns_count_deduplicated_model_calls(self):
        self.seed()
        tasks = self.report()["tasks"]
        self.assertEqual((tasks[0]["main_turns"], tasks[1]["main_turns"]), (2, 1))

    def test_prices_convert_tokens_and_flag_unpriced_categories(self):
        self.seed()
        data = json.loads(self.run_cli("--json", prices=PRICES).stdout)
        t1, t2 = data["modules"][0]["tasks"]
        # opus: 1000*5 + 1000*10 + 3,000,000*0.5 + 2000*25 = 5000+10000+1500000+50000 = 1,565,000 per 1M -> 1.565
        self.assertAlmostEqual(t1["cost"]["main"], 1.565, places=6)
        self.assertEqual(t1["cost"]["unpriced"], [])
        # sonnet subagent has cache_write_1h tokens but no cache_write_1h price -> flagged, not guessed
        self.assertIn("claude-sonnet-5-5:cache_write_1h", t2["cost"]["unpriced"])
        self.assertAlmostEqual(t2["cost"]["sub"], 2000 * 10 / 1e6, places=6)

    def test_without_prices_there_is_no_money(self):
        self.seed()
        data = json.loads(self.run_cli("--json").stdout)
        self.assertNotIn("cost", data["modules"][0]["tasks"][0])

    def test_table_output_has_task_rows_and_unknowns_but_no_content(self):
        self.seed()
        result = self.run_cli(prices=PRICES)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout
        for needle in ("Task 1：a", "Task 2：b", "主会话轮次", "合计", "无法统计的部分", "未定价", "claude:s1", "shell 命令"):
            self.assertIn(needle, out)
        for secret in ("SECRET-PROMPT-TEXT", "SECRET-TASK-PROMPT", "SECRET-RESULT"):
            self.assertNotIn(secret, out)

    def test_no_session_data_is_reported_as_empty_not_an_error(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("没有找到会话数据", result.stdout)

    def test_two_modules_get_a_dispatched_versus_not_comparison(self):
        self.seed()
        other = self.project / "tasks" / "solo" / "todo.md"
        other.parent.mkdir(parents=True)
        other.write_text("- [ ] Task 1：x\n", encoding="utf-8")
        self.repo.git("add", "-A"); self.repo.git("commit", "-qm", "solo", when="2026-10-05T11:00:00Z")
        other.write_text("- [x] Task 1：x\n", encoding="utf-8")
        self.repo.git("add", "-A"); self.repo.git("commit", "-qm", "solo done", when="2026-10-05T11:30:00Z")
        self.write("s3.jsonl", [claude_row("assistant", "2026-10-05T11:10:00Z", self.real, "z1", usage=usage(out=300))])
        args = ["python3", "-B", str(Path(mcr.__file__)), "--project", str(self.project), "--claude-home", str(self.home),
                "--codex-home", str(Path(self.tmp.name) / "no-codex"), "--json", MODULE, "solo"]
        data = json.loads(subprocess.run(args, capture_output=True, text=True,
                                         env=dict(os.environ, SPEC_GUARD_COST_REPORT_NOW="2026-10-05T12:00:00Z")).stdout)
        groups = data["comparison"]
        self.assertEqual((groups["dispatched"]["tasks"], groups["not_dispatched"]["tasks"]), (1, 2))
        self.assertIn("趋势", data["comparison"]["note"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
