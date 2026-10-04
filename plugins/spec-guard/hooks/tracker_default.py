"""Read the project's default tracker backend and resolve it against explicit arguments.

The default only pre-fills a preview.  It never decides a write, never changes an
existing item's binding, and is not an activation signal: `.agent/tracker.json` has
no bearing on whether the phase hook speaks.  An unusable document is `invalid`, never
`absent`, so a typo can never be read as "no default was configured".
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

RELATIVE_PATH = Path(".agent") / "tracker.json"
BACKENDS = ("github", "gitlab", "local")
TARGET_KEYS = {"github": ("host", "repo"), "gitlab": ("host", "projectId"),
               "local": ("projectId",)}
DOCUMENT_KEYS = ("version", "defaultBackend", "defaultTarget")
VERSION = 1

HOST = re.compile(r"[A-Za-z0-9][A-Za-z0-9.-]*\Z")
REPO_PART = re.compile(r"[A-Za-z0-9_.-]+\Z")
LOCAL_PROJECT_ID = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")

INVALID = "tracker-default-invalid"


@dataclass(frozen=True)
class DefaultResult:
    """`absent` (no file), `invalid` (unusable), or `configured` (backend + target)."""

    state: str
    backend: str | None = None
    target: dict[str, Any] | None = None
    diagnostic: str | None = None


@dataclass(frozen=True)
class Resolution:
    """`resolved` with the source that supplied it, or `target-unselected`."""

    state: str
    backend: str | None = None
    target: dict[str, Any] | None = None
    source: str | None = None
    diagnostic: str | None = None


def _host(value: Any) -> bool:
    return isinstance(value, str) and bool(HOST.fullmatch(value))


def normalize_target(backend: str, value: Any) -> dict[str, Any] | None:
    """Return the canonical target for `backend`, or None when the shape is wrong.

    The key set must match exactly: a missing or surplus key is a different shape, not
    a tolerable variation.  GitLab keeps a positive integer project id, matching the
    container `proposal_tracker_read` already uses, so there is only ever one form.
    """
    keys = TARGET_KEYS.get(backend)
    if keys is None or not isinstance(value, dict) or set(value) != set(keys):
        return None
    if backend == "github":
        repo = value["repo"]
        parts = repo.split("/") if isinstance(repo, str) else []
        if (not _host(value["host"]) or len(parts) != 2 or
                any(not REPO_PART.fullmatch(part) or part in (".", "..")
                    for part in parts)):
            return None
        return {"host": value["host"], "repo": repo}
    if backend == "gitlab":
        project_id = value["projectId"]
        if (not _host(value["host"]) or isinstance(project_id, bool) or
                not isinstance(project_id, int) or project_id <= 0):
            return None
        return {"host": value["host"], "projectId": project_id}
    project_id = value["projectId"]
    if not isinstance(project_id, str) or not LOCAL_PROJECT_ID.fullmatch(project_id):
        return None
    return {"projectId": project_id}


def read_default(root: Path) -> DefaultResult:
    """Read `.agent/tracker.json`.  Only a missing file is `absent`."""
    try:
        text = (Path(root) / RELATIVE_PATH).read_text(encoding="utf-8")
    except FileNotFoundError:
        return DefaultResult("absent")
    except OSError:
        return DefaultResult("invalid", diagnostic=INVALID)
    try:
        document = json.loads(text)
    except ValueError:
        return DefaultResult("invalid", diagnostic=INVALID)
    if (not isinstance(document, dict) or set(document) != set(DOCUMENT_KEYS) or
            document["version"] != VERSION or
            document["defaultBackend"] not in BACKENDS):
        return DefaultResult("invalid", diagnostic=INVALID)
    backend = document["defaultBackend"]
    target = normalize_target(backend, document["defaultTarget"])
    if target is None:
        return DefaultResult("invalid", diagnostic=INVALID)
    return DefaultResult("configured", backend=backend, target=target)


def resolve(explicit_backend: str | None, explicit_target: dict[str, Any] | None,
            default: DefaultResult) -> Resolution:
    """Combine explicit arguments with the project default.

    An explicit value that differs from the default is not a conflict: the default is a
    pre-fill, so the caller is simply overriding it.  Detecting a write that contradicts
    an item's recorded binding belongs to the writing module, not here.
    """
    if explicit_backend is not None and explicit_backend not in BACKENDS:
        return Resolution("target-unselected", diagnostic="explicit-target-invalid")
    if explicit_target is not None:
        if explicit_backend is None:
            return Resolution("target-unselected", diagnostic="backend-unselected")
        target = normalize_target(explicit_backend, explicit_target)
        if target is None:
            return Resolution("target-unselected", diagnostic="explicit-target-invalid")
        return Resolution("resolved", explicit_backend, target, source="explicit")
    if default.state == "invalid":
        return Resolution("target-unselected", diagnostic=INVALID)
    if default.state != "configured":
        return Resolution("target-unselected", diagnostic="tracker-default-absent")
    if explicit_backend is None:
        return Resolution("resolved", default.backend, default.target,
                          source="project-default")
    if explicit_backend != default.backend:
        return Resolution("target-unselected",
                          diagnostic="tracker-default-backend-differs")
    return Resolution("resolved", default.backend, default.target,
                      source="project-default-target")


def as_json(result: DefaultResult | Resolution) -> dict[str, Any]:
    """Safe JSON: state, backend, target, source and a stable diagnostic code only.

    No filesystem paths, document text or raw parse errors ever reach the output.
    """
    fields = ("state", "backend", "target", "source", "diagnostic")
    return {name: getattr(result, name) for name in fields
            if getattr(result, name, None) is not None}
