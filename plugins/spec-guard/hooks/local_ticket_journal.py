"""Private, versioned intent journal for explicit Local ticket handoffs."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from local_ticket_portability import InventoryError
from local_ticket_lock import acquire_lock


SCHEMA_VERSION = 1
STATES = {"planned", "partial", "verified", "conflict"}
PARTITION_NAME = re.compile(r"[0-9a-f]{64}\Z")


def binding_checksum(value: dict[str, Any]) -> str:
    payload = {key: item for key, item in value.items() if key != "bindingSha256"}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")
                                     ).encode("utf-8")).hexdigest()


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


def discover_journal_candidates(project: Path, project_id: str,
                                root: Path | None = None) -> dict[str, Any]:
    """Read same-project journals in other path partitions without claiming ownership."""
    current = journal_path(project, project_id, root)
    base = default_journal_root() if root is None else Path(root)

    def directory(path: Path, optional: bool = False) -> bool:
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            if optional:
                return False
            raise InventoryError("journal-discovery-unsafe: directory disappeared")
        except OSError as error:
            raise InventoryError("journal-discovery-unsafe: directory is unreadable") from error
        if (not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid() or
                stat.S_IMODE(metadata.st_mode) & 0o077):
            raise InventoryError("journal-discovery-unsafe: directory is not private")
        return True

    if not directory(base, optional=True):
        return {"state": "clear", "projectId": project_id,
                "currentPath": str(current), "candidates": []}
    candidates = []
    try:
        partitions = sorted(base.iterdir())
    except OSError as error:
        raise InventoryError("journal-discovery-unsafe: partitions are unreadable") from error
    for partition in partitions:
        if not PARTITION_NAME.fullmatch(partition.name):
            continue
        directory(partition)
        candidate_dir = partition / project_id
        if not directory(candidate_dir, optional=True):
            continue
        mapping = candidate_dir / "mapping.json"
        if mapping == current:
            continue
        try:
            metadata = mapping.lstat()
        except FileNotFoundError:
            candidates.append({"partition": partition.name, "path": str(mapping),
                               "journalState": "absent", "entryCount": None,
                               "stateCounts": None})
            continue
        except OSError as error:
            raise InventoryError("journal-discovery-unsafe: mapping is unreadable") from error
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid() or
                stat.S_IMODE(metadata.st_mode) & 0o077):
            raise InventoryError("journal-discovery-unsafe: mapping is not private")
        try:
            entries = read_journal(mapping)["entries"]
        except InventoryError as error:
            raise InventoryError("journal-discovery-invalid: mapping cannot be read") from error
        counts = {state: 0 for state in sorted(STATES)}
        for entry in entries.values():
            if not isinstance(entry, dict) or entry.get("state") not in STATES:
                raise InventoryError("journal-discovery-invalid: mapping state is unknown")
            counts[entry["state"]] += 1
        candidates.append({"partition": partition.name, "path": str(mapping),
                           "journalState": "present",
                           "entryCount": len(entries), "stateCounts": counts})
    return {"state": "manual-reconciliation-required" if candidates else "clear",
            "projectId": project_id, "currentPath": str(current),
            "candidates": candidates}


def active_journal(project: Path, project_id: str,
                   root: Path | None = None) -> tuple[Path, str | None, dict[str, Any] | None]:
    """Resolve one reviewed binding, or return unresolved old candidates."""
    current = journal_path(project, project_id, root)
    discovery = discover_journal_candidates(project, project_id, root)
    pointer = current.with_name("binding.json")
    try:
        descriptor = os.open(pointer, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except FileNotFoundError:
        return current, None, discovery if discovery["candidates"] else None
    except OSError as error:
        raise InventoryError("journal-bind-invalid: binding pointer is unsafe") from error
    with os.fdopen(descriptor, "rb") as handle:
        metadata = os.fstat(handle.fileno())
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid() or
                stat.S_IMODE(metadata.st_mode) != 0o600):
            raise InventoryError("journal-bind-invalid: binding pointer is not private")
        raw = handle.read()
    try:
        binding = json.loads(raw)
    except (UnicodeError, ValueError) as error:
        raise InventoryError("journal-bind-invalid: binding pointer is unreadable") from error
    if (not isinstance(binding, dict) or set(binding) != {
            "formatVersion", "projectId", "currentPartition", "candidatePartition",
            "canonicalPartition", "initialMappingSha256", "previewSha256", "boundAt",
            "bindingSha256"}
            or binding["formatVersion"] != 1 or binding["projectId"] != project_id or
            binding["currentPartition"] != current.parent.parent.name or
            not isinstance(binding["candidatePartition"], str) or
            PARTITION_NAME.fullmatch(binding["candidatePartition"]) is None or
            binding["canonicalPartition"] != binding["candidatePartition"] or
            not all(isinstance(binding[name], str) and PARTITION_NAME.fullmatch(binding[name])
                    for name in ("initialMappingSha256", "previewSha256")) or
            not isinstance(binding["boundAt"], str) or
            binding["bindingSha256"] != binding_checksum(binding)):
        raise InventoryError("journal-bind-invalid: binding pointer schema differs")
    if current.exists() or current.is_symlink():
        raise InventoryError("journal-bind-invalid: current partition has another mapping")
    if any(item.name != "binding.json" for item in current.parent.iterdir()):
        raise InventoryError("journal-bind-invalid: current partition has another file")
    candidate = next((item for item in discovery["candidates"]
                      if item["partition"] == binding["candidatePartition"]), None)
    if candidate is None or candidate["journalState"] != "present":
        raise InventoryError("journal-bind-invalid: canonical mapping is unavailable")
    if len(discovery["candidates"]) != 1:
        return current, None, discovery
    path = Path(candidate["path"])
    metadata = path.lstat()
    if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid() or
            stat.S_IMODE(metadata.st_mode) & 0o077):
        raise InventoryError("journal-bind-invalid: canonical mapping is unsafe")
    read_journal(path)
    return path, hashlib.sha256(raw).hexdigest(), None


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
    lock_descriptor = acquire_lock(lock, "journal-busy")
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
        os.close(lock_descriptor)


@contextmanager
def publication_lock(path: Path, key: str):
    """Exclude a second managed publisher for the entire remote transaction."""
    path = Path(path)
    _prepare_parent(path)
    lock = path.with_name("mapping." + key + ".publish.lock")
    descriptor = acquire_lock(lock, "journal-busy")
    try:
        yield
    finally:
        os.close(descriptor)
