"""GitLab Issues for explicit Local ticket handoffs, over the shared transport."""
from __future__ import annotations

from typing import Any, Callable

from hosted_ticket_provider import GitLabIssues
from local_ticket_preview import EVENT_MARKER, ISSUE_MARKER, target_facts
from local_ticket_provider import call, split


class GitLabHandoff:
    def __init__(self, host: str, target: str,
                 runner: Callable[[list[str], dict[str, Any] | None], Any] | None = None):
        self.host, self.target = host, target
        self.reader, self.writer = split(runner)
        self._client: GitLabIssues | None = None

    @property
    def client(self) -> GitLabIssues:
        if self._client is None:
            self._client = call(GitLabIssues, self.host, self.target, self.reader, self.writer)
        return self._client

    def target_facts(self) -> dict[str, Any]:
        return target_facts("gitlab", self.host, self.target, client=self.client)

    @staticmethod
    def _issue(issue: dict[str, Any]) -> dict[str, Any]:
        # GitLab drops the description's final newline; the snapshot digest keeps it.
        description = issue["body"]
        if description and not description.endswith("\n"):
            description += "\n"
        return {"id": issue["id"], "title": issue["title"], "body": description,
                "closed": issue["closed"], "url": issue["url"]}

    def list_issues(self) -> dict[str, Any]:
        listing = call(self.client.list_issues)
        return {"complete": True, "issues": [self._issue(item) for item in listing["issues"]]}

    def get_issue(self, issue_id: int) -> dict[str, Any]:
        return self._issue(call(self.client.get_issue, issue_id))

    def create_issue(self, title: str, body: str) -> dict[str, Any]:
        return self._issue(call(self.client.create_issue, title, body))

    def list_comments(self, issue_id: int) -> dict[str, Any]:
        return call(self.client.list_comments, issue_id, (ISSUE_MARKER, EVENT_MARKER))

    def create_comment(self, issue_id: int, body: str) -> None:
        call(self.client.create_comment, issue_id, body)

    def set_closed(self, issue_id: int, closed: bool) -> None:
        call(self.client.set_closed, issue_id, closed)
