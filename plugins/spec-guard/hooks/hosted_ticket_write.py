"""Preview and reconcile one authorized hosted Issue creation."""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any

from hosted_ticket_provider import HostedTicketError, ProviderRejected
from hosted_ticket_read import MARKER, REQUEST_ID, inspect_ticket


def _digest(value: dict[str, Any]) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def draft_preview(target: dict[str, Any], request_id: str,
                  title: str, body: str) -> dict[str, Any]:
    if (not REQUEST_ID.fullmatch(request_id) or not title.strip() or not body.strip() or
            MARKER in body):
        return {"state": "preview-invalid", "diagnostic": "content-or-identity-invalid"}
    marker = "<!-- " + MARKER + " " + request_id + " -->"
    complete_body = body.rstrip("\n") + "\n\n" + marker
    preview = {"state": "preview", "target": target,
               "requestId": request_id, "title": title, "body": complete_body,
               "rootCauseReviewRequired": True}
    return {**preview, "digest": _digest(preview)}


def make_preview(provider: Any, visibility: str, request_id: str,
                 title: str, body: str) -> dict[str, Any]:
    inspection = inspect_ticket(provider, visibility, request_id, title)
    if inspection["state"] != "absent":
        return inspection
    return draft_preview(inspection["target"], request_id, title, body)


def _private_root(root: Path) -> None:
    if root.is_symlink():
        raise HostedTicketError("intent-unsafe: root is a symlink")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not root.is_dir() or stat.S_IMODE(root.stat().st_mode) != 0o700:
        raise HostedTicketError("intent-unsafe: root must have mode 0700")


def _read_intent(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    if path.is_symlink() or stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise HostedTicketError("intent-unsafe: record must have mode 0600")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise HostedTicketError("intent-unknown: record is unreadable") from error
    if (not isinstance(record, dict) or record.get("version") != 1 or
            not isinstance(record.get("digest"), str) or
            not isinstance(record.get("attempted"), bool)):
        raise HostedTicketError("intent-unknown: record is invalid")
    return record


def _write_intent(path: Path, record: dict[str, Any]) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=".intent-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(record, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _same_issue(issue: dict[str, Any], preview: dict[str, Any]) -> bool:
    return (issue.get("title") == preview["title"] and
            issue.get("body", "").rstrip("\n") == preview["body"].rstrip("\n") and
            isinstance(issue.get("id"), int) and issue["id"] > 0 and
            isinstance(issue.get("url"), str))


def publish_preview(preview: dict[str, Any], provider: Any, intent_root: Path,
                    confirm: bool = False,
                    root_cause_reviewed: bool = False) -> dict[str, Any]:
    if not confirm:
        return {"state": "confirmation-required"}
    if not root_cause_reviewed:
        return {"state": "review-required", "diagnostic": "root-cause-review-required"}
    if (preview.get("state") != "preview" or
            not isinstance(preview.get("requestId"), str) or
            not REQUEST_ID.fullmatch(preview["requestId"]) or
            not isinstance(preview.get("title"), str) or
            not isinstance(preview.get("body"), str) or
            not isinstance(preview.get("target"), dict) or
            preview.get("digest") != _digest({key: value for key, value in preview.items()
                                               if key != "digest"}) or
            preview["body"].splitlines()[-1] !=
            "<!-- " + MARKER + " " + preview["requestId"] + " -->"):
        return {"state": "preview-invalid"}
    target = preview["target"]
    identity = "/".join(str(target.get(key, "")) for key in
                        ("platform", "host", "target", "targetId")) + "/" + preview["requestId"]
    key = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    root = Path(intent_root)
    try:
        _private_root(root)
        lock = os.open(root / (key + ".lock"),
                       os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(lock, "r+") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            path = root / (key + ".json")
            earlier = _read_intent(path)
            if earlier and earlier["digest"] != preview["digest"]:
                return {"state": "conflict", "diagnostic": "intent-content-changed"}
            inspection = inspect_ticket(provider, target.get("visibility", ""),
                                        preview["requestId"], preview["title"])
            if inspection.get("target") != target and inspection["state"] != "unknown":
                return {"state": "unknown", "diagnostic": "target-changed"}
            if inspection["state"] == "found":
                issue = inspection["issue"]
                if not _same_issue(issue, preview):
                    return {"state": "conflict", "diagnostic": "remote-content-changed"}
                if earlier:
                    path.unlink()
                return {"state": "found", "issue": issue}
            if inspection["state"] != "absent":
                return inspection
            if earlier and earlier["attempted"]:
                return {"state": "unknown", "diagnostic": "prior-create-not-visible"}
            record = {"version": 1, "digest": preview["digest"],
                      "target": target, "requestId": preview["requestId"],
                      "attempted": True}
            _write_intent(path, record)
            try:
                created = provider.create_issue(preview["title"], preview["body"])
            except ProviderRejected as error:
                _write_intent(path, {**record, "attempted": False,
                                     "rejectionStatus": error.status_code})
                return {"state": "rejected", "statusCode": error.status_code}
            except HostedTicketError:
                created = None
            if isinstance(created, dict) and isinstance(created.get("id"), int):
                try:
                    current = provider.get_issue(created["id"])
                except HostedTicketError:
                    current = None
                if current is not None:
                    if not _same_issue(current, preview):
                        return {"state": "conflict", "diagnostic": "remote-content-changed"}
                    path.unlink()
                    return {"state": "verified", "issue": current}
            recovered = inspect_ticket(provider, target.get("visibility", ""),
                                       preview["requestId"], preview["title"])
            if recovered["state"] == "found" and _same_issue(recovered["issue"], preview):
                path.unlink()
                return {"state": "verified", "issue": recovered["issue"]}
            if recovered["state"] == "conflict":
                return recovered
            return {"state": "unknown", "diagnostic": "create-result-uncertain"}
    except (OSError, HostedTicketError) as error:
        return {"state": "unknown", "diagnostic": str(error)}
