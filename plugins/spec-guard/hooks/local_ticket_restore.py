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
from local_ticket_portability import InventoryError, _event_lines


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
