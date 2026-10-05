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

    def test_encrypted_spawn_message_never_reaches_output(self):
        self.rollout("main1", [
            codex_meta("main1", self.real, "2026-10-05T10:01:00Z"),
            codex_model("2026-10-05T10:01:00Z", "gpt-6.1-sol"),
            codex_spawn("2026-10-05T10:05:00Z", "slugify", "call_1"),
        ])
        self.assertNotIn("ENCRYPTED", json.dumps(mcr._jsonable(self.report()), ensure_ascii=False))


if __name__ == "__main__":
    unittest.main(verbosity=1)
