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
    args = parser.parse_args(argv)
    root = Path(args.project).resolve()
    report, failed = {"modules": []}, False
    for module in args.modules:
        try:
            report["modules"].append(task_windows(root, module))
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
