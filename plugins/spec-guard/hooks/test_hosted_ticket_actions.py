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

    def test_comment_stops_when_issue_scope_changes_after_preview(self):
        preview = make_comment_preview(self.provider, 7, "decision-1", "Fix scope A")
        self.provider.issue["body"] = "Evidence and new scope"
        result = publish_comment(preview, self.provider, self.root, confirm=True)
        self.assertEqual(result["state"], "incomplete")
        self.assertEqual(result["diagnostic"], "issue-content-changed")
        self.assertEqual(self.provider.comment_attempts, 0)

    def test_changed_scope_still_recovers_an_already_posted_comment(self):
        preview = make_comment_preview(self.provider, 7, "decision-1", "Fix scope A")
        self.provider.hide_comment = True
        self.provider.lose_comment_response = True
        self.assertEqual(publish_comment(preview, self.provider, self.root,
                                         confirm=True)["state"], "unknown")
        self.provider.hide_comment = False
        self.provider.issue["body"] = "Evidence and new scope"
        result = publish_comment(preview, self.provider, self.root, confirm=True)
        self.assertEqual(result["state"], "found")
        self.assertEqual(self.provider.comment_attempts, 1)

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
        first = close_issue(preview, self.provider, confirm=True)
        self.assertEqual(first["state"], "verified")
        self.assertEqual(first["verifiedFact"], "remote-issue-closed")
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
                    "target_branch": "main",
                    "web_url": "https://gitlab.example.test/team/repo/-/merge_requests/12"}
        refs = [{"type": "branch", "name": "main"}]
        def read(args):
            endpoint = next(part for part in args if part.startswith("projects/"))
            if endpoint == "projects/team%2Frepo":
                return {"path_with_namespace": "team/repo", "id": 43,
                        "web_url": "https://gitlab.example.test/team/repo",
                        "visibility": "private", "issues_enabled": True}
            if "/refs?" in endpoint:
                return refs
            return delivery
        provider = GitLabIssues("gitlab.example.test", "team/repo", read)
        provider.target_facts()
        self.assertEqual(provider.get_delivery(12)["mergeCommit"], "c" * 40)
        refs[:] = [{"type": "branch", "name": "other"}]
        with self.assertRaises(HostedTicketError):
            provider.get_delivery(12)
        refs[:] = [{"type": "branch", "name": "main"}]
        delivery["squash_commit_sha"] = "d" * 40
        self.assertEqual(provider.get_delivery(12)["mergeCommit"], "d" * 40)


class Defect:
    """A provider whose one named method raises a programming error, as a typo would.

    AttributeError is the realistic shape: a misspelled attribute inside an adapter.
    It must not be reportable as a fact about the provider or the remote.
    """

    def __init__(self, provider, method):
        self._provider, self._method = provider, method

    def __getattr__(self, name):
        if name == self._method:
            def boom(*_arguments, **_keywords):
                raise AttributeError("'Adapter' object has no attribute 'typo'")
            return boom
        return getattr(self._provider, name)


class ProgrammingErrorTests(unittest.TestCase):
    """A defect in our own code must not be reported as provider uncertainty.

    Every handler here used to catch bare `Exception`, so an AttributeError inside an
    adapter came back as `unknown` + `provider-unavailable` / `*-uncertain`. That reads
    as "the remote flaked, retry", and sends the reader to check a remote that is fine.
    The CLI in `hosted_ticket_action.py` already catches only
    `(HostedTicketError, OSError, UnicodeError)`, so surfacing a programming error is
    this module's own existing contract; the library layer disagreed with it.
    """

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="sg-hosted-defect-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "intents"
        self.provider = FakeProvider()

    def comment_preview(self):
        return make_comment_preview(self.provider, 7, "decision-1", "Fix scope A")

    def close_preview(self):
        return make_close_preview(self.provider, 7, 12, True, "regression suite green")

    # ── a programming error propagates ────────────────────────────────────
    def test_comment_preview_propagates_a_programming_error(self):
        with self.assertRaises(AttributeError):
            make_comment_preview(Defect(self.provider, "get_issue"), 7, "decision-1", "Fix")

    def test_comment_publish_propagates_a_programming_error_in_the_write(self):
        preview = self.comment_preview()
        with self.assertRaises(AttributeError):
            publish_comment(preview, Defect(self.provider, "create_comment"),
                            self.root, confirm=True)

    def test_comment_publish_propagates_a_programming_error_before_the_write(self):
        preview = self.comment_preview()
        with self.assertRaises(AttributeError):
            publish_comment(preview, Defect(self.provider, "target_facts"),
                            self.root, confirm=True)

    def test_close_preview_propagates_a_programming_error(self):
        with self.assertRaises(AttributeError):
            make_close_preview(Defect(self.provider, "get_delivery"), 7, 12, True, "green")

    def test_close_propagates_a_programming_error_in_the_write(self):
        preview = self.close_preview()
        with self.assertRaises(AttributeError):
            close_issue(preview, Defect(self.provider, "set_closed"), confirm=True)

    def test_close_propagates_a_programming_error_before_the_write(self):
        preview = self.close_preview()
        with self.assertRaises(AttributeError):
            close_issue(preview, Defect(self.provider, "target_facts"), confirm=True)

    # ── control: a real transport failure still degrades, not raises ──────
    # Without these, a fix that simply let everything raise would look identical.
    def test_transport_failure_still_degrades_on_comment_preview(self):
        result = make_comment_preview(_Unavailable(self.provider, "get_issue"), 7,
                                      "decision-1", "Fix")
        self.assertEqual(result, {"state": "unknown", "diagnostic": "provider-unavailable"})

    def test_transport_failure_still_degrades_on_close_preview(self):
        result = make_close_preview(_Unavailable(self.provider, "get_delivery"), 7, 12,
                                    True, "green")
        self.assertEqual(result, {"state": "unknown", "diagnostic": "provider-unavailable"})

    def test_lost_write_response_is_still_uncertain_not_raised(self):
        preview = self.comment_preview()
        self.provider.lose_comment_response = True
        self.provider.hide_comment = True
        result = publish_comment(preview, self.provider, self.root, confirm=True)
        self.assertEqual(result["state"], "unknown")
        self.assertEqual(result["diagnostic"], "comment-result-uncertain")


class _Unavailable(Defect):
    """Same injection point, but the failure the transport actually raises."""

    def __getattr__(self, name):
        if name == self._method:
            def unavailable(*_arguments, **_keywords):
                raise HostedTicketError("provider-unavailable: request did not complete")
            return unavailable
        return getattr(self._provider, name)


if __name__ == "__main__":
    unittest.main()
