#!/usr/bin/env python3
"""Explicitly return new sessions to XATS without deleting native history.

The operator must independently confirm both services' session state. This
command never stops or starts a service and never acknowledges any message.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import stat
from typing import Sequence

from collaboration_backend import default_marker
from native_collaboration_cutover import inspect_legacy_mailbox, inspect_native_mailbox
from native_collaboration_runtime import BRIDGE_COMMIT, default_root


class RollbackError(ValueError):
    """Rollback would switch to an unavailable mailbox or strand native work."""


def rollback_native_backend(marker: Path, database: Path) -> dict[str, object]:
    """Remove only the selected native marker after both inboxes pass preflight."""
    marker, database = Path(marker), Path(database)
    if (not marker.is_absolute() or not database.is_absolute()
            or marker.name != "transport.json" or database.name != "bridge.sqlite"
            or marker.parent.parent != database.parent.parent.parent):
        raise RollbackError("rollback paths must belong to the same private runtime")
    shared_parent = marker.parent.parent
    for directory in (shared_parent, marker.parent, database.parent.parent,
                      database.parent):
        try:
            metadata = directory.lstat()
        except OSError as error:
            raise RollbackError("private rollback directory is unavailable") from error
        if (not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid()
                or (directory != shared_parent and stat.S_IMODE(metadata.st_mode) & 0o077)):
            raise RollbackError("rollback mailboxes must be owner-only")
    try:
        metadata = marker.lstat()
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) != 0o600):
            raise RollbackError("transport marker must be an owner-owned 0600 file")
        if json.loads(marker.read_text(encoding="utf-8")) != {
            "backend": "native", "commit": BRIDGE_COMMIT,
        }:
            raise RollbackError("transport marker is not the pinned native selection")
    except (OSError, UnicodeError, ValueError) as error:
        if isinstance(error, RollbackError):
            raise
        raise RollbackError("transport marker is unavailable or invalid") from error
    if inspect_legacy_mailbox(marker.parent / "messages.sqlite")["state"] == "unavailable":
        raise RollbackError("XATS mailbox is unavailable")
    native = inspect_native_mailbox(database)
    if native["state"] != "clear":
        raise RollbackError("native mailbox has unresolved sessions or deliveries")
    try:
        marker.unlink()
    except OSError as error:
        raise RollbackError("could not remove native transport marker") from error
    return {"state": "rolled-back", "nativeMailboxRetained": True,
            "unacknowledgedDirect": 0, "unacknowledgedBroadcastDeliveries": 0}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-native-sessions-stopped", action="store_true", required=True)
    parser.add_argument("--confirm-xats-running", action="store_true", required=True)
    args = parser.parse_args(argv)
    try:
        result = rollback_native_backend(default_marker(), default_root() / "mailbox/bridge.sqlite")
    except RollbackError as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
