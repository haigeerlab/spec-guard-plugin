"""Legacy mailbox preflight and private archive must fail closed."""
import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from native_collaboration_cutover import inspect_legacy_mailbox, inspect_native_mailbox
from native_collaboration_archive import ArchiveError, archive_legacy_mailbox


class LegacyMailboxPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sg-cutover-")
        self.addCleanup(self.tmp.cleanup)
        self.database = Path(self.tmp.name) / "messages.sqlite"
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
                INSERT INTO agents VALUES ('a', 'spec-guard-local', 'developer', 4);
                INSERT INTO agents VALUES ('b', 'spec-guard-local', 'reviewer', 6);
                INSERT INTO agents VALUES ('proxy', 'spec-guard-local', '__channel_proxy__', 0);
                INSERT INTO agents VALUES ('elsewhere', 'other-team', 'developer', 0);
                INSERT INTO messages VALUES ('old', 4, 'spec-guard-local', 'a', NULL, 'old');
                INSERT INTO messages VALUES ('direct', 5, 'spec-guard-local', 'a', NULL, 'private text');
                INSERT INTO messages VALUES ('role', 7, 'spec-guard-local', NULL, 'reviewer', 'role text');
                INSERT INTO messages VALUES ('other', 8, 'other-team', 'elsewhere', NULL, 'other text');
                INSERT INTO messages VALUES ('orphan', 9, 'spec-guard-local', 'unknown', NULL, 'orphan text');
            """)

    def test_counts_only_deliverable_unread_and_requires_session_review(self):
        before = self.database.read_bytes()
        result = inspect_legacy_mailbox(self.database)
        self.assertEqual(result, {
            "state": "blocked", "registeredIdentities": 2,
            "unreadDeliveries": 2, "activeSessions": "unverified",
        })
        self.assertEqual(self.database.read_bytes(), before)
        self.assertNotIn("private text", str(result))
        self.assertNotIn("role text", str(result))

    def test_no_unread_still_requires_live_session_review(self):
        with sqlite3.connect(self.database) as connection:
            connection.execute("UPDATE agents SET last_processed_event_id=100 WHERE team='spec-guard-local'")
        result = inspect_legacy_mailbox(self.database)
        self.assertEqual(result["unreadDeliveries"], 0)
        self.assertEqual(result["state"], "blocked")
        self.assertEqual(result["activeSessions"], "unverified")

    def test_proxy_mail_is_not_silently_dropped_from_unread_count(self):
        with sqlite3.connect(self.database) as connection:
            connection.execute("INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?)",
                               ("proxy-mail", 10, "spec-guard-local", "proxy", None, "hidden"))
        result = inspect_legacy_mailbox(self.database)
        self.assertEqual(result["registeredIdentities"], 2)
        self.assertEqual(result["unreadDeliveries"], 3)

    def test_empty_legacy_mailbox_is_ready_for_later_cutover_check(self):
        with sqlite3.connect(self.database) as connection:
            connection.execute("DELETE FROM agents WHERE team='spec-guard-local'")
        self.assertEqual(inspect_legacy_mailbox(self.database), {
            "state": "clear", "registeredIdentities": 0,
            "unreadDeliveries": 0, "activeSessions": "none-registered",
        })

    def test_missing_or_symlinked_database_fails_closed_without_creation(self):
        missing = Path(self.tmp.name) / "missing.sqlite"
        self.assertEqual(inspect_legacy_mailbox(missing)["state"], "unavailable")
        self.assertFalse(missing.exists())
        link = Path(self.tmp.name) / "link.sqlite"
        link.symlink_to(self.database)
        self.assertEqual(inspect_legacy_mailbox(link)["state"], "unavailable")

    def test_incompatible_database_fails_closed(self):
        broken = Path(self.tmp.name) / "broken.sqlite"
        broken.write_text("not a sqlite database")
        self.assertEqual(inspect_legacy_mailbox(broken)["state"], "unavailable")


class NativeMailboxRollbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sg-rollback-")
        self.addCleanup(self.tmp.cleanup)
        self.database = Path(self.tmp.name) / "bridge.sqlite"
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
                INSERT INTO agents VALUES ('claude', '2026-01-02', NULL);
                INSERT INTO agents VALUES ('codex', '2026-01-01', NULL);
                INSERT INTO messages VALUES (1, 'claude', 'codex', '2026-01-03', 'secret direct');
                INSERT INTO messages VALUES (2, 'codex', 'missing', '2026-01-03', 'unknown recipient');
                INSERT INTO messages VALUES (3, 'claude', '*', '2026-01-03', 'broadcast');
                INSERT INTO messages VALUES (4, 'claude', '*', '2026-01-01', 'before claude joined');
                INSERT INTO messages VALUES (5, 'codex', 'claude', '2026-01-03', 'handled');
                INSERT INTO acknowledgements VALUES (5, 'claude', '2026-01-04');
            """)
        self.database.chmod(0o600)

    def test_direct_and_broadcast_deliveries_block_rollback(self):
        before = self.database.read_bytes()
        result = inspect_native_mailbox(self.database)
        self.assertEqual(result, {
            "state": "blocked", "registeredIdentities": 2,
            "unacknowledgedDirect": 2, "unacknowledgedBroadcastDeliveries": 2,
            "activeSessions": "unverified",
        })
        self.assertEqual(self.database.read_bytes(), before)
        self.assertNotIn("secret direct", str(result))

    def test_acknowledged_mail_still_requires_session_review(self):
        with sqlite3.connect(self.database) as connection:
            connection.executescript("""
                INSERT INTO acknowledgements VALUES (1, 'codex', '2026-01-04');
                INSERT INTO acknowledgements VALUES (2, 'missing', '2026-01-04');
                INSERT INTO acknowledgements VALUES (3, 'codex', '2026-01-04');
                INSERT INTO acknowledgements VALUES (4, 'codex', '2026-01-04');
            """)
        result = inspect_native_mailbox(self.database)
        self.assertEqual(result["unacknowledgedDirect"], 0)
        self.assertEqual(result["unacknowledgedBroadcastDeliveries"], 0)
        self.assertEqual(result["state"], "blocked")

    def test_no_registered_agents_or_unhandled_deliveries_is_clear(self):
        with sqlite3.connect(self.database) as connection:
            connection.executescript("""
                DELETE FROM messages;
                DELETE FROM agents;
            """)
        self.assertEqual(inspect_native_mailbox(self.database), {
            "state": "clear", "registeredIdentities": 0,
            "unacknowledgedDirect": 0, "unacknowledgedBroadcastDeliveries": 0,
            "activeSessions": "none-registered",
        })

    def test_absent_or_unexpected_schema_fails_closed(self):
        missing = Path(self.tmp.name) / "missing.sqlite"
        self.assertEqual(inspect_native_mailbox(missing)["state"], "unavailable")
        self.assertFalse(missing.exists())
        with sqlite3.connect(self.database) as connection:
            connection.execute("PRAGMA user_version=3")
        self.assertEqual(inspect_native_mailbox(self.database)["state"], "unavailable")

    def test_native_mailbox_must_be_private_and_not_symlinked(self):
        self.database.chmod(0o644)
        self.assertEqual(inspect_native_mailbox(self.database)["state"], "unavailable")
        self.database.chmod(0o600)
        link = Path(self.tmp.name) / "link.sqlite"
        link.symlink_to(self.database)
        self.assertEqual(inspect_native_mailbox(link)["state"], "unavailable")


class LegacyMailboxArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sg-archive-")
        self.addCleanup(self.tmp.cleanup)
        self.database = Path(self.tmp.name) / "messages.sqlite"
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
                INSERT INTO messages VALUES ('first', 1, 'spec-guard-local', 'a', NULL, 'private mail');
            """)

    def test_archive_keeps_uncheckpointed_wal_mail_and_unread_state(self):
        archive_dir = Path(self.tmp.name) / "archive"
        archive_dir.mkdir(mode=0o700)
        with sqlite3.connect(self.database) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?)",
                               ("wal", 10, "spec-guard-local", "a", None, "uncheckpointed mail"))
            connection.commit()
            self.assertTrue(Path(f"{self.database}-wal").exists())
            expected = inspect_legacy_mailbox(self.database)
            result = archive_legacy_mailbox(self.database, archive_dir)
        archived = archive_dir / "messages.sqlite"
        self.assertEqual(result["unreadDeliveries"], expected["unreadDeliveries"])
        self.assertEqual(inspect_legacy_mailbox(archived), expected)
        self.assertEqual(archived.stat().st_mode & 0o777, 0o400)
        self.assertEqual([path.name for path in archive_dir.iterdir()], ["messages.sqlite"])
        self.assertEqual(result["sha256"], hashlib.sha256(archived.read_bytes()).hexdigest())
        self.assertNotIn("private mail", str(result))
        self.assertNotIn(str(self.database), str(result))
        with sqlite3.connect(f"file:{archived}?mode=ro", uri=True) as connection:
            self.assertEqual(connection.execute(
                "SELECT body FROM messages WHERE id='wal'").fetchone()[0], "uncheckpointed mail")
            self.assertEqual(connection.execute(
                "SELECT last_processed_event_id FROM agents WHERE agent_id='a'").fetchone()[0], 0)
        self.assertEqual(inspect_legacy_mailbox(self.database), expected)

    def test_archive_failure_leaves_no_staging_file_or_sidecar(self):
        archive_dir = Path(self.tmp.name) / "archive"
        archive_dir.mkdir(mode=0o700)
        with sqlite3.connect(self.database) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?)",
                               ("wal", 10, "spec-guard-local", "a", None, "uncheckpointed mail"))
            connection.commit()
        before = {"state": "clear", "registeredIdentities": 0,
                  "unreadDeliveries": 0, "activeSessions": "none-registered"}
        changed = {**before, "unreadDeliveries": 1}
        with patch("native_collaboration_archive.inspect_legacy_mailbox",
                   side_effect=[before, changed]):
            with self.assertRaises(ArchiveError):
                archive_legacy_mailbox(self.database, archive_dir)
        self.assertEqual(list(archive_dir.iterdir()), [])

    def test_archive_rejects_journal_mode_switch_that_did_not_take(self):
        archive_dir = Path(self.tmp.name) / "archive"
        archive_dir.mkdir(mode=0o700)
        real_connect = sqlite3.connect

        class _StubbedJournalModeConnection(sqlite3.Connection):
            """A real sqlite3.Connection (so source.backup() still accepts it)
            that reports staying in wal when asked to switch to delete."""

            def execute(self, sql, *args, **kwargs):
                cursor = super().execute(sql, *args, **kwargs)
                if sql.strip().upper().startswith("PRAGMA JOURNAL_MODE=DELETE"):
                    class _FakeCursor:
                        def fetchone(self_inner):
                            return ("wal",)
                    return _FakeCursor()
                return cursor

        def fake_connect(target, *args, **kwargs):
            if not kwargs.get("uri") and Path(str(target)).name.startswith(".messages-"):
                return real_connect(target, *args, factory=_StubbedJournalModeConnection, **kwargs)
            return real_connect(target, *args, **kwargs)

        with patch("native_collaboration_archive.sqlite3.connect", side_effect=fake_connect):
            with self.assertRaises(ArchiveError):
                archive_legacy_mailbox(self.database, archive_dir)
        self.assertEqual(list(archive_dir.iterdir()), [])

    def test_archive_refuses_to_overwrite_or_use_unsafe_paths(self):
        archive_dir = Path(self.tmp.name) / "archive"
        archive_dir.mkdir(mode=0o700)
        existing = archive_dir / "messages.sqlite"
        existing.write_text("keep me", encoding="utf-8")
        with self.assertRaises(ArchiveError):
            archive_legacy_mailbox(self.database, archive_dir)
        self.assertEqual(existing.read_text(encoding="utf-8"), "keep me")

        existing.unlink()
        existing.symlink_to(self.database)
        with self.assertRaises(ArchiveError):
            archive_legacy_mailbox(self.database, archive_dir)
        self.assertTrue(self.database.is_file())
        existing.unlink()

        archive_dir.chmod(0o755)
        with self.assertRaises(ArchiveError):
            archive_legacy_mailbox(self.database, archive_dir)
        self.assertFalse(existing.exists())

        archive_dir.chmod(0o700)
        Path(self.tmp.name).chmod(0o755)
        with self.assertRaises(ArchiveError):
            archive_legacy_mailbox(self.database, archive_dir)
        Path(self.tmp.name).chmod(0o700)

        source_link = Path(self.tmp.name) / "source-link.sqlite"
        source_link.symlink_to(self.database)
        with self.assertRaises(ArchiveError):
            archive_legacy_mailbox(source_link, archive_dir)
        self.assertFalse(existing.exists())

        elsewhere = Path(self.tmp.name) / "elsewhere"
        elsewhere.mkdir(mode=0o700)
        with self.assertRaises(ArchiveError):
            archive_legacy_mailbox(self.database, elsewhere / "archive")

    def test_archive_command_requires_quiescence_and_matching_inventory(self):
        archive_dir = Path(self.tmp.name) / "archive"
        archive_dir.mkdir(mode=0o700)
        command = [sys.executable, str(Path(__file__).with_name("native_collaboration_archive.py")),
                   "--database", str(self.database), "--archive-dir", str(archive_dir),
                   "--expected-registered", "1", "--expected-unread", "1"]

        without_confirmation = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(without_confirmation.returncode, 0)
        self.assertFalse((archive_dir / "messages.sqlite").exists())

        with_wrong_inventory = subprocess.run(
            command[:-1] + ["2", "--confirm-xats-stopped"], capture_output=True, text=True)
        self.assertNotEqual(with_wrong_inventory.returncode, 0)
        self.assertFalse((archive_dir / "messages.sqlite").exists())

        confirmed = subprocess.run(command + ["--confirm-xats-stopped"],
                                   capture_output=True, text=True)
        self.assertEqual(confirmed.returncode, 0, confirmed.stderr)
        self.assertEqual(json.loads(confirmed.stdout)["state"], "archived")
        self.assertNotIn("private mail", confirmed.stdout)
        self.assertEqual(inspect_legacy_mailbox(archive_dir / "messages.sqlite")["unreadDeliveries"], 1)


if __name__ == "__main__":
    unittest.main()
