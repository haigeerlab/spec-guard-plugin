"""The concurrency boundary of a module Spec (module-scope-boundary).

When `moduleConcurrency` is on, a module Spec may carry a `## 并行边界` (`## Concurrency boundary`)
section naming the paths the module owns exclusively and the shared-file categories it expects to
touch.  This file is the only parser of that section: verify-artifacts, the overreach check below and
`/map` all call it.

The section is repository content that may reach an agent's context, so problems are a fixed vocabulary
of codes and nothing from the file is echoed.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import NamedTuple

from capability_map import MODULE_ID, MapError, parse_map
from module_stage import module_state
from project_config import module_concurrency

HEADINGS = ("## 并行边界", "## Concurrency boundary")
EXCLUSIVE = ("独占", "Exclusive")
SHARED = ("公共", "Shared")
CATEGORIES = {"全局配置": "global-config", "锁文件": "lockfile", "迁移": "migration", "测试资源": "test-resource"}
NONE = ("无", "none")
FENCE = re.compile(r"^\s*(```|~~~)")
SECTION_END = re.compile(r"^#{1,2}\s")
FIELD = re.compile(r"^-\s+([^:：]+?)\s*[:：]\s*(.*)$")
TICKED = re.compile(r"^`([^`]*)`$")
SEPARATORS = re.compile(r"\s*[、,]\s*")
BAD_PATH_CHARS = set("*?[]\\")
SCOPES = ("exclusive", "own", "outside")  # interface.json scopeCheck.values.scope
# interface.json scopeOverlap.values.error: ScopeError codes, then the overlap command's own.
OVERLAP_ERRORS = ("no-boundary", "missing-exclusive", "bad-path", "bad-category", "duplicate-section", "unknown-line",
                  "unreadable", "no-capability-map", "map-unreadable")


class ScopeError(ValueError):
    """A malformed section; `code` is one of a fixed set and never carries file content."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class Scope(NamedTuple):
    exclusive: tuple
    shared: tuple


def _visible(text: str) -> list:
    """Lines outside fenced code blocks, so an example heading in a Spec is not a section."""
    lines, fenced = [], False
    for line in text.splitlines():
        if FENCE.match(line):
            fenced = not fenced
            lines.append("")
            continue
        lines.append("" if fenced else line)
    return lines


def _path(item: str) -> str:
    match = TICKED.match(item)
    if not match:
        raise ScopeError("bad-path")
    path = match.group(1)
    parts = path[:-1].split("/") if path.endswith("/") else path.split("/")
    if (not path or path.startswith("/") or any(char in BAD_PATH_CHARS for char in path)
            or any(part in ("", ".", "..") or part != part.strip() for part in parts)):
        raise ScopeError("bad-path")
    return path


def _categories(value: str) -> tuple:
    items = [item for item in SEPARATORS.split(value.strip()) if item]
    if len(items) == 1 and items[0] in NONE:
        return ()
    codes = []
    for item in items:
        code = CATEGORIES.get(item, item if item in CATEGORIES.values() else None)
        if code is None:
            raise ScopeError("bad-category")
        codes.append(code)
    return tuple(codes)


def parse(text: str) -> Scope | None:
    """The section's Scope, None when the Spec has no such section, ScopeError when it is malformed."""
    lines = _visible(text)
    starts = [index for index, line in enumerate(lines) if line.rstrip() in HEADINGS]
    if not starts:
        return None
    if len(starts) > 1:
        raise ScopeError("duplicate-section")
    exclusive = shared = None
    for line in lines[starts[0] + 1:]:
        if SECTION_END.match(line):
            break
        stripped = line.strip()
        if not stripped or (stripped.startswith("<!--") and stripped.endswith("-->")):
            continue
        match = FIELD.match(stripped)
        name = match.group(1) if match else None
        if name in EXCLUSIVE and exclusive is None:
            items = [item for item in SEPARATORS.split(match.group(2).strip()) if item]
            exclusive = tuple(_path(item) for item in items)
        elif name in SHARED and shared is None:
            shared = _categories(match.group(2))
        else:
            raise ScopeError("unknown-line")
    if not exclusive:
        raise ScopeError("missing-exclusive")
    return Scope(exclusive, shared or ())


def covers(scope: Scope, module_id: str, path: str) -> str:
    """`own` for the module's flow files, `exclusive` inside its paths, otherwise `outside`."""
    exclusive, own, outside = SCOPES
    if path == "spec/%s.md" % module_id or path.startswith("tasks/%s/" % module_id):
        return own
    for owned in scope.exclusive:
        if (path.startswith(owned) if owned.endswith("/") else path == owned):
            return exclusive
    return outside


def overlap(a: Scope, b: Scope) -> list:
    """Exclusive paths the two boundaries share: equal, or one inside the other's directory (the narrower one)."""
    found = set()
    for left in a.exclusive:
        for right in b.exclusive:
            if left == right:
                found.add(left)
            elif left.endswith("/") and right.startswith(left):
                found.add(right)
            elif right.endswith("/") and left.startswith(right):
                found.add(left)
    return sorted(found)


def _git(root: Path, *args: str) -> str | None:
    done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=False)
    return done.stdout.decode("utf-8", "surrogateescape") if done.returncode == 0 else None


def changed_files(root: Path, base: str) -> list | None:
    """(status, path) for every change since `base`: committed, uncommitted, deleted and untracked.

    None when `base` is not a commit in this repository.
    """
    if base.startswith("-") or _git(root, "rev-parse", "--verify", "--quiet", base + "^{commit}") is None:
        return None
    diff = _git(root, "diff", "--no-renames", "--name-status", "-z", base, "--")
    untracked = _git(root, "ls-files", "--others", "--exclude-standard", "-z")
    if diff is None or untracked is None:
        return None
    fields = [field for field in diff.split("\0") if field]
    files = [(fields[index][0], fields[index + 1]) for index in range(0, len(fields) - 1, 2)]
    files.extend(("?", path) for path in untracked.split("\0") if path)
    return sorted(files, key=lambda item: item[1])


def _check(root: Path, module_id: str, base: str, as_json: bool) -> int:
    if not MODULE_ID.fullmatch(module_id):
        print("module-id-invalid: not a capability-map module id")
        return 2
    if _git(root, "rev-parse", "--is-inside-work-tree") is None:
        print("not-a-git-repository: the overreach check compares against a git base")
        return 2
    if not module_concurrency(root):
        print("moduleConcurrency is not on in .agent/config.json; the overreach check does not run")
        return 3
    spec_path = root / "spec" / ("%s.md" % module_id)
    try:
        scope = parse(spec_path.read_text(encoding="utf-8")) if spec_path.is_file() else None
    except ScopeError as error:
        print("boundary-invalid (%s): fix the concurrency boundary section in spec/%s.md" % (error.code, module_id))
        return 4
    except (OSError, UnicodeDecodeError):
        scope = None
    if scope is None:
        print("no-boundary: spec/%s.md has no concurrency boundary section" % module_id)
        return 4
    files = changed_files(root, base)
    if files is None:
        print("base-invalid: the base is not a commit in this repository")
        return 2
    rows = [{"path": path, "status": status, "scope": covers(scope, module_id, path)} for status, path in files]
    outside = sum(1 for row in rows if row["scope"] == "outside")
    if as_json:
        print(json.dumps({"module": module_id, "base": base, "files": rows, "outside": outside},
                         ensure_ascii=False, sort_keys=True))
        return 0
    print("concurrency boundary check: %s against %s" % (module_id, base))
    for row in rows:
        print("  %-9s %s %s" % (row["scope"], row["status"], row["path"]))
    print("outside the boundary: %d" % outside)
    return 0


def validate(root: Path) -> list:
    """verify-artifacts lines: nothing when the switch is off; otherwise one line per unfinished module finding.

    `ok <n>` counts valid sections, `warn missing <id>` a Spec without one, `bad <code> <id>` a malformed one,
    `unverified map` when the capability map cannot be read.  Finished modules and modules without a Spec are skipped.
    """
    if not module_concurrency(root):
        return []
    try:
        modules = [row.module_id for row in parse_map(root / "spec" / "CAPABILITY-MAP.md").rows]
    except (MapError, OSError, UnicodeDecodeError):
        return ["unverified map"]
    valid, lines = 0, []
    for module_id in modules:
        spec_path = root / "spec" / ("%s.md" % module_id)
        if not spec_path.is_file() or module_state(root, module_id)["stage"] == "DONE":
            continue
        try:
            scope = parse(spec_path.read_text(encoding="utf-8"))
        except ScopeError as error:
            lines.append("bad %s %s" % (error.code, module_id))
            continue
        except (OSError, UnicodeDecodeError):
            lines.append("unverified %s" % module_id)
            continue
        if scope is None:
            lines.append("warn missing %s" % module_id)
        else:
            valid += 1
    return (["ok %d" % valid] if valid else []) + lines


def _scope_or_error(text: str | None) -> Scope | str:
    if text is None:
        return "unreadable"
    try:
        scope = parse(text)
    except ScopeError as error:
        return error.code
    return "no-boundary" if scope is None else scope


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _project_specs(root: Path) -> tuple:
    """(Build order, {module: Spec text or None}) for the modules /map reports in_progress or ready, or an error code."""
    from map_view import Unreadable, build  # map_view imports this module at its top

    if not (root / "spec" / "CAPABILITY-MAP.md").is_file():
        return [], {}, "no-capability-map"
    try:
        data = build(root)
    except (MapError, Unreadable, OSError, UnicodeError):
        return [], {}, "map-unreadable"
    order = [m["id"] for m in data["modules"]]
    specs = {m["id"]: _read(root / "spec" / ("%s.md" % m["id"])) for m in data["modules"]
             if m["status"] in ("in_progress", "ready") and (root / "spec" / ("%s.md" % m["id"])).is_file()}
    return order, specs, None


def overlaps(entries: list, order: list) -> dict:
    """scope-overlap-interface: entries are (module, source, Spec text or None); every pair of usable boundaries is compared.

    Modules in `order` (Build order) come first in that order, the rest keep their entry order.
    """
    rank = {module: index for index, module in enumerate(order)}
    entries = sorted(enumerate(entries), key=lambda item: (item[1][0] not in rank, rank.get(item[1][0], 0), item[0]))
    usable, errors = [], []
    for _, (module, source, text) in entries:
        scope = _scope_or_error(text)
        if isinstance(scope, str):
            errors.append({"module": module, "source": source, "error": scope})
        else:
            usable.append((module, source, scope))
    conflicts = []
    for index, (first, first_source, first_scope) in enumerate(usable):
        for second, second_source, second_scope in usable[index + 1:]:
            paths = overlap(first_scope, second_scope)
            if paths:
                conflicts.append({"modules": [first, second], "paths": paths,
                                  "sources": {first: first_source, second: second_source}})
    return {"conflicts": conflicts, "errors": errors}


def _overlap_command(specs: list, project: str | None) -> int:
    if not specs and project is None:
        print("usage: give at least one --spec <module-id>=<file> or --project <root>")
        return 2
    given = {}
    for item in specs:
        module, sep, source = item.partition("=")
        if not sep or not source:
            print("spec-arg-invalid: --spec takes <module-id>=<file>")
            return 2
        if not MODULE_ID.fullmatch(module):
            print("module-id-invalid: not a capability-map module id")
            return 2
        if module in given:
            print("module-repeated: a module id is given twice")
            return 2
        given[module] = source
    root = Path(project) if project is not None else None
    if root is not None and not root.is_dir():
        print("project-not-a-directory: --project is not a directory")
        return 2
    order, from_project, problem = _project_specs(root) if root is not None else ([], {}, None)
    entries = [(module, "project", text) for module, text in from_project.items() if module not in given]
    entries += [(module, source, _read(Path(source))) for module, source in given.items()]
    result = overlaps(entries, order)
    if problem:
        result["errors"].insert(0, {"module": None, "source": "project", "error": problem})
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Concurrency boundary of module Specs (read-only).")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="classify a module's changes since a base against its boundary")
    check.add_argument("--module", required=True)
    check.add_argument("--base", required=True)
    check.add_argument("--format", choices=("text", "json"), default="text")
    check.add_argument("--project", default=".")
    checker = commands.add_parser("validate", help="lines for verify-artifacts; silent when the switch is off")
    checker.add_argument("--project", default=".")
    pairs = commands.add_parser("overlap", help="exclusive-path overlaps between given Specs and, with --project, open modules")
    pairs.add_argument("--spec", action="append", default=[])
    pairs.add_argument("--project")
    args = parser.parse_args()
    if args.command == "overlap":
        return _overlap_command(args.spec, args.project)
    root = Path(args.project)
    if args.command == "validate":
        for line in validate(root):
            print(line)
        return 0
    return _check(root, args.module, args.base, args.format == "json")


if __name__ == "__main__":
    raise SystemExit(main())
