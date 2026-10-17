"""The concurrency boundary of a module Spec (module-scope-boundary).

When `moduleConcurrency` is on, a module Spec may carry a `## 并行边界` (`## Concurrency boundary`)
section naming the paths the module owns exclusively and the shared-file categories it expects to
touch.  This file is the only parser of that section: verify-artifacts, the overreach check below and
`/map` all call it.

The section is repository content that may reach an agent's context, so problems are a fixed vocabulary
of codes and nothing from the file is echoed.
"""
from __future__ import annotations

import re
from typing import NamedTuple

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
    if path == "spec/%s.md" % module_id or path.startswith("tasks/%s/" % module_id):
        return "own"
    for owned in scope.exclusive:
        if (path.startswith(owned) if owned.endswith("/") else path == owned):
            return "exclusive"
    return "outside"
