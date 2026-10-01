"""Synthetic GitHub/GitLab CLI contract tests; no network or user ledger."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from local_ticket_github import GitHubHandoff
from local_ticket_gitlab import GitLabHandoff
from local_ticket_preview import render_body
from local_ticket_publish import publish_preview
from local_ticket_portability import InventoryError
from local_ticket_provider import PAGE_SIZE, MAX_PAGES, pages


PROJECT_ID = "01M37F8MKQRSB562YCBQ004QGJ"
ISSUE_ID = "01M3SX6JWYGM5120R5VDA15T35"


class ApiFixture:
    def __init__(self, platform, scheme="https"):
        self.platform = platform
        self.scheme = scheme
        self.issues = []
        self.comments = {}
        self.calls = []
        self.lose_issue_after = False
        self.lose_note_after = False

    def __call__(self, arguments, body):
        self.calls.append((arguments, body))
        endpoint = next(part for part in arguments if part.startswith(("repos/", "projects/")))
        method = arguments[arguments.index("--method") + 1] if "--method" in arguments else "GET"
        if endpoint in ("repos/team/repo", "projects/group%2Fproject"):
            if self.platform == "github":
                return {"full_name": "team/repo", "id": 42, "private": True,
                        "has_issues": True, "permissions": {"push": True}}
            return {"path_with_namespace": "group/project", "id": 43,
                    "web_url": self.scheme + "://gitlab.example.test/group/project",
                    "visibility": "private", "issues_enabled": True,
                    "permissions": {"project_access": {"access_level": 30}}}
        if "?" in endpoint:
            path = endpoint.split("?", 1)[0]
            if path.endswith("/notes") or path.endswith("/comments"):
                issue_id = int(path.split("/")[-2])
                return list(self.comments.get(issue_id, []))
            if path.endswith("/issues"):
                if self.platform == "github":
                    return [{"number": 99, "title": "PR", "body": None,
                             "state": "open", "html_url": "https://github.com/team/repo/pull/99",
                             "pull_request": {"url": "https://api.github.com/pulls/99"}}] + list(self.issues)
                return list(self.issues)
        if endpoint.endswith("/issues"):
            self.issues.append(self.issue(1, body["title"],
                                          body.get("body", body.get("description", ""))))
            if self.lose_issue_after:
                raise TimeoutError("response lost after issue creation")
            return dict(self.issues[-1])
        parts = endpoint.split("/")
        issue_id = int(parts[-2] if parts[-1] in ("comments", "notes") else parts[-1])
        if parts[-1] in ("comments", "notes"):
            if method == "POST":
                note = {"body": body["body"]}
                if self.platform == "gitlab":
                    note.update({"system": False, "internal": False})
                self.comments.setdefault(issue_id, []).append(note)
                if self.lose_note_after:
                    raise TimeoutError("response lost after note creation")
                return note
            return list(self.comments.get(issue_id, []))
        issue = next(item for item in self.issues if self.key(item) == issue_id)
        if method in ("PATCH", "PUT"):
            if self.platform == "github":
                issue["state"] = body["state"]
            else:
                issue["state"] = "closed" if body["state_event"] == "close" else "opened"
        return dict(issue)

    def key(self, issue):
        return issue["number"] if self.platform == "github" else issue["iid"]

    def issue(self, number, title, body):
        if self.platform == "github":
            return {"number": number, "title": title, "body": body, "state": "open",
                    "html_url": "https://github.com/team/repo/issues/" + str(number)}
        return {"iid": number, "project_id": 43, "title": title,
                "description": body, "state": "opened",
                "web_url": self.scheme + "://gitlab.example.test/group/project/-/issues/" + str(number)}


class ProviderTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="sg-provider-fixture-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.project = self.base / "project"
        self.project.mkdir()
        import subprocess
        subprocess.run(["git", "-C", str(self.project), "init", "-q"], check=True)
        self.source = {"projectId": PROJECT_ID, "issueId": ISSUE_ID,
                       "sourceDigest": "a" * 64,
                       "issue": {"title": "Scope", "description": "Current", "isClosed": True},
                       "events": [
                           {"id": "E1", "action": "add.issue", "payload": {"id": ISSUE_ID}},
                           {"id": "E2", "action": "add.issue.comment",
                            "payload": {"id": "C1", "issue": ISSUE_ID, "md": "Decision"}},
                       ], "attachments": [], "codeReferences": []}

    def roundtrip(self, platform, scheme="https"):
        fixture = ApiFixture(platform, scheme)
        if platform == "github":
            provider = GitHubHandoff("github.com", "team/repo", fixture)
        else:
            provider = GitLabHandoff("gitlab.example.test", "group/project", fixture)
        destination = provider.target_facts()
        preview = {"formatVersion": 1, "state": "preview", "source": self.source,
                   "destination": destination, "title": "Scope",
                   "body": render_body(self.source)}
        with patch("local_ticket_publish.snapshot_issue", return_value=self.source):
            first = publish_preview(preview, self.project, self.base / "runtime",
                                    provider, self.base / "journal", confirm=True)
            second = publish_preview(preview, self.project, self.base / "runtime",
                                     provider, self.base / "journal", confirm=True)
        self.assertEqual(first["state"], "verified")
        self.assertEqual(second["state"], "verified")
        self.assertEqual(len(fixture.issues), 1)
        self.assertEqual(len(fixture.comments[1]), 1)
        self.assertEqual(fixture.issues[0]["state"],
                         "closed" if platform == "github" else "closed")
        self.assertTrue(any("page=1" in part for args, _ in fixture.calls for part in args))
        return fixture, provider

    def test_github_roundtrip_excludes_pull_request(self):
        self.roundtrip("github")

    def test_gitlab_roundtrip_excludes_system_notes(self):
        fixture, provider = self.roundtrip("gitlab")
        fixture.comments[1].append({"body": "system change", "system": True})
        self.assertEqual(len(provider.list_comments(1)["comments"]), 1)

    def test_gitlab_http_project_roundtrip_uses_project_web_scheme(self):
        self.roundtrip("gitlab", scheme="http")

    def test_gitlab_internal_marker_is_conflict(self):
        fixture = ApiFixture("gitlab")
        provider = GitLabHandoff("gitlab.example.test", "group/project", fixture)
        provider.target_facts()
        fixture.comments[1] = [{"body": "spec-guard-local-event:v1 E2",
                                "system": False, "internal": True}]
        with self.assertRaisesRegex(InventoryError, "conflict"):
            provider.list_comments(1)

    def test_both_adapters_reconcile_lost_write_responses(self):
        for platform in ("github", "gitlab"):
            with self.subTest(platform=platform):
                fixture = ApiFixture(platform)
                fixture.lose_issue_after = True
                fixture.lose_note_after = True
                provider = (GitHubHandoff("github.com", "team/repo", fixture)
                            if platform == "github" else
                            GitLabHandoff("gitlab.example.test", "group/project", fixture))
                preview = {"formatVersion": 1, "state": "preview",
                           "source": self.source, "destination": provider.target_facts(),
                           "title": "Scope", "body": render_body(self.source)}
                with patch("local_ticket_publish.snapshot_issue", return_value=self.source):
                    outcome = publish_preview(
                        preview, self.project, self.base / "runtime", provider,
                        self.base / ("journal-" + platform), confirm=True,
                    )
                self.assertEqual(outcome["state"], "verified")
                self.assertEqual(len(fixture.issues), 1)
                self.assertEqual(len(fixture.comments[1]), 1)

    def test_incomplete_pagination_and_rate_limit_fail_closed(self):
        with self.assertRaisesRegex(InventoryError, "pagination limit"):
            pages(lambda number: [{}] * PAGE_SIZE)
        self.assertEqual(MAX_PAGES, 50)
        fixture = ApiFixture("github")
        def limited(arguments, body):
            if any("issues?" in part for part in arguments):
                raise InventoryError("provider-unavailable: rate limited")
            return fixture(arguments, body)
        provider = GitHubHandoff("github.com", "team/repo", limited)
        provider.target_facts()
        with self.assertRaisesRegex(InventoryError, "rate limited"):
            provider.list_issues()


if __name__ == "__main__":
    unittest.main()
