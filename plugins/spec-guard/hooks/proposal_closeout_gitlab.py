"""GitLab adapter for Proposal closeout.

Same protocol as the GitHub adapter, same transport, three platform differences:

- the container is a positive integer project id, the form the existing Proposal
  commands already use, so there is only ever one target shape in the repository;
- a note marked `system: true` is the platform's own audit trail, not discussion, so it
  is dropped -- counting it would let a label change masquerade as the closeout record;
- closing is a `state_event`, and a label swap is one request carrying both
  `add_labels` and `remove_labels`, so the item is never briefly without a stage.
"""
from __future__ import annotations

import re
from typing import Any, Callable
from urllib.parse import urlparse

from hosted_ticket_provider import (
    HostedTicketError, pages, run_json, run_write_json,
)


class GitLabCloseout:
    def __init__(self, host: str, target: Any,
                 runner: Callable[[list[str]], Any] = run_json,
                 writer: Callable[[list[str], dict[str, Any]], Any] = run_write_json):
        if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]{0,252}", host or "") or
                isinstance(target, bool) or not isinstance(target, int) or target <= 0):
            raise HostedTicketError("target-invalid: host or project id is invalid")
        self.host, self.target = host, target
        self.runner, self.writer = runner, writer
        self.base = "projects/" + str(target) + "/issues"

    # ── reads ─────────────────────────────────────────────────────────────
    def _get(self, endpoint: str) -> Any:
        return self.runner(["glab", "api", endpoint])

    def _write(self, method: str, endpoint: str, body: dict[str, Any]) -> Any:
        return self.writer(["glab", "api", "--method", method, endpoint], body)

    def target_facts(self) -> dict[str, Any]:
        raw = self._get("projects/" + str(self.target))
        address = urlparse(raw.get("web_url", "")) if isinstance(raw, dict) else None
        if (not isinstance(raw, dict) or raw.get("id") != self.target or
                not isinstance(raw.get("path_with_namespace"), str) or
                raw.get("visibility") not in ("public", "internal", "private") or
                raw.get("issues_enabled") is not True or
                address is None or address.scheme != "https" or
                address.netloc != self.host):
            raise HostedTicketError("target-unknown: GitLab target is unavailable")
        return {"platform": "gitlab", "host": self.host, "target": self.target,
                "targetId": raw["id"], "visibility": raw["visibility"]}

    def _issue(self, item: Any, expected: int | None = None) -> dict[str, Any]:
        iid = item.get("iid") if isinstance(item, dict) else None
        address = urlparse(item.get("web_url", "")) if isinstance(item, dict) else None
        if (not isinstance(item, dict) or not isinstance(iid, int) or iid <= 0 or
                (expected is not None and iid != expected) or
                item.get("state") not in ("opened", "closed") or
                not isinstance(item.get("description"), (str, type(None))) or
                not isinstance(item.get("labels"), list) or
                address is None or address.scheme != "https" or
                address.netloc != self.host):
            raise HostedTicketError("provider-unavailable: invalid GitLab issue")
        return {"iid": iid, "project_id": self.target, "state": item["state"],
                "description": item.get("description") or "", "labels": item["labels"],
                "url": item["web_url"]}

    def list_issues(self) -> dict[str, Any]:
        raw = pages(lambda page: self._get(
            self.base + "?state=all&per_page=100&page=" + str(page)))
        return {"complete": True, "issues": [self._issue(item) for item in raw]}

    def get_issue(self, issue_id: int) -> dict[str, Any]:
        return self._issue(self._get(self.base + "/" + str(issue_id)), issue_id)

    def list_comments(self, issue_id: int) -> dict[str, Any]:
        endpoint = self.base + "/" + str(issue_id) + "/notes"
        raw = pages(lambda page: self._get(endpoint + "?per_page=100&page=" + str(page)))
        if any(not isinstance(item.get("body"), str) or
               not isinstance(item.get("system"), bool) for item in raw):
            raise HostedTicketError("provider-unavailable: invalid GitLab note")
        return {"complete": True,
                "comments": [{"body": item["body"]} for item in raw
                             if item["system"] is False]}

    # ── writes ────────────────────────────────────────────────────────────
    def create_comment(self, issue_id: int, body: str) -> None:
        self._write("POST", self.base + "/" + str(issue_id) + "/notes", {"body": body})

    def set_stage(self, issue_id: int, from_stage: str | None, to_stage: str) -> None:
        body: dict[str, Any] = {"add_labels": to_stage}
        if from_stage and from_stage != to_stage:
            body["remove_labels"] = from_stage
        self._write("PUT", self.base + "/" + str(issue_id), body)

    def set_closed(self, issue_id: int) -> None:
        self._write("PUT", self.base + "/" + str(issue_id), {"state_event": "close"})
