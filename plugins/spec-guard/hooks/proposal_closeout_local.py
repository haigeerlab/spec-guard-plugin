"""Local ledger adapter for Proposal closeout, over Epiq's stdio MCP.

Same seven-method protocol as the hosted adapters, so the decision and the identity
rules are shared and only the transport differs.  Every response shape below was
observed from the pinned epiq@1.11.0 runtime in an isolated temporary ledger.

Two observations drive the implementation:

- `epiq_issue_list` omits closed issues unless `includeClosed` is set.  A closed
  Proposal read as `absent` is the worst possible answer, because absent invites
  creating an item that already exists, so the flag is not optional here.
- `epiq_issue_tag_remove` takes a `tagId`, not a tag name.  The id comes from the
  issue's own `tags`, each `{"id": ..., "name": ...}`.  When the old stage tag is not
  in that list its identity is unknown, and this adapter stops instead of guessing.

It calls only everyday Epiq tools.  The gated ones -- `epiq_sync` above all, which
publishes ticket contents to a Git remote -- are never reached from here.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any, Callable

from local_ledger_runtime import (
    MCP_RELATIVE_PATH, RuntimeContractError, default_runtime_dir, mcp_tool_call, node_status, project_status,
    runtime_status, state_worktree_status,
)

PROJECT_ID = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
DEFAULT_RUNTIME = default_runtime_dir()


class LocalCloseoutError(Exception):
    """The ledger could not be read or written in a way worth acting on."""


def _caller(project: Path, runtime_dir: Path) -> Callable[..., Any]:
    """Build a caller bound to one project root and the pinned runtime."""
    runtime = runtime_status(Path(runtime_dir))
    node = node_status()
    if runtime["state"] != "ready" or node["state"] != "ready":
        raise LocalCloseoutError("local-ledger runtime or Node is not ready")
    command = [node["path"], str(Path(runtime_dir) / MCP_RELATIVE_PATH)]
    environment = dict(os.environ)

    def call(name: str, **arguments: Any) -> Any:
        try:
            response = mcp_tool_call(command, name, {
                "repoRoot": str(project), **arguments,
            }, environment=environment)
        except RuntimeContractError as error:
            raise LocalCloseoutError(str(error)) from error
        return response["value"]

    return call


class LocalCloseout:
    def __init__(self, project_id: Any, project: Path | None = None,
                 runtime_dir: Path | None = None,
                 caller: Callable[..., Any] | None = None):
        if not isinstance(project_id, str) or not PROJECT_ID.fullmatch(project_id):
            raise LocalCloseoutError("target-invalid: project id is invalid")
        self.project_id = project_id
        self.project = None if project is None else Path(project)
        if caller is None:
            if project is None:
                raise LocalCloseoutError("target-invalid: project root is required")
            caller = _caller(Path(project), runtime_dir or DEFAULT_RUNTIME)
        self.call = caller

    # ── shaping ───────────────────────────────────────────────────────────
    def _normalize(self, raw: Any, expected: str | None = None) -> dict[str, Any]:
        tags = raw.get("tags") if isinstance(raw, dict) else None
        identifier = raw.get("id") if isinstance(raw, dict) else None
        if (not isinstance(raw, dict) or not isinstance(identifier, str) or
                not identifier or (expected is not None and identifier != expected) or
                not isinstance(raw.get("ref"), str) or
                not isinstance(raw.get("description"), (str, type(None))) or
                not isinstance(raw.get("isClosed"), bool) or
                not isinstance(tags, list) or
                any(not isinstance(item, dict) or not isinstance(item.get("id"), str) or
                    not isinstance(item.get("name"), str) for item in tags)):
            raise LocalCloseoutError("provider-unavailable: invalid Epiq issue")
        return {"id": identifier, "ref": raw["ref"], "projectId": self.project_id,
                "description": raw.get("description") or "",
                "labels": [item["name"] for item in tags],
                "isClosed": raw["isClosed"], "tags": tags}

    # ── reads ─────────────────────────────────────────────────────────────
    def target_facts(self) -> dict[str, Any]:
        """The committed ledger identity, not an echo of the caller's own argument.

        `exactTarget` is what the operator reads before authorizing, so it has to be a
        fact about the destination.  The project actually written to is decided by
        `.epiq/project.json` under the project root, while the id came from `--target`
        or from `.agent/tracker.json`; a repository shipping two different values would
        otherwise show one destination and write to another.  There is no URL and no
        platform visibility to report for a Local ledger.
        """
        if self.project is None:
            raise LocalCloseoutError("target-unknown: project root is required")
        identity = project_status(self.project)
        if identity.get("state") != "initialized":
            raise LocalCloseoutError("target-unknown: the ledger is not initialized")
        if identity.get("projectId") != self.project_id:
            raise LocalCloseoutError(
                "target-unknown: the ledger identity differs from the named target")
        # Every other Local writer here gates on ownership: a second checkout of the
        # same project can own the state worktree, and writing through one we do not
        # own would land the record in someone else's copy.
        owner = state_worktree_status(self.project, self.project_id)
        if owner.get("state") != "owned":
            raise LocalCloseoutError(
                "target-unknown: the Epiq state worktree is not owned by this checkout")
        return {"platform": "local", "target": self.project_id,
                "targetId": identity["projectId"],
                "stateBranch": identity.get("stateBranch"),
                "publishesTo": self._publish_remote()}

    def _publish_remote(self):
        """The Git remote a confirmed `epiq_sync` would publish the state branch to.

        The operator authorizes the write from the preview, so whether the record can
        become public belongs in it. This module never calls `epiq_sync`; it only
        reports where one would go, or `None` when there is no remote.
        """
        try:
            done = subprocess.run(
                ["git", "-C", str(self.project), "remote", "get-url", "origin"],
                capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            return None
        return "origin" if done.returncode == 0 and done.stdout.strip() else None

    def list_issues(self) -> dict[str, Any]:
        raw = self.call("epiq_issue_list", includeClosed=True)
        if not isinstance(raw, list):
            raise LocalCloseoutError("provider-unavailable: invalid Epiq listing")
        return {"complete": True, "issues": [self._normalize(item) for item in raw]}

    def get_issue(self, issue_id: str) -> dict[str, Any]:
        return self._normalize(self.call("epiq_issue_get", idOrRef=issue_id), issue_id)

    def list_comments(self, issue_id: str) -> dict[str, Any]:
        raw = self.call("epiq_issue_get", idOrRef=issue_id)
        comments = raw.get("comments") if isinstance(raw, dict) else None
        if (not isinstance(comments, list) or
                any(not isinstance(item, dict) or not isinstance(item.get("body"), str)
                    for item in comments)):
            raise LocalCloseoutError("provider-unavailable: invalid Epiq comments")
        return {"complete": True, "comments": [{"body": item["body"]}
                                               for item in comments]}

    # ── writes ────────────────────────────────────────────────────────────
    def create_comment(self, issue_id: str, body: str) -> None:
        self.call("epiq_issue_comment_add", issueId=issue_id, body=body)

    def set_stage(self, issue_id: str, from_stage: str | None, to_stage: str) -> None:
        """Add the new stage tag, then remove the old one by its id.

        Adding first is the same ordering the hosted adapters use: a failure between
        the two steps may leave two stage tags, which the next read reports as a
        contract violation, but never leaves the item with no stage at all.
        """
        self.call("epiq_issue_tag_add", issueId=issue_id, tagName=to_stage)
        if not from_stage or from_stage == to_stage:
            return
        identities = {item["name"]: item["id"]
                      for item in self.get_issue(issue_id)["tags"]}
        if from_stage not in identities:
            raise LocalCloseoutError(
                "provider-unavailable: the previous stage tag has no readable identity")
        self.call("epiq_issue_tag_remove", issueId=issue_id,
                  tagId=identities[from_stage])

    def set_closed(self, issue_id: str) -> None:
        self.call("epiq_issue_close", issueId=issue_id)
