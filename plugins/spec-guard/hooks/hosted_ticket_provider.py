"""Narrow, Epiq-independent read transport for ordinary hosted Issues."""
from __future__ import annotations

import json
import re
import subprocess
from typing import Any, Callable
from urllib.parse import quote, urlparse


PAGE_SIZE = 100
MAX_PAGES = 50
DEFINITE_REJECTIONS = {400, 401, 403, 404, 405, 410, 413, 414, 422}


class HostedTicketError(ValueError):
    """A hosted target or response cannot be treated as complete."""


class ProviderRejected(HostedTicketError):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"provider-rejected: HTTP {status_code}")


def run_json(arguments: list[str]) -> Any:
    try:
        response = subprocess.run(arguments, capture_output=True, text=True,
                                  timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise HostedTicketError("provider-unavailable: request did not complete") from error
    if response.returncode:
        raise HostedTicketError("provider-unavailable: request failed")
    try:
        return json.loads(response.stdout)
    except ValueError as error:
        raise HostedTicketError("provider-unavailable: invalid JSON") from error


def run_write_json(arguments: list[str], body: dict[str, Any]) -> Any:
    try:
        response = subprocess.run([*arguments, "--input", "-", "--include"],
                                  input=json.dumps(body), capture_output=True,
                                  text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise HostedTicketError("provider-unavailable: write did not complete") from error
    normalized = response.stdout.replace("\r\n", "\n")
    header, separator, payload = normalized.partition("\n\n")
    match = re.match(r"^HTTP/\S+\s+(\d{3})(?:\s|$)", header)
    status = int(match.group(1)) if match and separator else None
    if response.returncode or status is None or status >= 400:
        if status in DEFINITE_REJECTIONS:
            raise ProviderRejected(status)
        raise HostedTicketError("provider-unavailable: write result is unknown")
    try:
        return json.loads(payload)
    except ValueError as error:
        raise HostedTicketError("provider-unavailable: invalid write response") from error


def pages(fetch: Callable[[int], Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for number in range(1, MAX_PAGES + 1):
        batch = fetch(number)
        if (not isinstance(batch, list) or len(batch) > PAGE_SIZE or
                any(not isinstance(item, dict) for item in batch)):
            raise HostedTicketError("provider-unavailable: malformed page")
        items.extend(batch)
        if len(batch) < PAGE_SIZE:
            return items
    raise HostedTicketError("provider-unavailable: pagination limit reached")


def _target(platform: str, host: str, target: str) -> None:
    if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*", host) or
            not target or any(not re.fullmatch(r"[A-Za-z0-9_.-]+", part) or
                              part in (".", "..") for part in target.split("/")) or
            (platform == "github" and len(target.split("/")) != 2)):
        raise HostedTicketError("target-invalid: host or project is invalid")


class GitHubIssues:
    def __init__(self, host: str, target: str,
                 runner: Callable[[list[str]], Any] = run_json,
                 writer: Callable[[list[str], dict[str, Any]], Any] = run_write_json):
        _target("github", host, target)
        self.host, self.target, self.runner, self.writer = host, target, runner, writer
        self.base = "repos/" + target + "/issues"

    def _get(self, endpoint: str) -> Any:
        return self.runner(["gh", "api", "--hostname", self.host, endpoint])

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

    def list_issues(self) -> dict[str, Any]:
        raw = pages(lambda page: self._get(
            self.base + "?state=all&per_page=100&page=" + str(page)))
        return {"complete": True, "issues": [self._issue(item) for item in raw
                                             if "pull_request" not in item]}

    def _issue(self, item: Any) -> dict[str, Any]:
        if not isinstance(item, dict):
            raise HostedTicketError("provider-unavailable: invalid GitHub issue")
        number = item.get("number")
        address = urlparse(item.get("html_url", ""))
        if (not isinstance(number, int) or number <= 0 or
                not isinstance(item.get("title"), str) or
                not isinstance(item.get("body"), (str, type(None))) or
                item.get("state") not in ("open", "closed") or
                address.scheme != "https" or address.netloc != self.host or
                address.path != "/" + self.target + "/issues/" + str(number) or
                address.query or address.fragment or "pull_request" in item):
            raise HostedTicketError("provider-unavailable: invalid GitHub issue")
        return {"id": number, "title": item["title"], "body": item.get("body") or "",
                "closed": item["state"] == "closed", "url": item["html_url"]}

    def get_issue(self, issue_id: int) -> dict[str, Any]:
        issue = self._issue(self._get(self.base + "/" + str(issue_id)))
        if issue["id"] != issue_id:
            raise HostedTicketError("provider-unavailable: GitHub issue ID differs")
        return issue

    def create_issue(self, title: str, body: str) -> dict[str, Any]:
        arguments = ["gh", "api", "--hostname", self.host, "--method", "POST", self.base]
        return self._issue(self.writer(arguments, {"title": title, "body": body}))


class GitLabIssues:
    def __init__(self, host: str, target: str,
                 runner: Callable[[list[str]], Any] = run_json,
                 writer: Callable[[list[str], dict[str, Any]], Any] = run_write_json):
        _target("gitlab", host, target)
        self.host, self.target, self.runner, self.writer = host, target, runner, writer
        self.base = "projects/" + quote(target, safe="") + "/issues"
        self.project_id: int | None = None
        self.web_scheme: str | None = None

    def _get(self, endpoint: str) -> Any:
        return self.runner(["glab", "api", "--hostname", self.host, endpoint])

    def target_facts(self) -> dict[str, Any]:
        raw = self._get("projects/" + quote(self.target, safe=""))
        address = urlparse(raw.get("web_url", "")) if isinstance(raw, dict) else None
        if (not isinstance(raw, dict) or raw.get("path_with_namespace") != self.target or
                not isinstance(raw.get("id"), int) or raw["id"] <= 0 or
                raw.get("visibility") not in ("public", "internal", "private") or
                raw.get("issues_enabled") is not True or address is None or
                address.scheme not in ("http", "https") or address.netloc != self.host or
                address.path != "/" + self.target or address.query or address.fragment):
            raise HostedTicketError("target-unknown: GitLab target is unavailable")
        self.project_id, self.web_scheme = raw["id"], address.scheme
        return {"platform": "gitlab", "host": self.host, "target": self.target,
                "targetId": raw["id"], "visibility": raw["visibility"],
                "webScheme": address.scheme}

    def list_issues(self) -> dict[str, Any]:
        if self.project_id is None or self.web_scheme is None:
            raise HostedTicketError("target-unknown: GitLab target has not been checked")
        raw = pages(lambda page: self._get(
            self.base + "?state=all&scope=all&per_page=100&page=" + str(page)))
        return {"complete": True, "issues": [self._issue(item) for item in raw]}

    def _issue(self, item: Any) -> dict[str, Any]:
        if not isinstance(item, dict):
            raise HostedTicketError("provider-unavailable: invalid GitLab issue")
        number = item.get("iid")
        address = urlparse(item.get("web_url", ""))
        if (not isinstance(number, int) or number <= 0 or
                item.get("project_id") != self.project_id or
                not isinstance(item.get("title"), str) or
                not isinstance(item.get("description"), (str, type(None))) or
                item.get("state") not in ("opened", "closed") or
                address.scheme != self.web_scheme or address.netloc != self.host or
                address.path != "/" + self.target + "/-/issues/" + str(number) or
                address.query or address.fragment):
            raise HostedTicketError("provider-unavailable: invalid GitLab issue")
        return {"id": number, "title": item["title"],
                "body": item.get("description") or "",
                "closed": item["state"] == "closed", "url": item["web_url"]}

    def get_issue(self, issue_id: int) -> dict[str, Any]:
        issue = self._issue(self._get(self.base + "/" + str(issue_id)))
        if issue["id"] != issue_id:
            raise HostedTicketError("provider-unavailable: GitLab issue ID differs")
        return issue

    def create_issue(self, title: str, body: str) -> dict[str, Any]:
        arguments = ["glab", "api", "--hostname", self.host, "--method", "POST",
                     self.base, "--header", "Content-Type: application/json"]
        return self._issue(self.writer(arguments, {"title": title, "description": body}))
