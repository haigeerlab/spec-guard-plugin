"""Prove an offline Epiq archive can be read and extended in isolation."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from local_ledger_runtime import (
    MCP_RELATIVE_PATH, node_status, runtime_status, mcp_tool_call,
)
from local_ticket_archive import verify_archive
from local_ticket_inventory import InventoryError, _event_lines
from local_ticket_lock import acquire_lock


PROOF_ACTOR_ID = "01M3SRSVX16EAHRM78KQ1K7J01"


def _git(root: Path, *arguments: str) -> None:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False, capture_output=True, text=True,
    )
    if completed.returncode != 0:
        raise InventoryError("restore-proof-failed: Git could not build isolated ledger")


def _source_events(archive: Path, files: list[dict[str, Any]]) -> dict[str, tuple[str, Any]]:
    events: dict[str, tuple[str, Any]] = {}
    for entry in files:
        name = entry["path"]
        if not name.startswith(".epiq/events/"):
            continue
        for value in _event_lines((archive / name).read_bytes(), name):
            action = next(key for key in value if key not in ("v", "id"))
            item = (action, value[action])
            earlier = events.setdefault(value["id"][0], item)
            if earlier != item:
                raise InventoryError("restore-proof-failed: duplicate source event differs")
    return events


def _call(command: list[str], environment: dict[str, str], name: str,
          root: Path, **arguments: Any) -> Any:
    response = mcp_tool_call(
        command, name, {"repoRoot": str(root), **arguments}, environment=environment,
    )
    return response["value"]


def _populate_archive(archive: Path, manifest: dict[str, Any],
                      root: Path, state_root: Path) -> None:
    config = root / ".epiq" / "project.json"
    config.parent.mkdir()
    config.write_bytes((archive / ".epiq" / "project.json").read_bytes())
    _git(root, "fetch", "-q", str(archive / "state.bundle"),
         "refs/heads/__epiq_state__:refs/heads/__epiq_state__")
    _git(root, "worktree", "add", "-q", str(state_root), "__epiq_state__")
    for entry in manifest["files"]:
        name = entry["path"]
        if not name.startswith((".epiq/events/", ".epiq/media/")):
            continue
        target = state_root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((archive / name).read_bytes())
        if hashlib.sha256(target.read_bytes()).hexdigest() != entry["sha256"]:
            raise InventoryError("restore-proof-failed: restored file hash differs")


def prove_restore(archive: Path, runtime_dir: Path) -> dict[str, Any]:
    """Use disposable Git/Epiq state; never mutate the archive or caller's ledger."""
    archive = Path(archive).resolve()
    verified = verify_archive(archive)
    runtime_dir = Path(runtime_dir)
    runtime = runtime_status(runtime_dir)
    node = node_status()
    if runtime["state"] != "ready" or node["state"] != "ready":
        raise InventoryError("restore-proof-unavailable: pinned Epiq runtime or Node is absent")
    manifest = json.loads((archive / "manifest.json").read_text(encoding="utf-8"))
    source_events = _source_events(archive, manifest["files"])
    if sorted(source_events) != manifest["eventIds"]:
        raise InventoryError("archive-invalid: event list differs from source files")

    with tempfile.TemporaryDirectory(prefix="sg-restore-proof-") as temporary:
        base = Path(temporary)
        root = base / "project"
        root.mkdir()
        global_dir = base / "epiq-global"
        state_root = global_dir / "worktrees" / manifest["projectId"]
        state_root.parent.mkdir(parents=True)
        _git(root, "init", "-q")
        _git(root, "config", "user.name", "Spec Guard restore proof")
        _git(root, "config", "user.email", "restore-proof@example.invalid")
        _populate_archive(archive, manifest, root, state_root)

        global_dir.mkdir(exist_ok=True)
        (global_dir / "config.json").write_text(json.dumps({
            "logLevel": "error", "userId": PROOF_ACTOR_ID,
            "userName": "Spec Guard restore proof", "preferredEditor": "true",
            "autoSync": False,
        }), encoding="utf-8")
        environment = dict(os.environ)
        environment["EPIQ_GLOBAL_DIR"] = str(global_dir)
        command = [node["path"], str(runtime_dir / MCP_RELATIVE_PATH)]
        try:
            state = _call(command, environment, "epiq_state_get", root)
            restored = {
                item["id"]: (item["action"], item["payload"])
                for item in state["eventLog"]
            }
            if restored != source_events:
                raise InventoryError("restore-proof-failed: materialized events differ")
            issues = _call(command, environment, "epiq_issue_list", root,
                           includeClosed=True, brief=True)
            issue_views = []
            for issue in issues:
                issue_views.append(_call(command, environment, "epiq_issue_get", root,
                                         idOrRef=issue["id"]))
            lanes = _call(command, environment, "epiq_swimlane_list", root)
            lane = next((item for item in lanes if not item["isClosed"]), None)
            if lane is None:
                boards = _call(command, environment, "epiq_board_list", root)
                board = boards[0] if boards else _call(
                    command, environment, "epiq_board_create", root, title="Restore proof",
                )
                lane = _call(command, environment, "epiq_swimlane_create", root,
                             boardId=board["id"], title="Open")
            created = _call(command, environment, "epiq_issue_create", root,
                            parentId=lane["id"], title="Restore proof",
                            description="Disposable writeability check")
            read_back = _call(command, environment, "epiq_issue_get", root,
                              idOrRef=created["id"])
            if read_back["id"] != created["id"]:
                raise InventoryError("restore-proof-failed: new issue was not readable")
        except (KeyError, TypeError, ValueError) as error:
            if isinstance(error, InventoryError):
                raise
            raise InventoryError("restore-proof-failed: Epiq readback is incomplete") from error
        digest = hashlib.sha256(json.dumps(
            state["eventLog"], sort_keys=True, ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")).hexdigest()
        issue_digest = hashlib.sha256(json.dumps(
            sorted(issue_views, key=lambda item: item["id"]),
            sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        ).encode("utf-8")).hexdigest()
    media_hashes = sorted(entry["sha256"] for entry in manifest["files"]
                          if entry["path"].startswith(".epiq/media/"))
    return {"state": "proved", "projectId": verified["projectId"],
            "eventCount": len(source_events), "eventDigest": digest,
            "issueCount": len(issues), "issueDigest": issue_digest,
            "mediaCount": len(media_hashes), "mediaHashes": media_hashes,
            "writable": True}


def _preflight_target(archive: Path, project: Path, global_dir: Path) -> None:
    if (project.is_symlink() or not project.is_dir() or
            set(path.name for path in project.iterdir()) != {".git"} or
            (project / ".git").is_symlink() or not (project / ".git").is_dir()):
        raise InventoryError("target-not-empty: target must be an empty Git repository")
    if (global_dir.is_symlink() or not global_dir.is_dir() or
            any(global_dir.iterdir())):
        raise InventoryError("target-not-empty: Epiq global directory must be empty")
    resolved = (archive.resolve(), project.resolve(), global_dir.resolve())
    for index, first in enumerate(resolved):
        for second in resolved[index + 1:]:
            if first == second or first in second.parents or second in first.parents:
                raise InventoryError("target-not-empty: archive and target paths overlap")
    top = subprocess.run(
        ["git", "-C", str(project), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=False,
    )
    if top.returncode != 0 or Path(top.stdout.strip()).resolve() != project.resolve():
        raise InventoryError("target-not-empty: target is not a Git worktree root")
    for arguments in (("show-ref",), ("rev-parse", "--verify", "HEAD")):
        result = subprocess.run(
            ["git", "-C", str(project), *arguments],
            capture_output=True, text=True, check=False,
        )
        if result.returncode == 0:
            raise InventoryError("target-not-empty: Git repository already has history")


def restore_archive(archive: Path, project: Path, global_dir: Path,
                    runtime_dir: Path, confirm: bool = False) -> dict[str, Any]:
    """Restore only into a caller-named empty repository and empty Epiq home."""
    if not confirm:
        raise InventoryError("confirmation-required: restore needs explicit confirmation")
    archive, project, global_dir = Path(archive), Path(project), Path(global_dir)
    verify_archive(archive)
    _preflight_target(archive, project, global_dir)
    proof = prove_restore(archive, runtime_dir)
    manifest = json.loads((archive / "manifest.json").read_text(encoding="utf-8"))
    lock = project / ".git" / "spec-guard-local-restore.lock"
    lock_descriptor = acquire_lock(lock, "target-busy")
    try:
        _preflight_target(archive, project, global_dir)
        verify_archive(archive)
        if not subprocess.run(
            ["git", "-C", str(project), "config", "user.name"],
            capture_output=True, check=False,
        ).stdout.strip() or not subprocess.run(
            ["git", "-C", str(project), "config", "user.email"],
            capture_output=True, check=False,
        ).stdout.strip():
            raise InventoryError("target-identity-missing: configure Git author before restore")
        state_root = global_dir / "worktrees" / manifest["projectId"]
        os.chmod(global_dir, 0o700)
        state_root.parent.mkdir(parents=True, mode=0o700)
        try:
            _populate_archive(archive, manifest, project, state_root)
            _git(project, "add", ".epiq/project.json")
            _git(project, "commit", "-qm", "Restore Epiq project identity")
            environment = dict(os.environ)
            environment["EPIQ_GLOBAL_DIR"] = str(global_dir)
            node = node_status()
            command = [node["path"], str(Path(runtime_dir) / MCP_RELATIVE_PATH)]
            state = _call(command, environment, "epiq_state_get", project)
            digest = hashlib.sha256(json.dumps(
                state["eventLog"], sort_keys=True, ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")).hexdigest()
            if digest != proof["eventDigest"]:
                raise InventoryError("restore-incomplete: restored Epiq state differs")
        except (InventoryError, OSError, KeyError, TypeError, ValueError) as error:
            raise InventoryError(
                "restore-incomplete: inspect the target; partial data was preserved"
            ) from error
    finally:
        os.close(lock_descriptor)
    return {"state": "restored", "projectId": proof["projectId"],
            "eventCount": proof["eventCount"], "mediaCount": proof["mediaCount"],
            "stateBranch": "__epiq_state__", "gitIdentityCommitted": True,
            "localIdentitySetupRequired": True}
