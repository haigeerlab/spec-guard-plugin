"""Conservative, per-issue handoff reconciliation independent of provider transport."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from local_ticket_handoff import snapshot_issue
from local_ticket_journal import (
    entry_key, journal_path, publication_lock, read_journal, write_entry,
)
from local_ticket_portability import InventoryError
from local_ticket_preview import EVENT_MARKER, ISSUE_MARKER, render_body


def _items(page: Any, kind: str) -> list[dict[str, Any]]:
    if (not isinstance(page, dict) or page.get("complete") is not True or
            not isinstance(page.get(kind), list)):
        raise InventoryError("publication-uncertain: provider listing is incomplete")
    return page[kind]


def _comment_text(event: dict[str, Any]) -> str:
    payload = event["payload"]
    return (str(payload.get("md", "")) + "\n\n<!-- " + EVENT_MARKER + " " +
            event["id"] + " -->")


def publish_preview(preview: dict[str, Any], project: Path, runtime_dir: Path,
                    provider: Any, journal_root: Path | None = None,
                    confirm: bool = False) -> dict[str, Any]:
    """Recheck source/target, then create or reconcile exactly one remote issue."""
    if not confirm:
        raise InventoryError("confirmation-required: handoff needs explicit confirmation")
    if (preview.get("formatVersion") != 1 or preview.get("state") != "preview" or
            not isinstance(preview.get("source"), dict) or
            not isinstance(preview.get("destination"), dict) or
            not isinstance(preview.get("body"), str)):
        raise InventoryError("preview-invalid: handoff preview is incomplete")
    source = preview["source"]
    destination = preview["destination"]
    fresh = snapshot_issue(project, source["issueId"], runtime_dir)
    if (fresh != source or preview["body"] != render_body(fresh) or
            preview.get("title") != fresh["issue"]["title"]):
        raise InventoryError("preview-stale: Local source changed")
    if provider.target_facts() != destination:
        raise InventoryError("preview-stale: remote target facts changed")
    path = journal_path(project, source["projectId"], journal_root)
    key = entry_key(source["projectId"], source["issueId"], destination)
    marker = "<!-- " + ISSUE_MARKER + " " + source["projectId"] + "/" + source["issueId"] + " -->"
    expected_comments = {
        event["id"]: _comment_text(event)
        for event in source["events"] if event["action"] == "add.issue.comment"
    }

    with publication_lock(path, key):
        earlier = read_journal(path)["entries"].get(key)
        if earlier and earlier.get("sourceDigest") != source["sourceDigest"]:
            write_entry(path, key, {**earlier, "state": "conflict"})
            return {"state": "conflict", "diagnostic": "source history diverged"}
        issues = _items(provider.list_issues(), "issues")
        matches = [issue for issue in issues if not issue.get("isPullRequest") and
                   marker in str(issue.get("body", "")).splitlines()]
        if len(matches) > 1:
            write_entry(path, key, {"state": "conflict", "sourceDigest": source["sourceDigest"],
                                    "destination": destination, "reason": "multiple markers"})
            return {"state": "conflict", "diagnostic": "multiple destination issues"}
        if matches:
            issue = matches[0]
        else:
            if earlier and earlier.get("createAttempted"):
                return {"state": "publication-uncertain",
                        "diagnostic": "prior create attempt is not visible; manual reconciliation required"}
            entry = {"state": "planned", "sourceDigest": source["sourceDigest"],
                     "destination": destination, "createAttempted": True,
                     "remoteId": None, "verifiedEventIds": []}
            write_entry(path, key, entry)
            try:
                issue = provider.create_issue(preview["title"], preview["body"])
            except Exception:
                issues = _items(provider.list_issues(), "issues")
                matches = [item for item in issues if not item.get("isPullRequest") and
                           marker in str(item.get("body", "")).splitlines()]
                if len(matches) > 1:
                    write_entry(path, key, {**entry, "state": "conflict",
                                            "reason": "multiple markers"})
                    return {"state": "conflict", "diagnostic": "multiple destination issues"}
                if len(matches) != 1:
                    write_entry(path, key, {**entry, "state": "partial"})
                    return {"state": "publication-uncertain",
                            "diagnostic": "create result unavailable; do not retry automatically"}
                issue = matches[0]
        remote_id = issue.get("id")
        if not isinstance(remote_id, int) or remote_id <= 0:
            raise InventoryError("publication-uncertain: remote issue identity is invalid")
        current = provider.get_issue(remote_id)
        if (current.get("body") != preview["body"] or
                current.get("title") != preview["title"]):
            write_entry(path, key, {"state": "conflict", "sourceDigest": source["sourceDigest"],
                                    "destination": destination, "remoteId": remote_id,
                                    "reason": "remote issue edited"})
            return {"state": "conflict", "diagnostic": "remote issue was edited"}
        entry = {"state": "partial", "sourceDigest": source["sourceDigest"],
                 "destination": destination, "remoteId": remote_id,
                 "remoteUrl": current.get("url"), "createAttempted": True,
                 "commentAttempts": (earlier or {}).get("commentAttempts", []),
                 "verifiedEventIds": [event["id"] for event in source["events"]]}
        write_entry(path, key, entry)
        for event_id, body in expected_comments.items():
            comments = _items(provider.list_comments(remote_id), "comments")
            comment_marker = "<!-- " + EVENT_MARKER + " " + event_id + " -->"
            matches = [item for item in comments if comment_marker in
                       str(item.get("body", "")).splitlines()]
            if len(matches) > 1:
                write_entry(path, key, {**entry, "state": "conflict", "reason": "duplicate comment"})
                return {"state": "conflict", "diagnostic": "duplicate remote comment"}
            if matches and matches[0].get("body") != body:
                write_entry(path, key, {**entry, "state": "conflict", "reason": "comment edited"})
                return {"state": "conflict", "diagnostic": "remote comment was edited"}
            if not matches:
                if event_id in entry["commentAttempts"]:
                    return {"state": "publication-uncertain",
                            "diagnostic": "prior comment attempt is not visible"}
                entry["commentAttempts"].append(event_id)
                write_entry(path, key, entry)
                try:
                    provider.create_comment(remote_id, body)
                except Exception:
                    comments = _items(provider.list_comments(remote_id), "comments")
                    if sum(item.get("body") == body for item in comments) != 1:
                        return {"state": "publication-uncertain",
                                "diagnostic": "comment result unavailable; do not retry automatically"}
            comments = _items(provider.list_comments(remote_id), "comments")
            if sum(item.get("body") == body for item in comments) != 1:
                return {"state": "publication-uncertain",
                        "diagnostic": "comment readback differs"}
        desired_closed = bool(source["issue"].get("isClosed"))
        if bool(provider.get_issue(remote_id).get("closed")) != desired_closed:
            provider.set_closed(remote_id, desired_closed)
        final = provider.get_issue(remote_id)
        comments = _items(provider.list_comments(remote_id), "comments")
        if (final.get("body") != preview["body"] or final.get("title") != preview["title"]
                or not isinstance(final.get("url"), str) or not final["url"]
                or bool(final.get("closed")) != desired_closed or any(
                    sum(item.get("body") == body for item in comments) != 1
                    for body in expected_comments.values())):
            return {"state": "publication-uncertain", "diagnostic": "final readback differs"}
        if source["attachments"]:
            return {"state": "partial", "remoteId": remote_id,
                    "diagnostic": "attachments are not verified on destination"}
        write_entry(path, key, {**entry, "state": "verified"})
        return {"state": "verified", "remoteId": remote_id,
                "remoteUrl": final.get("url"), "eventCount": len(source["events"])}
