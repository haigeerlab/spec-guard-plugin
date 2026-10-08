#!/usr/bin/env python3
"""Maintainer-only, read-only self-observation report (self-observation-report).

Reads the stage hints spec-guard injected, as the hosts recorded them in their own session
logs (Claude Code transcripts, Codex rollouts), and lists suspected problems.  It writes no
file, contacts nothing, and is not shipped with the plugin.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "plugins" / "spec-guard" / "hooks"))
from module_cost_report import parse_iso  # noqa: E402

HEADINGS = ("## spec-guard ", "## agent-skills 链路状态")
STAGE = re.compile(r"当前阶段: \*\*(.+?)\*\*")
SUGGESTION_PREFIXES = ("Suggested next step:", "建议下一步:")
# phase-guard's own fallback sentences when python3 is missing or cannot run (no heading).
PYTHON3_PREFIX = "spec-guard: "
PYTHON3_STAGE = "python3 故障"
DIAGNOSTIC_STAGES = {"UNKNOWN", "MAP_INVALID", "?", PYTHON3_STAGE}
EXAMPLES = 3
# Fixtures and throwaway checkouts live here; their injections say nothing about real use.
TEMP_PREFIXES = ("/private/tmp/", "/private/var/folders/", "/tmp/", "/var/folders/")
MIN_SPAN = timedelta(hours=24)
UNOBSERVABLE = (
    "hook 进程失败：两个宿主都不记录 hook 崩溃或无输出，看不到就不报，不等于没有。",
    "插件版本：注入文本不含版本号，只报首次与末次出现时间。",
)


def _numbered_rows(path):
    """(line number, row) for every JSON object line; other lines still advance the count."""
    try:
        handle = path.open(encoding="utf-8", errors="replace")
    except OSError:
        return
    with handle:
        for number, line in enumerate(handle, 1):
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, dict):
                yield number, row


def _segment(text):
    """(stage, suggestion) when text is a spec-guard injection, else None."""
    if not isinstance(text, str):
        return None
    if text.lstrip().startswith(PYTHON3_PREFIX) and "python3" in text:
        return PYTHON3_STAGE, ""
    if not text.lstrip().startswith(HEADINGS):
        return None
    match = STAGE.search(text)
    suggestion = next((line.strip() for line in text.splitlines()
                       if line.strip().startswith(SUGGESTION_PREFIXES)), "")
    return (match.group(1).strip() if match else "?"), suggestion


def _event(host, when, project, session, line, parsed):
    stage, suggestion = parsed
    return {"time": when, "host": host, "project": os.path.realpath(project) if project else "?",
            "session": session or "?", "line": line, "stage": stage, "suggestion": suggestion}


def _when(text, since, counter):
    """Parsed time if at or after since; None otherwise.  Unparseable times are counted."""
    try:
        moment = parse_iso(text)
    except (AttributeError, TypeError, ValueError):
        counter[0] += 1
        return None
    return moment if moment >= since else None


def read_claude(claude_home, since):
    events, unparsed = [], [0]
    for path in sorted(Path(claude_home).glob("projects/*/*.jsonl")):
        for number, row in _numbered_rows(path):
            attachment = row.get("attachment")
            if row.get("type") != "attachment" or not isinstance(attachment, dict) \
                    or attachment.get("type") != "hook_additional_context":
                continue
            contents = attachment.get("content")
            segments = [s for s in map(_segment, contents if isinstance(contents, list) else [contents]) if s]
            if not segments:
                continue
            when = _when(row.get("timestamp"), since, unparsed)
            if when is None:
                continue
            events += [_event("claude", when, row.get("cwd"), row.get("sessionId"), number, s) for s in segments]
    return events, unparsed[0]


def read_codex(codex_home, since):
    events, unparsed = [], [0]
    for path in sorted(Path(codex_home).glob("sessions/*/*/*/*.jsonl")):
        project = thread = None
        for number, row in _numbered_rows(path):
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            if row.get("type") == "session_meta":
                source = payload.get("source")
                if isinstance(source, dict) and "subagent" in source:
                    break
                project, thread = payload.get("cwd"), payload.get("id")
                continue
            if row.get("type") != "response_item" or payload.get("role") != "developer":
                continue
            content = payload.get("content")
            segments = [s for s in (_segment(item.get("text")) for item in content if isinstance(item, dict))
                        if s] if isinstance(content, list) else []
            if not segments:
                continue
            when = _when(row.get("timestamp"), since, unparsed)
            if when is None:
                continue
            events += [_event("codex", when, project, thread, number, s) for s in segments]
    return events, unparsed[0]


def is_temp(project):
    return project.startswith(TEMP_PREFIXES)


def normalise(text):
    return re.sub(r"\d+", "<n>", re.sub(r"`[^`]*`", "<id>", text))


def _short_id(text):
    """Four hex digits from CRC-32: a display id, not the capability-map fingerprint (hooks/spec-digest.py)."""
    return "%04x" % (zlib.crc32(text.encode("utf-8")) & 0xFFFF)


def project_hash(project):
    return _short_id(project)


def _fingerprint(signal, stage, suggestion):
    return "F-" + _short_id("%s|%s|%s" % (signal, stage, suggestion))


def _s1_runs(events, min_repeat):
    """Runs of unchanged (stage, suggestion) per project, long enough and at least MIN_SPAN from first to last."""
    by_project = {}
    for item in events:
        if item["stage"] not in DIAGNOSTIC_STAGES:
            by_project.setdefault(item["project"], []).append(item)
    for items in by_project.values():
        items.sort(key=lambda e: (e["time"], e["line"]))
        run = []
        for item in items + [None]:
            # Raw text, not normalised: a falling count or a new module id is progress, not repetition.
            key = None if item is None else (item["stage"], item["suggestion"])
            if run and key != (run[0]["stage"], run[0]["suggestion"]):
                if len(run) >= min_repeat and run[-1]["time"] - run[0]["time"] >= MIN_SPAN:
                    yield run
                run = []
            if item is not None:
                run.append(item)


def findings(events, min_repeat=20):
    groups = {}

    def add(signal, items):
        for item in items:
            suggestion = normalise(item["suggestion"])
            key = _fingerprint(signal, item["stage"], suggestion)
            groups.setdefault(key, {"fingerprint": key, "signal": signal, "stage": item["stage"],
                                    "suggestion": suggestion, "items": []})["items"].append(item)

    add("S2", [e for e in events if e["stage"] in DIAGNOSTIC_STAGES])
    for run in _s1_runs(events, min_repeat):
        add("S1", run)
    out = []
    for group in groups.values():
        items = sorted(group.pop("items"), key=lambda e: (e["time"], e["line"]))
        group.update({
            "count": len(items),
            "sessions": len({e["session"] for e in items}),
            "projects": sorted({project_hash(e["project"]) for e in items}),
            "first": items[0]["time"], "last": items[-1]["time"],
            "examples": [{"project": project_hash(e["project"]), "session": e["session"][:6], "line": e["line"],
                          "host": e["host"]} for e in items[:EXAMPLES]],
        })
        out.append(group)
    return sorted(out, key=lambda f: (-f["count"], f["fingerprint"]))


def _iso(moment):
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _since(text):
    match = re.fullmatch(r"(\d+)d", text)
    if not match:
        raise argparse.ArgumentTypeError("--since 需要形如 14d 的天数")
    return datetime.now(timezone.utc) - timedelta(days=int(match.group(1)))


SIGNAL_NAMES = {"S1": "重复未变", "S2": "诊断态"}


def render(found, scanned, unparsed, reveal, excluded=0):
    lines = ["spec-guard 自观测报告（只读；扫描到 %d 段注入，无法解析 %d 行；已排除临时目录中的 %d 段）"
             % (scanned, unparsed, excluded), ""]
    if not found:
        lines.append("没有发现疑似问题。")
    for item in found:
        lines.append("[%s] %s %s  阶段 %s：%d 次 / %d 个会话 / %d 个项目" % (
            item["fingerprint"], item["signal"], SIGNAL_NAMES[item["signal"]], item["stage"],
            item["count"], item["sessions"], len(item["projects"])))
        if item["suggestion"]:
            lines.append("       建议行: %s" % item["suggestion"])
        lines.append("       %s → %s；项目 %s" % (_iso(item["first"]), _iso(item["last"]),
                                               ", ".join("project#" + p for p in item["projects"])))
        for ex in item["examples"]:
            lines.append("       例: %s project#%s 会话 %s 第 %d 行" % (ex["host"], ex["project"], ex["session"], ex["line"]))
    lines += ["", "无法观测:"] + ["- " + text for text in UNOBSERVABLE]
    if reveal:
        lines += ["", "项目对照（--reveal，仅限本机）:"] + ["- project#%s  %s" % (h, p) for h, p in sorted(reveal.items())]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="spec-guard maintainer self-observation report (read-only)")
    parser.add_argument("--since", type=_since, default="14d")
    parser.add_argument("--min-repeat", type=int, default=20)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--reveal", action="store_true")
    parser.add_argument("--claude-home", default=str(Path.home() / ".claude"))
    parser.add_argument("--codex-home", default=str(Path.home() / ".codex"))
    args = parser.parse_args(argv)
    claude, claude_bad = read_claude(Path(args.claude_home), args.since)
    codex, codex_bad = read_codex(Path(args.codex_home), args.since)
    events = [e for e in claude + codex if not is_temp(e["project"])]
    excluded = len(claude) + len(codex) - len(events)
    found = findings(events, args.min_repeat)
    reveal = {project_hash(e["project"]): e["project"] for e in events} if args.reveal else {}
    if args.json:
        data = {"scanned": len(events), "unparsed": claude_bad + codex_bad, "excluded_temp": excluded,
                "unobservable": list(UNOBSERVABLE),
                "findings": [dict(f, first=_iso(f["first"]), last=_iso(f["last"])) for f in found]}
        if reveal:
            data["reveal"] = reveal
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(render(found, len(events), claude_bad + codex_bad, reveal, excluded))
    return 0


if __name__ == "__main__":
    sys.exit(main())
