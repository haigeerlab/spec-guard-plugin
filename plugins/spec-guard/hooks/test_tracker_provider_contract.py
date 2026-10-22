"""One contract for every GitHub/GitLab reader: hosted tickets, Local handoff, Proposal closeout and read.

The same fake platform answers all four entry points, so a rule that one of them stops
following (ordinary Issues only, host pinned, the same page limit, the same URL checks,
the same write verdict) turns this file red. No network, no CLI.
"""
import re
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, unquote, urlsplit

from hosted_ticket_provider import GitHubIssues, GitLabIssues, HostedTicketError, MAX_PAGES, PAGE_SIZE
from local_ticket_github import GitHubHandoff
from local_ticket_gitlab import GitLabHandoff
from local_ticket_inventory import InventoryError
from proposal_closeout_github import GitHubCloseout
from proposal_closeout_gitlab import GitLabCloseout
from proposal_contract import Baseline, Change, Proposal
from proposal_tracker_read import read_tracker

GITHUB_HOST, GITLAB_HOST = "ghe.example.com", "git.example.com"
REPO, PROJECT_ID = "team/repo", 17
MARKER = "<!-- spec-guard-proposal:v1 id=gamma -->"
LABELS = ["proposal", "proposal-stage:in-review"]


def proposal():
    return Proposal("gamma", MARKER,
                    Baseline("origin", "trunk", "0" * 40, "0" * 12, {}, "alpha"),
                    Change("gamma", "Gamma.", ("alpha",), "after:alpha"))


def github_issue(number, body="plain", host=GITHUB_HOST, scheme="https", pull=False):
    item = {"number": number, "title": "Issue %d" % number, "body": body, "state": "open",
            "labels": [{"name": label} for label in LABELS],
            "html_url": "%s://%s/%s/issues/%d" % (scheme, host, REPO, number)}
    if pull:
        item["pull_request"] = {"url": "https://%s/api/v3/repos/%s/pulls/%d" % (host, REPO, number)}
    return item


def gitlab_issue(iid, body="plain", host=GITLAB_HOST, scheme="https", path="issues",
                 issue_type="issue", kind="ISSUE"):
    return {"iid": iid, "project_id": PROJECT_ID, "title": "Issue %d" % iid, "description": body,
            "state": "opened", "labels": list(LABELS), "issue_type": issue_type, "type": kind,
            "web_url": "%s://%s/%s/-/%s/%d" % (scheme, host, REPO, path, iid)}


class Platform:
    """A fake `gh api` / `glab api`: answers by endpoint and records every argv."""

    def __init__(self, platform, issues, project_url=None, honours_type_filter=True):
        self.platform, self.issues, self.calls = platform, list(issues), []
        self.project_url = project_url or "https://%s/%s" % (GITLAB_HOST, REPO)
        self.honours_type_filter = honours_type_filter

    def __call__(self, args, body=None):
        self.calls.append(list(args))
        endpoint = next(arg for arg in args if arg.startswith(("repos/", "projects/")))
        address = urlsplit(endpoint)
        path, query = unquote(address.path), parse_qs(address.query)
        if path in ("repos/" + REPO, "projects/" + REPO, "projects/%d" % PROJECT_ID):
            return self._target()
        if path.endswith("/issues"):
            items = self.issues
            if (self.platform == "gitlab" and self.honours_type_filter and
                    query.get("issue_type") == ["issue"]):
                items = [item for item in items if item.get("issue_type", "issue") == "issue"]
            page, size = int(query.get("page", ["1"])[0]), int(query.get("per_page", ["20"])[0])
            return items[(page - 1) * size:page * size]
        raise AssertionError("unexpected endpoint %s" % endpoint)

    def _target(self):
        if self.platform == "github":
            return {"full_name": REPO, "id": 42, "private": True, "has_issues": True,
                    "permissions": {"push": True}}
        return {"id": PROJECT_ID, "path_with_namespace": REPO, "visibility": "private",
                "issues_enabled": True, "web_url": self.project_url,
                "permissions": {"project_access": {"access_level": 40}}}


UNTRUSTED = "untrusted"


def _listing(client, key):
    try:
        client.target_facts()
        return sorted(item[key] for item in client.list_issues()["issues"])
    except (HostedTicketError, InventoryError):
        return UNTRUSTED


def _proposal(platform, target, host, server):
    result = read_tracker(proposal(), platform, target, runner=server, host=host)
    if result.state == "unknown":
        return UNTRUSTED
    return [result.issue_id] if result.state == "verified" else []


def github_entries():
    return {
        "hosted": lambda s: _listing(GitHubIssues(GITHUB_HOST, REPO, s), "id"),
        "handoff": lambda s: _listing(GitHubHandoff(GITHUB_HOST, REPO, s), "id"),
        "closeout": lambda s: _listing(GitHubCloseout(GITHUB_HOST, REPO, s), "number"),
        "proposal": lambda s: _proposal("github", REPO, GITHUB_HOST, s),
    }


def gitlab_entries():
    return {
        "hosted": lambda s: _listing(GitLabIssues(GITLAB_HOST, REPO, s), "id"),
        "handoff": lambda s: _listing(GitLabHandoff(GITLAB_HOST, REPO, s), "id"),
        "closeout": lambda s: _listing(GitLabCloseout(GITLAB_HOST, PROJECT_ID, s), "iid"),
        "proposal": lambda s: _proposal("gitlab", PROJECT_ID, GITLAB_HOST, s),
    }


class ContractCase(unittest.TestCase):
    def each(self, entries, make_server, expect):
        """Run every entry against a fresh server; `expect(name)` is that entry's answer."""
        servers = []
        for name, entry in entries.items():
            server = make_server()
            with self.subTest(entry=name):
                self.assertEqual(entry(server), expect(name))
            servers.append((name, server))
        return servers


class HostPinning(ContractCase):
    def test_every_request_names_the_host(self):
        for entries, platform, host, issues in (
                (github_entries(), "github", GITHUB_HOST, [github_issue(1, MARKER)]),
                (gitlab_entries(), "gitlab", GITLAB_HOST, [gitlab_issue(1, MARKER)])):
            for name, server in self.each(entries, lambda: Platform(platform, issues), lambda _: [1]):
                cli = "gh" if platform == "github" else "glab"
                for call in server.calls:
                    with self.subTest(entry=name, call=call):
                        self.assertEqual(call[:4], [cli, "api", "--hostname", host])

    def test_a_target_on_another_host_is_untrusted(self):
        self.each(gitlab_entries(), lambda: Platform(
            "gitlab", [gitlab_issue(1, MARKER)], project_url="https://other.example.com/" + REPO),
            lambda _: UNTRUSTED)

    def test_an_issue_on_another_host_is_untrusted(self):
        self.each(github_entries(), lambda: Platform(
            "github", [github_issue(1, MARKER, host="github.com")]), lambda _: UNTRUSTED)
        self.each(gitlab_entries(), lambda: Platform(
            "gitlab", [gitlab_issue(1, MARKER, host="gitlab.com")]), lambda _: UNTRUSTED)


class OrdinaryIssuesOnly(ContractCase):
    def test_gitlab_lists_ask_for_ordinary_issues(self):
        for name, server in self.each(gitlab_entries(), lambda: Platform(
                "gitlab", [gitlab_issue(1, MARKER)]), lambda _: [1]):
            lists = [call for call in server.calls if "/issues?" in call[-1] or
                     any("/issues?" in arg for arg in call)]
            with self.subTest(entry=name):
                self.assertTrue(lists)
                for call in lists:
                    self.assertTrue(any("issue_type=issue" in arg for arg in call), call)

    def test_other_gitlab_types_never_count_as_issues(self):
        incident = gitlab_issue(2, MARKER, issue_type="incident", kind="INCIDENT")
        self.each(gitlab_entries(), lambda: Platform(
            "gitlab", [gitlab_issue(1), incident]),
            lambda name: [] if name == "proposal" else [1])

    def test_a_platform_that_ignores_the_type_filter_is_untrusted(self):
        task = gitlab_issue(2, issue_type="task", kind="TASK")
        self.each(gitlab_entries(), lambda: Platform(
            "gitlab", [gitlab_issue(1, MARKER), task], honours_type_filter=False),
            lambda _: UNTRUSTED)

    def test_github_pull_requests_are_never_issues(self):
        self.each(github_entries(), lambda: Platform(
            "github", [github_issue(1), github_issue(2, MARKER, pull=True)]),
            lambda name: [] if name == "proposal" else [1])


class Addresses(ContractCase):
    def test_gitlab_work_item_addresses_are_issues(self):
        self.each(gitlab_entries(), lambda: Platform(
            "gitlab", [gitlab_issue(1, MARKER, path="work_items")]), lambda _: [1])

    def test_gitlab_scheme_follows_the_target(self):
        self.each(gitlab_entries(), lambda: Platform(
            "gitlab", [gitlab_issue(1, MARKER, scheme="http")],
            project_url="http://%s/%s" % (GITLAB_HOST, REPO)), lambda _: [1])
        self.each(gitlab_entries(), lambda: Platform(
            "gitlab", [gitlab_issue(1, MARKER, scheme="http")]), lambda _: UNTRUSTED)


class Pagination(ContractCase):
    def test_the_same_page_limit_everywhere(self):
        self.assertEqual((PAGE_SIZE, MAX_PAGES), (100, 50))
        full = [github_issue(n) for n in range(1, PAGE_SIZE * MAX_PAGES + 1)]
        self.each(github_entries(), lambda: Platform("github", full), lambda _: UNTRUSTED)
        full = [gitlab_issue(n) for n in range(1, PAGE_SIZE * MAX_PAGES + 1)]
        self.each(gitlab_entries(), lambda: Platform("gitlab", full), lambda _: UNTRUSTED)

    def test_a_long_but_complete_set_is_read_to_the_end(self):
        count = PAGE_SIZE * 30 + 1
        issues = [github_issue(n, MARKER if n == count else "plain") for n in range(1, count + 1)]
        self.each(github_entries(), lambda: Platform("github", issues),
                       lambda name: [count] if name == "proposal" else list(range(1, count + 1)))
        issues = [gitlab_issue(n, MARKER if n == count else "plain") for n in range(1, count + 1)]
        self.each(gitlab_entries(), lambda: Platform("gitlab", issues),
                       lambda name: [count] if name == "proposal" else list(range(1, count + 1)))


class WriteVerdicts(unittest.TestCase):
    """Hosted tickets and Local handoff create Issues; both must read the HTTP status the same way."""

    WRITERS = {
        "hosted": lambda: GitHubIssues(GITHUB_HOST, REPO).create_issue("t", "b"),
        "handoff": lambda: GitHubHandoff(GITHUB_HOST, REPO).create_issue("t", "b"),
    }

    def verdict(self, writer, returncode, stdout):
        response = subprocess.CompletedProcess([], returncode, stdout=stdout, stderr="")
        with patch("subprocess.run", return_value=response):
            try:
                return ("created", writer()["id"])
            except (HostedTicketError, InventoryError) as error:
                status = getattr(error, "status_code", None)
                return ("rejected", status) if status else ("unknown", None)

    def test_the_same_verdict_for_every_response(self):
        created = '{"number": 5, "title": "t", "body": "b", "state": "open", ' \
                  '"html_url": "https://%s/%s/issues/5"}' % (GITHUB_HOST, REPO)
        for stdout, returncode, expected in (
                ("HTTP/2.0 201 Created\n\n" + created, 0, ("created", 5)),
                ("HTTP/2.0 403 Forbidden\n\n{}", 1, ("rejected", 403)),
                ("HTTP/2.0 422 Unprocessable\n\n{}", 1, ("rejected", 422)),
                (created, 0, ("unknown", None)),
                ("HTTP/2.0 502 Bad Gateway\n\n{}", 1, ("unknown", None))):
            for name, writer in self.WRITERS.items():
                with self.subTest(entry=name, stdout=stdout[:20]):
                    self.assertEqual(self.verdict(writer, returncode, stdout), expected)


class OneTransport(unittest.TestCase):
    def test_only_the_shared_provider_calls_gh_or_glab(self):
        hooks = Path(__file__).resolve().parent
        offenders = sorted(
            path.name for path in hooks.glob("*.py")
            if not path.name.startswith("test_") and path.name != "hosted_ticket_provider.py"
            and re.search(r"""["'](?:gh|glab)["']""", path.read_text(encoding="utf-8")))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
