#!/usr/bin/env python3
"""regression-doc-check: the one place that reads a regression document's Markdown into cases.

    regression_view.py --json --project <root> (--module <id> | --usage <name>) [--ref <git ref>]

Read-only.  A flow v2 module's cases live in tasks/<id>/regression.md (normal, important) or in the "回归用例" section
of spec/<id>.md (bug, small); a multi-module requirement's integration cases in spec/usage/<name>.regression.md.
Exit codes: 0 ok (problems are reported, not fatal); 2 usage error or module not in the capability map;
3 not-flow-v2, no-document or not-at-ref (stdout is one JSON error); 4 unreadable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SCHEMA_VERSION = 1
METHODS = ("command", "script", "ai-operate", "manual")
COMMAND_METHODS = ("command", "script")
FIELDS = (("steps", ("步骤", "Steps")), ("expected", ("预期", "Expected")), ("method", ("执行方式", "Method")),
          ("command", ("命令", "Command")), ("evidence", ("证据", "Evidence")))
REQUIRED = ("steps", "expected", "method", "evidence")
PROBLEM_CODES = ("case-field-missing", "case-method-invalid", "case-command-missing", "case-command-unexpected",
                 "case-id-duplicate", "criterion-uncovered", "criterion-unknown", "case-unknown",
                 "affected-existing-empty", "no-cases", "module-unknown")
ERRORS = ("not-flow-v2", "no-document", "not-at-ref", "unreadable")

# Section names: module documents use module_stage.DOC_SECTIONS["regression"]; the rest are defined here.
SHORT_SECTION = ("回归用例", "Regression cases")
CRITERIA_SECTION = ("成功标准", "Success criteria")
USAGE_SECTIONS = {"cases": ("用例清单", "Cases"),
                  "coverage": ("成功标准 → 联调用例", "Success criteria → integration cases"),
                  "modules": ("涉及的模块", "Modules involved")}

H2 = re.compile(r"^##\s+(.+?)\s*$")
H3 = re.compile(r"^###\s")
CASE = re.compile(r"^###\s+R(\d+)\s*[:：]\s*(.*?)\s*$")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
FIELD_NAMES = {name: key for key, names in FIELDS for name in names}
FIELD_LINE = re.compile(r"^\s*[-*]\s*(%s)\s*[:：]\s*(.*?)\s*$" % "|".join(map(re.escape, FIELD_NAMES)))
CRITERION_LINE = re.compile(r"^\s*(?:[-*+]\s+)?(?:\*\*)?(S\d+)\b")
SID = re.compile(r"^S\d+$")
RID = re.compile(r"^R\d+$")
USAGE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
MODULE_TOKEN = re.compile(r"`([^`\s]+)`|^\s*[-*]\s+([A-Za-z0-9][A-Za-z0-9_-]*)\s*$")


def _scan(text: str):
    """Yield (line number, line, in_fence, fence_marker_line) for every line."""
    fence = None
    for number, line in enumerate(text.splitlines(), 1):
        match = FENCE.match(line)
        if fence:
            closing = bool(match and match[1][0] == fence[0] and len(match[1]) >= len(fence) and not match[2].strip())
            if closing:
                fence = None
            yield number, line, True, closing
        elif match:
            fence = match[1]
            yield number, line, True, True
        else:
            yield number, line, False, False


def _sections(text: str) -> list:
    """[(heading, [(number, line, in_fence, marker), ...])] for the level-2 sections, the preamble under heading None."""
    found = [(None, [])]
    for item in _scan(text):
        heading = None if item[2] else H2.match(item[1])
        if heading:
            found.append((heading.group(1), []))
        else:
            found[-1][1].append(item)
    return found


def _section_lines(text: str, names) -> list | None:
    """The lines of the first section whose heading is one of names; None when there is no such section."""
    for heading, lines in _sections(text):
        if heading in names:
            return lines
    return None


def criteria_ids(text: str) -> list:
    """The S<n> ids that open lines under the requirement's 成功标准 / Success criteria section, in order."""
    lines = _section_lines(text, CRITERIA_SECTION) or []
    found = []
    for _number, line, in_fence, _marker in lines:
        match = None if in_fence else CRITERION_LINE.match(line)
        if match and match.group(1) not in found:
            found.append(match.group(1))
    return found


def _cases(lines, label: str, affected: bool) -> list:
    """Cases under a section: each `### R<n>: title` and its field lines; continuation lines join the open field."""
    cases, case, field = [], None, None
    for number, line, in_fence, marker in lines:
        if not in_fence:
            start = CASE.match(line)
            if start or H3.match(line):
                case = {"id": "R%s" % start.group(1), "title": start.group(2), "fields": {}, "line": number,
                        "affectedExisting": affected} if start else None
                if case:
                    cases.append(case)
                field = None
                continue
            hit = FIELD_LINE.match(line) if case else None
            if hit:
                field = FIELD_NAMES[hit.group(1)]
                case["fields"].setdefault(field, [])
                if hit.group(2):
                    case["fields"][field].append(hit.group(2))
                continue
        if case is None or field is None:
            continue
        if in_fence:
            if not marker:
                case["fields"][field].append(line.strip())
        elif line.strip() and line[:1].isspace():
            case["fields"][field].append(line.strip())
        elif line.strip():
            field = None
    for case in cases:
        values = {key: "\n".join(part for part in case["fields"].get(key, []) if part).strip() for key, _ in FIELDS}
        case["present"] = {key for key in case["fields"]}
        for key, _ in FIELDS:
            value = values[key]
            if key in ("method", "command") and value.startswith("`") and value.endswith("`") and len(value) > 1:
                value = value.strip("`").strip()
            case[key] = value or None
        case["label"] = label
    return cases


def _table(lines) -> list:
    """[(line number, S id, [tokens of the cases cell])] for the table rows whose first cell is an S<n> id."""
    rows = []
    for number, line, in_fence, _marker in lines:
        text = line.strip()
        if in_fence or not text.startswith("|"):
            continue
        cells = [cell.strip().strip("*`").strip() for cell in text.strip("|").split("|")]
        if len(cells) >= 2 and SID.match(cells[0]):
            rows.append((number, cells[0], [token.strip("`*") for token in re.split(r"[,，、\s]+", cells[1])
                                            if token.strip("`*")]))
    return rows


def case_sha256(case: dict) -> str:
    """sha256 of the five fields, each with runs of whitespace collapsed; the id and the title do not count."""
    data = {key: " ".join((case.get(key) or "").split()) for key, _ in FIELDS}
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
                          .encode("utf-8")).hexdigest()


def _problem(code: str, where: str) -> dict:
    return {"code": code, "where": where}


def parse_regression(text: str, kind: str, criteria: list | None, label: str = "") -> dict:
    """kind: module (three sections), short (the 回归用例 section of spec/<id>.md) or usage (integration regression).

    criteria: the S<n> ids every one of which must be covered; None skips the coverage check (bug, usage).
    Returns {"cases", "problems", "modules"}; problems are {"code", "where"} with where = "<label>:<line>" or a case id.
    """
    from module_stage import DOC_SECTIONS
    names = DOC_SECTIONS["regression"]
    pairs = list(zip(names["zh"], names["en"]))
    sections = _sections(text)
    lookup = {}
    for heading, lines in sections:
        if heading is not None:
            lookup.setdefault(heading, lines)

    def pick(pair):
        for name in pair:
            if name in lookup:
                return lookup[name]
        return None

    modules = []
    if kind == "module":
        case_lines, coverage, affected = pick(pairs[0]), pick(pairs[1]), pick(pairs[2])
    elif kind == "short":
        case_lines, affected = pick(SHORT_SECTION), None
        coverage = case_lines
    else:
        case_lines, coverage, affected = pick(USAGE_SECTIONS["cases"]), pick(USAGE_SECTIONS["coverage"]), None
        for _number, line, in_fence, _marker in pick(USAGE_SECTIONS["modules"]) or []:
            match = None if in_fence else MODULE_TOKEN.search(line)
            if match and (match.group(1) or match.group(2)) not in modules:
                modules.append(match.group(1) or match.group(2))
    cases = _cases(case_lines or [], label, False) + _cases(affected or [], label, True)
    problems = []
    where = (lambda number: "%s:%d" % (label, number)) if label else (lambda number: "line %d" % number)
    if not cases:
        problems.append(_problem("no-cases", label or "document"))
    seen = set()
    for case in cases:
        if case["id"] in seen:
            problems.append(_problem("case-id-duplicate", where(case["line"])))
        seen.add(case["id"])
        missing = [key for key in REQUIRED if not case[key]]
        for key in missing:
            problems.append(_problem("case-field-missing", "%s %s" % (case["id"], key)))
        if case["method"] and case["method"] not in METHODS:
            problems.append(_problem("case-method-invalid", case["id"]))
        if case["method"] in COMMAND_METHODS and not case["command"]:
            problems.append(_problem("case-command-missing", case["id"]))
        if case["method"] in METHODS and case["method"] not in COMMAND_METHODS and case["command"]:
            problems.append(_problem("case-command-unexpected", case["id"]))
    known_cases = {case["id"] for case in cases}
    covered, listed = {}, []
    known_criteria = set(criteria or [])
    for number, sid, rids in _table(coverage or []):
        if sid not in listed:
            listed.append(sid)
        if criteria is not None and sid not in known_criteria:
            problems.append(_problem("criterion-unknown", where(number)))
        for rid in rids:
            if rid not in known_cases:
                problems.append(_problem("case-unknown", where(number)))
            elif sid not in covered.setdefault(rid, []):
                covered[rid].append(sid)
    for sid in criteria or []:
        if sid not in listed:
            problems.append(_problem("criterion-uncovered", sid))
    out = []
    for case in cases:
        out.append({"id": case["id"], "title": case["title"], "steps": case["steps"], "expected": case["expected"],
                    "method": case["method"], "command": case["command"], "evidence": case["evidence"],
                    "criteria": covered.get(case["id"], []), "affectedExisting": case["affectedExisting"],
                    "sha256": case_sha256(case)})
    return {"cases": out, "problems": problems, "modules": modules,
            "affectedCount": sum(1 for case in cases if case["affectedExisting"]),
            "coverageCriteria": listed}


class ViewError(Exception):
    def __init__(self, code: str, exit_code: int, detail: str = ""):
        super().__init__(code)
        self.code, self.exit_code, self.detail = code, exit_code, detail


def _git(project: Path, *args, binary: bool = False):
    try:
        done = subprocess.run(["git", "-C", str(project), *args], capture_output=True, timeout=20, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    return done.stdout if binary else done.stdout.decode("utf-8", "replace")


def _reader(root: Path, project: Path | None = None, commit: str | None = None):
    """read(relative path) -> bytes or None.  With a commit, the raw blob from the original repository."""
    if commit is None:
        def read(relative: str):
            try:
                return (root / relative).read_bytes()
            except OSError:
                return None
        return read

    def read_blob(relative: str):
        return _git(project, "cat-file", "blob", "%s:%s" % (commit, relative), binary=True)
    return read_blob


def _decode(data: bytes, relative: str) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeError:
        raise ViewError("unreadable", 4, relative)


def module_report(root: Path, module: str, read=None) -> dict:
    """The regression view of one flow v2 module; raises ViewError for the documented errors."""
    import module_stage
    read = read or _reader(root)
    flow = module_stage.effective_tier(root, module)
    if not flow["v2"]:
        raise ViewError("not-flow-v2", 3)
    short = flow["tier"] in module_stage.SHORT_TIERS
    spec_path = "spec/%s.md" % module
    document = spec_path if short else "tasks/%s/regression.md" % module
    data = read(document)
    if data is None:
        raise ViewError("no-document", 3, document)
    requirement_bytes = data if short else read(spec_path)
    requirement = _decode(requirement_bytes, spec_path) if requirement_bytes is not None else ""
    text = _decode(data, document)
    found = criteria_ids(requirement)
    if short:
        criteria = found if flow["tier"] == "small" else None
        parsed = parse_regression(text, "short", criteria, document)
    else:
        parsed = parse_regression(text, "module", found, document)
        design = read("tasks/%s/design.md" % module)
        if design is not None and parsed["affectedCount"] == 0:
            if module_stage.impact_has_old_files(root, module, _decode(design, "tasks/%s/design.md" % module)):
                parsed["problems"].append(_problem("affected-existing-empty", document))
    return {"schemaVersion": SCHEMA_VERSION, "module": module, "usage": None, "tier": flow["tier"], "document": document,
            "sha256": hashlib.sha256(data).hexdigest(), "ref": None, "criteria": found, "cases": parsed["cases"],
            "problems": parsed["problems"]}


def usage_report(root: Path, name: str, read=None) -> dict:
    """The regression view of a multi-module requirement's integration regression."""
    from capability_map import parse_map
    read = read or _reader(root)
    document = "spec/usage/%s.regression.md" % name
    data = read(document)
    if data is None:
        raise ViewError("no-document", 3, document)
    text = _decode(data, document)
    draft = read("spec/usage/%s.md" % name)
    found = criteria_ids(_decode(draft, "spec/usage/%s.md" % name)) if draft is not None else []
    parsed = parse_regression(text, "usage", None, document)
    known = set(found)
    for sid in parsed["coverageCriteria"]:
        if sid not in known:
            parsed["problems"].append(_problem("criterion-unknown", sid))
    try:
        parsed_map = parse_map(root / "spec" / "CAPABILITY-MAP.md")
        ids = {row.module_id for row in parsed_map.rows}
    except Exception:
        ids = None
    for module in parsed["modules"]:
        if ids is not None and module not in ids:
            parsed["problems"].append(_problem("module-unknown", module))
    return {"schemaVersion": SCHEMA_VERSION, "module": None, "usage": name, "tier": None, "document": document,
            "sha256": hashlib.sha256(data).hexdigest(), "ref": None, "criteria": found, "modules": parsed["modules"],
            "cases": parsed["cases"], "problems": parsed["problems"]}


def _in_map(root: Path, module: str) -> bool | None:
    from capability_map import parse_map
    path = root / "spec" / "CAPABILITY-MAP.md"
    if not path.is_file():
        return None
    try:
        return module in {row.module_id for row in parse_map(path).rows}
    except Exception:
        return None


def at_ref(project: Path, ref: str, build):
    """Run build(root, read) on a shared local clone checked out at ref; documents come from the raw blobs."""
    commit = _git(project, "rev-parse", "--verify", "--quiet", "%s^{commit}" % ref)
    if not commit or not commit.strip():
        raise ViewError("unreadable", 4, "ref")
    commit = commit.strip()
    with tempfile.TemporaryDirectory(prefix="spec-guard-regression-") as tmp:
        clone = Path(tmp) / "repo"
        if _git(project, "clone", "--quiet", "--shared", "--no-checkout", str(project), str(clone)) is None:
            raise ViewError("unreadable", 4, "clone")
        if _git(clone, "-c", "core.autocrlf=false", "checkout", "--quiet", "--detach", commit) is None:
            raise ViewError("unreadable", 4, "checkout")
        return build(clone, _reader(clone, project, commit))


def run(project: Path, module: str | None, usage: str | None, ref: str | None) -> dict:
    def build(root: Path, read):
        if module is not None:
            here = _in_map(root, module)
            if here is None or not here:
                if ref is not None:
                    raise ViewError("not-at-ref", 3)
                raise ViewError("not-in-map", 2)
            return module_report(root, module, read)
        return usage_report(root, usage, read)
    try:
        report = at_ref(project, ref, build) if ref is not None else build(project, _reader(project))
    except ViewError as error:
        if ref is not None and error.code == "no-document":
            raise ViewError("not-at-ref", 3, error.detail)
        raise
    report["ref"] = ref
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Read a regression document into cases (read-only).")
    parser.add_argument("--json", action="store_true", required=True)
    parser.add_argument("--project", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--module")
    group.add_argument("--usage")
    parser.add_argument("--ref")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exit_:
        return 2 if exit_.code else 0
    from capability_map import MODULE_ID
    project = Path(args.project)
    if not project.is_dir():
        print("--project is not a directory", file=sys.stderr)
        return 2
    if args.module is not None and not MODULE_ID.fullmatch(args.module):
        print("not a module id", file=sys.stderr)
        return 2
    if args.usage is not None and not USAGE_NAME.fullmatch(args.usage):
        print("not a usage draft name", file=sys.stderr)
        return 2
    try:
        report = run(project, args.module, args.usage, args.ref)
    except ViewError as error:
        if error.exit_code == 2:
            print("module not in the capability map", file=sys.stderr)
            return 2
        print(json.dumps({"schemaVersion": SCHEMA_VERSION, "error": error.code}))
        return error.exit_code
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
