"""Create and verify a source-stable, offline Epiq ledger archive."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from local_ledger_runtime import (
    PACKAGE_VERSION, STATE_BRANCH, project_status, state_worktree_status,
)
from local_ticket_portability import InventoryError, _event_lines, inventory_project, worktree_roots
from local_ticket_journal import (binding_chain_evidence, binding_checksum,
                                  read_journal)


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
    if name in (".spec-guard/mapping.json", ".spec-guard/binding-provenance.json"):
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
    if (not isinstance(manifest, dict) or manifest.get("formatVersion") not in (1, 2)
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
    event_payloads: dict[str, str] = {}
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
        if record["path"].startswith(".epiq/events/"):
            try:
                events = _event_lines(data, record["path"])
            except InventoryError as error:
                raise InventoryError("archive-invalid: event file is invalid") from error
            for event in events:
                event_id = event["id"][0]
                canonical = json.dumps(event, sort_keys=True, separators=(",", ":"))
                if event_id in event_payloads and event_payloads[event_id] != canonical:
                    raise InventoryError("archive-invalid: duplicate event differs")
                event_payloads[event_id] = canonical
    if manifest.get("eventIds") != sorted(event_payloads):
        raise InventoryError("archive-invalid: event IDs differ from archived files")
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
    proof_name = ".spec-guard/binding-provenance.json"
    if manifest["formatVersion"] == 1 and proof_name in expected:
        raise InventoryError("archive-invalid: v1 archive has binding provenance")
    if manifest["formatVersion"] == 2:
        if proof_name not in expected or ".spec-guard/mapping.json" not in expected:
            raise InventoryError("archive-invalid: bound mapping evidence is missing")
        try:
            proof = json.loads((archive / proof_name).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError) as error:
            raise InventoryError("archive-invalid: binding provenance is unreadable") from error
        bindings = proof.get("bindings") if isinstance(proof, dict) else None
        canonical = proof.get("canonicalPartition") if isinstance(proof, dict) else None
        mapping_bytes = (archive / ".spec-guard/mapping.json").read_bytes()
        if (not isinstance(proof, dict) or set(proof) != {
                "formatVersion", "projectId", "canonicalPartition", "mappingSha256",
                "bindings"} or proof["formatVersion"] != 1 or
                proof["projectId"] != manifest["projectId"] or
                not isinstance(canonical, str) or re.fullmatch(r"[0-9a-f]{64}", canonical) is None or
                proof["mappingSha256"] != hashlib.sha256(mapping_bytes).hexdigest() or
                not isinstance(bindings, list) or not bindings):
            raise InventoryError("archive-invalid: binding provenance differs")
        seen: set[str] = set()
        previous = None
        for binding in bindings:
            if (not isinstance(binding, dict) or set(binding) != {
                    "formatVersion", "projectId", "currentPartition", "candidatePartition",
                    "canonicalPartition", "initialMappingSha256", "previewSha256",
                    "boundAt", "bindingSha256"} or
                    binding["formatVersion"] != 1 or binding["projectId"] != proof["projectId"] or
                    binding["canonicalPartition"] != canonical or
                    not all(isinstance(binding[name], str) and
                            re.fullmatch(r"[0-9a-f]{64}", binding[name])
                            for name in ("currentPartition", "candidatePartition",
                                         "initialMappingSha256", "previewSha256")) or
                    not isinstance(binding["boundAt"], str) or
                    binding["currentPartition"] in seen or
                    (previous is not None and binding["currentPartition"] != previous) or
                    binding["bindingSha256"] != binding_checksum(binding)):
                raise InventoryError("archive-invalid: binding chain differs")
            seen.add(binding["currentPartition"])
            previous = binding["candidatePartition"]
        if previous != canonical or canonical in seen:
            raise InventoryError("archive-invalid: binding chain does not reach mapping")
    with tempfile.TemporaryDirectory(prefix="sg-archive-verify-") as temporary:
        checkout = Path(temporary)
        bundle = str(archive / "state.bundle")
        _git(checkout, "init", "-q")
        _git(checkout, "bundle", "verify", bundle)
        heads = _git(checkout, "bundle", "list-heads", bundle)
        if heads.splitlines() != [manifest["stateHead"] + " refs/heads/" + STATE_BRANCH]:
            raise InventoryError("archive-invalid: bundle does not match state branch HEAD")
        _git(checkout, "fetch", "-q", bundle,
             "refs/heads/" + STATE_BRANCH + ":refs/heads/" + STATE_BRANCH)
        history = _git(checkout, "log", "--name-only", "--no-renames", "-z",
                       "--pretty=format:", "refs/heads/" + STATE_BRANCH)
        if any(name and not name.startswith(".epiq/") for name in history.split("\0")):
            raise InventoryError("archive-invalid: bundle history contains non-ledger files")
        tree = _git(checkout, "ls-tree", "-rz", "--full-tree",
                    "refs/heads/" + STATE_BRANCH)
        for record in tree.split("\0"):
            if not record:
                continue
            metadata, separator, name = record.partition("\t")
            fields = metadata.split()
            if (separator != "\t" or len(fields) != 3 or
                    fields[0] not in ("100644", "100755") or fields[1] != "blob" or
                    not name.startswith(".epiq/")):
                raise InventoryError("archive-invalid: bundle tree contains unsafe file")
    return {"state": "verified", "projectId": manifest.get("projectId"),
            "eventCount": len(manifest.get("eventIds", [])), "fileCount": len(expected) - 1}


def archive_project(project: Path, output: Path,
                    journal_root: Path | None = None) -> dict[str, Any]:
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
        mapping_source, binding_token, bindings = binding_chain_evidence(
            project, before["projectId"], journal_root)
        mapping_present = mapping_source.exists() or mapping_source.is_symlink()
        if mapping_present:
            metadata = mapping_source.lstat()
            if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid() or
                    stat.S_IMODE(metadata.st_mode) & 0o077):
                raise InventoryError("archive-source-unsafe: mapping journal is not private")
            read_journal(mapping_source)
            mapping = temporary / ".spec-guard" / "mapping.json"
            mapping.parent.mkdir(mode=0o700)
            mapping.write_bytes(mapping_source.read_bytes())
            records.append(_record(mapping, temporary))
        if binding_token is not None:
            if not mapping_present:
                raise InventoryError("archive-invalid: bound mapping is absent")
            provenance = temporary / ".spec-guard" / "binding-provenance.json"
            provenance.write_text(json.dumps({
                "formatVersion": 1, "projectId": before["projectId"],
                "canonicalPartition": mapping_source.parent.parent.name,
                "mappingSha256": hashlib.sha256(mapping.read_bytes()).hexdigest(),
                "bindings": bindings,
            }, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
            provenance.chmod(0o600)
            records.append(_record(provenance, temporary))
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
        after_mapping, after_token, after_bindings = binding_chain_evidence(
            project, before["projectId"], journal_root)
        if (after_mapping != mapping_source or after_token != binding_token or
                after_bindings != bindings):
            raise InventoryError("source-changed: binding chain changed during archive")
        manifest = {
            "formatVersion": 2 if binding_token is not None else 1,
            "epiqVersion": before["epiqVersion"],
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
