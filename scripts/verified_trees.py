#!/usr/bin/env python3
"""Record trees that passed verify-and-commit, and let pre-push skip pushes made only of recorded trees.

    verified_trees.py tier            staged paths on stdin -> prints "quick" or "full"
    verified_trees.py record TIER     append HEAD's tree with TIER (skipped while untracked files exist)
    verified_trees.py check           pre-push ref lines on stdin -> exit 0 when every pushed commit is covered

Records live in the git common dir, shared by every worktree: <common-dir>/spec-guard/verified-trees,
one "<tree> <full|quick>" per line. Anything unexpected -> not covered, so pre-push runs the full checks.
"""
from __future__ import print_function

import os
import subprocess
import sys

ZERO = set("0")
QUICK_DIRS = ("spec/", "tasks/", "docs/")
NOT_QUICK_DIRS = ("plugins/", ".github/")


def git(*args):
    return subprocess.run(["git"] + list(args), capture_output=True, text=True)


def is_quick_path(path):
    """Docs-only paths: spec/, tasks/, docs/, and *.md outside plugins/ and .github/. Anything else is full."""
    if path.startswith(QUICK_DIRS):
        return True
    return path.endswith(".md") and not path.startswith(NOT_QUICK_DIRS)


def record_file():
    out = git("rev-parse", "--git-common-dir")
    if out.returncode != 0:
        return None
    return os.path.join(os.path.abspath(out.stdout.strip()), "spec-guard", "verified-trees")


def load_records():
    path = record_file()
    records = {}
    if not path or not os.path.isfile(path):
        return records
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            parts = line.split()
            if len(parts) == 2 and parts[1] in ("full", "quick"):
                # a full record outranks a quick one for the same tree
                if records.get(parts[0]) != "full":
                    records[parts[0]] = parts[1]
    return records


def cmd_tier():
    paths = [line.strip() for line in sys.stdin if line.strip()]
    print("quick" if paths and all(is_quick_path(p) for p in paths) else "full")
    return 0


def cmd_record(tier):
    if tier not in ("full", "quick"):
        print("record: tier must be full or quick", file=sys.stderr)
        return 2
    untracked = git("ls-files", "--others", "--exclude-standard").stdout.split("\n")
    untracked = [u for u in untracked if u]
    if untracked:
        print("  ℹ  未写入检查记录：工作区有未跟踪文件，检查看到的内容可能和提交不同；推送时会照常全跑：")
        for name in untracked[:10]:
            print("     " + name)
        return 0
    tree = git("rev-parse", "HEAD^{tree}")
    path = record_file()
    if tree.returncode != 0 or not path:
        print("  ⚠️  未写入检查记录：读不到 HEAD 的 tree 或 git 目录", file=sys.stderr)
        return 0
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("%s %s\n" % (tree.stdout.strip(), tier))
    except OSError as error:
        print("  ⚠️  未写入检查记录：%s" % error, file=sys.stderr)
        return 0
    print("  ✅ 已记录本次提交的 tree（%s）" % tier)
    return 0


def pending_commits(local_sha, remote_sha):
    """Commits the push adds, oldest first; None when git cannot tell."""
    if set(remote_sha) <= ZERO:
        out = git("rev-list", "--reverse", "--topo-order", local_sha, "--not", "--remotes")
    else:
        out = git("rev-list", "--reverse", "--topo-order", remote_sha + ".." + local_sha)
    if out.returncode != 0:
        return None
    return [c for c in out.stdout.split() if c]


def cmd_check():
    records = load_records()
    if not records:
        print("  ℹ  没有检查记录，照常全跑")
        return 1
    if git("diff", "--quiet").returncode != 0 or git("diff", "--cached", "--quiet").returncode != 0:
        print("  ℹ  已跟踪文件有未提交的改动，照常全跑")
        return 1
    reasons = []
    for line in sys.stdin:
        parts = line.split()
        if len(parts) != 4:
            continue
        _, local_sha, remote_ref, remote_sha = parts
        if set(local_sha) <= ZERO or remote_ref.startswith("refs/tags/"):
            continue
        commits = pending_commits(local_sha, remote_sha)
        if commits is None:
            print("  ℹ  读不到 %s 要推的提交，照常全跑" % remote_ref)
            return 1
        # Oldest first: an unrecorded parent among the pushed commits stops the loop before its children,
        # so a quick child is only reached when its parent is on the remote or already accepted here.
        for commit in commits:
            why = commit_basis(commit, records)
            if why is None:
                print("  ℹ  %s 没有可用的检查记录，照常全跑" % commit[:7])
                return 1
            reasons.append("%s %s" % (commit[:7], why))
    if not reasons:
        print("  ℹ  没有要推的新提交，照常全跑")
        return 1
    print("── pre-push: 跳过检查（%d 个提交都已在提交时检查过：%s）──" % (len(reasons), "、".join(reasons)))
    return 0


def commit_basis(commit, records):
    tree = git("rev-parse", commit + "^{tree}").stdout.strip()
    tier = records.get(tree)
    if tier == "full":
        return "full"
    if tier != "quick":
        return None
    parents = git("rev-list", "--parents", "-n", "1", commit).stdout.split()[1:]
    if len(parents) != 1:
        return None  # merges need a full record
    names = git("diff", "--name-only", "--no-renames", parents[0], commit)
    if names.returncode != 0:
        return None
    if not all(is_quick_path(p) for p in names.stdout.split("\n") if p):
        return None
    return "quick"


def main(argv):
    if len(argv) >= 2 and argv[1] == "tier":
        return cmd_tier()
    if len(argv) == 3 and argv[1] == "record":
        return cmd_record(argv[2])
    if len(argv) == 2 and argv[1] == "check":
        return cmd_check()
    print("usage: verified_trees.py tier | record full|quick | check", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
