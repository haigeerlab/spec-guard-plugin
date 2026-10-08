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


def _compacted(record) -> int | None:
    """Context size right after a compaction record, 0 when it records none; None if the record is not one.

    context-after-compact: Claude's compact_boundary carries postTokens; Codex's compacted record carries no size
    and is followed by a zero token_count, so it counts as below every threshold.
    """
    if not isinstance(record, dict):
        return None
    if record.get("type") == "system" and record.get("subtype") == "compact_boundary":
        meta = record.get("compactMetadata")
        post = _count(meta.get("postTokens")) if isinstance(meta, dict) else None
        return post if post is not None else 0
    if record.get("type") == "compacted":
        return 0
    return None


def _window(record) -> int | None:
    """Codex's model context window on a token_count record; Claude records carry none."""
    payload = record.get("payload") if isinstance(record, dict) else None
    info = payload.get("info") if isinstance(payload, dict) else None
    window = info.get("model_context_window") if isinstance(info, dict) else None
    return window if isinstance(window, int) and not isinstance(window, bool) and window > 0 else None


def context_tokens(transcript_path) -> int | None:
    """Context size of the last main-session turn, read from the last TAIL_LIMIT bytes."""
    usage = context_usage(transcript_path)
    return usage[0] if usage else None


def context_usage(transcript_path) -> tuple | None:
    """(context size, model context window or None) of the last main-session turn, from one record."""
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
        if tokens:  # zero is a synthetic record (e.g. after an interruption), not a reading
            return tokens, _window(record)
        compacted = _compacted(record)
        if compacted is not None:  # newer than any reading: the pre-compaction size no longer applies
            return compacted, None
    return None


def unattended(transcript_path) -> bool:
    """True only when the host says nobody attends this run (unattended-run-hint).

    Claude Code sets CLAUDE_CODE_SESSION_ATTENDED=0 for `claude -p` (measured 2026-10-08, undocumented); a Codex
    `codex exec` rollout starts with a session_meta record whose source is "exec". Anything else, including an
    unreadable transcript, counts as attended, so an interactive session never loses its hints.
    """
    if os.environ.get("CLAUDE_CODE_SESSION_ATTENDED") == "0":
        return True
    if not isinstance(transcript_path, str) or not transcript_path:
        return False
    try:
        with open(transcript_path, "rb") as handle:
            first = handle.readline(65536)
        record = json.loads(first)
    except (OSError, ValueError):
        return False
    payload = record.get("payload") if isinstance(record, dict) and record.get("type") == "session_meta" else None
    return isinstance(payload, dict) and payload.get("source") == "exec"


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


def main() -> None:
    if len(sys.argv) > 2 and sys.argv[1] == "--resolve-root":
        resolve_root_main(sys.argv[2])
        return
    try:
        path = transcript_path_from_hook_input(read_hook_input(sys.stdin.fileno()))
    except Exception:  # a hook helper must never break the stage injection
        path = None
    try:
        usage = context_usage(path)
    except Exception:
        usage = None
    try:
        nobody = unattended(path)
    except Exception:
        nobody = False
    tokens, window = usage if usage else (None, None)
    try:
        location = location_line(sys.argv[1] if len(sys.argv) > 1 else ".")
    except Exception:
        location = None
    print("" if tokens is None else tokens)
    print(location or "")
    print("" if window is None else window)
    print("unattended" if nobody else "")


if __name__ == "__main__":
    main()
