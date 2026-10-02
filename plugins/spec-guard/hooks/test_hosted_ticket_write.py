"""Safe single-Issue creation with fake providers and private intent files."""
import tempfile
import threading
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from hosted_ticket_provider import (GitHubIssues, GitLabIssues, HostedTicketError,
                                    ProviderRejected, run_write_json)
from hosted_ticket_write import make_preview, publish_preview


class FakeProvider:
    def __init__(self):
        self.issues = []
        self.attempts = 0
        self.lose_response = False
        self.invisible_after_write = False
        self.reject = False
        self.reject_readback = False

    def target_facts(self):
        return {"platform": "github", "host": "github.com", "target": "team/repo",
                "targetId": 42, "visibility": "private"}

    def list_issues(self):
        return {"complete": True,
                "issues": [] if self.invisible_after_write else list(self.issues)}

    def create_issue(self, title, body):
        self.attempts += 1
        if self.reject:
            raise ProviderRejected(422)
        item = {"id": len(self.issues) + 1, "title": title, "body": body,
                "closed": False,
                "url": "https://github.com/team/repo/issues/" + str(len(self.issues) + 1)}
        self.issues.append(item)
        if self.lose_response:
            raise HostedTicketError("provider-unavailable: lost response")
        return item

    def get_issue(self, issue_id):
        if self.reject_readback:
            raise ProviderRejected(404)
        if self.invisible_after_write:
            raise HostedTicketError("provider-unavailable: not yet visible")
        return self.issues[issue_id - 1]


class WriteTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="sg-hosted-write-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "private-intents"
        self.provider = FakeProvider()
        self.preview = make_preview(self.provider, "private", "B-1-F-2",
                                    "Crash", "Steps and acceptance")

    def publish(self, **kwargs):
        return publish_preview(self.preview, self.provider, self.root,
                               confirm=True, root_cause_reviewed=True, **kwargs)

    def test_preview_is_read_only_and_requires_root_cause_review(self):
        self.assertEqual(self.preview["state"], "preview")
        self.assertFalse(self.root.exists())
        self.assertEqual(publish_preview(self.preview, self.provider, self.root,
                                         confirm=True)["state"], "review-required")
        self.assertEqual(self.provider.attempts, 0)

    def test_create_reads_back_and_repeat_reuses_identity(self):
        first = self.publish()
        second = self.publish()
        self.assertEqual(first["state"], "verified")
        self.assertEqual(second["state"], "found")
        self.assertEqual(first["issue"]["id"], second["issue"]["id"])
        self.assertEqual(self.provider.attempts, 1)
        self.assertEqual(list(self.root.glob("*.json")), [])

    def test_lost_response_recovers_by_marker(self):
        self.provider.lose_response = True
        result = self.publish()
        self.assertEqual(result["state"], "verified")
        self.assertEqual(self.provider.attempts, 1)

    def test_invisible_attempt_stays_uncertain_across_calls(self):
        self.provider.lose_response = True
        self.provider.invisible_after_write = True
        self.assertEqual(self.publish()["state"], "unknown")
        self.assertEqual(self.publish()["state"], "unknown")
        self.assertEqual(self.provider.attempts, 1)
        records = list(self.root.glob("*.json"))
        self.assertEqual(len(records), 1)
        self.assertNotIn("Steps and acceptance", records[0].read_text())

    def test_readback_404_after_creation_cannot_reset_create_attempt(self):
        self.provider.reject_readback = True
        self.provider.invisible_after_write = True
        self.assertEqual(self.publish()["state"], "unknown")
        self.assertEqual(self.publish()["state"], "unknown")
        self.assertEqual(self.provider.attempts, 1)

    def test_definite_rejection_does_not_claim_created(self):
        self.provider.reject = True
        result = self.publish()
        self.assertEqual(result["state"], "rejected")
        self.assertEqual(result["statusCode"], 422)
        self.assertEqual(self.provider.issues, [])

    def test_concurrent_calls_share_one_intent_lock(self):
        outcomes = []
        threads = [threading.Thread(target=lambda: outcomes.append(self.publish()))
                   for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(self.provider.attempts, 1)
        self.assertEqual({item["state"] for item in outcomes}, {"verified", "found"})

    def test_preview_change_or_existing_title_candidate_blocks_write(self):
        changed = {**self.preview, "title": "Different"}
        self.assertEqual(publish_preview(changed, self.provider, self.root,
                                         confirm=True, root_cause_reviewed=True)["state"],
                         "preview-invalid")
        self.provider.issues.append({"id": 9, "title": "Crash", "body": "",
                                     "closed": False,
                                     "url": "https://github.com/team/repo/issues/9"})
        self.assertEqual(self.publish()["state"], "conflict")
        self.assertEqual(self.provider.attempts, 0)

    def test_provider_rejection_does_not_expose_response_body(self):
        response = CompletedProcess([], 1,
                                    'HTTP/2.0 422 Unprocessable Entity\r\n\r\n{"secret":"x"}',
                                    "private error")
        with patch("hosted_ticket_provider.subprocess.run", return_value=response):
            with self.assertRaises(ProviderRejected) as caught:
                run_write_json(["gh", "api", "repos/team/repo/issues"],
                               {"title": "Crash"})
        self.assertEqual(caught.exception.status_code, 422)
        self.assertNotIn("secret", str(caught.exception))

    def test_both_platform_adapters_create_and_read_back(self):
        for platform in ("github", "gitlab"):
            with self.subTest(platform=platform):
                raw_issue = None

                def read(args):
                    nonlocal raw_issue
                    endpoint = next(part for part in args if part.startswith(("repos/", "projects/")))
                    if endpoint in ("repos/team/repo", "projects/team%2Frepo"):
                        if platform == "github":
                            return {"full_name": "team/repo", "id": 42,
                                    "private": True, "has_issues": True}
                        return {"path_with_namespace": "team/repo", "id": 43,
                                "web_url": "https://gitlab.example.test/team/repo",
                                "visibility": "private", "issues_enabled": True}
                    if "?" in endpoint:
                        return [raw_issue] if raw_issue else []
                    return raw_issue

                def write(args, body):
                    nonlocal raw_issue
                    if platform == "github":
                        raw_issue = {"number": 1, "title": body["title"],
                                     "body": body["body"], "state": "open",
                                     "html_url": "https://github.com/team/repo/issues/1"}
                    else:
                        raw_issue = {"iid": 1, "project_id": 43,
                                     "title": body["title"],
                                     "description": body["description"],
                                     "state": "opened",
                                     "web_url": "https://gitlab.example.test/team/repo/-/issues/1"}
                    return raw_issue

                provider = (GitHubIssues("github.com", "team/repo", read, write)
                            if platform == "github" else
                            GitLabIssues("gitlab.example.test", "team/repo", read, write))
                preview = make_preview(provider, "private", "B-1-F-2",
                                       "Crash", "Steps and acceptance")
                result = publish_preview(preview, provider,
                                         self.root / platform, confirm=True,
                                         root_cause_reviewed=True)
                self.assertEqual(result["state"], "verified")
                self.assertEqual(result["issue"]["id"], 1)


if __name__ == "__main__":
    unittest.main()
