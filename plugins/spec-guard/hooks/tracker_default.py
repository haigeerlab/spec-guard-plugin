"""Read the project's default tracker backend and resolve it against explicit arguments.

The default only pre-fills a preview.  It never decides a write, never changes an
existing item's binding, and is not an activation signal: `.agent/tracker.json` has
no bearing on whether the phase hook speaks.  An unusable document is `invalid`, never
`absent`, so a typo can never be read as "no default was configured".
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
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


def render(backend: str, target: dict[str, Any]) -> str:
    """The canonical on-disk text, so a rewrite with the same values is a no-op diff."""
    document = {"version": VERSION, "defaultBackend": backend, "defaultTarget": target}
    return json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _target_from_arguments(args: argparse.Namespace) -> dict[str, Any] | None:
    if args.backend == "github":
        return {"host": args.host, "repo": args.repo}
    if args.backend == "gitlab":
        project_id = args.project_id
        if not isinstance(project_id, str) or not project_id.isdigit():
            return None
        return {"host": args.host, "projectId": int(project_id)}
    return {"projectId": args.project_id}


def _write_atomic(path: Path, text: str) -> None:
    try:
        mode = path.stat().st_mode & 0o777
    except FileNotFoundError:
        mode = 0o644
    temporary = path.with_name(path.name + "." + str(os.getpid()) + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.chmod(temporary, mode)
    os.replace(temporary, path)


def _set(args: argparse.Namespace) -> int:
    """Preview the document change; only `--confirm` writes, and only this one file."""
    target = _target_from_arguments(args)
    target = None if target is None else normalize_target(args.backend, target)
    if target is None:
        print("target-invalid: the target does not match the %s shape" % args.backend)
        return 2
    path = Path(args.project) / RELATIVE_PATH
    try:
        before = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        before = ""
    except OSError:
        print("tracker-default-unreadable: the existing document cannot be read")
        return 2
    after = render(args.backend, target)
    diff = "".join(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile=str(RELATIVE_PATH) + " (current)",
        tofile=str(RELATIVE_PATH) + " (proposed)"))
    print(diff if diff else "no change: the project default already has these values")
    if not args.confirm:
        print("\npreview only; nothing was written. Re-run with --confirm to apply.")
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_atomic(path, after)
    print("\nwrote %s" % RELATIVE_PATH)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Show or set the project default tracker backend. The default only "
                    "pre-fills a preview; it never authorizes or performs a write.")
    commands = parser.add_subparsers(dest="command", required=True)

    show = commands.add_parser("show", help="read-only")
    show.add_argument("--project", default=".")
    show.add_argument("--format", choices=("json", "text"), default="json")

    setter = commands.add_parser("set", help="preview, and with --confirm write")
    setter.add_argument("--project", default=".")
    setter.add_argument("--backend", choices=BACKENDS, required=True)
    setter.add_argument("--host")
    setter.add_argument("--repo")
    setter.add_argument("--project-id")
    setter.add_argument("--confirm", action="store_true")

    args = parser.parse_args()
    if args.command == "set":
        return _set(args)
    result = read_default(Path(args.project))
    if args.format == "json":
        print(json.dumps(as_json(result), ensure_ascii=False, sort_keys=True))
    elif result.state == "configured":
        print("%s %s" % (result.backend,
                         json.dumps(result.target, ensure_ascii=False, sort_keys=True)))
    else:
        print(result.state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
