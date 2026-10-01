"""Read-only evidence preview for rebinding a moved Local handoff journal."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from local_ledger_runtime import state_worktree_status
from local_ticket_archive import verify_archive
from local_ticket_handoff import _raw_events, _source_digest, snapshot_issue
from local_ticket_journal import (PARTITION_NAME, default_journal_root,
                                  discover_journal_candidates, entry_key, journal_path,
                                  read_journal)
from local_ticket_portability import InventoryError, inventory_project, worktree_roots


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_evidence(project: Path, inventory: dict[str, Any]) -> list[str]:
    owner = state_worktree_status(project, inventory["projectId"])
    if owner["state"] != "owned":
        raise InventoryError("journal-bind-source: Epiq state worktree is not owned")
    raw = _raw_events(Path(owner["path"]), inventory["files"])
    ids = {payload["id"] for action, payload in raw.values()
           if action == "add.issue" and isinstance(payload, dict)
           and isinstance(payload.get("id"), str)}
    return sorted(ids)


def _archive_evidence(project: Path, archive: Path, project_id: str,
                      mapping_bytes: bytes) -> dict[str, Any]:
    manifest_path = archive / "manifest.json"
    if (archive.is_symlink() or not archive.is_dir() or
            manifest_path.is_symlink() or not manifest_path.is_file()):
        raise InventoryError("journal-bind-evidence: archive is unsafe")
    manifest_bytes = manifest_path.read_bytes()
    verified = verify_archive(archive)
    if manifest_path.read_bytes() != manifest_bytes:
        raise InventoryError("journal-bind-evidence: archive changed during review")
    manifest = json.loads(manifest_bytes)
    archived_mapping = archive / ".spec-guard" / "mapping.json"
    record = next((item for item in manifest["files"]
                   if item["path"] == ".spec-guard/mapping.json"), None)
    if (verified["projectId"] != project_id or record is None or
            record["sha256"] != _sha(mapping_bytes) or
            record["size"] != len(mapping_bytes) or not archived_mapping.is_file() or
            archived_mapping.read_bytes() != mapping_bytes):
        raise InventoryError("journal-bind-evidence: archive mapping differs")
    ancestor = subprocess.run(
        ["git", "-C", str(project), "merge-base", "--is-ancestor",
         manifest["stateHead"], "refs/heads/__epiq_state__"],
        capture_output=True, check=False,
    )
    if ancestor.returncode != 0:
        raise InventoryError("journal-bind-evidence: archive state is not a source ancestor")
    return {"kind": "archive", "path": str(archive.resolve()),
            "stateHead": manifest["stateHead"]}


def _old_path_evidence(old_common_dir: Path, candidate: str) -> dict[str, Any]:
    old = Path(old_common_dir)
    if (not old.is_absolute() or ".." in old.parts or
            hashlib.sha256(str(old).encode("utf-8")).hexdigest() != candidate):
        raise InventoryError("journal-bind-evidence: old Git common path does not match")
    if old.exists() or old.is_symlink():
        raise InventoryError("journal-bind-evidence: old Git common path is still occupied")
    return {"kind": "old-common-dir", "path": str(old)}


def _entry_evidence(project: Path, runtime_dir: Path, project_id: str,
                    issue_ids: list[str], key: str, entry: Any) -> dict[str, Any]:
    if (re.fullmatch(r"[0-9a-f]{64}", key) is None or not isinstance(entry, dict)
            or entry.get("state") not in ("planned", "partial", "verified", "conflict")
            or not isinstance(entry.get("destination"), dict)
            or re.fullmatch(r"[0-9a-f]{64}", str(entry.get("sourceDigest"))) is None
            or entry.get("digestVersion", 1) not in (1, 2)):
        raise InventoryError("journal-bind-evidence: mapping entry is incomplete")
    destination = entry["destination"]
    if (destination.get("platform") not in ("github", "gitlab") or
            not all(isinstance(destination.get(name), str) and destination[name]
                for name in ("platform", "host", "target")) or
            type(destination.get("targetId")) is not int or destination["targetId"] <= 0):
        raise InventoryError("journal-bind-evidence: mapping destination is incomplete")
    matching = [issue_id for issue_id in issue_ids
                if entry_key(project_id, issue_id, destination) == key]
    if len(matching) != 1:
        raise InventoryError("journal-bind-evidence: mapping key has no unique Local issue")
    issue_id = matching[0]
    version = entry.get("digestVersion", 1)
    snapshot = snapshot_issue(project, issue_id, runtime_dir, legacy=version == 1)
    if version == 1:
        matched = "current" if snapshot["sourceDigest"] == entry["sourceDigest"] else None
    else:
        matched = next(("current" if size == len(snapshot["events"]) else "prefix"
                        for size in range(1, len(snapshot["events"]) + 1)
                        if _source_digest(snapshot["events"][:size]) == entry["sourceDigest"]), None)
    if matched is None:
        raise InventoryError("journal-bind-evidence: source digest cannot be proven")
    return {"key": key, "issueId": issue_id, "state": entry["state"],
            "digestVersion": version, "sourceMatch": matched,
            "sourceDigest": entry["sourceDigest"], "destination": destination}


def preview_binding(project: Path, candidate: str, output: Path, runtime_dir: Path,
                    old_common_dir: Path | None = None, archive: Path | None = None,
                    journal_root: Path | None = None) -> dict[str, Any]:
    """Require local evidence before writing a new private review artifact."""
    project, output = Path(project).resolve(), Path(output)
    if (not isinstance(candidate, str) or PARTITION_NAME.fullmatch(candidate) is None or
            (old_common_dir is None) == (archive is None)):
        raise InventoryError("journal-bind-evidence: exactly one source proof is required")
    before = inventory_project(project)
    project_id = before["projectId"]
    root = default_journal_root() if journal_root is None else Path(journal_root)
    current = journal_path(project, project_id, root)
    discovery = discover_journal_candidates(project, project_id, root)
    candidates = discovery["candidates"]
    if (len(candidates) != 1 or candidates[0]["partition"] != candidate or
            candidates[0]["journalState"] != "present"):
        raise InventoryError("journal-bind-evidence: one complete candidate is required")
    if current.parent.exists() and (not current.parent.is_dir() or
                                    any(current.parent.iterdir())):
        raise InventoryError("journal-bind-evidence: current partition is already active")
    mapping = Path(candidates[0]["path"])
    mapping_bytes = mapping.read_bytes()
    entries = read_journal(mapping)["entries"]
    proof = (_old_path_evidence(old_common_dir, candidate) if old_common_dir is not None
             else _archive_evidence(project, Path(archive), project_id, mapping_bytes))
    issue_ids = _source_evidence(project, before)
    resolved = [_entry_evidence(project, runtime_dir, project_id, issue_ids, key, entry)
                for key, entry in sorted(entries.items())]
    if inventory_project(project) != before or mapping.read_bytes() != mapping_bytes:
        raise InventoryError("journal-bind-evidence: source changed during review")
    destination = output.resolve(strict=False)
    owner = state_worktree_status(project, project_id)
    protected = [*worktree_roots(project), Path(owner["path"]).resolve(), root.resolve()]
    if archive is not None:
        protected.append(Path(archive).resolve())
    if (not output.parent.is_dir() or output.exists() or output.is_symlink() or
            any(path == destination or path in destination.parents for path in protected)):
        raise InventoryError("journal-bind-output: output must be a new file outside source")
    preview = {
        "formatVersion": 1, "state": "journal-bind-preview", "projectId": project_id,
        "currentPartition": current.parent.parent.name, "candidatePartition": candidate,
        "mappingSha256": _sha(mapping_bytes), "sourceInventorySha256": _sha(json.dumps(
            before, sort_keys=True, separators=(",", ":")).encode("utf-8")),
        "evidence": proof, "entries": resolved,
        "limitation": "Matching Local history cannot independently prove repository identity; confirm ownership before binding",
    }
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            os.fchmod(handle.fileno(), 0o600)
            json.dump(preview, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    return {"state": "journal-bind-previewed", "projectId": project_id,
            "candidatePartition": candidate, "entryCount": len(resolved),
            "output": str(output)}
