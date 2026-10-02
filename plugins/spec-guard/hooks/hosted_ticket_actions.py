"""Conservative comment and delivery-close operations for one hosted Issue."""
from __future__ import annotations

import fcntl
import hashlib
import os
from pathlib import Path
from typing import Any

from hosted_ticket_provider import HostedTicketError, ProviderRejected
from hosted_ticket_read import REQUEST_ID
from hosted_ticket_write import _digest, _private_root, _read_intent, _write_intent


COMMENT_MARKER = "spec-guard-hosted-comment:v1"


def _comment_matches(provider: Any, issue_id: int,
                     marker: str) -> dict[str, Any]:
    listing = provider.list_comments(issue_id)
    if listing.get("complete") is not True or not isinstance(listing.get("comments"), list):
        return {"state": "unknown", "diagnostic": "comments-incomplete"}
    matches, displaced = [], []
    for comment in listing["comments"]:
        body = comment.get("body") if isinstance(comment, dict) else None
        if not isinstance(body, str):
            return {"state": "unknown", "diagnostic": "comments-incomplete"}
        if marker in body:
            lines = body.splitlines()
            (matches if lines.count(marker) == 1 and lines[-1] == marker
             else displaced).append(comment)
    if displaced or len(matches) > 1:
        return {"state": "conflict", "diagnostic": "comment-marker-ambiguous"}
    return {"state": "found", "comment": matches[0]} if matches else {"state": "absent"}


def make_comment_preview(provider: Any, issue_id: int, event_id: str,
                         message: str) -> dict[str, Any]:
    if (not isinstance(issue_id, int) or issue_id <= 0 or
            not REQUEST_ID.fullmatch(event_id) or not message.strip() or
            COMMENT_MARKER in message):
        return {"state": "preview-invalid"}
    try:
        target = provider.target_facts()
        issue = provider.get_issue(issue_id)
        if issue.get("closed") is True:
            return {"state": "incomplete", "diagnostic": "issue-already-closed"}
        marker = "<!-- " + COMMENT_MARKER + " " + event_id + " -->"
        existing = _comment_matches(provider, issue_id, marker)
        if existing["state"] != "absent":
            return existing
        preview = {"state": "preview", "target": target, "issueId": issue_id,
                   "issueUrl": issue["url"], "eventId": event_id,
                   "body": message.rstrip("\n") + "\n\n" + marker}
        return {**preview, "digest": _digest(preview)}
    except Exception:
        return {"state": "unknown", "diagnostic": "provider-unavailable"}


def publish_comment(preview: dict[str, Any], provider: Any, intent_root: Path,
                    confirm: bool = False) -> dict[str, Any]:
    if not confirm:
        return {"state": "confirmation-required"}
    if (preview.get("state") != "preview" or
            not isinstance(preview.get("eventId"), str) or
            not REQUEST_ID.fullmatch(preview["eventId"]) or
            not isinstance(preview.get("body"), str) or
            not isinstance(preview.get("issueId"), int) or
            not isinstance(preview.get("target"), dict) or
            preview.get("digest") != _digest({key: value for key, value in preview.items()
                                               if key != "digest"})):
        return {"state": "preview-invalid"}
    marker = "<!-- " + COMMENT_MARKER + " " + preview["eventId"] + " -->"
    if preview["body"].splitlines()[-1] != marker:
        return {"state": "preview-invalid"}
    target = preview["target"]
    identity = "/".join(str(target.get(key, "")) for key in
                        ("platform", "host", "target", "targetId"))
    key = hashlib.sha256((identity + "/" + str(preview["issueId"]) +
                          "/" + preview["eventId"]).encode()).hexdigest()
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
            if provider.target_facts() != target:
                return {"state": "unknown", "diagnostic": "target-changed"}
            issue = provider.get_issue(preview["issueId"])
            if issue.get("url") != preview["issueUrl"] or issue.get("closed") is True:
                return {"state": "unknown", "diagnostic": "issue-changed"}
            existing = _comment_matches(provider, preview["issueId"], marker)
            if existing["state"] == "found":
                if existing["comment"]["body"] != preview["body"]:
                    return {"state": "conflict", "diagnostic": "comment-content-changed"}
                if earlier:
                    path.unlink()
                return {"state": "found", "issue": issue}
            if existing["state"] != "absent":
                return existing
            if earlier and earlier["attempted"]:
                return {"state": "unknown", "diagnostic": "prior-comment-not-visible"}
            record = {"version": 1, "digest": preview["digest"],
                      "target": target, "eventId": preview["eventId"],
                      "issueId": preview["issueId"], "attempted": True}
            _write_intent(path, record)
            try:
                provider.create_comment(preview["issueId"], preview["body"])
            except ProviderRejected as error:
                _write_intent(path, {**record, "attempted": False,
                                     "rejectionStatus": error.status_code})
                return {"state": "rejected", "statusCode": error.status_code}
            except Exception:
                pass
            existing = _comment_matches(provider, preview["issueId"], marker)
            if existing["state"] == "found" and existing["comment"]["body"] == preview["body"]:
                path.unlink()
                return {"state": "verified", "issue": issue}
            if existing["state"] == "conflict":
                return existing
            return {"state": "unknown", "diagnostic": "comment-result-uncertain"}
    except Exception:
        return {"state": "unknown", "diagnostic": "provider-or-intent-unavailable"}


def make_close_preview(provider: Any, issue_id: int, delivery_id: int,
                       coverage_complete: bool,
                       validation_evidence: str) -> dict[str, Any]:
    if (not isinstance(issue_id, int) or issue_id <= 0 or
            not isinstance(delivery_id, int) or delivery_id <= 0 or
            coverage_complete is not True or not validation_evidence.strip()):
        return {"state": "incomplete", "diagnostic": "coverage-or-validation-missing"}
    try:
        target = provider.target_facts()
        issue = provider.get_issue(issue_id)
        delivery = provider.get_delivery(delivery_id)
        if delivery.get("merged") is not True or not delivery.get("mergeCommit"):
            return {"state": "incomplete", "diagnostic": "delivery-not-merged"}
        if issue.get("closed") is True:
            return {"state": "already-closed", "issue": issue}
        preview = {"state": "preview", "target": target, "issueId": issue_id,
                   "issueUrl": issue["url"], "deliveryId": delivery_id,
                   "deliveryUrl": delivery["url"],
                   "mergeCommit": delivery["mergeCommit"],
                   "issueContentDigest": _digest({"title": issue["title"],
                                                  "body": issue["body"]}),
                   "validationEvidence": validation_evidence.strip(),
                   "coverageComplete": True}
        return {**preview, "digest": _digest(preview)}
    except Exception:
        return {"state": "unknown", "diagnostic": "provider-unavailable"}


def close_issue(preview: dict[str, Any], provider: Any,
                confirm: bool = False) -> dict[str, Any]:
    if not confirm:
        return {"state": "confirmation-required"}
    if (preview.get("state") != "preview" or
            preview.get("coverageComplete") is not True or
            not isinstance(preview.get("validationEvidence"), str) or
            not preview["validationEvidence"].strip() or
            preview.get("digest") != _digest({key: value for key, value in preview.items()
                                               if key != "digest"})):
        return {"state": "preview-invalid"}
    try:
        if provider.target_facts() != preview["target"]:
            return {"state": "unknown", "diagnostic": "target-changed"}
        delivery = provider.get_delivery(preview["deliveryId"])
        if (delivery.get("merged") is not True or
                delivery.get("mergeCommit") != preview["mergeCommit"] or
                delivery.get("url") != preview["deliveryUrl"]):
            return {"state": "incomplete", "diagnostic": "delivery-changed"}
        issue = provider.get_issue(preview["issueId"])
        if issue.get("url") != preview["issueUrl"]:
            return {"state": "unknown", "diagnostic": "issue-changed"}
        if _digest({"title": issue["title"], "body": issue["body"]}) != \
                preview.get("issueContentDigest"):
            return {"state": "incomplete", "diagnostic": "issue-content-changed"}
        if issue.get("closed") is True:
            return {"state": "already-closed", "issue": issue}
        try:
            provider.set_closed(preview["issueId"])
        except Exception:
            pass
        current = provider.get_issue(preview["issueId"])
        if current.get("closed") is True:
            return {"state": "verified", "issue": current,
                    "mergeCommit": preview["mergeCommit"]}
        return {"state": "unknown", "diagnostic": "close-result-uncertain"}
    except Exception:
        return {"state": "unknown", "diagnostic": "provider-unavailable"}
