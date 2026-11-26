#!/usr/bin/env python3
"""Read-only session facts for the phase hint: the location, the host and the state code of the last injection.

Only those three facts leave this module; no other transcript content does.
Anything unreadable is "unknown" (None), never a guess.
"""
from __future__ import annotations

import json
import os
import re
import select
import subprocess
import sys
import time

from module_stage import safe_fragment

TAIL_LIMIT = 4 * 1024 * 1024
INPUT_LIMIT = 1024 * 1024
INPUT_WAIT = 1.0


def _is_compaction(record) -> bool:
    """True when `record` is a host's compaction record: Claude's compact_boundary or Codex's compacted."""
    if not isinstance(record, dict):
        return False
    return ((record.get("type") == "system" and record.get("subtype") == "compact_boundary")
            or record.get("type") == "compacted")


def tail_lines(transcript_path) -> list | None:
    """The whole lines in the last TAIL_LIMIT bytes of the transcript, or None when it cannot be read."""
    if not isinstance(transcript_path, str) or not transcript_path:
        return None
    try:
        with open(transcript_path, "rb") as handle:
            size = os.fstat(handle.fileno()).st_size
            start = max(0, size - TAIL_LIMIT)
            handle.seek(start)
            tail = handle.read(TAIL_LIMIT)
    except OSError:
        return None
    lines = tail.split(b"\n")
    return lines[1:] if start > 0 else lines  # the first line was cut by the window


def _records(lines):
    """The JSON records among `lines`, newest first."""
    for line in reversed(lines):
        try:
            yield json.loads(line)
        except ValueError:
            continue


# quiet-injection (D5): the state code of the last spec-guard injection, so the hook can give one line when nothing
# changed.  Only what a host recorded as injected context counts -- Claude's hook_additional_context attachment and
# Codex's developer message -- never user or assistant text, where an agent may have quoted a code.  Only the code
# leaves this module.
_STATE = re.compile(r"<!-- spec-guard-state: ([0-9a-f]{8}) -->")
_OURS = re.compile(r"(?m)^(## spec-guard local workflow|spec-guard: )")


def _injected(record) -> list:
    """The texts `record` holds as hook-injected context, newest last; [] for any other record."""
    if not isinstance(record, dict):
        return []
    if record.get("type") == "attachment":
        attachment = record.get("attachment")
        if isinstance(attachment, dict) and attachment.get("type") == "hook_additional_context":
            content = attachment.get("content")
            return [text for text in (content if isinstance(content, list) else [content]) if isinstance(text, str)]
    payload = record.get("payload") if record.get("type") == "response_item" else None
    if isinstance(payload, dict) and payload.get("type") == "message" and payload.get("role") == "developer":
        content = payload.get("content")
        return [item.get("text") for item in (content if isinstance(content, list) else [])
                if isinstance(item, dict) and item.get("type") == "input_text" and isinstance(item.get("text"), str)]
    return []


def last_state(lines) -> str | None:
    """State code of the newest spec-guard injection in the tail; None when a compaction is newer or none is found.

    An injection without a code (a diagnostic) also gives None, so the next turn is full again.
    """
    for record in _records(lines or []):
        if _is_compaction(record):
            return None
        for text in reversed(_injected(record)):
            if _OURS.search(text):
                found = _STATE.findall(text)
                return found[-1] if found else None
    return None


# A Codex rollout's first record carries the whole base instructions (19-24 KB measured on 2026-10-08); the read
# stays bounded but leaves ample room.
FIRST_RECORD_LIMIT = 1 << 20


def _first_record(transcript_path):
    """The transcript's first record, or None when it is missing, cut off or not JSON."""
    if not isinstance(transcript_path, str) or not transcript_path:
        return None
    try:
        with open(transcript_path, "rb") as handle:
            first = handle.readline(FIRST_RECORD_LIMIT)
        if not first.endswith(b"\n"):  # cut off at the limit (or no line end at all): not a whole record
            return None
        return json.loads(first)
    except (OSError, ValueError):
        return None


def host_from_hook_input(text, transcript_path) -> str | None:
    """"codex" when the hook input itself says so (codex-command-wording), else None.

    Codex's UserPromptSubmit input carries its own `turn_id` extension (codex-rs/hooks/src/schema.rs) and a Codex
    rollout starts with a session_meta record; Claude Code's input has neither (measured 2026-10-09). The input
    never proves Claude, so phase-guard.sh decides the rest from the environment.
    """
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        data = None
    if isinstance(data, dict) and "turn_id" in data:
        return "codex"
    record = _first_record(transcript_path)
    if isinstance(record, dict) and record.get("type") == "session_meta":
        return "codex"
    return None


def transcript_path_from_hook_input(text) -> str | None:
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        return None
    path = data.get("transcript_path") if isinstance(data, dict) else None
    return path if isinstance(path, str) and path else None


def _git(root, *args) -> str | None:
    try:
        done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 and done.stdout.strip() else None


def root_from_hook_input(text, fallback: str) -> str:
    """Git root of the hook input's `cwd`, else `fallback`.

    A desktop worktree session can hand the hook a project directory that is the main checkout while the
    conversation runs in a linked worktree; the input's `cwd` is where the session actually is.
    """
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        return fallback
    cwd = data.get("cwd") if isinstance(data, dict) else None
    if not isinstance(cwd, str) or not cwd or not os.path.isdir(cwd):
        return fallback
    return _git(cwd, "rev-parse", "--show-toplevel") or fallback


def location_line(root, lang: str | None = None) -> str | None:
    """Branch (or detached commit) and worktree root of `root`, or None outside a git worktree.

    hint-language-follow: `lang` "zh-CN" gives the Chinese line; anything else the English one.
    """
    zh = lang == "zh-CN"
    top = _git(root, "rev-parse", "--show-toplevel")
    if not top:
        return None
    branch = _git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    if branch:
        head = ("分支 `%s`" if zh else "branch `%s`") % safe_fragment(branch)
    else:
        sha = _git(root, "rev-parse", "--short", "HEAD")
        if not sha:
            return None
        head = ("分离于 `%s`" if zh else "detached at `%s`") % safe_fragment(sha)
    if zh:
        return "位置: %s · worktree `%s`。请用户审阅或确认时，向用户说明这个位置。" % (head, safe_fragment(top))
    return ("Location: %s · worktree `%s`. State this location to the user whenever you ask them "
            "to review or confirm." % (head, safe_fragment(top)))


def read_hook_input(fd: int) -> str:
    """Hook input from fd, waiting at most INPUT_WAIT seconds; "" if it is over INPUT_LIMIT."""
    deadline = time.monotonic() + INPUT_WAIT
    chunks, size = [], 0
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([fd], [], [], remaining)[0]:
            return ""  # the caller never closed stdin: treat the input as unavailable
        chunk = os.read(fd, 65536)
        if not chunk:
            return b"".join(chunks).decode("utf-8", "replace")
        size += len(chunk)
        if size > INPUT_LIMIT:
            return ""
        chunks.append(chunk)


def resolve_root_main(fallback: str) -> None:
    """`--resolve-root <fallback>`: the project root, then the hook input as one JSON line (empty if unusable)."""
    try:
        text = read_hook_input(sys.stdin.fileno())
        data = json.loads(text)
        line = json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else ""
    except Exception:
        text, line = "", ""
    try:
        root = root_from_hook_input(text, fallback) if line else fallback
    except Exception:
        root = fallback
    print(root)
    print(line)


# receipt-hint-on-message: Claude Code delivers a message from another session as a prompt wrapped in
# <cross-session-message from-session="local_..." from-name="...">. Only the wrapper's two attributes are read.
_RECEIVED_TAG = re.compile(r"<cross-session-message\s[^>]*>")
_RECEIVED_SESSION = re.compile(r"^local_[A-Za-z0-9-]+$")


def received_from(text) -> tuple | None:
    """(sender name, session id) when the hook input's prompt is a forwarded session message, else None."""
    data = json.loads(text)
    prompt = data.get("prompt") if isinstance(data, dict) else None
    if not isinstance(prompt, str):
        return None
    prompt = prompt.lstrip()
    match = _RECEIVED_TAG.match(prompt) if prompt.startswith("<cross-session-message ") else None
    if not match:
        return None
    attributes = dict(re.findall(r'([a-z-]+)="([^"]*)"', match.group(0)))
    session = attributes.get("from-session", "")
    return (safe_fragment(attributes.get("from-name", ""), 79),
            session if _RECEIVED_SESSION.match(session) else "")


def main() -> None:
    if len(sys.argv) > 2 and sys.argv[1] == "--resolve-root":
        resolve_root_main(sys.argv[2])
        return
    if len(sys.argv) > 1 and sys.argv[1] == "--received":
        try:
            found = received_from(read_hook_input(sys.stdin.fileno()))
        except Exception:
            found = None
        if found:
            print("received\t%s\t%s" % found)
        return
    try:
        text = read_hook_input(sys.stdin.fileno())
        path = transcript_path_from_hook_input(text)
    except Exception:  # a hook helper must never break the stage injection
        text, path = "", None
    try:
        last = last_state(tail_lines(path))
    except Exception:
        last = None
    try:
        lang = sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == "--lang" else None
        location = location_line(sys.argv[1] if len(sys.argv) > 1 else ".", lang)
    except Exception:
        location = None
    try:
        host = host_from_hook_input(text, path)
    except Exception:
        host = None
    print(location or "")
    print(host or "")
    print(last or "")


if __name__ == "__main__":
    main()
