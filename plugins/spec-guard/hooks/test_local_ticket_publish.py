"""Failure-injection tests for explicit Local ticket handoff reconciliation."""
import io
from copy import deepcopy
import json
import tempfile
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from local_ticket_handoff import _digest
from local_ticket_journal import (binding_checksum, entry_key, journal_path, publication_lock,
                                  read_journal, write_entry)
from local_ticket_publish import publish_preview
from local_ticket_preview import EVENT_MARKER, render_body
from local_ticket_portability import InventoryError, main
from local_ticket_provider import ProviderRejected


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
        self.reject_create = False
        self.reject_comment = False

    def target_facts(self):
        return DESTINATION

    def list_issues(self):
        return {"complete": True, "issues": [dict(issue) for issue in self.issues]}

    def get_issue(self, issue_id):
        return dict(next(issue for issue in self.issues if issue["id"] == issue_id))

    def create_issue(self, title, body):
        if self.reject_create:
            raise ProviderRejected(422)
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
        if self.reject_comment:
            raise ProviderRejected(403)
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
            "projectId": PROJECT_ID, "issueId": ISSUE_ID, "formatVersion": 2,
            "sourceDigest": "a" * 64,
            "issue": {"title": "Scope", "description": "Current scope",
                      "isClosed": True}, "attachments": [], "codeReferences": [],
            "events": [
                {"id": "E1", "action": "add.issue", "payload": {"id": ISSUE_ID}},
                {"id": "E2", "action": "add.issue.comment",
                 "payload": {"id": "C1", "issue": ISSUE_ID, "md": "Decision"}},
            ],
        }
        self.preview = {"formatVersion": 2, "state": "preview",
                        "source": self.source, "destination": DESTINATION,
                        "title": "Scope", "body": render_body(self.source)}
        self.provider = FakeProvider()

    def publish(self):
        with patch("local_ticket_publish.snapshot_issue", return_value=self.source):
            return publish_preview(self.preview, self.project, self.base / "runtime",
                                   self.provider, self.journal_root, confirm=True)

    def bind_moved_journal(self):
        old = journal_path(self.project, PROJECT_ID, self.journal_root)
        moved = self.base / "moved-project"
        self.project.rename(moved)
        self.project = moved
        current = journal_path(moved, PROJECT_ID, self.journal_root)
        current.parent.mkdir(parents=True, mode=0o700)
        current.parent.parent.chmod(0o700)
        pointer = current.with_name("binding.json")
        binding = {
            "formatVersion": 1, "projectId": PROJECT_ID,
            "currentPartition": current.parent.parent.name,
            "candidatePartition": old.parent.parent.name,
            "canonicalPartition": old.parent.parent.name,
            "initialMappingSha256": "a" * 64, "previewSha256": "b" * 64,
            "boundAt": "2026-10-01T00:00:00+00:00",
        }
        binding["bindingSha256"] = binding_checksum(binding)
        pointer.write_text(json.dumps(binding))
        pointer.chmod(0o600)
        return old, current, pointer

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

    def test_moved_project_stops_before_remote_or_new_journal_write(self):
        old_path = journal_path(self.project, PROJECT_ID, self.journal_root)
        key = entry_key(PROJECT_ID, ISSUE_ID, DESTINATION)
        write_entry(old_path, key, {"state": "partial", "sourceDigest": "a" * 64})
        moved = self.base / "moved-project"
        self.project.rename(moved)
        self.project = moved
        current_path = journal_path(self.project, PROJECT_ID, self.journal_root)
        with patch("local_ticket_publish.snapshot_issue",
                   side_effect=AssertionError("source must not be read before candidate review")):
            result = publish_preview(self.preview, self.project, self.base / "runtime",
                                     self.provider, self.journal_root, confirm=True)
        self.assertEqual(result["state"], "manual-reconciliation-required")
        self.assertEqual(result["candidates"][0]["stateCounts"]["partial"], 1)
        self.assertEqual(self.provider.issues, [])
        self.assertFalse(current_path.exists())

    def test_bound_project_reuses_old_journal_and_never_duplicates(self):
        self.assertEqual(self.publish()["state"], "verified")
        old, current, pointer = self.bind_moved_journal()
        old_before = old.read_bytes()
        key = entry_key(PROJECT_ID, ISSUE_ID, DESTINATION)
        with publication_lock(old, key):
            with self.assertRaisesRegex(InventoryError, "journal-busy"):
                self.publish()
        self.assertEqual(self.publish()["state"], "verified")
        self.assertEqual(len(self.provider.issues), 1)

        original_lock = publication_lock

        @contextmanager
        def changed_binding(path, issue_key):
            with original_lock(path, issue_key):
                value = json.loads(pointer.read_text())
                value["previewSha256"] = "c" * 64
                value["bindingSha256"] = binding_checksum(value)
                pointer.write_text(json.dumps(value))
                yield

        with patch("local_ticket_publish.publication_lock", changed_binding):
            with self.assertRaisesRegex(InventoryError, "journal-bind-stale"):
                self.publish()
        self.assertEqual(len(self.provider.issues), 1)
        self.assertEqual(len(self.provider.comments[1]), 1)
        self.assertEqual(old.read_bytes(), old_before)
        self.assertFalse(current.exists())

        clone = self.base / "independent-clone"
        clone.mkdir()
        import subprocess
        subprocess.run(["git", "-C", str(clone), "init", "-q"], check=True)
        duplicate = journal_path(clone, PROJECT_ID, self.journal_root)
        write_entry(duplicate, "c" * 64, {"state": "partial"})
        self.assertEqual(self.publish()["state"], "manual-reconciliation-required")
        self.assertEqual(len(self.provider.issues), 1)

    def test_bound_uncertain_create_and_invalid_pointer_stop_before_remote_write(self):
        old = journal_path(self.project, PROJECT_ID, self.journal_root)
        key = entry_key(PROJECT_ID, ISSUE_ID, DESTINATION)
        write_entry(old, key, {"state": "planned", "digestVersion": 2,
                               "sourceDigest": self.source["sourceDigest"],
                               "destination": DESTINATION, "createAttempted": True,
                               "remoteId": None, "verifiedEventIds": []})
        _, current, pointer = self.bind_moved_journal()
        self.assertEqual(self.publish()["state"], "publication-uncertain")
        self.assertEqual(self.provider.issues, [])
        self.assertFalse(current.exists())
        valid_pointer = pointer.read_text()
        tampered = json.loads(valid_pointer)
        tampered["previewSha256"] = "c" * 64
        pointer.write_text(json.dumps(tampered))
        with self.assertRaisesRegex(InventoryError, "journal-bind-invalid"):
            self.publish()
        self.assertEqual(self.provider.issues, [])
        pointer.write_text(valid_pointer)
        write_entry(current, key, {"state": "planned"})
        with self.assertRaisesRegex(InventoryError, "another mapping"):
            self.publish()
        self.assertEqual(self.provider.issues, [])

    def test_second_move_publishes_through_original_canonical_journal(self):
        self.assertEqual(self.publish()["state"], "verified")
        old, second_mapping, _ = self.bind_moved_journal()
        third = self.base / "third-project"
        self.project.rename(third)
        self.project = third
        current = journal_path(third, PROJECT_ID, self.journal_root)
        current.parent.mkdir(parents=True, mode=0o700)
        current.parent.parent.chmod(0o700)
        pointer = current.with_name("binding.json")
        value = {
            "formatVersion": 1, "projectId": PROJECT_ID,
            "currentPartition": current.parent.parent.name,
            "candidatePartition": second_mapping.parent.parent.name,
            "canonicalPartition": old.parent.parent.name,
            "initialMappingSha256": "a" * 64, "previewSha256": "b" * 64,
            "boundAt": "2026-10-01T00:00:00+00:00",
        }
        value["bindingSha256"] = binding_checksum(value)
        pointer.write_text(json.dumps(value))
        pointer.chmod(0o600)
        self.assertEqual(self.publish()["state"], "verified")
        self.assertEqual(len(self.provider.issues), 1)
        self.assertEqual(len(self.provider.comments[1]), 1)
        self.assertFalse(current.exists())

    def test_same_id_clone_candidate_blocks_even_when_source_digest_matches(self):
        clone = self.base / "independent-clone"
        clone.mkdir()
        import subprocess
        subprocess.run(["git", "-C", str(clone), "init", "-q"], check=True)
        path = journal_path(clone, PROJECT_ID, self.journal_root)
        key = entry_key(PROJECT_ID, ISSUE_ID, DESTINATION)
        write_entry(path, key, {"state": "verified", "sourceDigest": self.source["sourceDigest"]})
        self.assertEqual(self.publish()["state"], "manual-reconciliation-required")
        self.assertEqual(self.provider.issues, [])

    def test_old_partition_without_mapping_still_blocks_create(self):
        old_project = self.base / "old-project"
        old_project.mkdir()
        import subprocess
        subprocess.run(["git", "-C", str(old_project), "init", "-q"], check=True)
        old_path = journal_path(old_project, PROJECT_ID, self.journal_root)
        old_path.parent.mkdir(parents=True, mode=0o700)
        old_path.parent.parent.chmod(0o700)
        old_path.parent.chmod(0o700)
        self.journal_root.chmod(0o700)
        result = self.publish()
        self.assertEqual(result["state"], "manual-reconciliation-required")
        self.assertEqual(result["candidates"][0]["journalState"], "absent")
        self.assertEqual(self.provider.issues, [])

    def test_legacy_journal_requires_matching_preview_format(self):
        self.provider.issues = [{"id": 1, "title": "Scope", "body": "",
                                 "closed": True, "url": "https://example.invalid/issues/1"}]
        self.source["formatVersion"] = 1
        self.preview["formatVersion"] = 1
        self.preview["body"] = render_body(self.source)
        self.provider.issues[0]["body"] = self.preview["body"]
        self.assertEqual(self.publish()["state"], "verified")
        self.preview["formatVersion"] = 2
        self.source["formatVersion"] = 2
        self.preview["body"] = render_body(self.source)
        self.assertEqual(self.publish()["state"], "preview-incompatible")
        path = journal_path(self.project, PROJECT_ID, self.journal_root)
        key = entry_key(PROJECT_ID, ISSUE_ID, DESTINATION)
        self.assertEqual(read_journal(path)["entries"][key]["state"], "verified")
        self.preview["formatVersion"] = 1
        self.source["formatVersion"] = 1
        self.preview["body"] = render_body(self.source)
        self.assertEqual(self.publish()["state"], "verified")

    def test_saved_legacy_preview_survives_only_reachability_change(self):
        self.source["state"] = "snapshot"
        self.source["formatVersion"] = 1
        self.source["codeReferences"] = [{"sha": "a" * 40,
                                          "sourceCommitReachable": True,
                                          "targetCommitReachable": None}]
        self.source["sourceDigest"] = _digest({
            key: self.source[key] for key in
            ("events", "issue", "attachments", "codeReferences")})
        self.preview["formatVersion"] = 1
        self.preview["body"] = render_body(self.source)
        self.provider.issues = [{"id": 1, "title": "Scope", "body": self.preview["body"],
                                 "closed": True, "url": "https://example.invalid/issues/1"}]
        path = journal_path(self.project, PROJECT_ID, self.journal_root)
        key = entry_key(PROJECT_ID, ISSUE_ID, DESTINATION)
        write_entry(path, key, {"state": "partial", "digestVersion": 1,
                                "sourceDigest": self.source["sourceDigest"],
                                "destination": DESTINATION, "remoteId": 1,
                                "createAttempted": True, "commentAttempts": [],
                                "verifiedEventIds": [], "stateVerified": False})
        fresh = deepcopy(self.source)
        fresh["codeReferences"][0]["sourceCommitReachable"] = False
        fresh["stateHead"] = "unrelated-head-change"
        fresh["sourceDigest"] = _digest({
            key: fresh[key] for key in
            ("events", "issue", "attachments", "codeReferences")})
        with patch("local_ticket_publish.snapshot_issue", return_value=fresh):
            result = publish_preview(self.preview, self.project, self.base / "runtime",
                                     self.provider, self.journal_root, confirm=True)
        self.assertEqual(result["state"], "verified")
        self.assertEqual(len(self.provider.issues), 1)

    def test_saved_legacy_preview_rejects_changed_issue_events(self):
        self.source["formatVersion"] = 1
        self.preview["formatVersion"] = 1
        self.preview["body"] = render_body(self.source)
        fresh = deepcopy(self.source)
        fresh["events"][1]["payload"]["md"] = "Different decision"
        with patch("local_ticket_publish.snapshot_issue", return_value=fresh):
            with self.assertRaisesRegex(InventoryError, "preview-stale"):
                publish_preview(self.preview, self.project, self.base / "runtime",
                                self.provider, self.journal_root, confirm=True)

    def test_new_legacy_handoff_without_remote_evidence_is_rejected(self):
        self.source["formatVersion"] = 1
        self.preview["formatVersion"] = 1
        self.preview["body"] = render_body(self.source)
        self.assertEqual(self.publish()["state"], "preview-incompatible")
        self.assertEqual(self.provider.issues, [])

    def test_new_format_handoff_records_version(self):
        self.preview["formatVersion"] = 2
        self.source["formatVersion"] = 2
        self.preview["body"] = render_body(self.source)
        self.assertEqual(self.publish()["state"], "verified")
        path = journal_path(self.project, PROJECT_ID, self.journal_root)
        key = entry_key(PROJECT_ID, ISSUE_ID, DESTINATION)
        self.assertEqual(read_journal(path)["entries"][key]["digestVersion"], 2)

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

    def test_definite_create_rejection_can_retry_after_correction(self):
        self.provider.reject_create = True
        self.assertEqual(self.publish()["state"], "provider-rejected")
        path = journal_path(self.project, PROJECT_ID, self.journal_root)
        key = entry_key(PROJECT_ID, ISSUE_ID, DESTINATION)
        self.assertFalse(read_journal(path)["entries"][key]["createAttempted"])
        self.provider.reject_create = False
        self.assertEqual(self.publish()["state"], "verified")
        self.assertEqual(len(self.provider.issues), 1)

    def test_content_rejection_allows_new_source_preview_before_any_remote_write(self):
        self.provider.reject_create = True
        self.assertEqual(self.publish()["state"], "provider-rejected")
        self.source["sourceDigest"] = "b" * 64
        self.source["issue"]["description"] = "Revised scope"
        self.preview["body"] = render_body(self.source)
        self.provider.reject_create = False
        self.assertEqual(self.publish()["state"], "verified")
        self.assertEqual(len(self.provider.issues), 1)
        path = journal_path(self.project, PROJECT_ID, self.journal_root)
        key = entry_key(PROJECT_ID, ISSUE_ID, DESTINATION)
        self.assertEqual(read_journal(path)["entries"][key]["sourceDigest"], "b" * 64)

    def test_rejected_legacy_create_can_restart_with_version_two(self):
        path = journal_path(self.project, PROJECT_ID, self.journal_root)
        key = entry_key(PROJECT_ID, ISSUE_ID, DESTINATION)
        write_entry(path, key, {"state": "planned", "digestVersion": 1,
                                "sourceDigest": "a" * 64, "destination": DESTINATION,
                                "createAttempted": False, "remoteId": None,
                                "verifiedEventIds": [], "rejectionStatus": 422})
        self.source["sourceDigest"] = "b" * 64
        self.preview["body"] = render_body(self.source)
        self.assertEqual(self.publish()["state"], "verified")
        self.assertEqual(len(self.provider.issues), 1)

    def test_changed_source_after_rejection_conflicts_if_remote_marker_appears(self):
        self.provider.reject_create = True
        self.assertEqual(self.publish()["state"], "provider-rejected")
        self.source["sourceDigest"] = "b" * 64
        self.source["issue"]["description"] = "Revised scope"
        self.preview["body"] = render_body(self.source)
        self.provider.reject_create = False
        self.provider.issues = [{"id": 1, "title": "Scope", "body": self.preview["body"],
                                 "closed": True, "url": "https://example.invalid/issues/1"}]
        self.assertEqual(self.publish()["state"], "conflict")
        self.assertEqual(len(self.provider.issues), 1)

    def test_lost_comment_response_and_manual_edit(self):
        self.provider.lose_comment = "after"
        self.assertEqual(self.publish()["state"], "verified")
        self.provider.lose_comment = None
        self.provider.comments[1][0]["body"] = "Changed\n\n" + self.provider.comments[1][0]["body"].splitlines()[-1]
        self.assertEqual(self.publish()["state"], "conflict")
        self.assertEqual(len(self.provider.comments[1]), 1)

    def test_definite_comment_rejection_can_retry_after_correction(self):
        self.provider.reject_comment = True
        self.assertEqual(self.publish()["state"], "provider-rejected")
        path = journal_path(self.project, PROJECT_ID, self.journal_root)
        key = entry_key(PROJECT_ID, ISSUE_ID, DESTINATION)
        self.assertEqual(read_journal(path)["entries"][key]["commentAttempts"], [])
        self.provider.reject_comment = False
        self.assertEqual(self.publish()["state"], "verified")
        self.assertEqual(len(self.provider.comments[1]), 1)

    def test_duplicate_issue_marker_is_conflict(self):
        self.provider.issues = [
            {"id": number, "title": "Scope", "body": self.preview["body"],
             "closed": False, "url": "https://example.invalid/issues/" + str(number)}
            for number in (1, 2)
        ]
        self.assertEqual(self.publish()["state"], "conflict")
        self.assertEqual(len(self.provider.issues), 2)

    def test_marker_quoted_in_unrelated_issue_stops_without_duplicate(self):
        marker = "<!-- spec-guard-local-ticket:v1 " + PROJECT_ID + "/" + ISSUE_ID + " -->"
        self.provider.issues = [{"id": 9, "title": "Unrelated", "body": "Quote:\n" + marker,
                                 "closed": False, "url": "https://example.invalid/issues/9"}]
        self.provider.next_id = 10
        self.assertEqual(self.publish()["state"], "conflict")
        self.assertEqual(len(self.provider.issues), 1)

    def test_inline_marker_without_journal_is_ambiguous(self):
        marker = "<!-- spec-guard-local-ticket:v1 " + PROJECT_ID + "/" + ISSUE_ID + " -->"
        self.provider.issues = [{"id": 9, "title": "Unrelated",
                                 "body": "Copied " + marker + " in a discussion",
                                 "closed": False, "url": "https://example.invalid/issues/9"}]
        self.provider.next_id = 10
        self.assertEqual(self.publish()["state"], "conflict")
        self.assertEqual(len(self.provider.issues), 1)

    def test_marker_quoted_inside_unrelated_comment_stops(self):
        self.assertEqual(self.publish()["state"], "verified")
        marker = "<!-- spec-guard-local-event:v1 E2 -->"
        self.provider.comments[1].append({"body": marker + "\nquoted for discussion"})
        self.assertEqual(self.publish()["state"], "conflict")
        self.assertEqual(len(self.provider.comments[1]), 2)

    def test_moved_comment_marker_with_lost_journal_does_not_duplicate(self):
        self.assertEqual(self.publish()["state"], "verified")
        journal_path(self.project, PROJECT_ID, self.journal_root).unlink()
        self.provider.comments[1][0]["body"] += "\nmanual suffix"
        self.assertEqual(self.publish()["state"], "conflict")
        self.assertEqual(len(self.provider.comments[1]), 1)

    def test_moved_issue_marker_with_lost_journal_does_not_duplicate(self):
        self.assertEqual(self.publish()["state"], "verified")
        journal_path(self.project, PROJECT_ID, self.journal_root).unlink()
        marker = "<!-- spec-guard-local-ticket:v1 " + PROJECT_ID + "/" + ISSUE_ID + " -->"
        self.provider.issues[0]["body"] = "Edited by user\n" + marker
        self.assertEqual(self.publish()["state"], "conflict")
        self.assertEqual(len(self.provider.issues), 1)

    def test_remote_edit_conflict_preserves_uncertain_comment_attempt(self):
        self.provider.lose_comment = "before"
        self.assertEqual(self.publish()["state"], "publication-uncertain")
        original_body = self.provider.issues[0]["body"]
        self.provider.issues[0]["body"] = original_body + "\nmanual edit"
        self.assertEqual(self.publish()["state"], "conflict")
        self.provider.issues[0]["body"] = original_body
        self.provider.lose_comment = None
        self.assertEqual(self.publish()["state"], "publication-uncertain")
        self.assertEqual(self.provider.comments.get(1, []), [])

    def test_duplicate_marker_conflict_preserves_uncertain_comment_attempt(self):
        self.provider.lose_comment = "before"
        self.assertEqual(self.publish()["state"], "publication-uncertain")
        self.provider.issues.append({**self.provider.issues[0], "id": 2})
        self.assertEqual(self.publish()["state"], "conflict")
        self.provider.issues.pop()
        self.provider.lose_comment = None
        self.assertEqual(self.publish()["state"], "publication-uncertain")
        self.assertEqual(self.provider.comments.get(1, []), [])

    def test_attachment_remains_partial_without_duplicate_on_retry(self):
        self.source["attachments"] = [{"hash": "a" * 64, "ext": "gif", "bytes": 10}]
        self.preview["body"] = render_body(self.source)
        self.assertEqual(self.publish()["state"], "partial")
        self.assertEqual(self.publish()["state"], "partial")
        self.assertEqual(len(self.provider.issues), 1)
        self.assertEqual(len(self.provider.comments[1]), 1)
        self.assertNotIn("proposal-stage:", self.preview["body"])

    def test_manual_remote_state_change_after_verification_is_conflict(self):
        self.assertEqual(self.publish()["state"], "verified")
        self.provider.issues[0]["closed"] = False
        self.assertEqual(self.publish()["state"], "conflict")
        self.assertFalse(self.provider.issues[0]["closed"])
        path = journal_path(self.project, PROJECT_ID, self.journal_root)
        key = entry_key(PROJECT_ID, ISSUE_ID, DESTINATION)
        self.assertEqual(read_journal(path)["entries"][key]["state"], "conflict")

    def test_manual_remote_state_change_after_partial_is_conflict(self):
        self.source["attachments"] = [{"hash": "a" * 64, "ext": "gif", "bytes": 10}]
        self.preview["body"] = render_body(self.source)
        self.assertEqual(self.publish()["state"], "partial")
        self.provider.issues[0]["closed"] = False
        self.assertEqual(self.publish()["state"], "conflict")
        self.assertFalse(self.provider.issues[0]["closed"])

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

    def test_cli_routes_explicit_legacy_preview(self):
        output = io.StringIO()
        with (patch("local_ticket_preview.create_preview",
                    return_value={"state": "previewed"}) as create,
              redirect_stdout(output)):
            self.assertEqual(main([
                "handoff-preview", "--project", str(self.project), "--issue-id", ISSUE_ID,
                "--platform", "github", "--host", "github.com", "--target", "team/repo",
                "--visibility", "private", "--output", str(self.base / "preview.json"),
                "--legacy-format",
            ]), 0)
        self.assertTrue(create.call_args.kwargs["legacy"])


if __name__ == "__main__":
    unittest.main()
