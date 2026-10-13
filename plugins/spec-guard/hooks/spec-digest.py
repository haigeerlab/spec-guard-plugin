#!/usr/bin/env python3
"""Stable capability-map digests for read-only Proposal validation, and the text digest of one file.

Usage:
  spec-digest.py compute <map>
  spec-digest.py text <file>
  spec-digest.py --selftest

The script only parses a capability map and emits deterministic JSON.  A map
that cannot be read or parsed is an error (exit 1, reason on stderr), never an
empty digest.  It does
not read workflow state, contact a tracker, or compare a map with a projection.
"""
import hashlib
import json
import sys

from capability_map import parse_map as parse_capability_map

DIGEST_LEN = 12


def _h(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:DIGEST_LEN]


def parse_map(path):
    parsed = parse_capability_map(path, validate_graph=False)
    rows = [(row.module_id, row.normalized_row) for row in parsed.rows]
    return rows, parsed.goal


def compute(path):
    rows, goal = parse_map(path)
    return {
        "rows": [{"id": module_id, "rowDigest": _h(text)} for module_id, text in rows],
        "order": [module_id for module_id, _ in rows],
        "goalDigest": _h(goal) if goal is not None else None,
        "placeholder": any(module_id.startswith("example-") for module_id, _ in rows),
    }


def text_digest(text):
    """Digest of a text as given: the caller decides which lines belong to it."""
    return _h(text)


def _selftest():
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "CAPABILITY-MAP.md")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("## 目标\n\n测试\n\n| Module id | Responsibility | Depends on |\n|---|---|---|\n| alpha | x | — |\n")
        result = compute(path)
        if result["order"] != ["alpha"] or not result["goalDigest"] or result["placeholder"]:
            print("spec-digest self-test failed")
            return 1
        import subprocess
        missing = subprocess.run([sys.executable, __file__, "compute", os.path.join(directory, "absent.md")],
                                 capture_output=True, text=True)
        if missing.returncode != 1 or missing.stdout or "cannot digest" not in missing.stderr:
            print("spec-digest self-test failed: an unreadable map must exit 1 without JSON")
            return 1
        text_path = os.path.join(directory, "spec.md")
        with open(text_path, "w", encoding="utf-8") as handle:
            handle.write("# Spec\n\n正文\n")
        first = text_digest("# Spec\n\n正文\n")
        if (len(first) != DIGEST_LEN or first != text_digest("# Spec\n\n正文\n")
                or first == text_digest("# Spec\n\n正文。\n")):
            print("spec-digest self-test failed: text digest must be stable, fixed-length and content-sensitive")
            return 1
        shown = subprocess.run([sys.executable, __file__, "text", text_path], capture_output=True, text=True)
        if shown.returncode != 0 or shown.stdout.strip() != first:
            print("spec-digest self-test failed: `text <file>` must print the digest of the file's text")
            return 1
        absent = subprocess.run([sys.executable, __file__, "text", os.path.join(directory, "absent.md")],
                                capture_output=True, text=True)
        if absent.returncode != 1 or absent.stdout or "cannot digest" not in absent.stderr:
            print("spec-digest self-test failed: an unreadable text file must exit 1 without output")
            return 1
    print("spec-digest self-test passed")
    return 0


def main():
    argv = sys.argv[1:]
    if argv == ["--selftest"]:
        return _selftest()
    if len(argv) == 2 and argv[0] == "compute":
        try:
            print(json.dumps(compute(argv[1]), ensure_ascii=False))
            return 0
        except Exception as error:
            print("spec-digest: cannot digest %s: %s" % (argv[1], error), file=sys.stderr)
            return 1
    if len(argv) == 2 and argv[0] == "text":
        try:
            with open(argv[1], encoding="utf-8") as handle:
                print(text_digest(handle.read()))
            return 0
        except (OSError, UnicodeError) as error:
            print("spec-digest: cannot digest %s: %s" % (argv[1], error), file=sys.stderr)
            return 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
