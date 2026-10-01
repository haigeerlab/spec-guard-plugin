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
from local_ticket_provider import ProviderRejected


def _items(page: Any, kind: str) -> list[dict[str, Any]]:
    if (not isinstance(page, dict) or page.get("complete") is not True or
            not isinstance(page.get(kind), list)):
        raise InventoryError("publication-uncertain: provider listing is incomplete")
    return page[kind]


def _comment_text(event: dict[str, Any]) -> str:
    payload = event["payload"]
    return (str(payload.get("md", "")) + "\n\n<!-- " + EVENT_MARKER + " " +
            event["id"] + " -->")


def _has_issue_marker(body: Any, marker: str) -> bool:
    lines = str(body or "").splitlines()
    return any(
        line == marker and index >= 2 and index + 2 < len(lines) and
        lines[index - 2].startswith("Snapshot SHA-256: ") and
        lines[index - 1] == lines[index + 1] == "" and
        lines[index + 2] == "## Local history (original order)"
        for index, line in enumerate(lines)
    )


def _has_comment_marker(body: Any, marker: str) -> bool:
    lines = str(body or "").splitlines()
    return bool(lines) and lines[-1] == marker


def _contains_marker(body: Any, marker: str) -> bool:
    return marker in str(body or "")


def publish_preview(preview: dict[str, Any], project: Path, runtime_dir: Path,
                    provider: Any, journal_root: Path | None = None,
                    confirm: bool = False) -> dict[str, Any]:
    """Recheck source/target, then create or reconcile exactly one remote issue."""
    if not confirm:
        raise InventoryError("confirmation-required: handoff needs explicit confirmation")
    if (preview.get("formatVersion") not in (1, 2) or preview.get("state") != "preview" or
            not isinstance(preview.get("source"), dict) or
            not isinstance(preview.get("destination"), dict) or
            not isinstance(preview.get("body"), str)):
        raise InventoryError("preview-invalid: handoff preview is incomplete")
    source = preview["source"]
    destination = preview["destination"]
    version = preview["formatVersion"]
    fresh = snapshot_issue(project, source["issueId"], runtime_dir, legacy=version == 1)
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
        if earlier and earlier.get("digestVersion", 1) != version:
            return {"state": "preview-incompatible",
                    "diagnostic": "existing handoff uses another format; regenerate with --legacy-format if version 1"}
        rejected_before_write = bool(
            earlier and earlier.get("state") == "planned" and
            earlier.get("createAttempted") is False and
            earlier.get("remoteId") is None and
            type(earlier.get("rejectionStatus")) is int
        )
        if (earlier and earlier.get("sourceDigest") != source["sourceDigest"] and
                not rejected_before_write):
            write_entry(path, key, {**earlier, "state": "conflict"})
            return {"state": "conflict", "diagnostic": "source history diverged"}
        issues = _items(provider.list_issues(), "issues")
        if any(_contains_marker(issue.get("body"), marker) and
               not _has_issue_marker(issue.get("body"), marker)
               for issue in issues if not issue.get("isPullRequest")):
            write_entry(path, key, {**(earlier or {}), "state": "conflict",
                                    "digestVersion": version,
                                    "sourceDigest": source["sourceDigest"],
                                    "destination": destination,
                                    "reason": "marker outside managed section"})
            return {"state": "conflict", "diagnostic": "destination marker is ambiguous"}
        matches = [issue for issue in issues if not issue.get("isPullRequest") and
                   _has_issue_marker(issue.get("body"), marker)]
        if len(matches) > 1:
            write_entry(path, key, {"state": "conflict", "digestVersion": version,
                                    "sourceDigest": source["sourceDigest"],
                                    "destination": destination, "reason": "multiple markers"})
            return {"state": "conflict", "diagnostic": "multiple destination issues"}
        found_existing = bool(matches)
        if matches:
            issue = matches[0]
        else:
            if earlier and earlier.get("createAttempted"):
                return {"state": "publication-uncertain",
                        "diagnostic": "prior create attempt is not visible; manual reconciliation required"}
            if version == 1:
                return {"state": "preview-incompatible",
                        "diagnostic": "legacy format requires an existing remote handoff"}
            entry = {"state": "planned", "digestVersion": version,
                     "sourceDigest": source["sourceDigest"],
                     "destination": destination, "createAttempted": True,
                     "remoteId": None, "verifiedEventIds": []}
            write_entry(path, key, entry)
            try:
                issue = provider.create_issue(preview["title"], preview["body"])
            except ProviderRejected as error:
                write_entry(path, key, {**entry, "createAttempted": False,
                                        "rejectionStatus": error.status_code})
                return {"state": "provider-rejected", "diagnostic": str(error)}
            except Exception:
                issues = _items(provider.list_issues(), "issues")
                if any(_contains_marker(item.get("body"), marker) and
                       not _has_issue_marker(item.get("body"), marker)
                       for item in issues if not item.get("isPullRequest")):
                    write_entry(path, key, {**entry, "state": "conflict",
                                            "reason": "marker outside managed section"})
                    return {"state": "conflict",
                            "diagnostic": "destination marker is ambiguous"}
                matches = [item for item in issues if not item.get("isPullRequest") and
                           _has_issue_marker(item.get("body"), marker)]
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
            write_entry(path, key, {"state": "conflict", "digestVersion": version,
                                    "sourceDigest": source["sourceDigest"],
                                    "destination": destination, "remoteId": remote_id,
                                    "reason": "remote issue edited"})
            return {"state": "conflict", "diagnostic": "remote issue was edited"}
        desired_closed = bool(source["issue"].get("isClosed"))
        if (not isinstance(current.get("closed"), bool) or
                (earlier and earlier.get("stateVerified") and
                 current["closed"] != earlier.get("remoteClosed")) or
                (not earlier and found_existing and current["closed"] != desired_closed)):
            write_entry(path, key, {**(earlier or {}), "state": "conflict",
                                    "digestVersion": version,
                                    "sourceDigest": source["sourceDigest"],
                                    "destination": destination, "remoteId": remote_id,
                                    "reason": "remote state changed"})
            return {"state": "conflict", "diagnostic": "remote issue state changed"}
        entry = {"state": "partial", "digestVersion": version,
                 "sourceDigest": source["sourceDigest"],
                 "destination": destination, "remoteId": remote_id,
                 "remoteUrl": current.get("url"), "createAttempted": True,
                 "commentAttempts": (earlier or {}).get("commentAttempts", []),
                 "verifiedEventIds": [event["id"] for event in source["events"]],
                 "stateVerified": bool((earlier or {}).get("stateVerified")),
                 "remoteClosed": (earlier or {}).get("remoteClosed")}
        write_entry(path, key, entry)
        for event_id, body in expected_comments.items():
            comments = _items(provider.list_comments(remote_id), "comments")
            comment_marker = "<!-- " + EVENT_MARKER + " " + event_id + " -->"
            if any(_contains_marker(item.get("body"), comment_marker) and
                   not _has_comment_marker(item.get("body"), comment_marker)
                   for item in comments):
                write_entry(path, key, {**entry, "state": "conflict",
                                        "reason": "comment marker outside managed end"})
                return {"state": "conflict", "diagnostic": "comment marker is ambiguous"}
            matches = [item for item in comments if
                       _has_comment_marker(item.get("body"), comment_marker)]
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
                except ProviderRejected as error:
                    entry["commentAttempts"].remove(event_id)
                    write_entry(path, key, {**entry, "rejectionStatus": error.status_code})
                    return {"state": "provider-rejected", "diagnostic": str(error)}
                except Exception:
                    comments = _items(provider.list_comments(remote_id), "comments")
                    if sum(item.get("body") == body for item in comments) != 1:
                        return {"state": "publication-uncertain",
                                "diagnostic": "comment result unavailable; do not retry automatically"}
            comments = _items(provider.list_comments(remote_id), "comments")
            if sum(item.get("body") == body for item in comments) != 1:
                return {"state": "publication-uncertain",
                        "diagnostic": "comment readback differs"}
        current_state = provider.get_issue(remote_id).get("closed")
        if not isinstance(current_state, bool) or (earlier and earlier.get("stateVerified") and
                                                   current_state != earlier.get("remoteClosed")):
            write_entry(path, key, {**entry, "state": "conflict",
                                    "reason": "remote state changed"})
            return {"state": "conflict", "diagnostic": "remote issue state changed"}
        if current_state != desired_closed:
            provider.set_closed(remote_id, desired_closed)
        final = provider.get_issue(remote_id)
        comments = _items(provider.list_comments(remote_id), "comments")
        if (final.get("body") != preview["body"] or final.get("title") != preview["title"]
                or not isinstance(final.get("url"), str) or not final["url"]
                or bool(final.get("closed")) != desired_closed or any(
                    sum(item.get("body") == body for item in comments) != 1
                    for body in expected_comments.values())):
            return {"state": "publication-uncertain", "diagnostic": "final readback differs"}
        entry["stateVerified"] = True
        entry["remoteClosed"] = desired_closed
        write_entry(path, key, entry)
        if source["attachments"]:
            return {"state": "partial", "remoteId": remote_id,
                    "diagnostic": "attachments are not verified on destination"}
        write_entry(path, key, {**entry, "state": "verified"})
        return {"state": "verified", "remoteId": remote_id,
                "remoteUrl": final.get("url"), "eventCount": len(source["events"])}
