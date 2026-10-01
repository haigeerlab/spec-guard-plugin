"""Build a source-stable, read-only handoff snapshot for one Epiq issue."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from local_ledger_runtime import (
    MCP_RELATIVE_PATH, node_status, runtime_status, mcp_tool_call,
    state_worktree_status,
)
from local_ticket_portability import InventoryError, _event_lines, inventory_project


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _raw_events(state_root: Path, files: list[dict[str, Any]]) -> dict[str, tuple[str, Any]]:
    result: dict[str, tuple[str, Any]] = {}
    for entry in files:
        name = entry["path"]
        if not name.startswith(".epiq/events/"):
            continue
        for raw in _event_lines((state_root / name).read_bytes(), name):
            action = next(key for key in raw if key not in ("v", "id"))
            item = (action, raw[action])
            previous = result.setdefault(raw["id"][0], item)
            if previous != item:
                raise InventoryError("source-changed: duplicate event changed during snapshot")
    return result


def _issue_events(events: list[dict[str, Any]], issue_id: str) -> list[dict[str, Any]]:
    related = {issue_id}
    for item in events:
        payload = item["payload"]
        if payload.get("issue") == issue_id and isinstance(payload.get("id"), str):
            related.add(payload["id"])
    return [item for item in events if
            item["payload"].get("issue") == issue_id or
            item["payload"].get("id") in related]


def _code_references(project: Path, issue: dict[str, Any],
                     events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    text = json.dumps({"issue": issue, "events": events}, ensure_ascii=False)
    candidates = sorted(set(re.findall(r"(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])", text)))
    references = []
    for candidate in candidates:
        result = subprocess.run(
            ["git", "-C", str(project), "cat-file", "-e", candidate + "^{commit}"],
            capture_output=True, check=False,
        )
        references.append({"sha": candidate, "sourceCommitReachable": result.returncode == 0,
                           "targetCommitReachable": None})
    return references


def snapshot_issue(project: Path, issue_id: str, runtime_dir: Path) -> dict[str, Any]:
    """Read raw files and Epiq's view twice around a stable source inventory."""
    project = Path(project).resolve()
    if not issue_id or not isinstance(issue_id, str):
        raise InventoryError("source-unknown: full issue ID is required")
    before = inventory_project(project)
    owner = state_worktree_status(project, before["projectId"])
    if owner["state"] != "owned":
        raise InventoryError("source-unknown: Epiq state worktree is not owned")
    runtime = runtime_status(Path(runtime_dir))
    node = node_status()
    if runtime["state"] != "ready" or node["state"] != "ready":
        raise InventoryError("source-unknown: pinned Epiq runtime or Node is unavailable")
    raw = _raw_events(Path(owner["path"]), before["files"])
    command = [node["path"], str(Path(runtime_dir) / MCP_RELATIVE_PATH)]
    environment = dict(os.environ)

    def read(name: str, **arguments: Any) -> Any:
        response = mcp_tool_call(command, name, {
            "repoRoot": str(project), **arguments,
        }, environment=environment)
        return response["value"]

    try:
        state = read("epiq_state_get")
        issue = read("epiq_issue_get", idOrRef=issue_id)
        events = state["eventLog"]
        materialized = {item["id"]: (
            item["action"], item["payload"],
        ) for item in events}
        if (len(materialized) != len(events) or materialized != raw or
                sorted(materialized) != before["eventIds"] or issue["id"] != issue_id):
            raise InventoryError("source-changed: Epiq view differs from raw events")
        selected = _issue_events(events, issue_id)
        if not selected or not any(item["action"] == "add.issue" for item in selected):
            raise InventoryError("source-unknown: issue has no complete creation history")
        contributors = {item["payload"].get("id"): item["payload"].get("name")
                        for item in events if item["action"] == "create.contributor"}
        selected = [{**item, "actorName": contributors.get(item.get("userId"))}
                    for item in selected]
        attachments = []
        for item in selected:
            if item["action"] == "add.issue.attachment":
                payload = item["payload"]
                attachments.append({
                    "eventId": item["id"], "hash": payload["hash"],
                    "ext": payload["ext"], "bytes": payload["bytes"],
                    "name": payload.get("name"),
                })
        available = {entry["path"]: entry for entry in before["files"]}
        for item in attachments:
            path = ".epiq/media/" + item["hash"] + "." + item["ext"]
            if path not in available or available[path]["size"] != item["bytes"]:
                raise InventoryError("source-changed: issue attachment differs from source")
        after = inventory_project(project)
        if after != before:
            raise InventoryError("source-changed: Local ledger changed during snapshot")
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, InventoryError):
            raise
        raise InventoryError("source-unknown: Epiq issue view is incomplete") from error
    references = _code_references(project, issue, selected)
    source = {"events": selected, "issue": issue, "attachments": attachments,
              "codeReferences": references}
    return {
        "state": "snapshot", "formatVersion": 1,
        "projectId": before["projectId"], "issueId": issue_id,
        "stateHead": before["stateHead"], "sourceDigest": _digest(source),
        "issue": issue, "events": selected, "attachments": attachments,
        "codeReferences": references,
    }
