"""GitHub adapter for Proposal closeout: read the item, comment, move the stage, close.

The identity rules live in `proposal_tracker_read`; reading, the page limit, what counts
as an ordinary Issue and the write verdict live in `hosted_ticket_provider`. This file
only keeps what is closeout's own: the stage-label move.

`list_issues` and `get_issue` return the platform shape `recover_tracker_issue` reads
(`proposal_tracker_read.tracker_shape`), so the identity rules see the same fields
for closeout as for every other Proposal read.
"""
from __future__ import annotations

import re
from typing import Any, Callable

from hosted_ticket_provider import GitHubIssues, HostedTicketError, run_json, run_write_json
from proposal_tracker_read import tracker_shape


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
        self.client = GitHubIssues(host, target, runner, writer)
        self.base = self.client.base

    # ── reads ─────────────────────────────────────────────────────────────
    def target_facts(self) -> dict[str, Any]:
        return self.client.target_facts()

    @staticmethod
    def _issue(issue: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(issue.get("labels"), list):
            raise HostedTicketError("provider-unavailable: invalid GitHub issue")
        return tracker_shape("github", issue)

    def list_issues(self) -> dict[str, Any]:
        return {"complete": True,
                "issues": [self._issue(item) for item in self.client.list_issues()["issues"]]}

    def get_issue(self, issue_id: int) -> dict[str, Any]:
        return self._issue(self.client.get_issue(issue_id))

    def list_comments(self, issue_id: int) -> dict[str, Any]:
        return self.client.list_comments(issue_id)

    # ── writes ────────────────────────────────────────────────────────────
    def create_comment(self, issue_id: int, body: str) -> None:
        self.client.create_comment(issue_id, body)

    def set_stage(self, issue_id: int, from_stage: str | None, to_stage: str) -> None:
        """Add the new stage label first, then drop the old one.

        If the removal landed and the addition did not, the Issue would carry no stage
        label at all, which breaks the tracker contract and makes the item unreadable.
        Adding first can only ever leave two labels, which the next read reports as a
        contract violation rather than silently misinterpreting.
        """
        self.client.write("POST", self.base + "/" + str(issue_id) + "/labels",
                          {"labels": [to_stage]})
        if from_stage and from_stage != to_stage:
            self.client.write("DELETE",
                              self.base + "/" + str(issue_id) + "/labels/" + from_stage, {})

    def set_closed(self, issue_id: int) -> None:
        self.client.set_closed(issue_id)
