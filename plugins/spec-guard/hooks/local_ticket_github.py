"""GitHub Issues for explicit Local ticket handoffs, over the shared transport."""
from __future__ import annotations

from typing import Any, Callable

from hosted_ticket_provider import GitHubIssues
from local_ticket_preview import target_facts
from local_ticket_provider import call, split


class GitHubHandoff:
    def __init__(self, host: str, target: str,
                 runner: Callable[[list[str], dict[str, Any] | None], Any] | None = None):
        self.host, self.target = host, target
        self.reader, self.writer = split(runner)
        self._client: GitHubIssues | None = None

    @property
    def client(self) -> GitHubIssues:
        if self._client is None:
            self._client = call(GitHubIssues, self.host, self.target, self.reader, self.writer)
        return self._client

    def target_facts(self) -> dict[str, Any]:
        return target_facts("github", self.host, self.target, client=self.client)

    @staticmethod
    def _issue(issue: dict[str, Any]) -> dict[str, Any]:
        return {"id": issue["id"], "title": issue["title"], "body": issue["body"],
                "closed": issue["closed"], "url": issue["url"], "isPullRequest": False}

    def list_issues(self) -> dict[str, Any]:
        listing = call(self.client.list_issues)
        return {"complete": True, "issues": [self._issue(item) for item in listing["issues"]]}

    def get_issue(self, issue_id: int) -> dict[str, Any]:
        return self._issue(call(self.client.get_issue, issue_id))

    def create_issue(self, title: str, body: str) -> dict[str, Any]:
        return self._issue(call(self.client.create_issue, title, body))

    def list_comments(self, issue_id: int) -> dict[str, Any]:
        return call(self.client.list_comments, issue_id)

    def create_comment(self, issue_id: int, body: str) -> None:
        call(self.client.create_comment, issue_id, body)

    def set_closed(self, issue_id: int, closed: bool) -> None:
        call(self.client.set_closed, issue_id, closed)
