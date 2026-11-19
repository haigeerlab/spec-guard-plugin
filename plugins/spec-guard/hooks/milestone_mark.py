#!/usr/bin/env python3
"""Record that the user confirmed a milestone of a usage draft (milestone-stop).

Previews by default; writes only with --confirm. The record is one comment line after the draft's
Milestones table naming the milestone's modules at confirmation time, so a milestone that later gains a
module stops again once that module is done. The stop criterion itself lives in usage_draft.stop; this
script only checks that the milestone can be confirmed now and adds or replaces the line. It cannot check
that the user approved anything: the line is a record for later sessions, not a source of authority.
"""
from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path

import usage_draft
from capability_map import MapError, parse_map
from module_stage import module_state
from tracker_default import _write_atomic

DRAFT_PATH = re.compile(r"^spec/usage/[^/]+\.md$")


def record_line(milestone: str, modules: list) -> str:
    return "<!-- spec-guard: milestone %s confirmed %s -->" % (milestone, ", ".join(modules))


def _with_record(text: str, milestone: str, line: str) -> str:
    """The text with `line` as the one record of `milestone`: replaced in place, else after the Milestones table."""
    lines = text.splitlines(keepends=True)
    eol = "\r\n" if lines and lines[0].endswith("\r\n") else "\n"
    for index, raw in enumerate(lines):
        match = usage_draft.CONFIRM.match(raw.strip())
        if match and match.group(1) == milestone:
            lines[index] = line + raw[len(raw.rstrip("\r\n")):]
            return "".join(lines)
    start = next(i for i, raw in enumerate(lines) if raw.strip() == "## Milestones")
    table = next(i for i in range(start + 1, len(lines)) if lines[i].lstrip().startswith("|"))
    end = table
    while end < len(lines) and lines[end].lstrip().startswith("|"):
        end += 1
    at, last_record = end, None
    while at < len(lines) and (not lines[at].strip() or usage_draft.CONFIRM.match(lines[at].strip())):
        if lines[at].strip():
            last_record = at
        at += 1
    if end > 0 and not lines[end - 1].endswith(("\n", "\r")):
        lines[end - 1] += eol
    if last_record is not None:
        lines.insert(last_record + 1, line + eol)
    else:
        lines[end:end] = [eol, line + eol]
    return "".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Record a usage-draft milestone confirmation (preview unless --confirm).")
    parser.add_argument("--project", default=".")
    parser.add_argument("--draft", required=True, help="spec/usage/<requirement>.md")
    parser.add_argument("--milestone", required=True)
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.project)
    if not DRAFT_PATH.match(args.draft):
        print("不是用法草案：--draft 要写成 spec/usage/<需求>.md")
        return 2
    path = root / args.draft
    if not path.is_file():
        print("草案不存在：%s" % args.draft)
        return 2
    try:
        draft = usage_draft.parse(str(path), args.draft)
        parsed = parse_map(root / "spec" / "CAPABILITY-MAP.md")
        before = path.read_text(encoding="utf-8")
    except usage_draft.UsageDraftError as error:
        print("草案读不了：%s；先运行 /spec-guard:verify-artifacts" % error)
        return 2
    except (OSError, MapError, UnicodeError) as error:
        print("能力图或草案读不了（%s）；先运行 /spec-guard:verify-artifacts" % error)
        return 2
    order = list(parsed.order) or [row.module_id for row in parsed.rows]
    states = {module: module_state(root, module) for module in order}
    rows = draft["milestones"]
    ids = [row[0] for row in rows]
    if args.milestone not in ids:
        print("里程碑不存在：%s 里没有 %s（有 %s）" % (args.draft, args.milestone, "、".join(ids)))
        return 2
    index = ids.index(args.milestone)
    milestone, usages, modules = rows[index]
    missing = [module for module in modules if module not in states]
    if missing:
        print("模块不在能力图上：%s；先运行 /spec-guard:verify-artifacts" % "、".join(missing))
        return 2
    print("草案: %s\n里程碑: %s\n模块:" % (args.draft, milestone))
    for module in modules:
        print("  %s  %s" % (module, states[module]["stage"]))
    print("要实际跑过的典型用法: %s" % "、".join(usages))
    if usage_draft.confirmed(draft, milestone, modules):
        print("%s 已确认，记录与当前模块一致；无需改动。" % milestone)
        return 0
    unfinished = [module for module in modules if states[module]["stage"] != "DONE"]
    if unfinished:
        print("还不能确认：模块 %s 没有完成。" % "、".join(unfinished))
        return 2
    earlier = [row[0] for row in rows[:index] if not usage_draft.confirmed(draft, row[0], row[2])]
    if earlier:
        print("还不能确认：前面的里程碑 %s 还没确认，先按顺序确认它。" % "、".join(earlier))
        return 2
    line = record_line(milestone, modules)
    after = _with_record(before, milestone, line)
    print("将写入: %s" % line)
    print("".join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                                       fromfile=args.draft + " (current)", tofile=args.draft + " (proposed)")))
    pending = next((module for module in order if states[module]["stage"] != "DONE"), None)
    print("确认后：阶段提示不再报 %s 的停点；%s" % (
        milestone, ("当前模块按 Build order 是 `%s`。" % pending) if pending else "能力图里的模块都已完成。"))
    if not args.confirm:
        print("只在用户明确说 %s 通过之后，才在同一条命令后加 --confirm；「看起来还行」「继续」不算。" % milestone)
        print("preview only; nothing was written.")
        return 0
    try:
        _write_atomic(path, after)
        reread = usage_draft.parse(str(path), args.draft)
    except (OSError, usage_draft.UsageDraftError) as error:
        print("写入失败：%s" % error)
        return 1
    if not usage_draft.confirmed(reread, milestone, modules):
        print("写入后读回不一致，请检查 %s" % args.draft)
        return 1
    print("已记下：%s 的 %s 已确认。" % (args.draft, milestone))
    return 0


if __name__ == "__main__":
    sys.exit(main())
