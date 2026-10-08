#!/usr/bin/env python3
"""Maintainer-only, read-only self-observation report (self-observation-report).

Reads the stage hints spec-guard injected, as the hosts recorded them in their own session
logs (Claude Code transcripts, Codex rollouts), and lists suspected problems.  It writes no
file, contacts nothing, and is not shipped with the plugin.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "plugins" / "spec-guard" / "hooks"))
from module_cost_report import parse_iso  # noqa: E402

HEADINGS = ("## spec-guard ", "## agent-skills 链路状态")
STAGE = re.compile(r"当前阶段: \*\*(.+?)\*\*")
SUGGESTION_PREFIXES = ("Suggested next step:", "建议下一步:")


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
    if not isinstance(text, str) or not text.lstrip().startswith(HEADINGS):
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
