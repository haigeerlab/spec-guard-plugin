"""Audit an unfinished module's dependency changes against its Plan (dependency-check).

`scope-authorization` makes a Plan approval cover the items in its "需要的外部条件" section.  A host allows
commands by prefix, so writing a package into a manifest and running a bare install slips past the host's
question; this audit is the after-the-fact check.  For every module that is not DONE and has a Plan, it diffs
the dependency manifests from the commit that first added the module's Spec (the same point as /map's
startedAt) to the working tree, and reports packages that were added but are not listed in that section.

Only package.json, requirements*.txt and a few pyproject.toml shapes are read item by item; lock files are only
reported as changed (they are mostly indirect dependencies), other manifests and unreadable shapes as changed
but not checked.  Read-only: no network, no install, no writes.  verify-artifacts turns the output into hints.

    python3 -B dependency_check.py --project <root>
    -> one line per finding: "WARN<TAB><module><TAB><message>" or "UNVERIFIED<TAB><module><TAB><reason>"
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from capability_map import MapError, parse_map
from module_stage import FENCES, _git, module_state

NPM_KINDS = ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies")
LOCKS = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb", "poetry.lock", "uv.lock", "Pipfile.lock"}
OTHERS = {"Cargo.toml", "go.mod", "Gemfile", "composer.json", "Pipfile", "setup.py", "setup.cfg"}
SECTION = re.compile(r"^(#{1,6}\s*)?(?:\*\*)?(需要的外部条件|required external conditions)", re.IGNORECASE)
HEADING = re.compile(r"^(#{1,6})\s")
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+\.)\s")
ALLOWED = re.compile(r"允许范围|allowed scope", re.IGNORECASE)
REQUIREMENT = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
TOKEN = re.compile(r"@?[A-Za-z0-9][A-Za-z0-9._/@-]*")
TABLE = re.compile(r"^\s*\[([^\]]+)\]\s*$")
KEY = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*|\"[^\"]+\")\s*=")
QUOTED = re.compile(r"\"([^\"]+)\"|'([^']+)'")


def normalize_python(name: str) -> str:
    """PEP 503: lower case, runs of '-', '_' and '.' become one '-'."""
    return re.sub(r"[-_.]+", "-", name).lower()


def classify(path: str) -> str | None:
    """'npm', 'requirements', 'pyproject', 'lock', 'other', or None for a file this audit ignores."""
    parts = path.split("/")
    if "node_modules" in parts:
        return None
    name = parts[-1]
    if name == "package.json":
        return "npm"
    if name.startswith("requirements") and name.endswith(".txt"):
        return "requirements"
    if name == "pyproject.toml":
        return "pyproject"
    if name in LOCKS:
        return "lock"
    if name in OTHERS:
        return "other"
    return None


def npm_deps(text: str) -> set | None:
    """Package names in the four dependency maps of a package.json, or None when it is not a JSON object."""
    try:
        data = json.loads(text) if text.strip() else {}
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    names = set()
    for kind in NPM_KINDS:
        if isinstance(data.get(kind), dict):
            names.update(data[kind])
    return names


def requirement_deps(text: str) -> set:
    """Normalized package names of a requirements file; options (-r, -e, ...) and comments are skipped."""
    names = set()
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        match = REQUIREMENT.match(line)
        if match:
            names.add(normalize_python(match.group(1)))
    return names


def _requirement_names(chunk: str) -> set:
    return {normalize_python(m.group(1)) for m in (REQUIREMENT.match(a or b) for a, b in QUOTED.findall(chunk)) if m}


def pyproject_deps(text: str) -> tuple:
    """(normalized names, understood) for the pyproject shapes this audit reads line by line.

    Read: [project] dependencies = [...], [project.optional-dependencies] groups, and the keys of
    [tool.poetry.dependencies] / [tool.poetry.group.<name>.dependencies] (`python` is not a package).
    A dependency table of any other shape makes `understood` False, so it is reported as changed, not guessed.
    """
    names, understood, table, array = set(), True, "", None
    for line in text.splitlines():
        stripped = line.split("#", 1)[0].rstrip()
        if array is not None:
            array += " " + stripped
            if "]" in stripped:
                names |= _requirement_names(array)
                array = None
            continue
        header = TABLE.match(stripped)
        if header:
            table = header.group(1).strip()
            if "dependencies" in table and not (
                    table in ("project.optional-dependencies", "tool.poetry.dependencies")
                    or re.fullmatch(r"tool\.poetry\.group\.[^.]+\.dependencies", table)):
                understood = False
            continue
        key = KEY.match(stripped)
        if not key:
            continue
        name = key.group(1).strip('"')
        value = stripped.split("=", 1)[1]
        if table == "project" and name == "dependencies" or table == "project.optional-dependencies":
            if "[" not in value:
                understood = False
            elif "]" in value:
                names |= _requirement_names(value)
            else:
                array = value
        elif table == "tool.poetry.dependencies" or re.fullmatch(r"tool\.poetry\.group\.[^.]+\.dependencies", table):
            if name != "python":
                names.add(normalize_python(name))
        elif "dependencies" in name:
            understood = False
    return names, understood


def new_names(now: set, before: set) -> set:
    """Names present now and absent before; a changed version is not a new dependency."""
    return set(now) - set(before)


def _lines_outside_fences(text: str):
    fence = None
    for line in text.splitlines():
        stripped = line.strip()
        opener = stripped[:3] if stripped[:3] in FENCES else None
        if fence:
            fence = None if opener == fence else fence
            continue
        if opener:
            fence = opener
            continue
        yield line


def external_conditions(plan: str) -> str | None:
    """The text of the Plan's "需要的外部条件" section, or None when there is none (code blocks do not count).

    A heading takes everything up to the next heading of the same or a higher level; a line form takes that
    line and the list items (with their indented continuation) right after it.
    """
    lines = list(_lines_outside_fences(plan))
    for index, line in enumerate(lines):
        stripped = line.strip()
        match = SECTION.match(stripped)
        if not match:
            continue
        taken = [stripped]
        if match.group(1):
            level = len(match.group(1).strip())
            for later in lines[index + 1:]:
                heading = HEADING.match(later.strip())
                if heading and len(heading.group(1)) <= level:
                    break
                taken.append(later)
        else:
            for later in lines[index + 1:]:
                if LIST_ITEM.match(later) or (later.startswith((" ", "\t")) and later.strip()):
                    taken.append(later)
                else:
                    break
        return "\n".join(taken)
    return None


def _npm_token(token: str) -> str:
    token = token.rstrip(".")
    if token.startswith("@"):
        scope, _, rest = token.partition("/")
        return scope + "/" + rest.split("@", 1)[0] if rest else token
    return token.split("@", 1)[0]


def is_listed(name: str, section: str, kind: str) -> bool:
    """True when `name` appears as a whole word in the section (npm exact, Python by PEP 503)."""
    tokens = TOKEN.findall(section)
    if kind == "python":
        want = normalize_python(name)
        return any(normalize_python(token.rstrip(".")) == want for token in tokens)
    return any(_npm_token(token) == name for token in tokens)


def _changed_files(root: Path, base: str) -> list | None:
    tracked = _git(root, "diff", "--name-only", "--no-renames", base)
    untracked = _git(root, "ls-files", "--others", "--exclude-standard")
    if tracked is None or untracked is None:
        return None
    return sorted({p for p in (tracked + "\n" + untracked).splitlines() if p.strip()})


def _base(root: Path, module: str) -> str | None:
    if not _git(root, "rev-parse", "--verify", "--quiet", "HEAD"):
        return None
    added = _git(root, "log", "--diff-filter=A", "--format=%H", "--", "spec/%s.md" % module)
    if added is None:
        return None
    return added.splitlines()[-1] if added else "HEAD"


def audit_module(root: Path, module: str, plan_text: str) -> tuple:
    """("WARN", message) / ("UNVERIFIED", reason) / (None, None) for one module."""
    base = _base(root, module)
    files = _changed_files(root, base) if base else None
    if files is None:
        return "UNVERIFIED", "读不出 git 历史"
    section = external_conditions(plan_text)
    allowed = bool(section and ALLOWED.search(section))
    missing, by_scope, unchecked, locks = [], [], [], []
    for path in files:
        kind = classify(path)
        if kind is None:
            continue
        if kind == "lock":
            locks.append(path)
            continue
        if kind == "other":
            unchecked.append(path)
            continue
        current = root / path
        if not current.is_file():
            continue  # a removed manifest adds nothing
        try:
            now_text = current.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return "UNVERIFIED", "读不出 %s" % path
        before_text = _git(root, "show", "%s:%s" % (base, path)) or ""
        if kind == "npm":
            now, before = npm_deps(now_text), npm_deps(before_text) or set()
            understood = now is not None
        elif kind == "requirements":
            now, before, understood = requirement_deps(now_text), requirement_deps(before_text), True
        else:
            now, understood = pyproject_deps(now_text)
            before = pyproject_deps(before_text)[0]
        if not understood:
            unchecked.append(path)
            continue
        language = "npm" if kind == "npm" else "python"
        added = sorted(n for n in new_names(now, before) if not (section and is_listed(n, section, language)))
        if added:
            (by_scope if allowed else missing).append("%s：%s" % (path, "、".join(added)))
    parts = []
    if missing:
        label = "新增依赖没写进 Plan「需要的外部条件」" if section is not None else "新增依赖（Plan 没有「需要的外部条件」一节）"
        parts.append("%s：%s" % (label, "；".join(missing)))
    if by_scope:
        parts.append("按允许范围授权，未逐项核对：%s" % "；".join(by_scope))
    if unchecked:
        parts.append("改了，未逐项核对：%s" % "、".join(unchecked))
    if locks:
        parts.append("锁文件有改动：%s" % "、".join(locks))
    if not parts:
        return None, None
    return "WARN", "%s 的依赖改动：%s" % (module, "；".join(parts))


def audit(root: Path) -> list:
    """[(kind, module, text)] for every unfinished module that has a Plan."""
    try:
        rows = parse_map(root / "spec" / "CAPABILITY-MAP.md").rows
    except (MapError, OSError, UnicodeError):
        return []  # verify-artifacts reports the capability map itself
    found = []
    for row in rows:
        plan = root / "tasks" / row.module_id / "plan.md"
        if not plan.is_file():
            continue
        try:
            if module_state(root, row.module_id)["stage"] == "DONE":
                continue
            plan_text = plan.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            found.append(("UNVERIFIED", row.module_id, "读不出 Plan"))
            continue
        kind, text = audit_module(root, row.module_id, plan_text)
        if kind:
            found.append((kind, row.module_id, text))
    return found


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project", default=".")
    args = parser.parse_args(argv)
    for kind, module, text in audit(Path(args.project)):
        print("%s\t%s\t%s" % (kind, module, " ".join(text.split())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
