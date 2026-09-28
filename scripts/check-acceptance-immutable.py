#!/usr/bin/env python3
"""Acceptance attestations are immutable: every one on the base ref must stay byte-identical.

Adding a new attestation is allowed; changing or deleting an existing one is not.
This guards against accidental rewrites. It cannot prove who wrote an attestation.

usage: check-acceptance-immutable.py [repo-root] [--base <ref>]   (default base: origin/main)
"""
from pathlib import Path
import subprocess
import sys

DIRECTORY = "spec/proposal-acceptances"


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True)


def main(argv) -> int:
    base = "origin/main"
    if "--base" in argv:
        index = argv.index("--base")
        base = argv[index + 1]
        argv = argv[:index] + argv[index + 2:]
    root = Path(argv[0]).resolve() if argv else Path(__file__).resolve().parents[1]
    if git(root, "rev-parse", "--verify", "--quiet", base + "^{commit}").returncode != 0:
        print("  ⏭  没有 %s，未检查验收记录（不代表通过）" % base)
        return 0
    listed = git(root, "ls-tree", "-r", "--name-only", base, "--", DIRECTORY)
    if listed.returncode != 0:
        print("  ❌ 无法读取 %s 上的 %s" % (base, DIRECTORY))
        return 1
    paths = [line for line in listed.stdout.decode("utf-8").splitlines() if line]
    changed = []
    for path in paths:
        committed = git(root, "show", "%s:%s" % (base, path)).stdout
        current = root / path
        if not current.is_file() or current.read_bytes() != committed:
            changed.append(path)
    for path in changed:
        print("  ❌ 验收记录被改写或删除：%s（已有记录只能新增，不能修改）" % path)
    if not changed:
        print("  ✅ %d 份已有验收记录与 %s 一致" % (len(paths), base))
    return 1 if changed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
