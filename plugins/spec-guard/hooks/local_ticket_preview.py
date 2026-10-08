"""Render a private Local ticket handoff preview after read-only target checks."""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote, urlparse

from local_ledger_runtime import state_worktree_status
from local_ticket_handoff import snapshot_issue
from local_ticket_inventory import InventoryError, worktree_roots


ISSUE_MARKER = "spec-guard-local-ticket:v1"
EVENT_MARKER = "spec-guard-local-event:v1"
BASE32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _run(arguments: list[str]) -> str | None:
    try:
        result = subprocess.run(arguments, capture_output=True, text=True,
                                timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def target_facts(platform: str, host: str, target: str,
                 runner: Callable[[list[str]], str | None] = _run) -> dict[str, Any]:
    """Require an exact, writable target with a known visibility before previewing."""
    if not re.fullmatch(r"[A-Za-z0-9.-]+", host) or not target or any(
            part in ("", ".", "..") for part in target.split("/")):
        raise InventoryError("provider-unsupported: target or host is invalid")
    if platform == "github":
        if len(target.split("/")) != 2:
            raise InventoryError("provider-unsupported: GitHub target needs owner/repo")
        raw = runner(["gh", "api", "--hostname", host, "repos/" + target])
    elif platform == "gitlab":
        raw = runner(["glab", "api", "--hostname", host,
                      "projects/" + quote(target, safe="")])
    else:
        raise InventoryError("provider-unsupported: platform is unsupported")
    try:
        data = json.loads(raw) if raw is not None else None
    except ValueError:
        data = None
    if not isinstance(data, dict):
        raise InventoryError("provider-unavailable: target metadata is unavailable")
    if platform == "github":
        rights = data.get("permissions")
        if (data.get("full_name") != target or not isinstance(data.get("private"), bool)
                or data.get("has_issues") is not True or not isinstance(rights, dict)
                or not any(rights.get(key) is True for key in ("push", "maintain", "admin"))):
            raise InventoryError("provider-unavailable: GitHub target or write permission is unknown")
        visibility = "private" if data["private"] else "public"
        identity = data.get("id")
    else:
        rights = data.get("permissions")
        if not isinstance(rights, dict):
            raise InventoryError("provider-unavailable: GitLab permission is unknown")
        web_url = data.get("web_url")
        address = urlparse(web_url) if isinstance(web_url, str) else None
        levels = [entry.get("access_level") for entry in rights.values()
                  if isinstance(entry, dict)]
        if (data.get("path_with_namespace") != target or
                data.get("visibility") not in ("private", "internal", "public") or
                data.get("issues_enabled") is not True or
                address is None or address.scheme not in ("http", "https") or
                address.netloc != host or address.path != "/" + target or
                address.query or address.fragment or
                not any(isinstance(level, int) and level >= 30 for level in levels)):
            raise InventoryError("provider-unavailable: GitLab target or write permission is unknown")
        visibility = data["visibility"]
        identity = data.get("id")
    if not isinstance(identity, int) or identity <= 0:
        raise InventoryError("provider-unavailable: target identity is unknown")
    facts = {"platform": platform, "host": host, "target": target,
             "targetId": identity, "visibility": visibility}
    if platform == "gitlab":
        facts["webScheme"] = address.scheme
    return facts


def _event_time(event_id: str) -> str | None:
    try:
        value = 0
        for character in event_id[:10]:
            value = value * 32 + BASE32.index(character)
        return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat()
    except (ValueError, OverflowError, OSError):
        return None


def render_body(snapshot: dict[str, Any]) -> str:
    """Publish each original action as readable text with a stable event marker."""
    project_id, issue_id = snapshot["projectId"], snapshot["issueId"]
    issue = snapshot["issue"]
    lines = [
        issue["description"] or "", "", "## Local source", "",
        "Project: " + project_id, "Issue: " + issue_id,
        "Current state: " + ("closed" if issue.get("isClosed") else "open"),
        "Snapshot SHA-256: " + snapshot["sourceDigest"], "",
        "<!-- " + ISSUE_MARKER + " " + project_id + "/" + issue_id + " -->",
        "", "## Local history (original order)", "",
    ]
    for item in snapshot["events"]:
        payload_text = json.dumps(item["payload"], ensure_ascii=False, sort_keys=True)
        fence = "`" * max(4, max((len(run) for run in re.findall(r"`+", payload_text)),
                                    default=0) + 1)
        lines.extend([
            "### " + item["action"] + " · " + item["id"], "",
            "Event time (from ID): " + str(_event_time(item["id"]) or "unknown"),
            "Epiq user ID: " + str(item.get("userId") or "unknown"), "",
            "Epiq author: " + str(item.get("actorName") or "unknown"), "",
            fence + "json", payload_text,
            fence, "", "<!-- " + EVENT_MARKER + " " + item["id"] + " -->", "",
        ])
    if snapshot["attachments"]:
        lines.extend(["## Attachments pending transfer", ""])
        for item in snapshot["attachments"]:
            lines.append("- " + item["hash"] + "." + item["ext"] +
                         " (" + str(item["bytes"]) + " bytes)")
        lines.append("")
    if snapshot["codeReferences"]:
        lines.extend(["## Code references", ""])
        for reference in snapshot["codeReferences"]:
            if snapshot.get("formatVersion", 1) == 1:
                lines.append("- " + reference["sha"] + ": source commit " +
                             ("reachable" if reference["sourceCommitReachable"] else "missing") +
                             "; target commit unverified")
            else:
                lines.append("- " + reference["sha"] +
                             ": source reachability checked in preview; target commit unverified")
        lines.append("")
    return "\n".join(lines)


def create_preview(project: Path, issue_id: str, runtime_dir: Path, platform: str,
                   host: str, target: str, visibility: str, output: Path,
                   runner: Callable[[list[str]], str | None] = _run,
                   legacy: bool = False) -> dict[str, Any]:
    """Write one private preview only after source and target are readable."""
    project = Path(project).resolve()
    output = Path(output)
    facts = target_facts(platform, host, target, runner)
    if visibility != facts["visibility"]:
        raise InventoryError("provider-unavailable: target visibility differs from request")
    snapshot = snapshot_issue(project, issue_id, runtime_dir, legacy=legacy)
    state_root = Path(state_worktree_status(project, snapshot["projectId"])["path"])
    destination = output.resolve(strict=False)
    if (any(root == destination or root in destination.parents
            for root in worktree_roots(project)) or
            state_root == destination or state_root in destination.parents or
            not output.parent.is_dir() or output.exists() or output.is_symlink()):
        raise InventoryError("preview-output-unsafe: output must be a new file outside Local source")
    limitations = ["target code references not verified",
                   "short or indirect code references may require manual review",
                   "issue-write API scope is not proven by read-only metadata"]
    if facts.get("webScheme") == "http":
        limitations.append("GitLab target uses HTTP; transport confidentiality is unavailable")
    if snapshot["attachments"]:
        limitations.append("attachment bytes are not transferred or verified; publication remains partial")
    if legacy:
        limitations.append("legacy format is for continuing an existing version 1 handoff only")
    preview = {
        "formatVersion": snapshot.get("formatVersion", 1), "state": "preview", "source": snapshot,
        "destination": facts, "title": snapshot["issue"]["title"],
        "body": render_body(snapshot),
        "limitations": limitations,
        "attachmentTransfer": "unverified" if snapshot["attachments"] else "none",
    }
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(preview, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    return {"state": "previewed", "projectId": snapshot["projectId"],
            "issueId": issue_id, "sourceDigest": snapshot["sourceDigest"],
            "visibility": visibility, "attachmentTransfer": preview["attachmentTransfer"]}
