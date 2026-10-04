"""GitHub adapter for Proposal closeout: read the item, comment, move the stage, close.

The identity rules live in `proposal_tracker_read`; this file only moves bytes.  It
reuses `hosted_ticket_provider`'s transport so there is one place that decides what a
failed request, a definite rejection and an exhausted pagination mean.

`list_issues` and `get_issue` return GitHub's own shape, not a normalized one, because
`recover_tracker_issue` already knows how to read it -- so the identity rules apply to
exactly the bytes the API returned, with no adapter-shaped layer in between to drift.
"""
from __future__ import annotations

import re
from typing import Any, Callable
from urllib.parse import urlparse

from hosted_ticket_provider import (
    HostedTicketError, PAGE_SIZE, pages, run_json, run_write_json,
)


class GitHubCloseout:
    def __init__(self, host: str, target: str,
                 runner: Callable[[list[str]], Any] = run_json,
                 writer: Callable[[list[str], dict[str, Any]], Any] = run_write_json):
        if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]{0,252}", host or "") or
                not isinstance(target, str) or
                not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}"
                                 r"/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", target or "")):
            raise HostedTicketError("target-invalid: host or repository is invalid")
        self.host, self.target = host, target
        self.runner, self.writer = runner, writer
        self.base = "repos/" + target + "/issues"

    # ── reads ─────────────────────────────────────────────────────────────
    def _get(self, endpoint: str) -> Any:
        return self.runner(["gh", "api", "--hostname", self.host, endpoint])

    def _write(self, method: str, endpoint: str,
               body: dict[str, Any] | None = None) -> Any:
        return self.writer(["gh", "api", "--hostname", self.host,
                            "--method", method, endpoint], {} if body is None else body)

    def target_facts(self) -> dict[str, Any]:
        raw = self._get("repos/" + self.target)
        if (not isinstance(raw, dict) or raw.get("full_name") != self.target or
                not isinstance(raw.get("id"), int) or raw["id"] <= 0 or
                not isinstance(raw.get("private"), bool) or
                raw.get("has_issues") is not True):
            raise HostedTicketError("target-unknown: GitHub target is unavailable")
        return {"platform": "github", "host": self.host, "target": self.target,
                "targetId": raw["id"],
                "visibility": "private" if raw["private"] else "public"}

    def _issue(self, item: Any, expected: int | None = None) -> dict[str, Any]:
        number = item.get("number") if isinstance(item, dict) else None
        address = urlparse(item.get("html_url", "")) if isinstance(item, dict) else None
        if (not isinstance(item, dict) or not isinstance(number, int) or number <= 0 or
                (expected is not None and number != expected) or
                item.get("state") not in ("open", "closed") or
                not isinstance(item.get("body"), (str, type(None))) or
                not isinstance(item.get("labels"), list) or
                address is None or address.scheme != "https" or
                address.netloc != self.host or
                address.path != "/" + self.target + "/issues/" + str(number)):
            raise HostedTicketError("provider-unavailable: invalid GitHub issue")
        return {"number": number, "state": item["state"], "body": item.get("body") or "",
                "labels": item["labels"], "url": item["html_url"],
                "repository": {"full_name": self.target}}

    def list_issues(self) -> dict[str, Any]:
        raw = pages(lambda page: self._get(
            self.base + "?state=all&per_page=100&page=" + str(page)))
        return {"complete": True,
                "issues": [self._issue(item) for item in raw
                           if "pull_request" not in item]}

    def get_issue(self, issue_id: int) -> dict[str, Any]:
        return self._issue(self._get(self.base + "/" + str(issue_id)), issue_id)

    def list_comments(self, issue_id: int) -> dict[str, Any]:
        endpoint = self.base + "/" + str(issue_id) + "/comments"
        raw = pages(lambda page: self._get(endpoint + "?per_page=100&page=" + str(page)))
        if any(not isinstance(item.get("body"), str) for item in raw):
            raise HostedTicketError("provider-unavailable: invalid GitHub comment")
        return {"complete": True, "comments": [{"body": item["body"]} for item in raw]}

    # ── writes ────────────────────────────────────────────────────────────
    def create_comment(self, issue_id: int, body: str) -> None:
        self._write("POST", self.base + "/" + str(issue_id) + "/comments",
                    {"body": body})

    def set_stage(self, issue_id: int, from_stage: str | None, to_stage: str) -> None:
        """Add the new stage label first, then drop the old one.

        If the removal landed and the addition did not, the Issue would carry no stage
        label at all, which breaks the tracker contract and makes the item unreadable.
        Adding first can only ever leave two labels, which the next read reports as a
        contract violation rather than silently misinterpreting.
        """
        self._write("POST", self.base + "/" + str(issue_id) + "/labels",
                    {"labels": [to_stage]})
        if from_stage and from_stage != to_stage:
            self._write("DELETE",
                        self.base + "/" + str(issue_id) + "/labels/" + from_stage)

    def set_closed(self, issue_id: int) -> None:
        self._write("PATCH", self.base + "/" + str(issue_id), {"state": "closed"})
