"""Failure-injection tests for explicit Local ticket handoff reconciliation."""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from local_ticket_journal import entry_key, journal_path, read_journal
from local_ticket_publish import publish_preview
from local_ticket_preview import EVENT_MARKER, render_body
from local_ticket_portability import main


PROJECT_ID = "01M37F8MKQRSB562YCBQ004QGJ"
ISSUE_ID = "01M3SX6JWYGM5120R5VDA15T35"
DESTINATION = {"platform": "github", "host": "github.com", "target": "team/repo",
               "targetId": 42, "visibility": "private"}


class FakeProvider:
    def __init__(self):
        self.issues = []
        self.comments = {}
        self.next_id = 1
        self.lose_create = None
        self.lose_comment = None

    def target_facts(self):
        return DESTINATION

    def list_issues(self):
        return {"complete": True, "issues": [dict(issue) for issue in self.issues]}

    def get_issue(self, issue_id):
        return dict(next(issue for issue in self.issues if issue["id"] == issue_id))

    def create_issue(self, title, body):
        if self.lose_create == "before":
            raise TimeoutError("response lost before write")
        issue = {"id": self.next_id, "title": title, "body": body,
                 "closed": False, "url": "https://example.invalid/issues/1"}
        self.next_id += 1
        self.issues.append(issue)
        if self.lose_create == "after":
            raise TimeoutError("response lost after write")
        return dict(issue)

    def list_comments(self, issue_id):
        return {"complete": True, "comments": list(self.comments.get(issue_id, []))}

    def create_comment(self, issue_id, body):
        if self.lose_comment == "before":
            raise TimeoutError("comment result lost before write")
        self.comments.setdefault(issue_id, []).append({"body": body})
        if self.lose_comment == "after":
            raise TimeoutError("comment result lost after write")

    def set_closed(self, issue_id, closed):
        next(issue for issue in self.issues if issue["id"] == issue_id)["closed"] = closed


class HandoffTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="sg-handoff-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.project = self.base / "project"
        self.project.mkdir()
        import subprocess
        subprocess.run(["git", "-C", str(self.project), "init", "-q"], check=True)
        self.journal_root = self.base / "private-journal"
        self.source = {
            "projectId": PROJECT_ID, "issueId": ISSUE_ID, "sourceDigest": "a" * 64,
            "issue": {"title": "Scope", "description": "Current scope",
                      "isClosed": True}, "attachments": [], "codeReferences": [],
            "events": [
                {"id": "E1", "action": "add.issue", "payload": {"id": ISSUE_ID}},
                {"id": "E2", "action": "add.issue.comment",
                 "payload": {"id": "C1", "issue": ISSUE_ID, "md": "Decision"}},
            ],
        }
        self.preview = {"formatVersion": 1, "state": "preview",
                        "source": self.source, "destination": DESTINATION,
                        "title": "Scope", "body": render_body(self.source)}
        self.provider = FakeProvider()

    def publish(self):
        with patch("local_ticket_publish.snapshot_issue", return_value=self.source):
            return publish_preview(self.preview, self.project, self.base / "runtime",
                                   self.provider, self.journal_root, confirm=True)

    def test_verified_handoff_and_repeat_do_not_duplicate(self):
        result = self.publish()
        self.assertEqual(result["state"], "verified")
        self.assertEqual(len(self.provider.issues), 1)
        self.assertEqual(len(self.provider.comments[1]), 1)
        self.assertIn(EVENT_MARKER, self.provider.comments[1][0]["body"])
        self.assertTrue(self.provider.issues[0]["closed"])
        self.assertEqual(self.publish()["state"], "verified")
        self.assertEqual(len(self.provider.issues), 1)
        self.assertEqual(len(self.provider.comments[1]), 1)
        path = journal_path(self.project, PROJECT_ID, self.journal_root)
        key = entry_key(PROJECT_ID, ISSUE_ID, DESTINATION)
        self.assertEqual(read_journal(path)["entries"][key]["state"], "verified")

    def test_lost_create_response_reconciles_visible_issue(self):
        self.provider.lose_create = "after"
        self.assertEqual(self.publish()["state"], "verified")
        self.assertEqual(len(self.provider.issues), 1)

    def test_lost_create_without_visible_issue_stops_retry(self):
        self.provider.lose_create = "before"
        self.assertEqual(self.publish()["state"], "publication-uncertain")
        self.provider.lose_create = None
        self.assertEqual(self.publish()["state"], "publication-uncertain")
        self.assertEqual(len(self.provider.issues), 0)

    def test_lost_comment_response_and_manual_edit(self):
        self.provider.lose_comment = "after"
        self.assertEqual(self.publish()["state"], "verified")
        self.provider.lose_comment = None
        self.provider.comments[1][0]["body"] = "Changed\n\n" + self.provider.comments[1][0]["body"].splitlines()[-1]
        self.assertEqual(self.publish()["state"], "conflict")
        self.assertEqual(len(self.provider.comments[1]), 1)

    def test_duplicate_issue_marker_is_conflict(self):
        self.provider.issues = [
            {"id": number, "title": "Scope", "body": self.preview["body"],
             "closed": False, "url": "https://example.invalid/issues/" + str(number)}
            for number in (1, 2)
        ]
        self.assertEqual(self.publish()["state"], "conflict")
        self.assertEqual(len(self.provider.issues), 2)

    def test_attachment_remains_partial_without_duplicate_on_retry(self):
        self.source["attachments"] = [{"hash": "a" * 64, "ext": "gif", "bytes": 10}]
        self.preview["body"] = render_body(self.source)
        self.assertEqual(self.publish()["state"], "partial")
        self.assertEqual(self.publish()["state"], "partial")
        self.assertEqual(len(self.provider.issues), 1)
        self.assertEqual(len(self.provider.comments[1]), 1)
        self.assertNotIn("proposal-stage:", self.preview["body"])

    def test_stale_source_and_incomplete_listing_stop_before_write(self):
        self.preview["body"] = "edited preview"
        from local_ticket_portability import InventoryError
        with self.assertRaisesRegex(InventoryError, "preview-stale"):
            self.publish()
        self.preview["body"] = render_body(self.source)
        self.provider.list_issues = lambda: {"complete": False, "issues": []}
        with self.assertRaisesRegex(InventoryError, "publication-uncertain"):
            self.publish()
        self.assertEqual(self.provider.issues, [])

    def test_prior_comment_attempt_without_readback_stops_retry(self):
        self.provider.lose_comment = "before"
        self.assertEqual(self.publish()["state"], "publication-uncertain")
        self.provider.lose_comment = None
        self.assertEqual(self.publish()["state"], "publication-uncertain")
        self.assertEqual(len(self.provider.issues), 1)
        self.assertEqual(self.provider.comments.get(1, []), [])

    def test_cli_needs_confirm_before_hosted_write(self):
        preview_file = self.base / "preview.json"
        preview_file.write_text(json.dumps(self.preview), encoding="utf-8")
        output = io.StringIO()
        with (patch("local_ticket_github.GitHubHandoff", return_value=self.provider),
              patch("local_ticket_publish.snapshot_issue", return_value=self.source),
              patch("local_ticket_journal.default_journal_root",
                    return_value=self.journal_root),
              redirect_stdout(output)):
            self.assertEqual(main(["handoff-publish", "--project", str(self.project),
                                   "--preview", str(preview_file)]), 1)
            self.assertEqual(self.provider.issues, [])
            output.seek(0)
            output.truncate(0)
            self.assertEqual(main(["handoff-publish", "--project", str(self.project),
                                   "--preview", str(preview_file), "--confirm"]), 0)
        self.assertEqual(json.loads(output.getvalue())["state"], "verified")


if __name__ == "__main__":
    unittest.main()
