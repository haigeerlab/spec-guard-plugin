"""Build a verified, private XATS snapshot for a separately approved cutover.

The command requires an operator assertion that XATS is stopped. It cannot
establish session liveness or stop the service itself.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import tempfile
from urllib.parse import quote

from native_collaboration_cutover import inspect_legacy_mailbox


class ArchiveError(ValueError):
    """The source or archive target is unsafe, or verification failed."""


def archive_legacy_mailbox(
    database: Path, archive_dir: Path, *, expected_counts: tuple[int, int] | None = None
) -> dict[str, object]:
    """Create one non-overwriting SQLite backup; never acknowledge or delete mail."""
    database, archive_dir = Path(database), Path(archive_dir)
    if (not database.is_absolute() or not archive_dir.is_absolute()
            or archive_dir.parent != database.parent):
        raise ArchiveError("archive must be next to the private legacy mailbox")
    before = inspect_legacy_mailbox(database)
    if before["state"] == "unavailable":
        raise ArchiveError("legacy mailbox is unavailable or unsafe")
    if (expected_counts is not None
            and (before["registeredIdentities"], before["unreadDeliveries"]) != expected_counts):
        raise ArchiveError("mailbox inventory differs from the operator's reviewed counts")
    try:
        parent = database.parent.lstat()
        directory = archive_dir.lstat()
    except OSError as error:
        raise ArchiveError("archive directory is unavailable") from error
    if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.getuid()
            or stat.S_IMODE(parent.st_mode) & 0o077
            or not stat.S_ISDIR(directory.st_mode) or directory.st_uid != os.getuid()
            or stat.S_IMODE(directory.st_mode) & 0o077):
        raise ArchiveError("archive directory must be owner-only and not a symlink")
    final = archive_dir / "messages.sqlite"
    if final.exists() or final.is_symlink():
        raise ArchiveError("archive already exists; refusing to overwrite")

    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".messages-", suffix=".sqlite", dir=archive_dir)
    except OSError as error:
        raise ArchiveError("cannot create private archive staging file") from error
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        source_uri = f"file:{quote(str(database.absolute()))}?mode=ro"
        with sqlite3.connect(source_uri, uri=True) as source:
            with sqlite3.connect(temporary) as target:
                source.backup(target)
                target.execute("PRAGMA journal_mode=DELETE")
                if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ArchiveError("archive integrity check failed")
        archived = inspect_legacy_mailbox(temporary)
        if archived != before:
            raise ArchiveError("mailbox changed during archive; review and retry")
        digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
        temporary.chmod(0o400)
        os.link(temporary, final)  # Same private directory; fails if another archive appeared.
        return {"state": "archived", "registeredIdentities": archived["registeredIdentities"],
                "unreadDeliveries": archived["unreadDeliveries"], "sha256": digest}
    except (OSError, sqlite3.Error, ValueError) as error:
        raise ArchiveError("archive creation or verification failed") from error
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--archive-dir", type=Path, required=True)
    parser.add_argument("--expected-registered", type=int, required=True)
    parser.add_argument("--expected-unread", type=int, required=True)
    parser.add_argument("--confirm-xats-stopped", action="store_true", required=True)
    args = parser.parse_args()
    if min(args.expected_registered, args.expected_unread) < 0:
        parser.error("expected counts must be non-negative")
    try:
        result = archive_legacy_mailbox(
            args.database, args.archive_dir,
            expected_counts=(args.expected_registered, args.expected_unread))
    except ArchiveError as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
