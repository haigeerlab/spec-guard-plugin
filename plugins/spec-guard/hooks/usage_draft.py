#!/usr/bin/env python3
"""Usage drafts (spec/usage/<requirement>.md): structure checks and milestone lookup.

The only place that decides whether a usage draft is well formed and consistent with the
capability map. verify-artifacts and module-insert call it; the capability map format is
untouched (milestones live only in the drafts).
"""
import argparse
import json
import os
import re
import sys

from capability_map import MapError, _table_cells, _visible_lines, parse_map

SECTIONS = (
    ("Entry points", ("Entry", "Does", "Module")),
    ("Typical usage", None),
    ("Milestones", ("Milestone", "Usage", "Modules")),
)
USAGE_HEADING = re.compile(r"^###\s+(U\d+)\s*[:：]\s*\S")
MILESTONE_ID = re.compile(r"^M\d+$")
SEPARATOR = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?$")


class UsageDraftError(ValueError):
    pass


def _split(value):
    return [item.strip().strip("`").strip() for item in re.split(r"[,，、]", value) if item.strip().strip("`").strip()]


def _sections(lines, label):
    found = {}
    current = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            current = stripped[3:].strip()
            if current in found:
                raise UsageDraftError("%s: `## %s` 出现了不止一次" % (label, current))
            found[current] = []
        elif current is not None:
            found[current].append(line)
    for name, _ in SECTIONS:
        if name not in found:
            raise UsageDraftError("%s: 缺少 `## %s` 一节" % (label, name))
    return found


def _table(lines, label, section, headers):
    start = None
    for index, line in enumerate(lines):
        if line.lstrip().startswith("|"):
            start = index
            break
    where = "%s: `## %s` 的表格" % (label, section)
    if start is None:
        raise UsageDraftError("%s不存在" % where)
    header = _table_cells(lines[start])
    if [cell.lower() for cell in header] != [name.lower() for name in headers]:
        raise UsageDraftError("%s表头应为 `| %s |`" % (where, " | ".join(headers)))
    if start + 1 >= len(lines) or not SEPARATOR.match(lines[start + 1].strip()):
        raise UsageDraftError("%s缺少分隔行" % where)
    rows = []
    for line in lines[start + 2:]:
        if not line.lstrip().startswith("|"):
            break
        cells = _table_cells(line)
        if len(cells) != len(headers):
            raise UsageDraftError("%s有一行格数不对: %s" % (where, line.strip()))
        rows.append(cells)
    if not rows:
        raise UsageDraftError("%s没有数据行" % where)
    return rows


def parse(path, label):
    """Parse one draft into entries, usage ids and ordered milestones; raise UsageDraftError."""
    try:
        with open(path, encoding="utf-8") as handle:
            lines = _visible_lines(handle.read().splitlines())
    except (OSError, UnicodeDecodeError) as error:
        raise UsageDraftError("%s: 读不了（%s）" % (label, error))
    sections = _sections(lines, label)
    entries = [(entry, _split(module)) for entry, _does, module in
               _table(sections["Entry points"], label, "Entry points", SECTIONS[0][1])]
    usages = []
    for line in sections["Typical usage"]:
        if line.strip().startswith("### "):
            match = USAGE_HEADING.match(line.strip())
            if not match:
                raise UsageDraftError("%s: 典型用法标题要写成 `### U<n>: 标题`: %s" % (label, line.strip()))
            if match.group(1) in usages:
                raise UsageDraftError("%s: 典型用法 %s 重复" % (label, match.group(1)))
            usages.append(match.group(1))
    if not usages:
        raise UsageDraftError("%s: `## Typical usage` 里没有典型用法（`### U<n>: 标题`）" % label)
    milestones = []
    for milestone, usage, modules in _table(sections["Milestones"], label, "Milestones", SECTIONS[2][1]):
        milestone = milestone.strip("`")
        if not MILESTONE_ID.match(milestone):
            raise UsageDraftError("%s: 里程碑编号要写成 M<n>: %s" % (label, milestone))
        if milestone in [item[0] for item in milestones]:
            raise UsageDraftError("%s: 里程碑 %s 重复" % (label, milestone))
        if not _split(modules):
            raise UsageDraftError("%s: 里程碑 %s 没有列模块" % (label, milestone))
        milestones.append((milestone, _split(usage), _split(modules)))
    return {"entries": entries, "usages": usages, "milestones": milestones}


def draft_files(project):
    folder = os.path.join(project, "spec", "usage")
    if not os.path.isdir(folder):
        return []
    return ["spec/usage/" + name for name in sorted(os.listdir(folder))
            if name.endswith(".md") and os.path.isfile(os.path.join(folder, name))]


def milestones(project):
    """Map module id -> (draft file, milestone id). Raises UsageDraftError when a draft is unreadable."""
    found = {}
    for label in draft_files(project):
        for milestone, _usage, modules in parse(os.path.join(project, label), label)["milestones"]:
            for module in modules:
                found.setdefault(module, (label, milestone))
    return found


def _check_one(label, draft, positions, owner, failures, warnings):
    usages = draft["usages"]
    referenced = set()
    for milestone, usage, _modules in draft["milestones"]:
        for item in usage:
            if item not in usages:
                failures.append("%s: 里程碑 %s 引用了不存在的典型用法 %s" % (label, milestone, item))
            referenced.add(item)
    for item in usages:
        if item not in referenced:
            failures.append("%s: 典型用法 %s 没有被任何里程碑引用" % (label, item))
    last, last_usage, _ = draft["milestones"][-1]
    missing = [item for item in usages if item not in last_usage]
    if missing:
        failures.append("%s: 最后一个里程碑 %s 要跑通全部典型用法，缺 %s" % (label, last, "、".join(missing)))

    in_draft = set()
    for milestone, _usage, modules in draft["milestones"]:
        for module in modules:
            if module not in positions:
                failures.append("%s: 里程碑 %s 的模块 %s 不在能力图上" % (label, milestone, module))
                continue
            if module in owner:
                failures.append("%s: 模块 %s 已归在 %s 的 %s，又归在 %s" % (label, module, owner[module][0], owner[module][1], milestone))
                continue
            owner[module] = (label, milestone)
            in_draft.add(module)

    with_entry = set()
    for entry, modules in draft["entries"]:
        for module in modules:
            with_entry.add(module)
            if module not in in_draft:
                failures.append("%s: 入口 %s 归属的模块 %s 不在本草案的里程碑里" % (label, entry, module))
    for milestone, _usage, modules in draft["milestones"]:
        for module in modules:
            if module in in_draft and module not in with_entry:
                warnings.append("%s: 里程碑 %s 的模块 %s 没有对应任何入口（可能拆多了，基础设施模块可忽略）" % (label, milestone, module))

    previous = None
    for milestone, _usage, modules in draft["milestones"]:
        placed = [positions[module] for module in modules if module in positions]
        if not placed:
            continue
        if previous is not None and min(placed) <= previous[1]:
            failures.append("%s: Build order 把里程碑 %s 的模块排在了 %s 的模块之前或同一组" % (label, milestone, previous[0]))
        previous = (milestone, max(placed) if previous is None else max(max(placed), previous[1]))


def validate(project):
    files = draft_files(project)
    if not files:
        return {"status": "absent", "files": [], "failures": [], "warnings": []}
    try:
        parsed = parse_map(os.path.join(project, "spec", "CAPABILITY-MAP.md"))
    except (MapError, OSError, UnicodeDecodeError) as error:
        return {"status": "unverified", "files": files, "failures": [], "warnings": [], "reason": str(error)}
    positions = {}
    for index, group in enumerate(parsed.declared_groups):
        for module in group:
            positions[module] = index
    failures, warnings, owner = [], [], {}
    for label in files:
        try:
            draft = parse(os.path.join(project, label), label)
        except UsageDraftError as error:
            failures.append(str(error))
            continue
        _check_one(label, draft, positions, owner, failures, warnings)
    return {"status": "fail" if failures else "pass", "files": files, "failures": failures, "warnings": warnings}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check usage drafts under spec/usage/.")
    sub = parser.add_subparsers(dest="command")
    check = sub.add_parser("validate")
    check.add_argument("--project", required=True)
    check.add_argument("--format", choices=("lines", "json"), default="lines")
    args = parser.parse_args(argv)
    if args.command != "validate":
        parser.print_usage(sys.stderr)
        return 2
    if not os.path.isdir(args.project):
        print("--project is not a directory: %s" % args.project, file=sys.stderr)
        return 2
    result = validate(args.project)
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False))
    elif result["status"] == "absent":
        print("absent")
    elif result["status"] == "unverified":
        print("unverified %s" % result["reason"].replace("\n", " "))
    else:
        if result["status"] == "pass":
            print("ok %d" % len(result["files"]))
        for item in result["failures"]:
            print("bad %s" % item.replace("\n", " "))
        for item in result["warnings"]:
            print("warn %s" % item.replace("\n", " "))
    return 1 if result["status"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
