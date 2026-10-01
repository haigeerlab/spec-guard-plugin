"""Optional real-Epiq archive/restore proof in disposable repositories."""
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

from local_ledger_runtime import (
    MCP_RELATIVE_PATH, initialize_project, mcp_tool_call, node_status, runtime_status,
)
from local_ticket_archive import archive_project
from local_ticket_portability import inventory_project, main
from local_ticket_handoff import snapshot_issue


def git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True,
                   capture_output=True, text=True)


class RealEpiqRestoreProof(unittest.TestCase):
    def test_archive_restores_full_event_history_and_accepts_new_issue(self):
        runtime = Path(os.environ["SPEC_GUARD_EPIQ_RUNTIME"])
        self.assertEqual(runtime_status(runtime)["state"], "ready")
        node = node_status()
        self.assertEqual(node["state"], "ready")
        command = [node["path"], str(runtime / MCP_RELATIVE_PATH)]

        with tempfile.TemporaryDirectory(prefix="sg-restore-acceptance-") as temporary:
            base = Path(temporary)
            source = base / "source"
            source.mkdir()
            git(source, "init", "-q")
            git(source, "config", "user.name", "Restore Fixture")
            git(source, "config", "user.email", "restore@example.invalid")
            (source / "README.md").write_text("fixture\n", encoding="utf-8")
            git(source, "add", "README.md")
            git(source, "commit", "-qm", "initial")
            source_global = base / "source-global"
            with patch.dict(os.environ, {"EPIQ_GLOBAL_DIR": str(source_global)}):
                initialize_project(runtime, source, "Restore Fixture", "true", False)
                lanes = mcp_tool_call(command, "epiq_swimlane_list", {
                    "repoRoot": str(source),
                })["value"]
                lane = next((item for item in lanes if not item["isClosed"]), None)
                if lane is None:
                    boards = mcp_tool_call(command, "epiq_board_list", {
                        "repoRoot": str(source),
                    })["value"]
                    lane = mcp_tool_call(command, "epiq_swimlane_create", {
                        "repoRoot": str(source), "boardId": boards[0]["id"],
                        "title": "Work",
                    })["value"]
                issue = mcp_tool_call(command, "epiq_issue_create", {
                    "repoRoot": str(source), "parentId": lane["id"],
                    "title": "Restore proof", "description": "Original scope",
                })["value"]
                mcp_tool_call(command, "epiq_issue_comment_add", {
                    "repoRoot": str(source), "issueId": issue["id"],
                    "body": "Scope revised with an explicit decision",
                })
                mcp_tool_call(command, "epiq_issue_description_edit", {
                    "repoRoot": str(source), "issueId": issue["id"],
                    "description": "Revised scope",
                })
                image = base / "image.gif"
                image.write_bytes(b"GIF89a" + b"restore-fixture")
                mcp_tool_call(command, "epiq_issue_attachment_add", {
                    "repoRoot": str(source), "issueId": issue["id"],
                    "filePath": str(image),
                })
                mcp_tool_call(command, "epiq_issue_close", {
                    "repoRoot": str(source), "issueId": issue["id"],
                })
                mcp_tool_call(command, "epiq_issue_reopen", {
                    "repoRoot": str(source), "issueId": issue["id"],
                })
                mcp_tool_call(command, "epiq_issue_close", {
                    "repoRoot": str(source), "issueId": issue["id"],
                })
                source_events = mcp_tool_call(command, "epiq_state_get", {
                    "repoRoot": str(source),
                })["value"]["eventLog"]
                source_issue = mcp_tool_call(command, "epiq_issue_get", {
                    "repoRoot": str(source), "idOrRef": issue["id"],
                })["value"]
                before = inventory_project(source)
                snapshot = snapshot_issue(source, issue["id"], runtime)
                self.assertEqual(snapshot["state"], "snapshot")
                self.assertEqual(snapshot["issueId"], issue["id"])
                self.assertEqual(snapshot["issue"]["description"], "Revised scope")
                self.assertEqual(snapshot["events"][-1]["action"], "close.issue")
                self.assertIn("reopen.issue",
                              [item["action"] for item in snapshot["events"]])
                self.assertEqual(sum(item["action"] == "edit.description"
                                     for item in snapshot["events"]), 2)
                self.assertEqual(len(snapshot["attachments"]), 1)
                self.assertEqual(inventory_project(source), before)
                archive = base / "archive"
                archive_project(source, archive)

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["verify", "--archive", str(archive),
                                       "--prove", "--runtime-dir", str(runtime)]), 0)
            result = json.loads(output.getvalue())
            self.assertEqual(result["state"], "proved")
            self.assertEqual(result["eventCount"], len(before["eventIds"]))
            self.assertEqual(result["mediaCount"], 1)
            self.assertEqual(result["mediaHashes"], [hashlib.sha256(image.read_bytes()).hexdigest()])
            self.assertEqual(result["issueCount"], 1)
            self.assertEqual(result["eventDigest"], hashlib.sha256(json.dumps(
                source_events, sort_keys=True, ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")).hexdigest())
            self.assertEqual(result["issueDigest"], hashlib.sha256(json.dumps(
                [source_issue], sort_keys=True, ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")).hexdigest())
            self.assertTrue(result["writable"])
            self.assertEqual(json.loads((archive / "manifest.json").read_text())["eventIds"],
                             before["eventIds"])

            target = base / "restored-project"
            target.mkdir()
            git(target, "init", "-q")
            git(target, "config", "user.name", "Restore Fixture")
            git(target, "config", "user.email", "restore@example.invalid")
            target_global = base / "restored-global"
            target_global.mkdir()
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main([
                    "restore", "--archive", str(archive), "--project", str(target),
                    "--epiq-global-dir", str(target_global),
                    "--runtime-dir", str(runtime), "--confirm",
                ]), 0)
            restored = json.loads(output.getvalue())
            self.assertEqual(restored["state"], "restored")
            self.assertEqual(restored["eventCount"], result["eventCount"])
            self.assertEqual((target / ".epiq/project.json").read_bytes(),
                             (archive / ".epiq/project.json").read_bytes())
            git(target, "ls-files", "--error-unmatch", ".epiq/project.json")
            target_environment = dict(os.environ, EPIQ_GLOBAL_DIR=str(target_global))
            (target_global / "config.json").write_text(json.dumps({
                "logLevel": "error", "userId": "01M3SRSVX16EAHRM78KQ1K7J02",
                "userName": "Restore Fixture", "autoSync": False,
            }), encoding="utf-8")
            mcp_tool_call(command, "epiq_issue_comment_add", {
                "repoRoot": str(target), "issueId": issue["id"],
                "body": "Continued after restore",
            }, environment=target_environment)
            resumed = mcp_tool_call(command, "epiq_issue_get", {
                "repoRoot": str(target), "idOrRef": issue["id"],
            }, environment=target_environment)["value"]
            self.assertIn("Continued after restore",
                          [comment["body"] for comment in resumed["comments"]])


if __name__ == "__main__":
    if not os.environ.get("SPEC_GUARD_EPIQ_RUNTIME"):
        print("SKIP: set SPEC_GUARD_EPIQ_RUNTIME to a verified Epiq runtime")
        raise SystemExit(2)
    unittest.main()
