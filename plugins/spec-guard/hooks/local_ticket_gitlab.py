"""GitLab Issues transport for explicit Local ticket handoffs."""
from __future__ import annotations

import json
from typing import Any, Callable
from urllib.parse import quote, urlparse

from local_ticket_portability import InventoryError
from local_ticket_preview import EVENT_MARKER, ISSUE_MARKER, target_facts
from local_ticket_provider import pages, run_json


class GitLabHandoff:
    def __init__(self, host: str, target: str,
                 runner: Callable[[list[str], dict[str, Any] | None], Any] = run_json):
        self.host, self.target, self.runner = host, target, runner
        self.base = "projects/" + quote(target, safe="") + "/issues"
        self.target_id: int | None = None
        self.web_scheme: str | None = None

    def _request(self, endpoint: str, method: str = "GET",
                 body: dict[str, Any] | None = None) -> Any:
        arguments = ["glab", "api", "--hostname", self.host, "--method", method,
                     endpoint]
        if body is not None:
            arguments.extend(["--input", "-"])
        return self.runner(arguments, body)

    def target_facts(self) -> dict[str, Any]:
        facts = target_facts("gitlab", self.host, self.target,
                             runner=lambda args: json.dumps(self.runner(args, None)))
        self.target_id = facts["targetId"]
        self.web_scheme = facts["webScheme"]
        return facts

    def _issue(self, raw: Any) -> dict[str, Any]:
        if (not isinstance(raw, dict) or not isinstance(raw.get("iid"), int)
                or raw["iid"] <= 0 or raw.get("project_id") != self.target_id
                or not isinstance(raw.get("title"), str)
                or (raw.get("description") is not None and
                    not isinstance(raw.get("description"), str))
                or raw.get("state") not in ("opened", "closed")
                or not isinstance(raw.get("web_url"), str)):
            raise InventoryError("provider-unavailable: GitLab issue response is incomplete")
        address = urlparse(raw["web_url"])
        if (address.scheme != self.web_scheme or address.netloc != self.host or
                address.path != "/" + self.target + "/-/issues/" + str(raw["iid"])):
            raise InventoryError("provider-unavailable: GitLab issue URL differs from target")
        return {"id": raw["iid"], "title": raw["title"],
                "body": raw["description"] or "", "closed": raw["state"] == "closed",
                "url": raw["web_url"]}

    def list_issues(self) -> dict[str, Any]:
        raw = pages(lambda page: self._request(
            self.base + "?state=all&scope=all&per_page=100&page=" + str(page),
        ))
        return {"complete": True, "issues": [self._issue(item) for item in raw]}

    def get_issue(self, issue_id: int) -> dict[str, Any]:
        issue = self._issue(self._request(self.base + "/" + str(issue_id)))
        if issue["id"] != issue_id:
            raise InventoryError("provider-unavailable: GitLab issue IID differs")
        return issue

    def create_issue(self, title: str, body: str) -> dict[str, Any]:
        return self._issue(self._request(self.base, "POST",
                                         {"title": title, "description": body}))

    def list_comments(self, issue_id: int) -> dict[str, Any]:
        endpoint = self.base + "/" + str(issue_id) + "/notes"
        raw = pages(lambda page: self._request(
            endpoint + "?per_page=100&page=" + str(page),
        ))
        comments = []
        for item in raw:
            body = item.get("body")
            if not isinstance(body, str) or not isinstance(item.get("system"), bool):
                raise InventoryError("provider-unavailable: GitLab note response is incomplete")
            if item["system"]:
                continue
            if not isinstance(item.get("internal"), bool):
                raise InventoryError("provider-unavailable: GitLab note visibility is unknown")
            if item.get("internal") is True:
                if ISSUE_MARKER in body or EVENT_MARKER in body:
                    raise InventoryError("conflict: Local marker is in an internal GitLab note")
                continue
            comments.append({"body": body})
        return {"complete": True, "comments": comments}

    def create_comment(self, issue_id: int, body: str) -> None:
        self._request(self.base + "/" + str(issue_id) + "/notes", "POST",
                      {"body": body})

    def set_closed(self, issue_id: int, closed: bool) -> None:
        self._request(self.base + "/" + str(issue_id), "PUT",
                      {"state_event": "close" if closed else "reopen"})
