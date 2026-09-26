"""Rollback must not strand native mail or delete its retained history."""
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from collaboration_backend import selected_backend
from native_collaboration_rollback import RollbackError, rollback_native_backend
from native_collaboration_runtime import BRIDGE_COMMIT


class NativeRollbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sg-rollback-switch-")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.config = self.base / ".spec-guard/collaboration"
        self.config.parent.mkdir(mode=0o700)
        self.config.mkdir(mode=0o700)
        self.marker = self.config / "transport.json"
        self.marker.write_text(json.dumps({"backend": "native", "commit": BRIDGE_COMMIT}))
        self.marker.chmod(0o600)
        self.legacy = self.config / "messages.sqlite"
        with sqlite3.connect(self.legacy) as connection:
            connection.executescript("""
                CREATE TABLE agents (
                    agent_id TEXT PRIMARY KEY, team TEXT, role TEXT,
                    last_processed_event_id INTEGER
                );
                CREATE TABLE messages (
                    id TEXT PRIMARY KEY, event_id INTEGER, to_team TEXT,
                    to_agent_id TEXT, to_role TEXT, body TEXT
                );
            """)
        self.mailbox = self.base / ".spec-guard/native-collaboration/mailbox"
        self.mailbox.parent.mkdir(mode=0o700)
        self.mailbox.mkdir(mode=0o700)
        self.database = self.mailbox / "bridge.sqlite"
        with sqlite3.connect(self.database) as connection:
            connection.executescript("""
                PRAGMA user_version=2;
                CREATE TABLE agents (name TEXT PRIMARY KEY, registered_at TEXT, retired_at TEXT);
                CREATE TABLE messages (
                    id INTEGER PRIMARY KEY, from_agent TEXT, to_agent TEXT,
                    created_at TEXT, body TEXT
                );
                CREATE TABLE acknowledgements (
                    message_id INTEGER, agent TEXT, acked_at TEXT,
                    PRIMARY KEY (message_id, agent)
                );
                INSERT INTO messages VALUES (1, 'claude', 'codex', '2026-01-03', 'retained text');
                INSERT INTO acknowledgements VALUES (1, 'codex', '2026-01-04');
            """)
        self.database.chmod(0o600)

    def test_empty_delivery_queue_removes_only_marker_and_retains_history(self):
        original = self.database.read_bytes()
        result = rollback_native_backend(self.marker, self.database)
        self.assertEqual(result["state"], "rolled-back")
        self.assertFalse(self.marker.exists())
        self.assertEqual(self.database.read_bytes(), original)
        self.assertEqual(selected_backend(self.marker, self.base / "native"), {"backend": "xats"})
        self.assertNotIn("retained text", str(result))

    def test_live_identity_or_unacknowledged_mail_blocks_rollback(self):
        with sqlite3.connect(self.database) as connection:
            connection.execute("INSERT INTO agents VALUES ('codex', '2026-01-01', NULL)")
        with self.assertRaises(RollbackError):
            rollback_native_backend(self.marker, self.database)
        self.assertTrue(self.marker.exists())
        with sqlite3.connect(self.database) as connection:
            connection.execute("DELETE FROM agents")
            connection.execute("INSERT INTO messages VALUES (2, 'claude', 'codex', '2026-01-03', 'unread')")
        with self.assertRaises(RollbackError):
            rollback_native_backend(self.marker, self.database)
        self.assertTrue(self.marker.exists())

    def test_invalid_marker_or_unsafe_mailbox_never_changes_marker(self):
        self.marker.chmod(0o644)
        with self.assertRaises(RollbackError):
            rollback_native_backend(self.marker, self.database)
        self.marker.chmod(0o600)
        self.database.chmod(0o644)
        with self.assertRaises(RollbackError):
            rollback_native_backend(self.marker, self.database)
        self.database.chmod(0o600)
        self.marker.write_text("wrong marker")
        with self.assertRaises(RollbackError):
            rollback_native_backend(self.marker, self.database)
        self.assertEqual(self.marker.read_text(), "wrong marker")

    def test_missing_legacy_mailbox_blocks_rollback(self):
        self.legacy.unlink()
        with self.assertRaises(RollbackError):
            rollback_native_backend(self.marker, self.database)
        self.assertTrue(self.marker.exists())

    def test_symlink_marker_blocks_rollback(self):
        actual = self.config / "real-marker.json"
        self.marker.rename(actual)
        self.marker.symlink_to(actual)
        with self.assertRaises(RollbackError):
            rollback_native_backend(self.marker, self.database)
        self.assertTrue(self.marker.is_symlink())
        self.assertTrue(actual.exists())

    def test_shared_parent_may_be_traversable_when_mailboxes_are_private(self):
        self.config.parent.chmod(0o755)
        self.assertEqual(rollback_native_backend(self.marker, self.database)["state"], "rolled-back")
        self.assertFalse(self.marker.exists())

    def test_non_private_mailbox_directory_blocks_rollback(self):
        self.mailbox.parent.chmod(0o755)
        with self.assertRaises(RollbackError):
            rollback_native_backend(self.marker, self.database)
        self.assertTrue(self.marker.exists())

    def test_cli_requires_both_operator_confirmations(self):
        command = [sys.executable, str(Path(__file__).with_name("native_collaboration_rollback.py"))]
        environment = {"HOME": str(self.base), "PATH": "/usr/bin:/bin"}
        refused = subprocess.run(command, env=environment, capture_output=True, text=True)
        self.assertNotEqual(refused.returncode, 0)
        self.assertTrue(self.marker.exists())
        confirmed = subprocess.run(command + ["--confirm-native-sessions-stopped",
                                          "--confirm-xats-running"], env=environment,
                                   capture_output=True, text=True)
        self.assertEqual(confirmed.returncode, 0, confirmed.stderr)
        self.assertEqual(json.loads(confirmed.stdout)["state"], "rolled-back")


if __name__ == "__main__":
    unittest.main()
