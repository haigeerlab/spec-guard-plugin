#!/usr/bin/env python3
"""Read-only module cost and rework report.

Splits a module's build into per-task time windows from the git history of
`tasks/<module>/todo.md`, then (in later layers) attributes host session usage to
those windows. Reads only the repository's git history and the hosts' own session
records; never writes a file and never prints session content.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ITEM = re.compile(r"^\s*[-*+]\s+\[([ xX])\]\s*(.*?)\s*$")


class AttributionError(Exception):
    """The module's tasks cannot be placed on a timeline; reported, never treated as zero usage."""


def parse_iso(text):
    return datetime.fromisoformat(text.strip().replace("Z", "+00:00")).astimezone(timezone.utc)


def iso(moment):
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def todo_items(text):
    """Checklist items in file order as (checked, title)."""
    items = []
    for line in text.splitlines():
        match = ITEM.match(line)
        if match:
            items.append((match.group(1) != " ", match.group(2)))
    return items


def _git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise AttributionError("git %s 失败：%s" % (args[0], (result.stderr.strip().splitlines() or ["未知错误"])[-1]))
    return result.stdout


def task_windows(root, module, now=None):
    """Return {"module", "tasks": [{"index", "title", "done", "start", "end"}]}.

    A task's end is the committer time of the first commit in which its checklist line (matched by
    position) is ticked; its start is the previous completion, or the commit that first added the
    todo. Unticked tasks run until `now`. Anything that prevents placing the tasks on a timeline
    raises AttributionError instead of yielding empty windows.
    """
    root = Path(root)
    now = now or datetime.now(timezone.utc)
    rel = "tasks/%s/todo.md" % module
    path = root / rel
    if not path.is_file():
        raise AttributionError("找不到 %s" % rel)
    items = todo_items(path.read_text(encoding="utf-8"))
    if not items:
        raise AttributionError("%s 没有清单项" % rel)
    _git(root, "rev-parse", "--git-dir")
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "-q", "HEAD"], capture_output=True, text=True)
    if head.returncode != 0:
        raise AttributionError("%s 没有提交历史（仓库还没有任何提交），无法切出 task 时间窗" % rel)
    log = _git(root, "log", "--reverse", "--format=%H%x09%cI", "--", rel).split("\n")
    commits = [line.split("\t") for line in log if line.strip()]
    if not commits:
        raise AttributionError("%s 没有提交历史，无法切出 task 时间窗" % rel)
    first_seen = parse_iso(commits[0][1])
    done_at = [None] * len(items)
    for sha, when in commits:
        snapshot = todo_items(_git(root, "show", "%s:%s" % (sha, rel)))
        for index, (checked, _title) in enumerate(snapshot[:len(items)]):
            if checked and done_at[index] is None:
                done_at[index] = parse_iso(when)
    finished = sorted(moment for moment in done_at if moment is not None)
    tasks = []
    for index, (_checked, title) in enumerate(items):
        end = done_at[index]
        earlier = [moment for moment in finished if end is None or moment < end]
        start = earlier[-1] if earlier else first_seen
        tasks.append({"index": index, "title": title, "done": end is not None,
                      "start": start, "end": end if end is not None else now})
    return {"module": module, "tasks": tasks}


CLAUDE_CATEGORIES = ("input", "cache_write_5m", "cache_write_1h", "cache_write", "cache_read", "output")
DISPATCH_TOOLS = ("Agent", "Task")


def encode_project_dir(real_path):
    """Claude Code's project folder name: the realpath with `/`, `.` and `_` replaced by `-`."""
    return re.sub(r"[/._]", "-", real_path)


def claude_project_dir(claude_home, project):
    return Path(claude_home) / "projects" / encode_project_dir(os.path.realpath(str(project)))


def _rows(path):
    try:
        handle = path.open(encoding="utf-8")
    except OSError:
        return
    with handle:
        for line in handle:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, dict):
                yield row


def _claude_categories(usage):
    split = usage.get("cache_creation") if isinstance(usage.get("cache_creation"), dict) else None
    out = {"input": usage.get("input_tokens") or 0, "cache_read": usage.get("cache_read_input_tokens") or 0,
           "output": usage.get("output_tokens") or 0}
    if split is not None:
        out["cache_write_5m"] = split.get("ephemeral_5m_input_tokens") or 0
        out["cache_write_1h"] = split.get("ephemeral_1h_input_tokens") or 0
    else:
        out["cache_write"] = usage.get("cache_creation_input_tokens") or 0
    return out


def _claude_messages(path, in_project):
    """Deduplicated assistant usage of one transcript: per message.id the row with the largest total;
    rows without an id count one by one. Returns ([(ts, model, categories)], [(ts, tool_use_id)])."""
    best, loose, calls = {}, [], {}
    for row in _rows(path):
        if row.get("type") != "assistant" or not in_project(row.get("cwd")):
            continue
        message = row.get("message") or {}
        try:
            ts = parse_iso(row["timestamp"])
        except (KeyError, ValueError, AttributeError):
            continue
        for block in message.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") in DISPATCH_TOOLS:
                calls.setdefault(block.get("id"), ts)
        usage = message.get("usage")
        if not isinstance(usage, dict):
            continue
        entry = (ts, message.get("model") or "unknown", _claude_categories(usage))
        mid = message.get("id")
        if mid is None:
            loose.append(entry)
        elif mid not in best or sum(entry[2].values()) > sum(best[mid][2].values()):
            best[mid] = entry
    return list(best.values()) + loose, sorted((ts, tid) for tid, ts in calls.items())


def read_claude(claude_home, project):
    """Main-session usage and dispatches, plus each subagent file's whole usage keyed by its toolUseId."""
    folder = claude_project_dir(claude_home, project)
    real = os.path.realpath(str(project))

    def in_project(cwd):
        return isinstance(cwd, str) and (cwd == real or cwd.startswith(real + os.sep))

    sessions = []
    if not folder.is_dir():
        return sessions
    for main in sorted(folder.glob("*.jsonl")):
        messages, calls = _claude_messages(main, in_project)
        subagents = {}
        for meta in sorted((folder / main.stem / "subagents").glob("agent-*.meta.json")):
            try:
                link = json.loads(meta.read_text(encoding="utf-8")).get("toolUseId")
            except (OSError, ValueError, AttributeError):
                link = None
            transcript = meta.with_name(meta.name[:-len(".meta.json")] + ".jsonl")
            if link and transcript.is_file():
                subagents[link] = _claude_messages(transcript, in_project)[0]
        sessions.append({"id": "claude:" + main.stem, "messages": messages, "dispatches": calls,
                         "subagents": subagents})
    return sessions


def _add(bucket, model, categories):
    slot = bucket.setdefault(model, {})
    for key, value in categories.items():
        slot[key] = slot.get(key, 0) + value


def build_report(project, module, claude_home=None, codex_home=None, now=None):
    windows = task_windows(project, module, now=now)
    sessions = read_claude(claude_home, project) if claude_home else []
    tasks = []
    for window in windows["tasks"]:
        start, end = window["start"], window["end"]
        inside = lambda ts: start < ts <= end  # noqa: E731
        task = dict(window, main={}, sub={}, dispatches=0, dispatches_unrecorded=0, sessions={})
        for session in sessions:
            used = 0
            for ts, model, categories in session["messages"]:
                if inside(ts):
                    _add(task["main"], model, categories)
                    used += sum(categories.values())
            for ts, tool_id in session["dispatches"]:
                if not inside(ts):
                    continue
                task["dispatches"] += 1
                records = session["subagents"].get(tool_id)
                if records is None:
                    task["dispatches_unrecorded"] += 1
                    continue
                for _ts, model, categories in records:
                    _add(task["sub"], model, categories)
                    used += sum(categories.values())
            if used:
                task["sessions"][session["id"]] = used
        task["coverage"] = "%d/%d" % (task["dispatches"] - task["dispatches_unrecorded"], task["dispatches"])
        tasks.append(task)
    return {"module": module, "tasks": tasks}


def _jsonable(value):
    if isinstance(value, datetime):
        return iso(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description="只读的模块成本与返工报告")
    parser.add_argument("modules", nargs="+", metavar="MODULE")
    parser.add_argument("--project", default=".")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--claude-home", default=str(Path.home() / ".claude"))
    args = parser.parse_args(argv)
    root = Path(args.project).resolve()
    report, failed = {"modules": []}, False
    for module in args.modules:
        try:
            report["modules"].append(build_report(root, module, claude_home=Path(args.claude_home)))
        except AttributionError as error:
            failed = True
            report["modules"].append({"module": module, "unattributable": str(error)})
    if args.json:
        print(json.dumps(_jsonable(report), ensure_ascii=False, indent=2))
    else:
        for entry in report["modules"]:
            if "unattributable" in entry:
                print("模块 %s：无法归属——%s" % (entry["module"], entry["unattributable"]))
                continue
            print("模块 %s" % entry["module"])
            for task in entry["tasks"]:
                print("  %s  %s → %s%s" % (task["title"], iso(task["start"]), iso(task["end"]),
                                          "" if task["done"] else "（进行中）"))
    if failed:
        print("无法归属的模块不报告为 0；修正后重试。", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
