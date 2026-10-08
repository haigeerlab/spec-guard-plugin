#!/usr/bin/env python3
"""Reject a second implementation of the capability-map fingerprint.

`plugins/spec-guard/hooks/spec-digest.py` is the only fingerprint algorithm (CLAUDE.md invariant); other
modules load it with importlib. Until 2026-10-08 (audit F13) only convention kept it that way.

Rule, deliberately literal: a non-test Python file under `plugins/spec-guard/hooks/` or `scripts/`, other than
spec-digest.py, fails when it uses `hashlib` together with either the parsed row text the fingerprint hashes
(`normalized_row`) or a truncated hex digest (`hexdigest()[:`), which is how the fingerprint is shaped. Whole-file
hashes and idempotency keys use full digests and pass. Zero Python files is "not found", not "clean"
(docs/lenses.md A5).

Usage: check-digest-single-source.py [repo-root]
"""
import pathlib
import re
import sys

TRUNCATED = re.compile(r"hexdigest\(\)\s*\[\s*:")
OWNER = "spec-digest.py"


def is_test(path):
    return path.name.startswith(("test_", "test-"))


def main():
    root = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parents[1]
    files = []
    for folder in (root / "plugins/spec-guard/hooks", root / "scripts"):
        if folder.is_dir():
            files.extend(sorted(folder.glob("*.py")))
    if not files:
        print("  ❌ 0 个 Python 文件 —— 这是没找到，不是没问题", file=sys.stderr)
        return 1
    bad = []
    for path in files:
        if path.name == OWNER or is_test(path) or path.resolve() == pathlib.Path(__file__).resolve():
            continue
        text = path.read_text(encoding="utf-8")
        if "hashlib" not in text:
            continue
        if "normalized_row" in text or TRUNCATED.search(text):
            bad.append(path.relative_to(root))
    for rel in bad:
        print(f"  ❌ {rel} 像是在复制能力图指纹算法：请改为加载 hooks/{OWNER}")
    if bad:
        return 1
    print(f"  ✅ {len(files)} 个 Python 文件，指纹算法只在 hooks/{OWNER}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
