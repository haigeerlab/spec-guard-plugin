"""Read a delegate review report for codex-approval: a conclusion from Codex about the very file on disk, or why not.

The report is the JSON that `/delegate:review` prints on standard output (delegate interface 1.5).  Only a completed
review with a conclusion counts; the backend must be codex; a finding without `severity` counts as blocking.  The file
is bound to the report through `scope.files` (path -> sha256 of the reviewed bytes), compared with the file on disk.
Nothing is written; only `inspect_final` and `inspect_check` run read-only git.  "Codex reviewed it, so it is approved" is spec-guard's policy under the
user's takeover setting; the report itself says it authorizes nothing.
"""
import hashlib
import json
import re
import subprocess
from pathlib import Path

CONCLUSIONS = ("findings", "no_findings_in_scope")
REPORT_LIMIT = 4 * 1024 * 1024


def _invalid(reason):
    return {"status": "invalid", "reason": reason}


def inspect(report_path, project, relative):
    """{"status": "ok", "blocking", "suggestions", "sha256"} or {"status": "invalid", "reason"}."""
    try:
        path = Path(report_path)
        if path.stat().st_size > REPORT_LIMIT:
            return _invalid("report larger than %d bytes" % REPORT_LIMIT)
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        return _invalid("report unreadable: %s" % type(error).__name__)
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        return _invalid("not a delegate review report (schema_version 1)")
    if document.get("execution_status") != "completed":
        return _invalid("review not completed (execution_status %r)" % document.get("execution_status"))
    if document.get("review_outcome") not in CONCLUSIONS:
        return _invalid("review has no conclusion (review_outcome %r)" % document.get("review_outcome"))
    if document.get("backend") != "codex":
        return _invalid("backend is %r, not codex" % document.get("backend"))
    findings = document.get("findings")
    if not isinstance(findings, list) or not all(isinstance(item, dict) for item in findings):
        return _invalid("findings is not a list of findings")
    files = (document.get("scope") or {}).get("files") if isinstance(document.get("scope"), dict) else None
    if not isinstance(files, dict) or not isinstance(files.get(relative), str):
        return _invalid("%s is not in the report's scope.files" % relative)
    try:
        digest = hashlib.sha256((Path(project) / relative).read_bytes()).hexdigest()
    except OSError as error:
        return _invalid("%s unreadable: %s" % (relative, type(error).__name__))
    if files[relative] != digest:
        return _invalid("%s on disk differs from the reviewed bytes (sha256)" % relative)
    suggestions = sum(1 for item in findings if item.get("severity") == "suggestion")
    return {"status": "ok", "blocking": len(findings) - suggestions, "suggestions": suggestions, "sha256": digest}


EVIDENCE_SCHEMA = "autopilot.check-evidence/v1"
EVIDENCE_RUNNER = "autopilot-orchestrator"
ORIGIN = re.compile(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?/?$")


def _git(root, *args):
    try:
        done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def inspect_final(report_path, root, module):
    """codex-final-acceptance evidence 1: Codex reviewed the patch up to HEAD against spec/<module>.md, nothing blocking.

    {"status": "ok", "head", "sha256"} or {"status": "invalid", "reason"}.
    """
    relative = "spec/%s.md" % module
    found = inspect(report_path, root, relative)
    if found["status"] != "ok":
        return found
    if found["blocking"]:
        return _invalid("the final review has %d blocking finding(s)" % found["blocking"])
    head = _git(root, "rev-parse", "HEAD")
    if not head:
        return _invalid("HEAD unknown")
    document = json.loads(Path(report_path).read_text(encoding="utf-8"))
    baseline = document["scope"].get("baseline")
    if not isinstance(baseline, dict) or baseline.get("mode") != "commits":
        return _invalid("the final review is not over commits (scope.baseline.mode)")
    if baseline.get("to") != head:
        return _invalid("the final review ends at %r, not HEAD %s" % (baseline.get("to"), head[:12]))
    return {"status": "ok", "head": head, "sha256": found["sha256"]}


def inspect_check(root, evidence_root=None):
    """codex-final-acceptance evidence 2: autopilot's own record that a non-author ran the checks on HEAD and all passed.

    Read from <evidence_root>/<owner>__<repo>/<HEAD>.json (default ~/.autopilot/evidence); spec-guard does not judge
    authorship itself.  {"status": "ok", "head", "path"} or {"status": "invalid", "reason"}.
    """
    head = _git(root, "rev-parse", "HEAD")
    if not head:
        return _invalid("HEAD unknown")
    match = ORIGIN.search(_git(root, "remote", "get-url", "origin") or "")
    if not match:
        return _invalid("owner/repo unknown: no usable origin remote")
    folder = Path(evidence_root) if evidence_root else Path.home() / ".autopilot" / "evidence"
    path = folder / ("%s__%s" % match.groups()) / (head + ".json")
    if not path.is_file():
        return _invalid("no check evidence for HEAD %s (%s)" % (head[:12], path))
    try:
        if path.stat().st_size > REPORT_LIMIT:
            return _invalid("check evidence larger than %d bytes" % REPORT_LIMIT)
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        return _invalid("check evidence unreadable: %s" % type(error).__name__)
    if not isinstance(document, dict) or document.get("schema") != EVIDENCE_SCHEMA:
        return _invalid("check evidence is not %s" % EVIDENCE_SCHEMA)
    if document.get("runner") != EVIDENCE_RUNNER:
        return _invalid("checks were run by %r, not %s" % (document.get("runner"), EVIDENCE_RUNNER))
    if document.get("non_author") is not True:
        return _invalid("checks were not run by a non-author (non_author %r)" % document.get("non_author"))
    if document.get("head_sha") != head:
        return _invalid("checks ran on %r, not HEAD %s" % (document.get("head_sha"), head[:12]))
    checks = document.get("checks")
    if not isinstance(checks, list) or not checks or not all(isinstance(item, dict) for item in checks):
        return _invalid("check evidence lists no checks")
    failed = [item.get("cmd") for item in checks if item.get("exit") != 0 or isinstance(item.get("exit"), bool)]
    if failed:
        return _invalid("check(s) did not exit 0: %s" % ", ".join(map(str, failed)))
    return {"status": "ok", "head": head, "path": str(path)}
