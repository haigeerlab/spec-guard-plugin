"""Isolated tests for portable Local ticket inventory."""
import hashlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import local_ticket_archive
from local_ledger_runtime import RuntimeContractError
from local_ticket_archive import archive_project, verify_archive
from local_ticket_portability import InventoryError, inventory_project, main
from local_ticket_restore import prove_restore, restore_archive
from local_ticket_handoff import _issue_events
from local_ticket_preview import create_preview, target_facts
from local_ticket_journal import entry_key, journal_path, read_journal, write_entry


PROJECT_ID = "01M37F8MKQRSB562YCBQ004QGJ"


def git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True,
    ).stdout.strip()


def event(event_id, action="create.issue", payload=None):
    return {"v": 1, "id": [event_id, None], action: payload or {"id": "ISSUE1"}}


class SourceInventoryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="sg-portability-source-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "repo"
        self.root.mkdir()
        self.global_dir = Path(temporary.name) / "global"
        self.state_root = self.global_dir / "worktrees" / PROJECT_ID
        self.state_root.parent.mkdir(parents=True)
        environment = patch.dict(os.environ, {"EPIQ_GLOBAL_DIR": str(self.global_dir)})
        environment.start()
        self.addCleanup(environment.stop)
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "test@example.invalid")
        git(self.root, "config", "user.name", "Test")
        config = self.root / ".epiq" / "project.json"
        config.parent.mkdir()
        config.write_text(json.dumps({
            "projectId": PROJECT_ID,
            "stateBranch": "__epiq_state__",
            "createdAt": "2026-10-01T00:00:00.000Z",
        }), encoding="utf-8")
        (self.root / "README.md").write_text("fixture source\n", encoding="utf-8")
        git(self.root, "add", ".epiq/project.json", "README.md")
        git(self.root, "commit", "-qm", "initialize fixture")
        git(self.root, "worktree", "add", "-q", "--orphan", "-b", "__epiq_state__",
            str(self.state_root))
        state_config = self.state_root / ".epiq" / "project.json"
        state_config.parent.mkdir()
        state_config.write_bytes(config.read_bytes())
        git(self.state_root, "add", ".epiq/project.json")
        git(self.state_root, "commit", "-qm", "state genesis")
        self.events = self.state_root / ".epiq" / "events"
        self.media = self.state_root / ".epiq" / "media"
        self.events.mkdir(parents=True)
        self.media.mkdir(parents=True)

    def write_events(self, name, *entries):
        target = self.events / name
        target.write_text("".join(json.dumps(item) + "\n" for item in entries), encoding="utf-8")
        return target

    def test_inventory_includes_tracked_live_rotated_folded_and_media_without_writes(self):
        image = b"GIF89a" + b"fixture-image"
        media_hash = hashlib.sha256(image).hexdigest()
        (self.media / (media_hash + ".gif")).write_bytes(image)
        attachment = event("EV4", "add.issue.attachment", {
            "id": "ATT1", "issue": "ISSUE1", "hash": media_hash,
            "ext": "gif", "name": "image", "bytes": len(image),
        })
        self.write_events("actor.jsonl", event("EV1"), event("EV2"))
        self.write_events("actor~pending.jsonl", event("EV3"))
        self.write_events("actor~pending-fixture-folded-1.jsonl", attachment)
        self.write_events("actor~pending-fixture-folded-2-f1.jsonl", event("EV1"))
        before = {
            item.relative_to(self.state_root).as_posix(): item.read_bytes()
            for directory in (self.events, self.media) for item in directory.iterdir()
        }
        worktrees_before = git(self.root, "worktree", "list", "--porcelain")

        result = inventory_project(self.root)

        self.assertEqual(result["state"], "ready")
        self.assertEqual(result["projectId"], PROJECT_ID)
        self.assertEqual(result["eventIds"], ["EV1", "EV2", "EV3", "EV4"])
        self.assertEqual(result["eventFileCount"], 4)
        self.assertEqual(result["mediaCount"], 1)
        self.assertEqual(len(result["files"]), 5)
        self.assertEqual(worktrees_before, git(self.root, "worktree", "list", "--porcelain"))
        self.assertEqual(before, {
            item.relative_to(self.state_root).as_posix(): item.read_bytes()
            for directory in (self.events, self.media) for item in directory.iterdir()
        })

    def test_conflicting_duplicate_event_id_is_rejected(self):
        self.write_events("actor.jsonl", event("EV1", payload={"id": "FIRST"}))
        self.write_events("actor~pending.jsonl", event("EV1", payload={"id": "SECOND"}))
        with self.assertRaisesRegex(InventoryError, "duplicate-event-conflict"):
            inventory_project(self.root)

    def test_duplicate_id_from_different_actor_is_not_collapsed(self):
        self.write_events("actor-a.jsonl", event("EV1"))
        self.write_events("actor-b.jsonl", event("EV1"))
        with self.assertRaisesRegex(InventoryError, "duplicate-event-conflict"):
            inventory_project(self.root)

    def test_foreign_worktree_is_not_read_as_own_ledger(self):
        other = self.root.parent / "other"
        other.mkdir()
        git(other, "init", "-q")
        git(other, "config", "user.email", "test@example.invalid")
        git(other, "config", "user.name", "Test")
        config = other / ".epiq" / "project.json"
        config.parent.mkdir()
        config.write_bytes((self.root / ".epiq" / "project.json").read_bytes())
        git(other, "add", ".epiq/project.json")
        git(other, "commit", "-qm", "copied identity")
        with self.assertRaisesRegex(InventoryError, "source-unknown"):
            inventory_project(other)

    def test_empty_event_directory_is_not_a_complete_initialized_ledger(self):
        with self.assertRaisesRegex(InventoryError, "invalid-event-log"):
            inventory_project(self.root)

    def test_bad_jsonl_and_missing_media_are_rejected(self):
        (self.events / "actor.jsonl").write_text("not json\n", encoding="utf-8")
        with self.assertRaisesRegex(InventoryError, "invalid-event-log"):
            inventory_project(self.root)
        self.write_events("actor.jsonl", event("EV1", "add.issue.attachment", {
            "id": "ATT1", "issue": "ISSUE1", "hash": "a" * 64,
            "ext": "gif", "name": "image", "bytes": 12,
        }))
        with self.assertRaisesRegex(InventoryError, "missing-media"):
            inventory_project(self.root)

    def test_tampered_media_is_rejected(self):
        image = b"GIF89a" + b"fixture-image"
        media_hash = hashlib.sha256(image).hexdigest()
        (self.media / (media_hash + ".gif")).write_bytes(image + b"tampered")
        self.write_events("actor.jsonl", event("EV1", "add.issue.attachment", {
            "id": "ATT1", "issue": "ISSUE1", "hash": media_hash,
            "ext": "gif", "name": "image", "bytes": len(image),
        }))
        with self.assertRaisesRegex(InventoryError, "invalid-media"):
            inventory_project(self.root)

    def test_archive_preserves_bundle_and_raw_pending_bytes(self):
        tracked = self.write_events("actor.jsonl", event("EV1"))
        pending = self.write_events("actor~pending.jsonl", event("EV2"))
        archive = self.root.parent / "archive"

        created = archive_project(self.root, archive)
        verified = verify_archive(archive)

        self.assertEqual(created["state"], "archived")
        self.assertEqual(verified["state"], "verified")
        self.assertEqual((archive / ".epiq/events" / tracked.name).read_bytes(), tracked.read_bytes())
        self.assertEqual((archive / ".epiq/events" / pending.name).read_bytes(), pending.read_bytes())
        self.assertTrue((archive / "state.bundle").is_file())
        self.assertEqual(git(self.root, "status", "--porcelain", "--untracked-files=all"), "")

    def test_archive_verification_rejects_tampered_event_and_missing_bundle(self):
        self.write_events("actor.jsonl", event("EV1"))
        archive = self.root.parent / "archive"
        archive_project(self.root, archive)
        event_copy = archive / ".epiq/events/actor.jsonl"
        event_copy.write_bytes(event_copy.read_bytes() + b"tampered")
        with self.assertRaisesRegex(InventoryError, "archive-invalid"):
            verify_archive(archive)
        event_copy.write_bytes(self.events.joinpath("actor.jsonl").read_bytes())
        (archive / "state.bundle").unlink()
        with self.assertRaisesRegex(InventoryError, "archive-invalid"):
            verify_archive(archive)

    def test_archive_refuses_output_inside_source_or_an_existing_directory(self):
        self.write_events("actor.jsonl", event("EV1"))
        inside = self.root / "backup"
        with self.assertRaisesRegex(InventoryError, "archive-output-unsafe"):
            archive_project(self.root, inside)
        self.assertFalse(inside.exists())
        existing = self.root.parent / "existing"
        existing.mkdir()
        with self.assertRaisesRegex(InventoryError, "archive-output-exists"):
            archive_project(self.root, existing)

    def test_archive_refuses_output_in_sibling_worktree(self):
        self.write_events("actor.jsonl", event("EV1"))
        sibling = self.root.parent / "sibling"
        git(self.root, "worktree", "add", "-q", "-b", "sibling", str(sibling), "HEAD")
        output = sibling / "private-archive"
        with self.assertRaisesRegex(InventoryError, "archive-output-unsafe"):
            archive_project(self.root, output)
        self.assertFalse(output.exists())

    def test_archive_refuses_filesystem_without_private_directory_permissions(self):
        self.write_events("actor.jsonl", event("EV1"))
        archive = self.root.parent / "archive"
        original = local_ticket_archive._require_private_directory

        def reject_output(path):
            if path == archive:
                raise InventoryError("archive-output-unsafe: destination is not private")
            original(path)

        with patch("local_ticket_archive._require_private_directory", side_effect=reject_output):
            with self.assertRaisesRegex(InventoryError, "archive-output-unsafe"):
                archive_project(self.root, archive)
        self.assertFalse(archive.exists())
        world_readable = self.root.parent / "world-readable"
        world_readable.mkdir(mode=0o755)
        world_readable.chmod(0o755)
        with self.assertRaisesRegex(InventoryError, "archive-output-unsafe"):
            original(world_readable)

    def test_archive_rejects_state_branch_with_source_history(self):
        git(self.root, "worktree", "remove", str(self.state_root))
        git(self.root, "branch", "-D", "__epiq_state__")
        git(self.root, "worktree", "add", "-q", "-b", "__epiq_state__",
            str(self.state_root), "HEAD")
        self.events.mkdir(parents=True)
        self.media.mkdir(parents=True)
        self.write_events("actor.jsonl", event("EV1"))
        with self.assertRaisesRegex(InventoryError, "archive-source-history"):
            archive_project(self.root, self.root.parent / "unsafe-archive")

    def test_archive_verification_rejects_unlisted_symlink(self):
        self.write_events("actor.jsonl", event("EV1"))
        archive = self.root.parent / "archive"
        archive_project(self.root, archive)
        (archive / "unexpected").symlink_to(self.root)
        with self.assertRaisesRegex(InventoryError, "archive-invalid"):
            verify_archive(archive)

    def test_archive_verification_rejects_bundle_tree_symlink(self):
        self.write_events("actor.jsonl", event("EV1"))
        archive = self.root.parent / "archive"
        archive_project(self.root, archive)
        crafted = self.root.parent / "crafted-bundle"
        crafted.mkdir()
        git(crafted, "init", "-q")
        git(crafted, "config", "user.email", "test@example.invalid")
        git(crafted, "config", "user.name", "Test")
        git(crafted, "checkout", "-q", "--orphan", "__epiq_state__")
        (crafted / ".epiq").mkdir()
        (crafted / ".epiq" / "events").symlink_to(self.root.parent / "outside")
        git(crafted, "add", ".epiq")
        git(crafted, "commit", "-qm", "unsafe tree")
        bundle = archive / "state.bundle"
        bundle.unlink()
        git(crafted, "bundle", "create", str(bundle), "refs/heads/__epiq_state__")
        manifest_path = archive / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["stateHead"] = git(crafted, "rev-parse", "HEAD")
        bundle_record = next(item for item in manifest["files"]
                             if item["path"] == "state.bundle")
        bundle_record["size"] = bundle.stat().st_size
        bundle_record["sha256"] = hashlib.sha256(bundle.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(InventoryError, "archive-invalid"):
            verify_archive(archive)

    def test_archive_and_verify_cli_return_json_outcomes(self):
        self.write_events("actor.jsonl", event("EV1"))
        archive = self.root.parent / "archive"
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["archive", "--project", str(self.root),
                                   "--output", str(archive)]), 0)
        self.assertEqual(json.loads(output.getvalue())["state"], "archived")
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["verify", "--archive", str(archive)]), 0)
        self.assertEqual(json.loads(output.getvalue())["state"], "verified")

    def test_archive_verification_rejects_mismatched_project_identity(self):
        self.write_events("actor.jsonl", event("EV1"))
        archive = self.root.parent / "archive"
        archive_project(self.root, archive)
        manifest = archive / "manifest.json"
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        payload["projectId"] = "DIFFERENT"
        manifest.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(InventoryError, "archive-invalid"):
            verify_archive(archive)

    def test_archive_verification_rejects_mismatched_event_ids(self):
        self.write_events("actor.jsonl", event("EV1"))
        archive = self.root.parent / "archive"
        archive_project(self.root, archive)
        manifest_path = archive / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["eventIds"] = ["MISSING"]
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(InventoryError, "archive-invalid"):
            verify_archive(archive)

    def test_archive_verification_rejects_traversal_manifest(self):
        self.write_events("actor.jsonl", event("EV1"))
        archive = self.root.parent / "archive"
        archive_project(self.root, archive)
        manifest = archive / "manifest.json"
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        payload["files"][0]["path"] = "../outside"
        manifest.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(InventoryError, "archive-invalid"):
            verify_archive(archive)

    def test_archive_rejects_source_change_after_initial_inventory(self):
        source = self.write_events("actor.jsonl", event("EV1"))
        archive = self.root.parent / "archive"
        original = local_ticket_archive.inventory_project
        calls = 0

        def inventory_then_change(project):
            nonlocal calls
            result = original(project)
            calls += 1
            if calls == 1:
                with source.open("ab") as handle:
                    handle.write((json.dumps(event("EV2")) + "\n").encode("utf-8"))
            return result

        with patch("local_ticket_archive.inventory_project", side_effect=inventory_then_change):
            with self.assertRaisesRegex(InventoryError, "source-changed"):
                archive_project(self.root, archive)
        self.assertFalse(archive.exists())

    def test_restore_proof_reports_epiq_readback_failure(self):
        self.write_events("actor.jsonl", event("EV1"))
        archive = self.root.parent / "archive"
        archive_project(self.root, archive)
        with (patch("local_ticket_restore.runtime_status", return_value={"state": "ready"}),
              patch("local_ticket_restore.node_status", return_value={
                  "state": "ready", "path": "/usr/bin/node",
              }),
              patch("local_ticket_restore.mcp_tool_call",
                    side_effect=RuntimeContractError("unreadable fixture"))):
            with self.assertRaisesRegex(InventoryError, "restore-proof-failed"):
                prove_restore(archive, self.root.parent / "fake-runtime")

    def test_restore_requires_confirmation_and_empty_target(self):
        self.write_events("actor.jsonl", event("EV1"))
        archive = self.root.parent / "archive"
        archive_project(self.root, archive)
        target = self.root.parent / "target"
        target.mkdir()
        git(target, "init", "-q")
        global_dir = self.root.parent / "target-global"
        global_dir.mkdir()
        with self.assertRaisesRegex(InventoryError, "confirmation-required"):
            restore_archive(archive, target, global_dir, self.root.parent / "runtime",
                            confirm=False)
        (target / "README.md").write_text("existing work\n", encoding="utf-8")
        with self.assertRaisesRegex(InventoryError, "target-not-empty"):
            restore_archive(archive, target, global_dir, self.root.parent / "runtime",
                            confirm=True)
        self.assertFalse((target / ".epiq").exists())

    def test_restore_refuses_existing_global_state(self):
        self.write_events("actor.jsonl", event("EV1"))
        archive = self.root.parent / "archive"
        archive_project(self.root, archive)
        target = self.root.parent / "target"
        target.mkdir()
        git(target, "init", "-q")
        global_dir = self.root.parent / "target-global"
        global_dir.mkdir()
        (global_dir / "config.json").write_text("existing", encoding="utf-8")
        with self.assertRaisesRegex(InventoryError, "target-not-empty"):
            restore_archive(archive, target, global_dir, self.root.parent / "runtime",
                            confirm=True)
        self.assertFalse((target / ".epiq").exists())

    def test_restore_refuses_existing_branch_even_without_project_files(self):
        self.write_events("actor.jsonl", event("EV1"))
        archive = self.root.parent / "archive"
        archive_project(self.root, archive)
        target = self.root.parent / "target"
        target.mkdir()
        git(target, "init", "-q")
        git(target, "fetch", "-q", str(archive / "state.bundle"),
            "refs/heads/__epiq_state__:refs/heads/__epiq_state__")
        global_dir = self.root.parent / "target-global"
        global_dir.mkdir()
        with self.assertRaisesRegex(InventoryError, "target-not-empty"):
            restore_archive(archive, target, global_dir, self.root.parent / "runtime",
                            confirm=True)
        self.assertFalse((target / ".epiq").exists())

    def test_restore_preserves_partial_target_for_diagnosis(self):
        self.write_events("actor.jsonl", event("EV1"))
        archive = self.root.parent / "archive"
        archive_project(self.root, archive)
        target = self.root.parent / "target"
        target.mkdir()
        git(target, "init", "-q")
        git(target, "config", "user.email", "test@example.invalid")
        git(target, "config", "user.name", "Test")
        global_dir = self.root.parent / "target-global"
        global_dir.mkdir()
        proof = {"state": "proved", "eventDigest": "fixture"}

        def interrupted(*arguments):
            (target / ".epiq").mkdir()
            (target / ".epiq" / "partial").write_text("preserve", encoding="utf-8")
            raise OSError("injected failure")

        with (patch("local_ticket_restore.prove_restore", return_value=proof),
              patch("local_ticket_restore._populate_archive", side_effect=interrupted)):
            with self.assertRaisesRegex(InventoryError, "restore-incomplete"):
                restore_archive(archive, target, global_dir, self.root.parent / "runtime",
                                confirm=True)
        self.assertEqual((target / ".epiq" / "partial").read_text(), "preserve")
        self.assertFalse((target / ".git" / "spec-guard-local-restore.lock").exists())

    def test_handoff_includes_changes_to_related_comment(self):
        events = [
            {"id": "E1", "action": "add.issue", "payload": {"id": "I1"}},
            {"id": "E2", "action": "add.issue.comment",
             "payload": {"id": "C1", "issue": "I1", "md": "Original"}},
            {"id": "E3", "action": "edit.comment",
             "payload": {"id": "C1", "md": "Revised"}},
            {"id": "E4", "action": "edit.description",
             "payload": {"id": "I1", "md": "Current"}},
            {"id": "E5", "action": "add.issue", "payload": {"id": "I2"}},
        ]
        self.assertEqual([item["id"] for item in _issue_events(events, "I1")],
                         ["E1", "E2", "E3", "E4"])

    def test_preview_is_private_and_contains_full_history_markers(self):
        snapshot = {
            "projectId": PROJECT_ID, "issueId": "I1", "sourceDigest": "a" * 64,
            "issue": {"title": "Scope", "description": "New scope"},
            "attachments": [],
            "codeReferences": [],
            "events": [
                {"id": "01M3SX6JX0VMYEMES73BMEHQED", "action": "edit.description",
                 "payload": {"id": "I1", "md": "Old scope"}, "userId": "A1",
                 "actorName": "Ada"},
                {"id": "01M3SX6KH9C5E0W8KVH9PG1KW2", "action": "edit.description",
                 "payload": {"id": "I1", "md": "New scope"}, "userId": "A1",
                 "actorName": "Ada"},
            ],
        }
        output = self.root.parent / "preview.json"
        metadata = {"full_name": "team/repo", "private": True, "has_issues": True,
                    "permissions": {"push": True}, "id": 42}
        runner = lambda arguments: json.dumps(metadata)
        with patch("local_ticket_preview.snapshot_issue", return_value=snapshot):
            result = create_preview(self.root, "I1", self.root.parent / "runtime",
                                    "github", "github.com", "team/repo", "private",
                                    output, runner=runner)
        preview = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(result["state"], "previewed")
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        self.assertIn("Old scope", preview["body"])
        self.assertIn("New scope", preview["body"])
        self.assertEqual(preview["body"].count("spec-guard-local-event:v1"), 2)
        self.assertIn("spec-guard-local-ticket:v1", preview["body"])
        self.assertNotIn(str(self.root), output.read_text(encoding="utf-8"))

    def test_preview_refuses_output_in_sibling_worktree(self):
        sibling = self.root.parent / "sibling"
        git(self.root, "worktree", "add", "-q", "-b", "sibling", str(sibling), "HEAD")
        metadata = {"full_name": "team/repo", "private": True, "has_issues": True,
                    "permissions": {"push": True}, "id": 42}
        with patch("local_ticket_preview.snapshot_issue",
                   return_value={"projectId": PROJECT_ID}):
            with self.assertRaisesRegex(InventoryError, "preview-output-unsafe"):
                create_preview(self.root, "I1", self.root.parent / "runtime",
                               "github", "github.com", "team/repo", "private",
                               sibling / "private-preview.json",
                               runner=lambda arguments: json.dumps(metadata))

    def test_gitlab_http_attachment_preview_names_both_limits(self):
        snapshot = {
            "projectId": PROJECT_ID, "issueId": "I1", "sourceDigest": "a" * 64,
            "issue": {"title": "Synthetic", "description": "Test"},
            "attachments": [{"hash": "b" * 64, "ext": "png", "bytes": 1}],
            "codeReferences": [], "events": [],
        }
        metadata = {"path_with_namespace": "group/project", "id": 19,
                    "web_url": "http://gitlab.example.test/group/project",
                    "visibility": "private", "issues_enabled": True,
                    "permissions": {"project_access": {"access_level": 30}}}
        output = self.root.parent / "http-preview.json"
        with patch("local_ticket_preview.snapshot_issue", return_value=snapshot):
            create_preview(self.root, "I1", self.root.parent / "runtime",
                           "gitlab", "gitlab.example.test", "group/project",
                           "private", output,
                           runner=lambda arguments: json.dumps(metadata))
        limitations = json.loads(output.read_text(encoding="utf-8"))["limitations"]
        self.assertTrue(any("HTTP" in item for item in limitations))
        self.assertTrue(any("attachment bytes" in item for item in limitations))

    def test_preview_rejects_unknown_permission_and_visibility_mismatch(self):
        limited = {"full_name": "team/repo", "private": False, "has_issues": True,
                   "permissions": {"pull": True}, "id": 42}
        with self.assertRaisesRegex(InventoryError, "provider-unavailable"):
            target_facts("github", "github.com", "team/repo",
                         runner=lambda arguments: json.dumps(limited))
        limited["permissions"] = {"push": True}
        with self.assertRaisesRegex(InventoryError, "visibility"):
            create_preview(self.root, "I1", self.root.parent / "runtime",
                           "github", "github.com", "team/repo", "private",
                           self.root.parent / "preview.json",
                           runner=lambda arguments: json.dumps(limited))

    def test_gitlab_preview_requires_issue_permission(self):
        metadata = {"path_with_namespace": "group/project", "visibility": "internal",
                    "web_url": "https://gitlab.example.test/group/project",
                    "issues_enabled": True, "permissions": {
                        "project_access": {"access_level": 20},
                        "group_access": None,
                    }, "id": 19}
        with self.assertRaisesRegex(InventoryError, "provider-unavailable"):
            target_facts("gitlab", "gitlab.example.test", "group/project",
                         runner=lambda arguments: json.dumps(metadata))
        metadata["permissions"]["project_access"]["access_level"] = 30
        facts = target_facts("gitlab", "gitlab.example.test", "group/project",
                             runner=lambda arguments: json.dumps(metadata))
        self.assertEqual(facts["visibility"], "internal")
        self.assertEqual(facts["targetId"], 19)

    def test_private_mapping_journal_is_versioned_and_clone_scoped(self):
        base = self.root.parent / "private-journals"
        destination = {"platform": "github", "host": "github.com", "targetId": 42}
        path = journal_path(self.root, PROJECT_ID, base)
        key = entry_key(PROJECT_ID, "I1", destination)
        write_entry(path, key, {"state": "planned", "sourceDigest": "a" * 64,
                                "destination": destination})
        self.assertEqual(read_journal(path)["entries"][key]["state"], "planned")
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
        clone = self.root.parent / "clone"
        clone.mkdir()
        git(clone, "init", "-q")
        self.assertNotEqual(journal_path(clone, PROJECT_ID, base), path)

    def test_journal_rejects_symlink_and_broad_root(self):
        destination = {"platform": "github", "host": "github.com", "targetId": 42}
        key = entry_key(PROJECT_ID, "I1", destination)
        entry = {"state": "partial"}
        broad = self.root.parent / "broad"
        broad.mkdir(mode=0o755)
        broad.chmod(0o755)
        with self.assertRaisesRegex(InventoryError, "journal-unsafe"):
            write_entry(journal_path(self.root, PROJECT_ID, broad), key, entry)
        self.assertEqual(broad.stat().st_mode & 0o777, 0o755)
        pointer = self.root.parent / "pointer"
        pointer.symlink_to(broad, target_is_directory=True)
        with self.assertRaisesRegex(InventoryError, "journal-unsafe"):
            write_entry(journal_path(self.root, PROJECT_ID, pointer), key, entry)

    def test_next_archive_exports_private_mapping_snapshot(self):
        self.write_events("actor.jsonl", event("EV1"))
        journal_root = self.root.parent / "private-journals"
        destination = {"platform": "github", "host": "github.com", "targetId": 42}
        key = entry_key(PROJECT_ID, "I1", destination)
        with patch("local_ticket_journal.default_journal_root", return_value=journal_root):
            path = journal_path(self.root, PROJECT_ID)
            write_entry(path, key, {"state": "partial", "sourceDigest": "a" * 64})
            archive = self.root.parent / "archive"
            archive_project(self.root, archive)
            self.assertEqual(verify_archive(archive)["state"], "verified")
        exported = archive / ".spec-guard" / "mapping.json"
        self.assertEqual(read_journal(exported)["entries"][key]["state"], "partial")
        exported.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(InventoryError, "archive-invalid"):
            verify_archive(archive)


if __name__ == "__main__":
    unittest.main()
