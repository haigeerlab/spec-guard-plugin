"""Private, versioned intent journal for explicit Local ticket handoffs."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from local_ticket_portability import InventoryError


SCHEMA_VERSION = 1
STATES = {"planned", "partial", "verified", "conflict"}


def default_journal_root() -> Path:
    return Path.home() / ".spec-guard" / "local-ticket-portability"


def _common_dir(project: Path) -> Path:
    completed = subprocess.run(
        ["git", "-C", str(project), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True, text=True, check=False,
    )
    if completed.returncode != 0:
        raise InventoryError("journal-source-unknown: Git common directory is unavailable")
    return Path(completed.stdout.strip()).resolve()


def journal_path(project: Path, project_id: str, root: Path | None = None) -> Path:
    if not project_id or not project_id.isalnum():
        raise InventoryError("journal-source-unknown: project identity is invalid")
    common = _common_dir(Path(project))
    partition = hashlib.sha256(str(common).encode("utf-8")).hexdigest()
    return (default_journal_root() if root is None else Path(root)) / partition / project_id / "mapping.json"


def _prepare_parent(path: Path) -> None:
    managed = (path.parent.parent.parent, path.parent.parent, path.parent)
    for directory in managed:
        if directory.is_symlink():
            raise InventoryError("journal-unsafe: directory is a symbolic link")
        directory.mkdir(exist_ok=True, mode=0o700)
        if (directory.is_symlink() or not directory.is_dir() or
                directory.stat().st_mode & 0o077):
            raise InventoryError("journal-unsafe: directory is not private")


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schemaVersion": SCHEMA_VERSION, "entries": {}}
    if path.is_symlink() or not path.is_file():
        raise InventoryError("journal-unsafe: mapping file is not regular")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise InventoryError("journal-invalid: mapping file is unreadable") from error
    if (not isinstance(value, dict) or value.get("schemaVersion") != SCHEMA_VERSION or
            not isinstance(value.get("entries"), dict)):
        raise InventoryError("journal-invalid: mapping schema differs")
    return value


def read_journal(path: Path) -> dict[str, Any]:
    """Read only; absence means no local hints, never remote absence."""
    return _read(Path(path))


def entry_key(project_id: str, issue_id: str, destination: dict[str, Any]) -> str:
    identity = [project_id, issue_id, destination["platform"], destination["host"],
                destination["targetId"]]
    return hashlib.sha256(json.dumps(identity, separators=(",", ":")).encode()).hexdigest()


def write_entry(path: Path, key: str, entry: dict[str, Any]) -> None:
    """Serialize one transition under an exclusive local lock and atomic replace."""
    if entry.get("state") not in STATES or not isinstance(key, str) or len(key) != 64:
        raise InventoryError("journal-invalid: mapping entry has invalid state or key")
    path = Path(path)
    _prepare_parent(path)
    lock = path.with_name(path.name + ".lock")
    try:
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise InventoryError("journal-busy: handoff is already running") from error
    os.close(descriptor)
    try:
        ledger = _read(path)
        ledger["entries"][key] = entry
        descriptor, temporary = tempfile.mkstemp(prefix=".mapping-", dir=path.parent)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(ledger, handle, ensure_ascii=False, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            Path(temporary).unlink(missing_ok=True)
    finally:
        lock.unlink(missing_ok=True)


@contextmanager
def publication_lock(path: Path, key: str):
    """Exclude a second managed publisher for the entire remote transaction."""
    path = Path(path)
    _prepare_parent(path)
    lock = path.with_name("mapping." + key + ".publish.lock")
    try:
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise InventoryError("journal-busy: handoff is already running") from error
    os.close(descriptor)
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)
