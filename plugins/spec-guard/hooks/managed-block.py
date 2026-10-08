#!/usr/bin/env python3
"""Validate and atomically edit an explicitly delimited managed block."""

from __future__ import print_function

import os
import sys
import tempfile


def fail(message):
    print("声明块无效：%s" % message, file=sys.stderr)
    raise SystemExit(1)


def locate(path, begin, end):
    try:
        with open(path, "r", encoding="utf-8", newline="") as handle:
            lines = handle.readlines()
    except OSError as error:
        fail("无法读取 %s：%s" % (path, error))
    begins = [index for index, line in enumerate(lines) if line.strip() == begin]
    ends = [index for index, line in enumerate(lines) if line.strip() == end]
    if len(begins) != 1 or len(ends) != 1:
        fail("BEGIN 和 END 必须各恰好出现一次（当前 %d/%d）" % (len(begins), len(ends)))
    if begins[0] >= ends[0]:
        fail("BEGIN 必须位于 END 之前")
    return lines, begins[0], ends[0]


LOCAL_BEGIN = "<!-- BEGIN:spec-guard-local -->"
LOCAL_END = "<!-- END:spec-guard-local -->"


def local_section(block):
    """(start, end) indexes of the one local section inside block lines, or None; malformed -> fail."""
    begins = [index for index, line in enumerate(block) if line.strip() == LOCAL_BEGIN]
    ends = [index for index, line in enumerate(block) if line.strip() == LOCAL_END]
    if not begins and not ends:
        return None
    if len(begins) != 1 or len(ends) != 1 or begins[0] >= ends[0]:
        fail("本地段标记 %s / %s 必须各恰好出现一次且 BEGIN 在前（当前 %d/%d）"
             % (LOCAL_BEGIN, LOCAL_END, len(begins), len(ends)))
    return begins[0], ends[0]


def _text(lines):
    return [line.rstrip("\r\n") for line in lines if line.strip()]


def atomic_write(path, content):
    directory = os.path.dirname(os.path.abspath(path)) or "."
    mode = os.stat(path).st_mode & 0o777
    descriptor, temporary = tempfile.mkstemp(prefix=".spec-guard-block-", dir=directory)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def main(argv):
    if len(argv) < 5:
        raise SystemExit("usage: managed-block.py <validate|replace|remove> <file> <begin> <end> [template [options]]")
    action, path, begin, end = argv[1:5]
    lines, start, finish = locate(path, begin, end)
    if action == "validate":
        print(finish - start + 1)
        return
    if action == "replace":
        # replace <file> <begin> <end> <body> [--known FILE]... [--accept-removals] [--dry-run]
        # convention-block-local-lines: the local section is carried over verbatim at the end of the new block;
        # removing any other line that is not in a --known template needs --accept-removals.
        rest = argv[6:]
        if len(argv) < 6:
            raise SystemExit("replace requires a template path")
        known, accept, dry = [], False, False
        while rest:
            option = rest.pop(0)
            if option == "--known" and rest:
                known.append(rest.pop(0))
            elif option == "--accept-removals":
                accept = True
            elif option == "--dry-run":
                dry = True
            else:
                raise SystemExit("unknown replace option: %s" % option)
        with open(argv[5], "r", encoding="utf-8", newline="") as handle:
            body = handle.readlines()
        if body and not body[-1].endswith(("\n", "\r")):
            body[-1] += "\n"
        block = lines[start + 1:finish]
        section = local_section(block)
        local = block[section[0]:section[1] + 1] if section else []
        current = block[:section[0]] + block[section[1] + 1:] if section else block
        if local and not local[-1].endswith(("\n", "\r")):
            local[-1] += "\n"
        new_text, old_text = _text(body), _text(current)
        removed = [line for line in old_text if line not in new_text]
        added = [line for line in new_text if line not in old_text]
        known_text = set()
        for name in known:
            with open(name, "r", encoding="utf-8", newline="") as handle:
                known_text.update(_text(handle.readlines()))
        needs_accept = [line for line in removed if line not in known_text]
        if dry:
            for line in removed:
                print("will remove: %s%s" % (line, "" if line in known_text else "   [needs --accept-removals]"))
            for line in added:
                print("will add: %s" % line)
            if not removed and not added:
                print("block content unchanged")
            if local:
                print("keeps the local section (%d lines)" % len(local))
            return
        if needs_accept and not accept:
            print("these lines are not in the template and would be removed; move them into the local section "
                  "(%s ... %s) or re-run with --accept-removals:" % (LOCAL_BEGIN, LOCAL_END), file=sys.stderr)
            for line in needs_accept:
                print("  - %s" % line, file=sys.stderr)
            raise SystemExit(3)
        atomic_write(path, "".join(lines[: start + 1] + body + local + lines[finish:]))
        print(finish - start - 1)
        return
    if action == "remove":
        if len(argv) != 5:
            raise SystemExit("remove does not accept a template")
        output = lines[:start] + lines[finish + 1:]
        # Retain the historical one-blank-line normalization, while rejecting
        # malformed input before touching any file.
        while len(output) > start > 0 and output[start - 1].strip() == "" and start < len(output) and output[start].strip() == "":
            del output[start]
        # setup appends a separating blank line before a block at the end of a file;
        # reclaim it so an install/remove round trip leaves the file byte-identical.
        if start == len(output) and start > 0 and output[start - 1].strip() == "":
            del output[start - 1]
        atomic_write(path, "".join(output))
        print(finish - start + 1)
        return
    raise SystemExit("unknown action: %s" % action)


if __name__ == "__main__":
    main(sys.argv)
