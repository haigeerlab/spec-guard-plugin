#!/usr/bin/env python3
"""Read-only session facts for the phase hint: the main-session context size.

Only the last usage numbers are read; no transcript content ever leaves this module.
Anything unreadable is "unknown" (None), never a guess.
"""
from __future__ import annotations

import json
import os
import select
import sys
import time

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
    print("" if tokens is None else tokens)
    print("")


if __name__ == "__main__":
    main()
