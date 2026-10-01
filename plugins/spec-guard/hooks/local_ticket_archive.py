"""Create and verify a source-stable, offline Epiq ledger archive."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from local_ledger_runtime import (
    PACKAGE_VERSION, STATE_BRANCH, project_status, state_worktree_status,
)
from local_ticket_portability import InventoryError, inventory_project, worktree_roots
from local_ticket_journal import journal_path, read_journal


def _within(candidate: Path, parent: Path) -> bool:
    try:
        return os.path.commonpath((str(candidate), str(parent))) == str(parent)
    except ValueError:
        return False


def _git(directory: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(directory), *arguments],
        check=False, capture_output=True, text=True,
    )
    if completed.returncode != 0:
        raise InventoryError("archive-invalid: Git bundle operation failed")
    return completed.stdout.strip()


def _record(path: Path, base: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": path.relative_to(base).as_posix(), "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _require_private_directory(path: Path) -> None:
    if path.stat().st_mode & 0o077:
        raise InventoryError(
            "archive-output-unsafe: destination does not retain private POSIX mode"
        )


def _safe_name(name: str) -> bool:
    relative = PurePosixPath(name)
    if (relative.is_absolute() or not relative.parts or ".." in relative.parts
            or relative.as_posix() != name):
        return False
    if name in ("state.bundle", ".epiq/project.json"):
        return True
    if name == ".spec-guard/mapping.json":
        return True
    return (len(relative.parts) == 3 and relative.parts[:2] in
            ((".epiq", "events"), (".epiq", "media")))


def verify_archive(archive: Path) -> dict[str, Any]:
    """Verify manifest, every included byte and the single-state-branch bundle."""
    archive = Path(archive)
    if archive.is_symlink() or not archive.is_dir():
        raise InventoryError("archive-invalid: archive directory is absent or unsafe")
    manifest_path = archive / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise InventoryError("archive-invalid: manifest is absent or unsafe")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise InventoryError("archive-invalid: manifest is unreadable") from error
    if (not isinstance(manifest, dict) or manifest.get("formatVersion") != 1
            or manifest.get("epiqVersion") != PACKAGE_VERSION
            or manifest.get("stateBranch") != STATE_BRANCH
            or not isinstance(manifest.get("stateHead"), str)
            or re.fullmatch(r"[a-f0-9]{40}", manifest["stateHead"]) is None
            or not isinstance(manifest.get("projectId"), str)
            or not isinstance(manifest.get("files"), list)):
        raise InventoryError("archive-invalid: manifest contract is invalid")
    identity = project_status(archive)
    if (identity["state"] != "initialized" or
            identity["projectId"] != manifest["projectId"]):
        raise InventoryError("archive-invalid: project identity differs from manifest")
    expected = {"manifest.json"}
    for record in manifest["files"]:
        if (not isinstance(record, dict) or set(record) != {"path", "size", "sha256"}
                or not isinstance(record["path"], str) or not _safe_name(record["path"])
                or record["path"] in expected or not isinstance(record["size"], int)
                or record["size"] < 0 or not isinstance(record["sha256"], str)
                or len(record["sha256"]) != 64):
            raise InventoryError("archive-invalid: unsafe file manifest")
        expected.add(record["path"])
        file_path = archive / record["path"]
        components = record["path"].split("/")
        if any((archive.joinpath(*components[:index])).is_symlink()
               for index in range(1, len(components) + 1)):
            raise InventoryError("archive-invalid: symbolic link in archive")
        if not file_path.is_file():
            raise InventoryError("archive-invalid: file is missing")
        data = file_path.read_bytes()
        if len(data) != record["size"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
            raise InventoryError("archive-invalid: file hash differs")
    if not {"state.bundle", ".epiq/project.json"}.issubset(expected):
        raise InventoryError("archive-invalid: required file is missing")
    actual = set()
    for current, directories, file_names in os.walk(archive, followlinks=False):
        parent = Path(current)
        for name in directories:
            directory = parent / name
            if directory.is_symlink():
                raise InventoryError("archive-invalid: unlisted symbolic link")
            if directory.relative_to(archive).as_posix() not in (
                    ".epiq", ".epiq/events", ".epiq/media", ".spec-guard"):
                raise InventoryError("archive-invalid: unlisted directory")
        for name in file_names:
            path = parent / name
            if path.is_symlink() or not path.is_file():
                raise InventoryError("archive-invalid: unlisted symbolic link or file")
            actual.add(path.relative_to(archive).as_posix())
    if actual != expected:
        raise InventoryError("archive-invalid: unlisted or missing file")
    if ".spec-guard/mapping.json" in expected:
        read_journal(archive / ".spec-guard/mapping.json")
    with tempfile.TemporaryDirectory(prefix="sg-archive-verify-") as temporary:
        _git(Path(temporary), "init", "-q")
        _git(Path(temporary), "bundle", "verify", str(archive / "state.bundle"))
        heads = _git(Path(temporary), "bundle", "list-heads", str(archive / "state.bundle"))
    if heads.splitlines() != [manifest["stateHead"] + " refs/heads/" + STATE_BRANCH]:
        raise InventoryError("archive-invalid: bundle does not match state branch HEAD")
    return {"state": "verified", "projectId": manifest.get("projectId"),
            "eventCount": len(manifest.get("eventIds", [])), "fileCount": len(expected) - 1}


def archive_project(project: Path, output: Path) -> dict[str, Any]:
    """Save committed state and raw live files without sync, add or push."""
    project = Path(project).resolve()
    output = Path(output)
    before = inventory_project(project)
    state_root = Path(state_worktree_status(project, before["projectId"])["path"]).resolve()
    history = _git(project, "log", "--name-only", "--no-renames", "-z",
                   "--pretty=format:", "refs/heads/" + STATE_BRANCH)
    if any(name and not name.startswith(".epiq/")
           for name in history.split("\0")):
        raise InventoryError("archive-source-history: state branch includes non-ledger files")
    destination = output.resolve(strict=False)
    if _within(destination, state_root) or any(
            _within(destination, root) for root in worktree_roots(project)):
        raise InventoryError("archive-output-unsafe: output overlaps Local source")
    if output.exists() or output.is_symlink():
        raise InventoryError("archive-output-exists: output must be new")
    if not output.parent.is_dir():
        raise InventoryError("archive-output-unsafe: output parent is unavailable")

    temporary = Path(tempfile.mkdtemp(prefix=".sg-archive-", dir=output.parent))
    try:
        os.chmod(temporary, 0o700)
        _require_private_directory(temporary)
        bundle = temporary / "state.bundle"
        _git(project, "bundle", "create", str(bundle), "refs/heads/" + STATE_BRANCH)
        config_source = project / ".epiq" / "project.json"
        config = temporary / ".epiq" / "project.json"
        config.parent.mkdir(mode=0o700)
        config.write_bytes(config_source.read_bytes())
        records = [_record(bundle, temporary), _record(config, temporary)]
        mapping_source = journal_path(project, before["projectId"])
        mapping_present = mapping_source.exists() or mapping_source.is_symlink()
        if mapping_present:
            read_journal(mapping_source)
            mapping = temporary / ".spec-guard" / "mapping.json"
            mapping.parent.mkdir(mode=0o700)
            mapping.write_bytes(mapping_source.read_bytes())
            records.append(_record(mapping, temporary))
        for entry in before["files"]:
            source = state_root / entry["path"]
            if source.is_symlink() or not source.is_file():
                raise InventoryError("source-changed: source file disappeared")
            data = source.read_bytes()
            if len(data) != entry["size"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
                raise InventoryError("source-changed: source file changed during copy")
            destination_file = temporary / entry["path"]
            destination_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            destination_file.write_bytes(data)
            records.append(_record(destination_file, temporary))
        after = inventory_project(project)
        if before != after or config_source.read_bytes() != config.read_bytes():
            raise InventoryError("source-changed: Local source changed during archive")
        if (mapping_source.exists() or mapping_source.is_symlink()) != mapping_present or (
                mapping_present and mapping_source.read_bytes() != mapping.read_bytes()):
            raise InventoryError("source-changed: mapping journal changed during archive")
        manifest = {
            "formatVersion": 1, "epiqVersion": before["epiqVersion"],
            "projectId": before["projectId"], "stateBranch": STATE_BRANCH,
            "stateHead": before["stateHead"],
            "capturedAt": datetime.now(timezone.utc).isoformat(),
            "eventIds": before["eventIds"], "files": sorted(records, key=lambda item: item["path"]),
        }
        (temporary / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8",
        )
        verify_archive(temporary)
        try:
            output.mkdir(mode=0o700)
        except FileExistsError as error:
            raise InventoryError("archive-output-exists: output must be new") from error
        try:
            _require_private_directory(output)
        except InventoryError:
            output.rmdir()
            raise
        # Claim the directory before publishing; the manifest is moved last.
        for name in ("state.bundle", ".epiq", ".spec-guard", "manifest.json"):
            if (temporary / name).exists():
                (temporary / name).rename(output / name)
        return {"state": "archived", "projectId": before["projectId"],
                "eventCount": len(before["eventIds"]), "fileCount": len(records)}
    finally:
        shutil.rmtree(temporary)
