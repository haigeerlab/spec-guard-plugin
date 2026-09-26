"""A reviewed archive is required before selecting the native mailbox."""
import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from native_collaboration_activate import ActivationError, activate_native_backend
from native_collaboration_runtime import BRIDGE_COMMIT
from collaboration_backend import selected_backend


class NativeActivationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sg-activate-")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.database = self.base / "messages.sqlite"
        with sqlite3.connect(self.database) as connection:
            connection.executescript("""
                CREATE TABLE agents (
                    agent_id TEXT PRIMARY KEY, team TEXT, role TEXT,
                    last_processed_event_id INTEGER
                );
                CREATE TABLE messages (
                    id TEXT PRIMARY KEY, event_id INTEGER, to_team TEXT,
                    to_agent_id TEXT, to_role TEXT, body TEXT
                );
                INSERT INTO agents VALUES ('a', 'spec-guard-local', 'developer', 0);
                INSERT INTO messages VALUES ('one', 1, 'spec-guard-local', 'a', NULL, 'private mail');
            """)
        self.archive_dir = self.base / "archive"
        self.archive_dir.mkdir(mode=0o700)
        self.archive = self.archive_dir / "messages.sqlite"
        with sqlite3.connect(self.database) as source, sqlite3.connect(self.archive) as target:
            source.backup(target)
        self.archive.chmod(0o400)
        self.sha256 = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        self.config = self.base / "config"
        self.config.mkdir(mode=0o700)
        self.marker = self.config / "transport.json"
        self.native = self.base / "native"
        self.native.mkdir(mode=0o700)
        (self.native / "manifest.json").write_text(json.dumps({"commit": BRIDGE_COMMIT}))
        for child in ("dist", "mailbox", "mailbox/backups", "data"):
            (self.native / child).mkdir(mode=0o700)
        (self.native / "dist/server.js").write_text("// fixture")

    def activate(self):
        return activate_native_backend(
            self.database, self.archive, self.sha256, (1, 1), self.marker, self.native)

    def test_verified_archive_atomically_selects_native_without_changing_mail(self):
        original = self.database.read_bytes()
        result = self.activate()
        self.assertEqual(result["state"], "activated")
        self.assertEqual(result["archiveSha256"], self.sha256)
        self.assertEqual(selected_backend(self.marker, self.native), {"backend": "native"})
        self.assertEqual(self.marker.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.database.read_bytes(), original)
        self.assertEqual([p.name for p in self.config.iterdir()], ["transport.json"])
        self.assertNotIn("private mail", str(result))

    def test_stale_or_unverified_archive_never_writes_marker(self):
        for digest, counts in (("0" * 64, (1, 1)), (self.sha256, (1, 0))):
            with self.assertRaises(ActivationError):
                activate_native_backend(
                    self.database, self.archive, digest, counts, self.marker, self.native)
            self.assertFalse(self.marker.exists())
        with sqlite3.connect(self.database) as connection:
            connection.execute("UPDATE messages SET body='changed after archive' WHERE id='one'")
        with self.assertRaises(ActivationError):
            self.activate()
        self.assertFalse(self.marker.exists())
        with sqlite3.connect(self.database) as connection:
            connection.execute("INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?)",
                               ("two", 2, "spec-guard-local", "a", None, "new mail"))
        with self.assertRaises(ActivationError):
            self.activate()
        self.assertFalse(self.marker.exists())

    def test_unsafe_archive_or_existing_marker_is_not_overwritten(self):
        self.archive.chmod(0o644)
        with self.assertRaises(ActivationError):
            self.activate()
        self.archive.chmod(0o400)
        self.marker.symlink_to(self.archive)
        with self.assertRaises(ActivationError):
            self.activate()
        self.marker.unlink()
        self.marker.write_text("keep")
        with self.assertRaises(ActivationError):
            self.activate()
        self.assertEqual(self.marker.read_text(), "keep")

    def test_unready_runtime_and_staging_error_do_not_create_marker(self):
        (self.native / "manifest.json").unlink()
        with self.assertRaises(ActivationError):
            self.activate()
        self.assertFalse(self.marker.exists())
        (self.native / "manifest.json").write_text(json.dumps({"commit": BRIDGE_COMMIT}))
        with patch("native_collaboration_activate.tempfile.mkstemp", side_effect=OSError):
            with self.assertRaises(ActivationError):
                self.activate()
        self.assertFalse(self.marker.exists())

    def test_cli_requires_explicit_stopped_service_and_session_review(self):
        command = [sys.executable, str(Path(__file__).with_name("native_collaboration_activate.py")),
                   "--database", str(self.database), "--archive", str(self.archive),
                   "--archive-sha256", self.sha256, "--expected-registered", "1",
                   "--expected-unread", "1", "--marker", str(self.marker),
                   "--native-root", str(self.native)]
        without_review = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(without_review.returncode, 0)
        self.assertFalse(self.marker.exists())
        confirmed = subprocess.run(command + ["--confirm-xats-stopped",
                                          "--confirm-old-sessions-closed"],
                                   capture_output=True, text=True)
        self.assertEqual(confirmed.returncode, 0, confirmed.stderr)
        self.assertEqual(json.loads(confirmed.stdout)["state"], "activated")


if __name__ == "__main__":
    unittest.main()
