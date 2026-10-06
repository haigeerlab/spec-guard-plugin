#!/usr/bin/env python3
"""Read-only session facts for the phase hint: the main-session context size and location.

Only the last usage numbers are read; no transcript content ever leaves this module.
Anything unreadable is "unknown" (None), never a guess.
"""
from __future__ import annotations

import json
import os
import select
import subprocess
import sys
import time

from module_stage import safe_fragment

TAIL_LIMIT = 4 * 1024 * 1024
INPUT_LIMIT = 1024 * 1024
INPUT_WAIT = 1.0


def _count(value) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _usage(record) -> int | None:
    """Context size carried by one transcript record, or None if it carries none."""
    if not isinstance(record, dict):
        return None
    if record.get("type") == "assistant" and record.get("isSidechain") is not True:
        message = record.get("message")
        usage = message.get("usage") if isinstance(message, dict) else None
        if not isinstance(usage, dict):
            return None
        parts = [_count(usage.get(key)) for key in
                 ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")]
        return None if None in parts else sum(parts)
    payload = record.get("payload")
    if isinstance(payload, dict) and payload.get("type") == "token_count":
        info = payload.get("info")
        last = info.get("last_token_usage") if isinstance(info, dict) else None
        # Codex input_tokens already includes the cached part.
        return _count(last.get("input_tokens")) if isinstance(last, dict) else None
    return None


def context_tokens(transcript_path) -> int | None:
    """Context size of the last main-session turn, read from the last TAIL_LIMIT bytes."""
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
    if start > 0:
        lines = lines[1:]  # the first line was cut by the window
    for line in reversed(lines):
        try:
            record = json.loads(line)
        except ValueError:
            continue
        tokens = _usage(record)
        if tokens is not None:
            return tokens
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


def location_line(root) -> str | None:
    """Branch (or detached commit) and worktree root of `root`, or None outside a git worktree."""
    top = _git(root, "rev-parse", "--show-toplevel")
    if not top:
        return None
    branch = _git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    if branch:
        head = "branch `%s`" % safe_fragment(branch)
    else:
        sha = _git(root, "rev-parse", "--short", "HEAD")
        if not sha:
            return None
        head = "detached at `%s`" % safe_fragment(sha)
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


def main() -> None:
    try:
        tokens = context_tokens(transcript_path_from_hook_input(read_hook_input(sys.stdin.fileno())))
    except Exception:  # a hook helper must never break the stage injection
        tokens = None
    try:
        location = location_line(sys.argv[1] if len(sys.argv) > 1 else ".")
    except Exception:
        location = None
    print("" if tokens is None else tokens)
    print(location or "")


if __name__ == "__main__":
    main()
