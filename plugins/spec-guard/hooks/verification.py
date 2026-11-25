#!/usr/bin/env python3
"""verification-criteria: the pre-merge verification (step 7) of a flow v2 module, as spec-guard sees it.

    verification.py author --project <root> --module <id>
    verification.py check  --project <root> (--module <id> | --usage <name>) --report <path> [--json]
    verification.py record --project <root> (--module <id> | --usage <name>) --report <path> [--confirm]

`author` records the session writing the module (its id read from CLAUDE_CODE_SESSION_ID or CODEX_THREAD_ID, never
from the command line).  `check` says whether a spec-guard.verification/v1 report stands; it is read-only.  `record`
writes a standing report's verdict.  Records live in the common git directory, never in a commit.
Exit codes: 0 ok / established; 1 the report does not stand; 2 usage error, not in the capability map, not a flow v2
module, no session id; 3 cannot judge (no author record, git unreadable, no regression document).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SCHEMA = "spec-guard.verification/v1"
SCHEMA_VERSION = 1
AUTHORS_DIR = "spec-guard/authors"
RECORDS_DIR = "spec-guard/verification"
REPORT_LIMIT = 1 << 20
VERDICTS = ("pass", "pass-with-notes", "fail")
RESULTS = ("pass", "fail", "baseline-fail")
FAIL_CATEGORIES = ("run-failure", "user-bug", "check-failure", "wrong-doc")
EVIDENCE_TYPES = ("log", "screenshot", "file", "user-quote")
SESSION_ENV = (("CLAUDE_CODE_SESSION_ID", "claude-code"), ("CODEX_THREAD_ID", "codex"))
PROBLEM_CODES = ("report-invalid", "regression-changed", "case-missing", "case-unknown", "method-mismatch",
                 "manual-without-user", "fail-category-missing", "fail-evidence-missing", "baseline-evidence-missing",
                 "evidence-sha-mismatch", "verdict-inconsistent", "executor-is-author", "patch-mismatch",
                 "patch-id-wrong", "author-unknown")
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA64 = re.compile(r"^[0-9a-f]{64}$")


class Refused(Exception):
    def __init__(self, code: str, exit_code: int, detail: str = ""):
        super().__init__(code)
        self.code, self.exit_code, self.detail = code, exit_code, detail


def _git(root: Path, *args, data: bytes | None = None) -> bytes | None:
    try:
        done = subprocess.run(["git", "-C", str(root), *args], input=data, capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def _text(raw: bytes | None) -> str | None:
    return raw.decode("utf-8", "replace").strip() if raw is not None else None


def _common(root: Path) -> Path | None:
    found = _text(_git(root, "rev-parse", "--git-common-dir"))
    if not found:
        return None
    path = Path(found)
    return path if path.is_absolute() else Path(root) / path


def _record_path(root: Path, kind: str, name: str) -> Path | None:
    common = _common(root)
    return None if common is None else common / kind / ("%s.json" % name)


def _write_atomic(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    handle, temp = tempfile.mkstemp(prefix=".tmp-", dir=str(path.parent))
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temp, path)
    except BaseException:
        try:
            os.unlink(temp)
        except OSError:
            pass
        raise
    if json.loads(path.read_text(encoding="utf-8")) != value:
        raise OSError("read-back mismatch")


def _read_json(path: Path | None):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path is not None and path.is_file() else None
    except (OSError, UnicodeError, ValueError):
        return None


# ── patch id ──

def default_branch(root: Path) -> str | None:
    ref = _text(_git(root, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"))
    if ref:
        return ref
    return "main" if _git(root, "rev-parse", "--verify", "--quiet", "main^{commit}") is not None else None


def patch_id(root: Path, base: str, head: str) -> str | None:
    """The first column of `git diff base head | git patch-id --stable`; None when a commit is unreadable or empty."""
    diff = _git(root, "diff", base, head)
    if diff is None:
        return None
    out = _text(_git(root, "patch-id", "--stable", data=diff))
    return out.split()[0] if out else None


def current_patch_id(root: Path) -> str | None:
    """The patch from the merge-base of the default branch and HEAD to HEAD; unchanged by a rebase."""
    branch = default_branch(root)
    base = _text(_git(root, "merge-base", branch, "HEAD")) if branch else None
    return patch_id(root, base, "HEAD") if base else None


# ── authors ──

def _flow_module(root: Path, module: str) -> None:
    import module_stage
    from capability_map import parse_map
    try:
        ids = {row.module_id for row in parse_map(root / "spec" / "CAPABILITY-MAP.md").rows}
    except Exception:
        raise Refused("map-unreadable", 2)
    if module not in ids:
        raise Refused("not-in-map", 2)
    if not module_stage.flow_marker(root, module)["v2"]:
        raise Refused("not-flow-v2", 2)


def authors(root: Path, module: str) -> list:
    data = _read_json(_record_path(root, AUTHORS_DIR, module))
    if not isinstance(data, list):
        return []
    return [entry for entry in data if isinstance(entry, dict) and isinstance(entry.get("sessionId"), str)]


def add_author(root: Path, module: str) -> tuple:
    """(entry, added) for the session in the environment; raises Refused."""
    from project_link import SESSION_ID
    for key, host in SESSION_ENV:
        value = os.environ.get(key, "")
        if value:
            break
    else:
        raise Refused("no-session-id", 2)
    if not SESSION_ID.fullmatch(value):
        raise Refused("no-session-id", 2, "malformed")
    _flow_module(root, module)
    path = _record_path(root, AUTHORS_DIR, module)
    if path is None:
        raise Refused("git-unreadable", 3)
    current = authors(root, module)
    for entry in current:
        if entry["sessionId"] == value:
            return entry, False
    entry = {"sessionId": value, "host": host, "at": _now()}
    _write_atomic(path, current + [entry])
    return entry, True


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── the report check ──

def _problem(code: str, where: str = "") -> dict:
    return {"code": code, "where": where}


def _document(root: Path, module: str | None, usage: str | None) -> dict:
    import regression_view
    try:
        if module is not None:
            return regression_view.module_report(root, module)
        return regression_view.usage_report(root, usage)
    except regression_view.ViewError as error:
        if error.code == "not-flow-v2":
            raise Refused("not-flow-v2", 2)
        raise Refused(error.code, 3)


def _load_report(path: Path) -> tuple:
    """(report bytes, report dict or None)."""
    try:
        data = path.read_bytes()
    except OSError:
        raise Refused("report-unreadable", 2)
    if len(data) > REPORT_LIMIT:
        return data, None
    try:
        document = json.loads(data.decode("utf-8"))
    except (UnicodeError, ValueError):
        return data, None
    return data, document if isinstance(document, dict) else None


def _evidence_list(value) -> list | None:
    if not isinstance(value, list):
        return None
    for item in value:
        if (not isinstance(item, dict) or item.get("type") not in EVIDENCE_TYPES or not isinstance(item.get("path"), str)
                or not isinstance(item.get("sha256"), str) or not SHA64.match(item["sha256"])):
            return None
    return value


def check(root: Path, module: str | None, usage: str | None, report_path: Path) -> dict:
    """{established, verdict, patchId, problems, unverified, exit, reportSha256, regressionSha256}."""
    if module is not None:
        _flow_module(root, module)
    raw, report = _load_report(report_path)
    problems, unverified = [], []
    doc = _document(root, module, usage)
    if report is None or report.get("schema") != SCHEMA:
        problems.append(_problem("report-invalid", "schema"))
        return _result(problems, unverified, None, None, raw, doc, author_known=True)
    if report.get("module") != module or report.get("usage") != usage:
        problems.append(_problem("report-invalid", "module"))
    regression = report.get("regression")
    if not isinstance(regression, dict) or regression.get("sha256") != doc["sha256"]:
        problems.append(_problem("regression-changed", doc["document"]))
    cases = report.get("cases")
    notes = report.get("notes")
    verdict = report.get("verdict")
    if not isinstance(cases, list) or not isinstance(notes, list) or verdict not in VERDICTS:
        problems.append(_problem("report-invalid", "cases, notes or verdict"))
        cases = cases if isinstance(cases, list) else []
        notes = notes if isinstance(notes, list) else []
    wanted = {case["id"]: case for case in doc["cases"]}
    seen = set()
    base = report.get("base") if isinstance(report.get("base"), str) else None
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str) or case.get("result") not in RESULTS:
            problems.append(_problem("report-invalid", "case"))
            continue
        cid = case["id"]
        seen.add(cid)
        if cid not in wanted:
            problems.append(_problem("case-unknown", cid))
            continue
        if case.get("method") != wanted[cid]["method"]:
            problems.append(_problem("method-mismatch", cid))
        evidence = _evidence_list(case.get("evidence"))
        if evidence is None:
            problems.append(_problem("report-invalid", "%s evidence" % cid))
            evidence = []
        if wanted[cid]["method"] == "manual" and not any(
                item["type"] == "user-quote" and isinstance(item.get("source"), str) and item["source"].strip()
                for item in evidence):
            problems.append(_problem("manual-without-user", cid))
        if case["result"] == "fail":
            if case.get("failCategory") not in FAIL_CATEGORIES:
                problems.append(_problem("fail-category-missing", cid))
            if not evidence:
                problems.append(_problem("fail-evidence-missing", cid))
        if case["result"] == "baseline-fail":
            commit = case.get("baselineCommit")
            if not isinstance(commit, str) or not commit or not evidence:
                problems.append(_problem("baseline-evidence-missing", cid))
            elif base is None or _git(root, "cat-file", "-e", "%s^{commit}" % commit) is None:
                unverified.append("%s baselineCommit" % cid)
            elif _git(root, "merge-base", "--is-ancestor", commit, base) is None:
                problems.append(_problem("baseline-evidence-missing", cid))
        for item in evidence:
            path = Path(item["path"])
            path = path if path.is_absolute() else report_path.parent / path
            try:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                unverified.append("%s evidence %s" % (cid, item["path"]))
                continue
            if digest != item["sha256"]:
                problems.append(_problem("evidence-sha-mismatch", cid))
    for cid in wanted:
        if cid not in seen:
            problems.append(_problem("case-missing", cid))
    if not all(isinstance(note, dict) and isinstance(note.get("title"), str) for note in notes):
        problems.append(_problem("report-invalid", "notes"))
    results = [case.get("result") for case in cases if isinstance(case, dict)]
    expected = "fail" if "fail" in results else ("pass-with-notes" if notes else "pass")
    if verdict in VERDICTS and verdict != expected:
        problems.append(_problem("verdict-inconsistent", "%s, cases say %s" % (verdict, expected)))
    executor = report.get("executor")
    session = executor.get("sessionId") if isinstance(executor, dict) else None
    if not isinstance(session, str) or not session:
        problems.append(_problem("report-invalid", "executor"))
    modules = [module] if module is not None else doc.get("modules", [])
    known = [authors(root, m) for m in modules]
    author_known = bool(modules) and all(known)
    if not author_known:
        missing = [m for m, found in zip(modules, known) if not found]
        problems.append(_problem("author-unknown", ", ".join(missing) or "no module"))
    elif session in {entry["sessionId"] for found in known for entry in found}:
        problems.append(_problem("executor-is-author", session))
    current = current_patch_id(root)
    stated = report.get("patchId")
    if current is None:
        raise Refused("git-unreadable", 3, "current patch")
    if stated != current:
        problems.append(_problem("patch-mismatch", "report %s, current %s" % (stated, current)))
    head = report.get("head")
    if isinstance(base, str) and isinstance(head, str):
        computed = patch_id(root, base, head)
        if computed is None:
            unverified.append("patch-id of base..head (a commit is not in this repository)")
        elif computed != stated:
            problems.append(_problem("patch-id-wrong", "base..head is %s" % computed))
    else:
        problems.append(_problem("report-invalid", "base or head"))
    return _result(problems, unverified, verdict, stated, raw, doc, author_known)


def _result(problems, unverified, verdict, patch, raw, doc, author_known) -> dict:
    exit_code = 0 if not problems else (3 if not author_known else 1)
    return {"established": not problems, "verdict": verdict, "patchId": patch, "problems": problems,
            "unverified": unverified, "exit": exit_code, "reportSha256": hashlib.sha256(raw).hexdigest(),
            "regressionSha256": doc["sha256"]}


# ── records ──

def _name(module: str | None, usage: str | None) -> str:
    return module if module is not None else "usage-%s" % usage


def record(root: Path, module: str | None, usage: str | None, report_path: Path, confirm: bool) -> tuple:
    """(result of check, record or None, written)."""
    result = check(root, module, usage, report_path)
    if not result["established"]:
        return result, None, False
    _raw, report = _load_report(report_path)
    entry = {"schema": SCHEMA, "module": module, "usage": usage, "verdict": report["verdict"], "patchId": report["patchId"],
             "base": report["base"], "head": report["head"], "regressionSha256": result["regressionSha256"],
             "reportSha256": result["reportSha256"], "executor": report["executor"],
             "notes": [note["title"] for note in report["notes"]], "at": _now()}
    if confirm:
        path = _record_path(root, RECORDS_DIR, _name(module, usage))
        if path is None:
            raise Refused("git-unreadable", 3)
        _write_atomic(path, entry)
    return result, entry, confirm


def verification_state(root: Path, module: str | None = None, usage: str | None = None) -> dict | None:
    """The recorded verdict, or None; `current` is true when the patch and the regression document are unchanged."""
    entry = _read_json(_record_path(root, RECORDS_DIR, _name(module, usage)))
    if not isinstance(entry, dict) or entry.get("verdict") not in VERDICTS or not isinstance(entry.get("patchId"), str):
        return None
    try:
        sha = _document(root, module, usage)["sha256"]
    except Refused:
        sha = None
    current = entry["patchId"] == current_patch_id(root) and sha is not None and entry.get("regressionSha256") == sha
    notes = entry.get("notes") if isinstance(entry.get("notes"), list) else []
    return {"verdict": entry["verdict"], "patchId": entry["patchId"], "notes": notes,
            "reportSha256": entry.get("reportSha256"), "current": current}


def passed(state: dict | None) -> bool:
    return bool(state) and state["current"] and state["verdict"] != "fail"


# ── CLI ──

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Pre-merge verification records and report check.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("author", "check", "record"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--project", required=True)
        if name == "author":
            cmd.add_argument("--module", required=True)
            continue
        group = cmd.add_mutually_exclusive_group(required=True)
        group.add_argument("--module")
        group.add_argument("--usage")
        cmd.add_argument("--report", required=True)
        if name == "check":
            cmd.add_argument("--json", action="store_true")
        else:
            cmd.add_argument("--confirm", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exit_:
        return 2 if exit_.code else 0
    from capability_map import MODULE_ID
    import regression_view
    root = Path(args.project)
    if not root.is_dir():
        print("project-not-a-directory", file=sys.stderr)
        return 2
    module = getattr(args, "module", None)
    usage = getattr(args, "usage", None)
    if module is not None and not MODULE_ID.fullmatch(module):
        print("not-a-module-id")
        return 2
    if usage is not None and not regression_view.USAGE_NAME.fullmatch(usage):
        print("not-a-usage-name")
        return 2
    try:
        if args.command == "author":
            entry, added = add_author(root, module)
            print("%s author %s (%s) of %s" % ("recorded" if added else "already recorded:", entry["sessionId"],
                                                entry["host"], module))
            return 0
        if args.command == "check":
            result = check(root, module, usage, Path(args.report))
            if args.json:
                print(json.dumps({"schemaVersion": SCHEMA_VERSION, "established": result["established"],
                                  "verdict": result["verdict"], "patchId": result["patchId"],
                                  "problems": result["problems"], "unverified": result["unverified"]}, ensure_ascii=False))
            else:
                _print_result(result)
            return result["exit"]
        result, entry, written = record(root, module, usage, Path(args.report), args.confirm)
        _print_result(result)
        if entry is None:
            print("not recorded: the report does not stand")
            return result["exit"]
        print(json.dumps(entry, ensure_ascii=False, indent=2))
        print("recorded in the common git directory (not committed)" if written else
              "preview only; nothing was written. Re-run with --confirm to apply.")
        return 0
    except Refused as error:
        if args.command == "check" and getattr(args, "json", False):
            print(json.dumps({"schemaVersion": SCHEMA_VERSION, "error": error.code}))
        else:
            print("%s%s" % (error.code, ": " + error.detail if error.detail else ""))
        return error.exit_code


def _print_result(result: dict) -> None:
    print("established" if result["established"] else "does not stand")
    for problem in result["problems"]:
        print("- %s%s" % (problem["code"], " (%s)" % problem["where"] if problem["where"] else ""))
    for item in result["unverified"]:
        print("- unverified: %s" % item)


if __name__ == "__main__":
    sys.exit(main())
