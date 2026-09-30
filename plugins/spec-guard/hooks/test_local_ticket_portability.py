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
from local_ticket_restore import prove_restore


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


if __name__ == "__main__":
    unittest.main()
