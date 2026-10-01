"""GitHub Issues transport for explicit Local ticket handoffs."""
from __future__ import annotations

import json
from typing import Any, Callable
from urllib.parse import urlparse

from local_ticket_portability import InventoryError
from local_ticket_preview import target_facts
from local_ticket_provider import PAGE_SIZE, pages, run_json


class GitHubHandoff:
    def __init__(self, host: str, target: str,
                 runner: Callable[[list[str], dict[str, Any] | None], Any] = run_json):
        self.host, self.target, self.runner = host, target, runner
        self.base = "repos/" + target + "/issues"

    def _request(self, endpoint: str, method: str = "GET",
                 body: dict[str, Any] | None = None) -> Any:
        arguments = ["gh", "api", "--hostname", self.host, "--method", method,
                     endpoint]
        if body is not None:
            arguments.extend(["--input", "-"])
        return self.runner(arguments, body)

    def target_facts(self) -> dict[str, Any]:
        return target_facts("github", self.host, self.target,
                            runner=lambda args: json.dumps(self.runner(args, None)))

    def _issue(self, raw: Any) -> dict[str, Any]:
        if (not isinstance(raw, dict) or not isinstance(raw.get("number"), int)
                or raw["number"] <= 0 or not isinstance(raw.get("title"), str)
                or (raw.get("body") is not None and not isinstance(raw.get("body"), str))
                or raw.get("state") not in ("open", "closed")
                or not isinstance(raw.get("html_url"), str)):
            raise InventoryError("provider-unavailable: GitHub issue response is incomplete")
        address = urlparse(raw["html_url"])
        if (address.scheme != "https" or address.hostname != self.host or
                address.path != "/" + self.target + "/issues/" + str(raw["number"])):
            raise InventoryError("provider-unavailable: GitHub issue URL differs from target")
        return {"id": raw["number"], "title": raw["title"], "body": raw["body"] or "",
                "closed": raw["state"] == "closed", "url": raw["html_url"],
                "isPullRequest": "pull_request" in raw}

    def list_issues(self) -> dict[str, Any]:
        raw = pages(lambda page: self._request(
            self.base + "?state=all&per_page=100&page=" + str(page),
        ))
        return {"complete": True, "issues": [self._issue(item) for item in raw
                                               if "pull_request" not in item]}

    def get_issue(self, issue_id: int) -> dict[str, Any]:
        issue = self._issue(self._request(self.base + "/" + str(issue_id)))
        if issue["id"] != issue_id:
            raise InventoryError("provider-unavailable: GitHub issue ID differs")
        return issue

    def create_issue(self, title: str, body: str) -> dict[str, Any]:
        return self._issue(self._request(self.base, "POST", {"title": title, "body": body}))

    def list_comments(self, issue_id: int) -> dict[str, Any]:
        endpoint = self.base + "/" + str(issue_id) + "/comments"
        raw = pages(lambda page: self._request(
            endpoint + "?per_page=100&page=" + str(page),
        ))
        if any(item.get("body") is not None and
               not isinstance(item.get("body"), str) for item in raw):
            raise InventoryError("provider-unavailable: GitHub comment response is incomplete")
        return {"complete": True, "comments": [{"body": item.get("body") or ""}
                                               for item in raw]}

    def create_comment(self, issue_id: int, body: str) -> None:
        self._request(self.base + "/" + str(issue_id) + "/comments", "POST", {"body": body})

    def set_closed(self, issue_id: int, closed: bool) -> None:
        self._request(self.base + "/" + str(issue_id), "PATCH",
                      {"state": "closed" if closed else "open"})
