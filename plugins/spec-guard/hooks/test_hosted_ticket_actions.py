"""Comment and delivery-close contracts with no network writes."""
import tempfile
import unittest
from pathlib import Path

from hosted_ticket_actions import (close_issue, make_close_preview,
                                   make_comment_preview, publish_comment)
from hosted_ticket_provider import GitHubIssues, GitLabIssues, HostedTicketError


class FakeProvider:
    def __init__(self):
        self.issue = {"id": 7, "title": "Crash", "body": "Evidence",
                      "closed": False, "url": "https://github.com/team/repo/issues/7"}
        self.comments = []
        self.comment_attempts = 0
        self.close_attempts = 0
        self.lose_comment_response = False
        self.hide_comment = False
        self.lose_close_response = False
        self.delivery = {"merged": True, "mergeCommit": "a" * 40,
                         "url": "https://github.com/team/repo/pull/12"}

    def target_facts(self):
        return {"platform": "github", "host": "github.com", "target": "team/repo",
                "targetId": 42, "visibility": "private"}

    def get_issue(self, issue_id):
        assert issue_id == 7
        return dict(self.issue)

    def list_comments(self, issue_id):
        assert issue_id == 7
        return {"complete": True,
                "comments": [] if self.hide_comment else list(self.comments)}

    def create_comment(self, issue_id, body):
        self.comment_attempts += 1
        self.comments.append({"body": body})
        if self.lose_comment_response:
            raise HostedTicketError("provider-unavailable")

    def get_delivery(self, number):
        assert number == 12
        return dict(self.delivery)

    def set_closed(self, issue_id):
        self.close_attempts += 1
        self.issue["closed"] = True
        if self.lose_close_response:
            raise HostedTicketError("provider-unavailable")


class ActionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="sg-hosted-actions-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "intents"
        self.provider = FakeProvider()

    def test_comment_is_idempotent_and_reads_back(self):
        preview = make_comment_preview(self.provider, 7, "decision-1", "Fix scope A")
        first = publish_comment(preview, self.provider, self.root, confirm=True)
        second = publish_comment(preview, self.provider, self.root, confirm=True)
        self.assertEqual(first["state"], "verified")
        self.assertEqual(second["state"], "found")
        self.assertEqual(self.provider.comment_attempts, 1)

    def test_auto_closed_issue_can_record_validation_without_reopening(self):
        self.provider.issue["closed"] = True
        preview = make_comment_preview(self.provider, 7, "delivery-12", "Merged and CI passed")
        self.assertEqual(preview["state"], "preview")
        self.assertEqual(publish_comment(preview, self.provider, self.root,
                                         confirm=True)["state"], "verified")
        self.assertTrue(self.provider.issue["closed"])
        self.assertEqual(self.provider.comment_attempts, 1)

    def test_lost_comment_response_recovers_or_stays_unknown_without_retry(self):
        preview = make_comment_preview(self.provider, 7, "decision-1", "Fix scope A")
        self.provider.lose_comment_response = True
        self.assertEqual(publish_comment(preview, self.provider, self.root,
                                         confirm=True)["state"], "verified")
        self.provider.comments.clear()
        self.provider.hide_comment = True
        preview = make_comment_preview(self.provider, 7, "decision-2", "Fix scope B")
        self.assertEqual(publish_comment(preview, self.provider, self.root,
                                         confirm=True)["state"], "unknown")
        self.assertEqual(publish_comment(preview, self.provider, self.root,
                                         confirm=True)["state"], "unknown")
        self.assertEqual(self.provider.comment_attempts, 2)

    def test_duplicate_or_displaced_comment_marker_is_conflict(self):
        marker = "<!-- spec-guard-hosted-comment:v1 decision-1 -->"
        self.provider.comments = [{"body": marker}, {"body": marker}]
        self.assertEqual(make_comment_preview(self.provider, 7, "decision-1", "Fix")
                         ["state"], "conflict")
        self.provider.comments = [{"body": marker + "\nextra"}]
        self.assertEqual(make_comment_preview(self.provider, 7, "decision-1", "Fix")
                         ["state"], "conflict")

    def test_close_requires_merged_delivery_complete_coverage_and_validation(self):
        self.provider.delivery["merged"] = False
        self.assertEqual(make_close_preview(self.provider, 7, 12, True, "CI passed")
                         ["state"], "incomplete")
        self.provider.delivery["merged"] = True
        self.assertEqual(make_close_preview(self.provider, 7, 12, False, "CI passed")
                         ["state"], "incomplete")
        self.assertEqual(make_close_preview(self.provider, 7, 12, True, "")
                         ["state"], "incomplete")

    def test_close_reads_back_and_does_not_reclose(self):
        preview = make_close_preview(self.provider, 7, 12, True, "CI passed")
        self.assertEqual(close_issue(preview, self.provider, confirm=True)["state"], "verified")
        self.assertEqual(close_issue(preview, self.provider, confirm=True)["state"],
                         "already-closed")
        self.assertEqual(self.provider.close_attempts, 1)

    def test_lost_close_response_uses_readback(self):
        preview = make_close_preview(self.provider, 7, 12, True, "CI passed")
        self.provider.lose_close_response = True
        self.assertEqual(close_issue(preview, self.provider, confirm=True)["state"],
                         "verified")
        self.assertEqual(self.provider.close_attempts, 1)

    def test_close_stops_when_issue_scope_changes_after_preview(self):
        preview = make_close_preview(self.provider, 7, 12, True, "CI passed")
        self.provider.issue["body"] = "Evidence and new scope"
        result = close_issue(preview, self.provider, confirm=True)
        self.assertEqual(result["state"], "incomplete")
        self.assertEqual(result["diagnostic"], "issue-content-changed")
        self.assertEqual(self.provider.close_attempts, 0)


class AdapterActionTests(unittest.TestCase):
    def test_github_delivery_comment_and_close_transport(self):
        writes = []
        def read(args):
            endpoint = next(part for part in args if part.startswith("repos/"))
            if endpoint == "repos/team/repo":
                return {"full_name": "team/repo", "id": 42,
                        "private": True, "has_issues": True}
            if "/pulls/12" in endpoint:
                return {"number": 12, "merged": True,
                        "merge_commit_sha": "a" * 40,
                        "html_url": "https://github.com/team/repo/pull/12",
                        "base": {"repo": {"full_name": "team/repo"}}}
            if "/comments?" in endpoint:
                return [{"body": "Decision"}]
            return {"number": 7, "title": "Crash", "body": "Evidence",
                    "state": "open", "html_url": "https://github.com/team/repo/issues/7"}
        def write(args, body):
            writes.append((args, body))
            return {"id": 1}
        provider = GitHubIssues("github.com", "team/repo", read, write)
        provider.target_facts()
        self.assertEqual(provider.get_delivery(12)["mergeCommit"], "a" * 40)
        self.assertEqual(provider.list_comments(7)["comments"], [{"body": "Decision"}])
        provider.create_comment(7, "Decision")
        provider.set_closed(7)
        self.assertEqual([body for _, body in writes],
                         [{"body": "Decision"}, {"state": "closed"}])

    def test_gitlab_delivery_comment_and_close_transport(self):
        writes = []
        def read(args):
            endpoint = next(part for part in args if part.startswith("projects/"))
            if endpoint == "projects/team%2Frepo":
                return {"path_with_namespace": "team/repo", "id": 43,
                        "web_url": "https://gitlab.example.test/team/repo",
                        "visibility": "private", "issues_enabled": True}
            if "/merge_requests/12" in endpoint:
                return {"iid": 12, "project_id": 43, "state": "merged",
                        "merge_commit_sha": "b" * 40,
                        "web_url": "https://gitlab.example.test/team/repo/-/merge_requests/12"}
            if "/notes?" in endpoint:
                return [{"body": "system", "system": True},
                        {"body": "Decision", "system": False, "internal": False}]
            return {"iid": 7, "project_id": 43, "title": "Crash",
                    "description": "Evidence", "state": "opened",
                    "web_url": "https://gitlab.example.test/team/repo/-/issues/7"}
        def write(args, body):
            writes.append((args, body))
            return {"id": 1}
        provider = GitLabIssues("gitlab.example.test", "team/repo", read, write)
        provider.target_facts()
        self.assertEqual(provider.get_delivery(12)["mergeCommit"], "b" * 40)
        self.assertEqual(provider.list_comments(7)["comments"], [{"body": "Decision"}])
        provider.create_comment(7, "Decision")
        provider.set_closed(7)
        self.assertEqual([body for _, body in writes],
                         [{"body": "Decision"}, {"state_event": "close"}])

    def test_gitlab_fast_forward_and_squash_delivery_commit(self):
        delivery = {"iid": 12, "project_id": 43, "state": "merged",
                    "merge_commit_sha": None, "sha": "c" * 40,
                    "web_url": "https://gitlab.example.test/team/repo/-/merge_requests/12"}
        def read(args):
            endpoint = next(part for part in args if part.startswith("projects/"))
            if endpoint == "projects/team%2Frepo":
                return {"path_with_namespace": "team/repo", "id": 43,
                        "web_url": "https://gitlab.example.test/team/repo",
                        "visibility": "private", "issues_enabled": True}
            return delivery
        provider = GitLabIssues("gitlab.example.test", "team/repo", read)
        provider.target_facts()
        self.assertEqual(provider.get_delivery(12)["mergeCommit"], "c" * 40)
        delivery["squash_commit_sha"] = "d" * 40
        self.assertEqual(provider.get_delivery(12)["mergeCommit"], "d" * 40)


if __name__ == "__main__":
    unittest.main()
