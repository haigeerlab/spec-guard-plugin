"""GitLab adapter for Proposal closeout.

Same protocol as the GitHub adapter, same shared client (`hosted_ticket_provider`), and
what is closeout's own:

- the container is a positive integer project id, the form the existing Proposal
  commands already use, so there is only ever one target shape in the repository;
- the exact target keeps the keys previews were written with, so a preview made
  before this adapter moved onto the shared client still matches;
- a label swap is one request carrying both `add_labels` and `remove_labels`, so the
  item is never briefly without a stage.

System notes and internal notes are not discussion: the shared client drops them, and a
closeout marker inside an internal note is ambiguous rather than absent.
"""
from __future__ import annotations

import re
from typing import Any, Callable

from hosted_ticket_provider import GitLabIssues, HostedTicketError, run_json, run_write_json
from proposal_tracker_read import tracker_shape

CLOSEOUT_MARKER = "spec-guard-proposal-closeout:v1"


class GitLabCloseout:
    def __init__(self, host: str, target: Any,
                 runner: Callable[[list[str]], Any] = run_json,
                 writer: Callable[[list[str], dict[str, Any]], Any] = run_write_json):
        if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]{0,252}", host or "") or
                isinstance(target, bool) or not isinstance(target, int) or target <= 0):
            raise HostedTicketError("target-invalid: host or project id is invalid")
        self.host, self.target = host, target
        self.client = GitLabIssues(host, target, runner, writer)
        self.base = self.client.base

    # ── reads ─────────────────────────────────────────────────────────────
    def target_facts(self) -> dict[str, Any]:
        facts = self.client.target_facts()
        return {key: facts[key] for key in ("platform", "host", "target", "targetId",
                                            "visibility")}

    @staticmethod
    def _issue(issue: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(issue.get("labels"), list):
            raise HostedTicketError("provider-unavailable: invalid GitLab issue")
        return tracker_shape("gitlab", issue)

    def list_issues(self) -> dict[str, Any]:
        return {"complete": True,
                "issues": [self._issue(item) for item in self.client.list_issues()["issues"]]}

    def get_issue(self, issue_id: int) -> dict[str, Any]:
        return self._issue(self.client.get_issue(issue_id))

    def list_comments(self, issue_id: int) -> dict[str, Any]:
        return self.client.list_comments(issue_id, (CLOSEOUT_MARKER,))

    # ── writes ────────────────────────────────────────────────────────────
    def create_comment(self, issue_id: int, body: str) -> None:
        self.client.create_comment(issue_id, body)

    def set_stage(self, issue_id: int, from_stage: str | None, to_stage: str) -> None:
        body: dict[str, Any] = {"add_labels": to_stage}
        if from_stage and from_stage != to_stage:
            body["remove_labels"] = from_stage
        self.client.write("PUT", self.base + "/" + str(issue_id), body)

    def set_closed(self, issue_id: int) -> None:
        self.client.set_closed(issue_id)
