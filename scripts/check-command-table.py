#!/usr/bin/env python3
"""Every slash command appears in the docs/commands.md command table (2026-10-08 audit F18).

The table moved from docs/workflow.md to docs/commands.md in docs-reorganization; workflow.md links to it.

A command counts as listed when the "## 命令对照" section names it in backticks, with or without the
`/spec-guard:` prefix, or through a backticked wildcard such as `/spec-guard:documentation-*`. Zero commands or a
missing section is "not found", not "clean" (docs/lenses.md A5).

Usage: check-command-table.py [repo-root]
"""
import fnmatch
import pathlib
import re
import sys

HEADING = "## 命令对照"
TOKEN = re.compile(r"`(?:/spec-guard:)?([a-z0-9*-]+)`")


def main():
    root = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parents[1]
    commands = sorted((root / "plugins/spec-guard/commands").glob("*.md"))
    if not commands:
        print("  ❌ 0 个命令文件 —— 这是没找到，不是没问题", file=sys.stderr)
        return 1
    workflow = root / "docs/commands.md"
    text = workflow.read_text(encoding="utf-8") if workflow.is_file() else ""
    if HEADING not in text:
        print(f"  ❌ docs/commands.md 没有「{HEADING}」一节", file=sys.stderr)
        return 1
    section = text.split(HEADING, 1)[1].split("\n## ", 1)[0]
    tokens = set(TOKEN.findall(section))
    missing = [path.stem for path in commands
               if path.stem not in tokens and not any("*" in token and fnmatch.fnmatch(path.stem, token)
                                                      for token in tokens)]
    for name in missing:
        print(f"  ❌ /spec-guard:{name} 不在 docs/commands.md 的命令对照表里")
    if missing:
        return 1
    print(f"  ✅ {len(commands)} 个命令都在 docs/commands.md 的命令对照表里")
    return 0


if __name__ == "__main__":
    sys.exit(main())
