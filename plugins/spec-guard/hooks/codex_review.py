"""Read a delegate review report for codex-approval: a conclusion from Codex about the very file on disk, or why not.

The report is the JSON that `/delegate:review` prints on standard output (delegate interface 1.5).  Only a completed
review with a conclusion counts; the backend must be codex; a finding without `severity` counts as blocking.  The file
is bound to the report through `scope.files` (path -> sha256 of the reviewed bytes), compared with the file on disk.
Nothing is written and no other process is run.  "Codex reviewed it, so it is approved" is spec-guard's policy under the
user's takeover setting; the report itself says it authorizes nothing.
"""
import hashlib
import json
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
