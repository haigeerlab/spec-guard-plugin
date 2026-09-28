#!/usr/bin/env python3
"""Explicitly select native only after the operator has stopped and reviewed XATS.

The confirmations are operator assertions, not a process-liveness detector. This
command never stops a service, acknowledges mail, or changes host configuration.
"""
from __future__ import annotations
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import tempfile
from typing import Sequence
from urllib.parse import quote

from collaboration_backend import default_marker, selected_backend
from native_collaboration_cutover import inspect_legacy_mailbox
from native_collaboration_runtime import BRIDGE_COMMIT, default_root, status as native_status


class ActivationError(ValueError):
    """The reviewed cutover evidence is absent, stale, or unsafe."""


def _private_directory(path: Path) -> None:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise ActivationError("private cutover directory is unavailable") from error
    if (not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) & 0o077):
        raise ActivationError("cutover directory must be owner-only and not a symlink")


def _logical_digest(database: Path) -> str:
    """Compare all SQLite rows and schema without exposing message bodies."""
    digest = hashlib.sha256()
    try:
        with closing(sqlite3.connect(
            f"file:{quote(str(database))}?mode=ro", uri=True,
        )) as connection:
            connection.execute("BEGIN")
            for statement in connection.iterdump():
                digest.update(statement.encode("utf-8"))
                digest.update(b"\n")
    except (OSError, sqlite3.Error) as error:
        raise ActivationError("could not compare archived and current mailbox") from error
    return digest.hexdigest()


def activate_native_backend(
    database: Path, archive: Path, expected_sha256: str,
    expected_counts: tuple[int, int], marker: Path, native_root: Path,
) -> dict[str, object]:
    """Validate the retained XATS snapshot, then publish one complete marker."""
    database, archive, marker = Path(database), Path(archive), Path(marker)
    if (not all(path.is_absolute() for path in (database, archive, marker))
            or marker.name != "transport.json"
            or archive.name != "messages.sqlite"
            or archive.parent.parent != database.parent):
        raise ActivationError("cutover paths must be absolute private mailbox paths")
    if marker.exists() or marker.is_symlink():
        raise ActivationError("transport marker already exists; refusing to overwrite")
    for directory in (database.parent, archive.parent, marker.parent):
        _private_directory(directory)
    if native_status(native_root)["state"] != "ready":
        raise ActivationError("pinned native runtime is not ready")
    if (min(expected_counts) < 0 or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256)):
        raise ActivationError("reviewed archive counts or checksum are invalid")
    try:
        metadata = archive.lstat()
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) != 0o400):
            raise ActivationError("archive must be an owner-owned read-only regular file")
        digest = hashlib.sha256()
        with archive.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != expected_sha256:
            raise ActivationError("archive checksum differs from reviewed evidence")
        with closing(sqlite3.connect(
            f"file:{quote(str(archive))}?mode=ro", uri=True,
        )) as connection:
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ActivationError("archive integrity check failed")
    except (OSError, sqlite3.Error) as error:
        raise ActivationError("archive is unavailable or invalid") from error
    for source in (archive, database):
        inventory = inspect_legacy_mailbox(source)
        if (inventory["state"] == "unavailable"
                or (inventory["registeredIdentities"], inventory["unreadDeliveries"])
                != expected_counts):
            raise ActivationError("mailbox inventory differs from reviewed archive")
    if _logical_digest(archive) != _logical_digest(database):
        raise ActivationError("XATS mailbox contents changed after archive")

    payload = json.dumps({"backend": "native", "commit": BRIDGE_COMMIT}) + "\n"
    try:
        descriptor, temporary_name = tempfile.mkstemp(prefix=".transport-", dir=marker.parent)
    except OSError as error:
        raise ActivationError("could not create private transport marker staging file") from error
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, marker)  # Atomic visibility; never replaces an existing marker.
    except OSError as error:
        raise ActivationError("could not atomically publish transport marker") from error
    finally:
        temporary.unlink(missing_ok=True)
    if selected_backend(marker, native_root)["backend"] != "native":
        raise ActivationError("native marker was published but runtime became unavailable")
    return {"state": "activated", "archiveSha256": expected_sha256,
            "registeredIdentities": expected_counts[0], "unreadDeliveries": expected_counts[1]}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--expected-registered", type=int, required=True)
    parser.add_argument("--expected-unread", type=int, required=True)
    parser.add_argument("--marker", type=Path, default=default_marker())
    parser.add_argument("--native-root", type=Path, default=default_root())
    parser.add_argument("--confirm-xats-stopped", action="store_true", required=True)
    parser.add_argument("--confirm-old-sessions-closed", action="store_true", required=True)
    args = parser.parse_args(argv)
    try:
        result = activate_native_backend(
            args.database, args.archive, args.archive_sha256,
            (args.expected_registered, args.expected_unread), args.marker, args.native_root)
    except ActivationError as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
