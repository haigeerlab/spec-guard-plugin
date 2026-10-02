"""Read-only hosted ticket contract; no network or Local ledger."""
import unittest

from hosted_ticket_read import inspect_ticket
from hosted_ticket_provider import GitHubIssues, GitLabIssues, HostedTicketError, PAGE_SIZE, pages


class FakeProvider:
    def __init__(self, issues=(), complete=True, visibility="private"):
        self.issues = list(issues)
        self.complete = complete
        self.visibility = visibility

    def target_facts(self):
        return {"platform": "github", "host": "github.com", "target": "team/repo",
                "targetId": 42, "visibility": self.visibility}

    def list_issues(self):
        return {"complete": self.complete, "issues": self.issues}


def issue(number, title="Crash", body=""):
    return {"id": number, "title": title, "body": body, "closed": False,
            "url": f"https://github.com/team/repo/issues/{number}"}


class ReadTests(unittest.TestCase):
    def inspect(self, provider):
        return inspect_ticket(provider, "private", "B-1-F-2", "Crash")

    def test_empty_complete_target_is_absent_but_requires_root_cause_review(self):
        result = self.inspect(FakeProvider())
        self.assertEqual(result["state"], "absent")
        self.assertTrue(result["rootCauseReviewRequired"])
        self.assertEqual(result["scannedCount"], 0)

    def test_single_exact_marker_is_found_even_when_title_changed(self):
        body = "Evidence\n\n<!-- spec-guard-hosted-ticket:v1 B-1-F-2 -->"
        result = self.inspect(FakeProvider([issue(7, "Renamed", body)]))
        self.assertEqual(result["state"], "found")
        self.assertEqual(result["issue"]["id"], 7)

    def test_duplicate_or_displaced_marker_is_conflict(self):
        marker = "<!-- spec-guard-hosted-ticket:v1 B-1-F-2 -->"
        self.assertEqual(self.inspect(FakeProvider([
            issue(7, body=marker), issue(8, body=marker)]))["state"], "conflict")
        self.assertEqual(self.inspect(FakeProvider([
            issue(7, body=marker + "\nother text")]))["state"], "conflict")

    def test_unmarked_title_candidate_requires_manual_resolution(self):
        result = self.inspect(FakeProvider([issue(9, "Crash")]))
        self.assertEqual(result["state"], "conflict")
        self.assertEqual(result["candidates"][0]["id"], 9)

    def test_visibility_or_pagination_unknown_never_means_absent(self):
        self.assertEqual(self.inspect(FakeProvider(visibility="public"))["state"], "unknown")
        self.assertEqual(self.inspect(FakeProvider(complete=False))["state"], "unknown")


class ProviderTests(unittest.TestCase):
    def test_read_only_metadata_does_not_require_write_permission(self):
        def github(args):
            endpoint = next(x for x in args if x.startswith("repos/"))
            if endpoint == "repos/team/repo":
                return {"full_name": "team/repo", "id": 42, "private": False,
                        "has_issues": True}
            return []
        self.assertEqual(GitHubIssues("github.com", "team/repo", github)
                         .target_facts()["visibility"], "public")

    def test_full_pagination_limit_is_unknown(self):
        with self.assertRaises(HostedTicketError):
            pages(lambda number: [{}] * PAGE_SIZE)

    def test_github_filters_pull_requests_and_reads_closed_issues(self):
        def runner(args):
            endpoint = next(x for x in args if x.startswith("repos/"))
            if endpoint == "repos/team/repo":
                return {"full_name": "team/repo", "id": 42, "private": True,
                        "has_issues": True, "permissions": {"push": True}}
            return [
                {"number": 1, "title": "PR", "body": "", "state": "open",
                 "html_url": "https://github.com/team/repo/pull/1", "pull_request": {}},
                {"number": 2, "title": "Crash", "body": "", "state": "closed",
                 "html_url": "https://github.com/team/repo/issues/2"},
            ]
        provider = GitHubIssues("github.com", "team/repo", runner)
        self.assertEqual(provider.target_facts()["visibility"], "private")
        listing = provider.list_issues()
        self.assertEqual([item["id"] for item in listing["issues"]], [2])
        self.assertTrue(listing["issues"][0]["closed"])

    def test_gitlab_rejects_wrong_project_issue(self):
        def runner(args):
            endpoint = next(x for x in args if x.startswith("projects/"))
            if endpoint == "projects/group%2Frepo":
                return {"path_with_namespace": "group/repo", "id": 43,
                        "web_url": "https://gitlab.example.test/group/repo",
                        "visibility": "private", "issues_enabled": True,
                        "permissions": {"project_access": {"access_level": 30}}}
            return [{"iid": 3, "project_id": 44, "title": "Crash", "description": "",
                     "state": "opened",
                     "web_url": "https://gitlab.example.test/group/repo/-/issues/3"}]
        provider = GitLabIssues("gitlab.example.test", "group/repo", runner)
        provider.target_facts()
        with self.assertRaises(HostedTicketError):
            provider.list_issues()

    def test_gitlab_system_note_is_ignored_but_private_marker_is_conflict(self):
        notes = [{"body": "system change", "system": True}]
        def runner(args):
            endpoint = next(x for x in args if x.startswith("projects/"))
            if endpoint == "projects/group%2Frepo":
                return {"path_with_namespace": "group/repo", "id": 43,
                        "web_url": "https://gitlab.example.test/group/repo",
                        "visibility": "private", "issues_enabled": True}
            if "/notes?" in endpoint:
                return notes
            return []
        provider = GitLabIssues("gitlab.example.test", "group/repo", runner)
        provider.target_facts()
        self.assertEqual(provider.list_comments(3)["comments"], [])
        notes[:] = [{"body": "<!-- spec-guard-hosted-comment:v1 decision-1 -->",
                    "system": False, "internal": True}]
        with self.assertRaises(HostedTicketError):
            provider.list_comments(3)

    def test_malformed_github_issue_url_has_a_safe_error(self):
        def runner(args):
            endpoint = next(x for x in args if x.startswith("repos/"))
            if endpoint == "repos/team/repo":
                return {"full_name": "team/repo", "id": 42, "private": True,
                        "has_issues": True}
            return [{"number": 3, "title": "Crash", "body": "", "state": "open",
                     "html_url": None}]
        provider = GitHubIssues("github.com", "team/repo", runner)
        with self.assertRaises(HostedTicketError):
            provider.list_issues()


if __name__ == "__main__":
    unittest.main()
