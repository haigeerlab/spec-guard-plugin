#!/usr/bin/env python3
"""Read-only XATS inventory before a separately authorized mailbox cutover.

This is a snapshot, not a cutover command or permission to switch backends.
It never reads message bodies or advances an inbox cursor.
"""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import stat
from urllib.parse import quote

from native_collaboration_runtime import default_root


TEAM = "spec-guard-local"


def _open_read_only(database: Path, *, private: bool = False) -> sqlite3.Connection:
    metadata = database.lstat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid():
        raise ValueError("mailbox must be an owner-owned regular file")
    if private and stat.S_IMODE(metadata.st_mode) != 0o600:
        raise ValueError("native mailbox must have mode 0600")
    return sqlite3.connect(f"file:{quote(str(database.absolute()))}?mode=ro", uri=True)


def inspect_legacy_mailbox(database: Path) -> dict[str, object]:
    """Count registered identities and deliverable unread XATS messages."""
    database = Path(database)
    try:
        with closing(_open_read_only(database)) as connection:
            connection.execute("BEGIN")  # Both counts describe one read-only snapshot.
            registered = connection.execute(
                "SELECT COUNT(*) FROM agents WHERE team=? AND role!='__channel_proxy__'",
                (TEAM,),
            ).fetchone()[0]
            unread = connection.execute("""
                SELECT COUNT(*) FROM messages m JOIN agents a
                  ON a.team=m.to_team AND a.team=?
                 AND m.event_id>a.last_processed_event_id
                 AND (m.to_agent_id=a.agent_id OR
                      (m.to_role IS NOT NULL AND m.to_role=a.role))
            """, (TEAM,)).fetchone()[0]
    except (OSError, sqlite3.Error, ValueError) as error:
        return {"state": "unavailable", "diagnostic": type(error).__name__}
    return {
        "state": "blocked" if registered or unread else "clear",
        "registeredIdentities": registered,
        "unreadDeliveries": unread,
        "activeSessions": "unverified" if registered else "none-registered",
    }


def inspect_native_mailbox(database: Path) -> dict[str, object]:
    """Count unacknowledged native deliveries before a separately approved rollback."""
    try:
        with closing(_open_read_only(Path(database), private=True)) as connection:
            connection.execute("BEGIN")
            if connection.execute("PRAGMA user_version").fetchone()[0] != 2:
                raise ValueError("unsupported native mailbox schema")
            registered = connection.execute(
                "SELECT COUNT(*) FROM agents WHERE retired_at IS NULL"
            ).fetchone()[0]
            direct = connection.execute("""
                SELECT COUNT(*) FROM messages m
                 WHERE m.to_agent != '*'
                   AND NOT EXISTS (
                     SELECT 1 FROM acknowledgements a
                      WHERE a.message_id=m.id AND a.agent=m.to_agent)
            """).fetchone()[0]
            broadcast = connection.execute("""
                SELECT COUNT(*) FROM messages m JOIN agents r
                  ON m.to_agent='*' AND m.from_agent!=r.name
                 AND m.created_at>=r.registered_at
                 WHERE NOT EXISTS (
                   SELECT 1 FROM acknowledgements a
                    WHERE a.message_id=m.id AND a.agent=r.name)
            """).fetchone()[0]
    except (OSError, sqlite3.Error, ValueError) as error:
        return {"state": "unavailable", "diagnostic": type(error).__name__}
    return {
        "state": "blocked" if registered or direct or broadcast else "clear",
        "registeredIdentities": registered,
        "unacknowledgedDirect": direct,
        "unacknowledgedBroadcastDeliveries": broadcast,
        "activeSessions": "unverified" if registered else "none-registered",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("legacy", "native"), default="legacy")
    parser.add_argument("--database", type=Path)
    args = parser.parse_args()
    database = args.database or (default_root() / "mailbox/bridge.sqlite" if args.backend == "native"
                                 else Path.home() / ".spec-guard/collaboration/messages.sqlite")
    result = (inspect_native_mailbox(database) if args.backend == "native"
              else inspect_legacy_mailbox(database))
    print(json.dumps(result, sort_keys=True))
    return {"clear": 0, "blocked": 2, "unavailable": 1}[result["state"]]


if __name__ == "__main__":
    raise SystemExit(main())
