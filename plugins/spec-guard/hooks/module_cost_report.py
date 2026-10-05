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
EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
HOOK_DENIAL = "hook error"
RECLAIM_MARK = "第二次失败后的收回"
PATCH_FILE = re.compile(r"\*\*\* (?:Update|Add|Delete) File: (.+?)(?=\\n|\n|$)")


def _text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(_text(item.get("text") if isinstance(item, dict) else item) for item in content)
    return ""


def _claude_events(path, in_project):
    """Tool results (for denials and hand-back times) and main-agent file edits; never their content."""
    results, edits, seen = {}, [], set()
    for row in _rows(path):
        if not in_project(row.get("cwd")):
            continue
        try:
            ts = parse_iso(row["timestamp"])
        except (KeyError, ValueError, AttributeError):
            continue
        for block in (row.get("message") or {}).get("content") or []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_result" and block.get("tool_use_id") not in results:
                results[block.get("tool_use_id")] = (ts, bool(block.get("is_error")), _text(block.get("content")))
            elif block.get("type") == "tool_use" and block.get("name") in EDIT_TOOLS and block.get("id") not in seen:
                seen.add(block.get("id"))
                target = (block.get("input") or {}).get("file_path") or (block.get("input") or {}).get("notebook_path")
                if isinstance(target, str):
                    edits.append((ts, target))
    return results, edits


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
        results, edits = _claude_events(main, in_project)
        sessions.append({"id": "claude:" + main.stem, "messages": messages, "dispatches": calls,
                         "subagents": subagents, "results": results, "edits": edits})
    return sessions


INFO_ONLY = ("reasoning_output",)


def _total(categories):
    """Tokens that count toward a total; reasoning is already inside Codex output, so it is reference only."""
    return sum(value for key, value in categories.items() if key not in INFO_ONLY)


def _codex_categories(before, after):
    def delta(key):
        return (after.get(key) or 0) - (before.get(key) or 0)
    cached = delta("cached_input_tokens")
    return {"input": delta("input_tokens") - cached, "cache_read": cached,
            "cache_write": delta("cache_write_input_tokens"), "output": delta("output_tokens"),
            "reasoning_output": delta("reasoning_output_tokens")}


def _codex_thread(path, in_project):
    """One rollout as {"meta", "records": [(ts, model, categories)], "spawns": [(ts, call_id, task_name)]}.
    Cumulative token_count totals become per-snapshot deltas, each tagged with the model in effect."""
    meta, model, previous, records, spawns, edits = None, "unknown", {}, [], [], []
    for row in _rows(path):
        kind, payload = row.get("type"), row.get("payload") or {}
        if kind == "session_meta":
            meta = payload
            if not in_project(payload.get("cwd")):
                return None
            continue
        if meta is None:
            continue
        try:
            ts = parse_iso(row["timestamp"])
        except (KeyError, ValueError, AttributeError):
            continue
        if kind == "turn_context":
            model = payload.get("model") or model
        elif kind == "event_msg" and payload.get("type") == "token_count":
            total = (payload.get("info") or {}).get("total_token_usage")
            if isinstance(total, dict):
                records.append((ts, model, _codex_categories(previous, total)))
                previous = total
        elif kind == "response_item" and payload.get("type") == "function_call" and payload.get("name") == "spawn_agent":
            try:
                task_name = json.loads(payload.get("arguments") or "{}").get("task_name")
            except (ValueError, AttributeError):
                task_name = None
            spawns.append((ts, payload.get("call_id"), task_name))
        elif kind == "response_item" and payload.get("type") in ("custom_tool_call", "function_call"):
            body = payload.get("input") if payload.get("type") == "custom_tool_call" else payload.get("arguments")
            if isinstance(body, str) and "apply_patch" in (payload.get("name") or "") + body:
                edits.extend((ts, target.strip()) for target in PATCH_FILE.findall(body))
    return None if meta is None else {"meta": meta, "records": records, "spawns": spawns, "edits": edits}


def _is_guardian(meta):
    """The host's approval reviewer. Real rollouts nest it as source.subagent.other; accept the flat form too."""
    source = meta.get("source")
    if not isinstance(source, dict):
        return False
    nested = source.get("subagent") if isinstance(source.get("subagent"), dict) else {}
    return source.get("other") == "guardian" or nested.get("other") == "guardian"


def read_codex(codex_home, project):
    """Main threads with their spawns linked to child rollouts; guardian threads listed apart."""
    real = os.path.realpath(str(project))

    def in_project(cwd):
        return isinstance(cwd, str) and (cwd == real or cwd.startswith(real + os.sep))

    threads = {}
    for path in sorted((Path(codex_home) / "sessions").glob("**/rollout-*.jsonl")):
        thread = _codex_thread(path, in_project)
        if thread:
            threads[thread["meta"].get("id")] = thread
    sessions = []
    for thread_id, thread in threads.items():
        source = thread["meta"].get("source")
        if _is_guardian(thread["meta"]) or (isinstance(source, dict) and source.get("subagent")):
            continue
        children = {}
        for child in threads.values():
            child_source = child["meta"].get("source")
            spawn = (child_source.get("subagent") or {}).get("thread_spawn") if isinstance(child_source, dict) else None
            if spawn and spawn.get("parent_thread_id") == thread_id:
                children.setdefault((spawn.get("agent_path") or "").rsplit("/", 1)[-1], []).append(child)
        dispatches, subagents = [], {}
        for ts, call_id, task_name in thread["spawns"]:
            dispatches.append((ts, call_id))
            queue = children.get(task_name or "", [])
            if queue:
                subagents[call_id] = queue.pop(0)["records"]
        guardian = [record for other in threads.values()
                    if _is_guardian(other["meta"])
                    and thread_id in (other["meta"].get("parent_thread_id"), other["meta"].get("session_id"))
                    for record in other["records"]]
        sessions.append({"id": "codex:" + str(thread_id), "messages": thread["records"],
                         "dispatches": dispatches, "subagents": subagents, "guardian": guardian,
                         "results": {}, "edits": thread["edits"]})
    return sessions


def _add(bucket, model, categories):
    slot = bucket.setdefault(model, {})
    for key, value in categories.items():
        slot[key] = slot.get(key, 0) + value


def build_report(project, module, claude_home=None, codex_home=None, now=None):
    windows = task_windows(project, module, now=now)
    sessions = (read_claude(claude_home, project) if claude_home else []) + \
        (read_codex(codex_home, project) if codex_home else [])
    tasks = []
    for window in windows["tasks"]:
        start, end = window["start"], window["end"]
        inside = lambda ts: start < ts <= end  # noqa: E731
        task = dict(window, main={}, sub={}, guardian={}, dispatches=0, dispatches_unrecorded=0, reclaims=0,
                    main_turns=0, sessions={})
        handbacks, edited = [], set()
        for session in sessions:
            used = 0
            for ts, model, categories in session["messages"]:
                if inside(ts):
                    _add(task["main"], model, categories)
                    used += _total(categories)
                    task["main_turns"] += _total(categories) > 0
            for ts, tool_id in session["dispatches"]:
                if not inside(ts):
                    continue
                result = session.get("results", {}).get(tool_id)
                if result and result[1] and HOOK_DENIAL in result[2]:
                    # Denied before the subagent existed: not a dispatch; a reclaim if tier-guard said so.
                    task["reclaims"] += RECLAIM_MARK in result[2]
                    continue
                task["dispatches"] += 1
                records = session["subagents"].get(tool_id)
                handback = result[0] if result else (records[-1][0] if records else None)
                if handback is not None:
                    handbacks.append(handback)
                if records is None:
                    task["dispatches_unrecorded"] += 1
                    continue
                for _ts, model, categories in records:
                    _add(task["sub"], model, categories)
                    used += _total(categories)
            for ts, model, categories in session.get("guardian", []):
                if inside(ts):
                    _add(task["guardian"], model, categories)
                    used += _total(categories)
            if used:
                task["sessions"][session["id"]] = used
        if handbacks:
            last = max(handbacks)
            todo = os.path.join("tasks", module, "todo.md")
            for session in sessions:
                edited.update(target for ts, target in session.get("edits", [])
                              if last < ts <= end and not target.replace("\\", "/").endswith(todo))
        task["redispatches"] = max(task["dispatches"] - 1, 0)
        task["edits_after_handback"] = len(edited)
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


def price_task(task, prices):
    """Equivalent money per role; tokens in a model or category without a price are listed, never guessed."""
    per = 1_000_000 if str(prices.get("per", "1M")).upper() == "1M" else float(prices.get("per"))
    table, cost = prices.get("models") or {}, {"main": 0.0, "sub": 0.0, "guardian": 0.0, "unpriced": []}
    for role in ("main", "sub", "guardian"):
        for model, categories in task[role].items():
            for category, tokens in categories.items():
                if category in INFO_ONLY or not tokens:
                    continue
                price = (table.get(model) or {}).get(category)
                if price is None:
                    label = "%s:%s" % (model, category)
                    if label not in cost["unpriced"]:
                        cost["unpriced"].append(label)
                    continue
                cost[role] += tokens * float(price) / per
    return cost


def _role_total(bucket, category=None):
    return sum((categories.get(category, 0) if category else _total(categories)) for categories in bucket.values())


def comparison(modules):
    groups = {"dispatched": {"tasks": 0, "tokens": 0, "cost": 0.0, "priced": True},
              "not_dispatched": {"tasks": 0, "tokens": 0, "cost": 0.0, "priced": True}}
    for module in modules:
        for task in module.get("tasks", []):
            group = groups["dispatched" if task["dispatches"] else "not_dispatched"]
            group["tasks"] += 1
            group["tokens"] += _role_total(task["main"]) + _role_total(task["sub"])
            if "cost" in task:
                group["cost"] += task["cost"]["main"] + task["cost"]["sub"]
                group["priced"] = group["priced"] and not task["cost"]["unpriced"]
            else:
                group["priced"] = False
    for group in groups.values():
        group["avg_tokens"] = group["tokens"] / group["tasks"] if group["tasks"] else None
        group["avg_cost"] = group["cost"] / group["tasks"] if group["tasks"] and group["priced"] else None
    groups["note"] = "不同模块与 task 的规模不同，这里只能看趋势；派活是否省钱的因果结论须来自受控对照实验。"
    return groups


def _fmt(number):
    return "{:,}".format(int(number))


def render(report, priced):
    lines = []
    for module in report["modules"]:
        if "unattributable" in module:
            lines.append("模块 %s：无法归属——%s" % (module["module"], module["unattributable"]))
            continue
        lines.append("模块 %s" % module["module"])
        header = "  %-28s %8s %14s %14s %14s %8s %4s %4s %6s" % (
            "task", "主会话轮次", "主代理 token", "主会话缓存读", "子代理 token", "派活", "重派", "收回", "交回后改")
        lines.append(header + ("   等价金额" if priced else ""))
        totals = {"turns": 0, "main": 0, "read": 0, "sub": 0, "disp": 0, "money": 0.0}
        for task in module["tasks"]:
            main, read, sub = _role_total(task["main"]), _role_total(task["main"], "cache_read"), _role_total(task["sub"])
            row = "  %-28s %8d %14s %14s %14s %8s %4d %4d %6d" % (
                task["title"][:28] + ("" if task["done"] else "（进行中）"), task["main_turns"], _fmt(main), _fmt(read),
                _fmt(sub), "%d(%s)" % (task["dispatches"], task["coverage"]), task["redispatches"], task["reclaims"],
                task["edits_after_handback"])
            if priced:
                money = task["cost"]["main"] + task["cost"]["sub"]
                totals["money"] += money
                row += "   %.4f%s" % (money, " *" if task["cost"]["unpriced"] else "")
            lines.append(row)
            for key, value in (("turns", task["main_turns"]), ("main", main), ("read", read), ("sub", sub),
                               ("disp", task["dispatches"])):
                totals[key] += value
        lines.append("  %-28s %8d %14s %14s %14s %8d" % ("合计", totals["turns"], _fmt(totals["main"]), _fmt(totals["read"]),
                                                        _fmt(totals["sub"]), totals["disp"]) +
                     ("            %.4f" % totals["money"] if priced else ""))
        sessions = {}
        for task in module["tasks"]:
            for name, used in task["sessions"].items():
                sessions[name] = sessions.get(name, 0) + used
        if sessions:
            lines.append("  贡献会话（时间窗内本项目的所有会话都会计入，含并行会话）：")
            lines.extend("    %s  %s token" % (name, _fmt(used)) for name, used in sorted(sessions.items()))
        else:
            lines.append("  没有找到会话数据：时间窗内本项目没有 Claude transcript 或 Codex rollout。")
        unknown = ["主代理通过 shell 命令（sed -i、脚本写文件等）改的文件不计入「交回后改」，只统计编辑工具与 apply_patch。"]
        unrecorded = sum(task["dispatches_unrecorded"] for task in module["tasks"])
        if unrecorded:
            unknown.append("%d 次派活宿主没有留下子代理记录，用量未知，未计入。" % unrecorded)
        unpriced = sorted({label for task in module["tasks"] for label in task.get("cost", {}).get("unpriced", [])})
        if unpriced:
            unknown.append("未定价（金额不含这部分，带 * 的行受影响）：" + "、".join(unpriced))
        lines.append("  无法统计的部分：")
        lines.extend("    - " + item for item in unknown)
    if "comparison" in report:
        lines.append("对照（%s）" % report["comparison"]["note"])
        for key, label in (("dispatched", "有派活的 task"), ("not_dispatched", "没有派活的 task")):
            group = report["comparison"][key]
            average = "-" if group["avg_tokens"] is None else _fmt(group["avg_tokens"])
            money = "" if group["avg_cost"] is None else "，平均等价金额 %.4f" % group["avg_cost"]
            lines.append("  %s：%d 个，平均 %s token%s" % (label, group["tasks"], average, money))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="只读的模块成本与返工报告")
    parser.add_argument("modules", nargs="+", metavar="MODULE")
    parser.add_argument("--project", default=".")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--prices", help="价格文件（JSON）；不给则只输出 token")
    parser.add_argument("--claude-home", default=str(Path.home() / ".claude"))
    parser.add_argument("--codex-home", default=str(Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")))
    args = parser.parse_args(argv)
    root = Path(args.project).resolve()
    now = parse_iso(os.environ["SPEC_GUARD_COST_REPORT_NOW"]) if os.environ.get("SPEC_GUARD_COST_REPORT_NOW") else None
    prices = None
    if args.prices:
        try:
            prices = json.loads(Path(args.prices).read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            print("价格文件无法读取：%s" % error, file=sys.stderr)
            return 2
    report, failed = {"modules": []}, False
    for module in args.modules:
        try:
            entry = build_report(root, module, claude_home=Path(args.claude_home), codex_home=Path(args.codex_home), now=now)
        except AttributionError as error:
            failed = True
            report["modules"].append({"module": module, "unattributable": str(error)})
            continue
        if prices is not None:
            for task in entry["tasks"]:
                task["cost"] = price_task(task, prices)
        report["modules"].append(entry)
    if len(args.modules) > 1:
        report["comparison"] = comparison(report["modules"])
    print(json.dumps(_jsonable(report), ensure_ascii=False, indent=2) if args.json else render(report, prices is not None))
    if failed:
        print("无法归属的模块不报告为 0；修正后重试。", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
