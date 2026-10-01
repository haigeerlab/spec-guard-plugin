"""Inspect the pinned Epiq Local ticket source without modifying it."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Sequence

from local_ledger_runtime import (
    PACKAGE_VERSION, STATE_BRANCH, default_runtime_dir,
    project_status, state_worktree_status,
)


MEDIA_NAME = re.compile(r"^([a-f0-9]{64})\.(png|jpg|gif|webp)$")


class InventoryError(ValueError):
    """A source cannot be treated as a complete Local ticket ledger."""


def _git(project: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(project), *arguments],
        check=False, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise InventoryError("source-unknown: unable to read Git state")
    return result.stdout.strip()


def worktree_roots(project: Path) -> list[Path]:
    """Return every registered checkout sharing this project's Git common dir."""
    listing = _git(project, "worktree", "list", "--porcelain", "-z")
    roots = []
    for record in listing.split("\0"):
        if record.startswith("worktree "):
            path = Path(record[len("worktree "):])
            if not path.is_absolute():
                raise InventoryError("source-unknown: Git worktree path is invalid")
            roots.append(path.resolve())
    if not roots or Path(project).resolve() not in roots:
        raise InventoryError("source-unknown: Git worktree list is incomplete")
    return roots


def _directory(path: Path) -> None:
    if path.is_symlink() or not path.is_dir():
        raise InventoryError("source-unknown: required Epiq directory is unsafe or absent")


def _read_file(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise InventoryError("source-unknown: Epiq file is unsafe or absent")
    try:
        return path.read_bytes()
    except OSError as error:
        raise InventoryError("source-unknown: Epiq file is unreadable") from error


def _file_record(path: Path, state_root: Path, data: bytes) -> dict[str, Any]:
    return {
        "path": path.relative_to(state_root).as_posix(),
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _event_lines(data: bytes, file_name: str) -> list[dict[str, Any]]:
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise InventoryError("invalid-event-log: non-UTF-8 JSONL") from error
    events = []
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError as error:
            raise InventoryError(
                f"invalid-event-log: {file_name}:{number} is not JSON"
            ) from error
        if not isinstance(value, dict) or value.get("v") != 1:
            raise InventoryError(f"invalid-event-log: {file_name}:{number} has invalid version")
        identity = value.get("id")
        if (not isinstance(identity, list) or len(identity) != 2
                or not isinstance(identity[0], str) or not identity[0]
                or (identity[1] is not None and
                    (not isinstance(identity[1], str) or not identity[1]))):
            raise InventoryError(f"invalid-event-log: {file_name}:{number} has invalid ID")
        actions = set(value) - {"v", "id"}
        if len(actions) != 1 or not isinstance(value[next(iter(actions))], dict):
            raise InventoryError(f"invalid-event-log: {file_name}:{number} has invalid action")
        events.append(value)
    return events


def _media_kind(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def inventory_project(project: Path) -> dict[str, Any]:
    """Report every event/media file and reject gaps before an archive is attempted."""
    project = Path(project).resolve()
    if _git(project, "rev-parse", "--show-toplevel") != str(project):
        raise InventoryError("source-unknown: project must be a Git worktree root")
    _directory(project / ".epiq")
    identity = project_status(project)
    if identity["state"] != "initialized":
        raise InventoryError("source-unknown: Epiq project identity is unavailable")
    owner = state_worktree_status(project, identity["projectId"])
    if owner["state"] != "owned":
        raise InventoryError("source-unknown: Epiq state worktree is not owned")
    state_root = Path(owner["path"])
    _directory(state_root / ".epiq")
    event_dir = state_root / ".epiq" / "events"
    media_dir = state_root / ".epiq" / "media"
    _directory(event_dir)
    if media_dir.exists() or media_dir.is_symlink():
        _directory(media_dir)
    branch_head = _git(project, "rev-parse", "refs/heads/" + STATE_BRANCH)
    if _git(state_root, "rev-parse", "HEAD") != branch_head:
        raise InventoryError("source-unknown: state worktree HEAD differs from branch")

    files: list[dict[str, Any]] = []
    by_id: dict[str, tuple[str, str]] = {}
    attachments: dict[str, int] = {}
    event_files = sorted(event_dir.iterdir())
    if not event_files:
        raise InventoryError("invalid-event-log: initialized ledger has no events")
    for path in event_files:
        if not path.name.endswith(".jsonl"):
            raise InventoryError("invalid-event-log: unexpected file in events directory")
        actor = path.name.split(".", 1)[0].split("~pending", 1)[0].lower()
        if not actor:
            raise InventoryError("invalid-event-log: event file has no actor")
        data = _read_file(path)
        files.append(_file_record(path, state_root, data))
        for value in _event_lines(data, path.name):
            event_id = value["id"][0]
            canonical = json.dumps(value, sort_keys=True, separators=(",", ":"))
            previous = by_id.setdefault(event_id, (actor, canonical))
            if previous != (actor, canonical):
                raise InventoryError("duplicate-event-conflict: event ID has different content")
            attachment = value.get("add.issue.attachment")
            if attachment is not None:
                media_hash = attachment.get("hash")
                extension = attachment.get("ext")
                size = attachment.get("bytes")
                if (not isinstance(media_hash, str) or not isinstance(extension, str)
                        or not isinstance(size, int) or size <= 0
                        or not MEDIA_NAME.fullmatch(media_hash + "." + extension)):
                    raise InventoryError("invalid-event-log: malformed attachment reference")
                name = media_hash + "." + extension
                if name in attachments and attachments[name] != size:
                    raise InventoryError("invalid-event-log: attachment size conflict")
                attachments[name] = size

    media_sizes: dict[str, int] = {}
    if media_dir.exists():
        for path in sorted(media_dir.iterdir()):
            match = MEDIA_NAME.fullmatch(path.name)
            if match is None:
                raise InventoryError("invalid-media: unexpected media file name")
            data = _read_file(path)
            if hashlib.sha256(data).hexdigest() != match.group(1) or _media_kind(data) != match.group(2):
                raise InventoryError("invalid-media: content does not match file name")
            media_sizes[path.name] = len(data)
            files.append(_file_record(path, state_root, data))
    for name, expected_size in attachments.items():
        if name not in media_sizes:
            raise InventoryError("missing-media: attachment blob is absent")
        if media_sizes[name] != expected_size:
            raise InventoryError("invalid-media: attachment byte count differs from event")
    return {
        "state": "ready", "projectId": identity["projectId"],
        "epiqVersion": PACKAGE_VERSION, "stateBranch": STATE_BRANCH,
        "stateHead": branch_head, "eventFileCount": len(event_files),
        "eventIds": sorted(by_id), "mediaCount": len(media_sizes), "files": files,
        "projectConfigSha256": hashlib.sha256(
            _read_file(project / ".epiq" / "project.json")
        ).hexdigest(),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=(
        "inventory", "journal-candidates", "archive", "verify", "restore", "handoff-preview",
        "handoff-publish",
    ))
    parser.add_argument("--project", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--preview", type=Path)
    parser.add_argument("--epiq-global-dir", type=Path)
    parser.add_argument("--issue-id")
    parser.add_argument("--platform", choices=("github", "gitlab"))
    parser.add_argument("--host")
    parser.add_argument("--target")
    parser.add_argument("--visibility", choices=("public", "internal", "private"))
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--prove", action="store_true")
    parser.add_argument("--legacy-format", action="store_true")
    parser.add_argument("--runtime-dir", type=Path, default=default_runtime_dir())
    parser.add_argument("--format", choices=("json",), default="json")
    args = parser.parse_args(argv)
    if args.command in ("inventory", "journal-candidates", "archive", "restore", "handoff-preview",
                        "handoff-publish") and args.project is None:
        parser.error("--project is required")
    if args.command in ("archive", "handoff-preview") and args.output is None:
        parser.error("--output is required")
    if args.command in ("verify", "restore") and args.archive is None:
        parser.error("--archive is required")
    if args.command == "restore" and args.epiq_global_dir is None:
        parser.error("--epiq-global-dir is required")
    if args.confirm and args.command not in ("restore", "handoff-publish"):
        parser.error("--confirm is only available with restore or handoff-publish")
    if args.command == "handoff-publish" and args.preview is None:
        parser.error("--preview is required")
    if args.command == "handoff-preview" and any(value is None for value in (
            args.issue_id, args.platform, args.host, args.target, args.visibility)):
        parser.error("--issue-id, --platform, --host, --target and --visibility are required")
    if args.prove and args.command != "verify":
        parser.error("--prove is only available with verify")
    if args.legacy_format and args.command != "handoff-preview":
        parser.error("--legacy-format is only available with handoff-preview")
    try:
        if args.command == "inventory":
            payload = inventory_project(args.project)
        elif args.command == "journal-candidates":
            from local_ticket_journal import discover_journal_candidates
            identity = project_status(args.project)
            if identity["state"] != "initialized":
                raise InventoryError("journal-source-unknown: Epiq project identity is unavailable")
            payload = discover_journal_candidates(args.project, identity["projectId"])
        elif args.command == "archive":
            from local_ticket_archive import archive_project
            payload = archive_project(args.project, args.output)
        elif args.command == "restore":
            from local_ticket_restore import restore_archive
            payload = restore_archive(
                args.archive, args.project, args.epiq_global_dir,
                args.runtime_dir, confirm=args.confirm,
            )
        elif args.command == "handoff-preview":
            from local_ticket_preview import create_preview
            payload = create_preview(
                args.project, args.issue_id, args.runtime_dir, args.platform,
                args.host, args.target, args.visibility, args.output,
                legacy=args.legacy_format,
            )
        elif args.command == "handoff-publish":
            from local_ticket_github import GitHubHandoff
            from local_ticket_gitlab import GitLabHandoff
            from local_ticket_publish import publish_preview
            if args.preview.is_symlink() or not args.preview.is_file():
                raise InventoryError("preview-invalid: preview file is absent or unsafe")
            preview = json.loads(args.preview.read_text(encoding="utf-8"))
            if not isinstance(preview, dict) or not isinstance(preview.get("destination"), dict):
                raise InventoryError("preview-invalid: destination is missing")
            destination = preview.get("destination", {})
            if destination.get("platform") == "github":
                provider = GitHubHandoff(destination["host"], destination["target"])
            elif destination.get("platform") == "gitlab":
                provider = GitLabHandoff(destination["host"], destination["target"])
            else:
                raise InventoryError("preview-invalid: destination platform is unsupported")
            payload = publish_preview(
                preview, args.project, args.runtime_dir, provider, confirm=args.confirm,
            )
        else:
            if args.prove:
                from local_ticket_restore import prove_restore
                payload = prove_restore(args.archive, args.runtime_dir)
            else:
                from local_ticket_archive import verify_archive
                payload = verify_archive(args.archive)
        code = 0
    except (InventoryError, OSError, ValueError, KeyError, TypeError) as error:
        payload = {"state": "invalid", "diagnostic": str(error)}
        code = 1
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
