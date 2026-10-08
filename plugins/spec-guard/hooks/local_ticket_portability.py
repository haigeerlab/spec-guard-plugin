"""Inspect the pinned Epiq Local ticket source without modifying it."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from local_ledger_runtime import default_runtime_dir, project_status
from local_ticket_inventory import (  # noqa: F401 -- re-exported for existing callers
    InventoryError, _event_lines, inventory_project, worktree_roots,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=(
        "inventory", "journal-candidates", "journal-bind-preview", "journal-bind", "archive", "verify", "restore", "handoff-preview",
        "handoff-publish",
    ))
    parser.add_argument("--project", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--candidate")
    parser.add_argument("--old-common-dir", type=Path)
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
    if args.command in ("inventory", "journal-candidates", "journal-bind-preview", "journal-bind", "archive", "restore", "handoff-preview",
                        "handoff-publish") and args.project is None:
        parser.error("--project is required")
    if args.command in ("archive", "handoff-preview", "journal-bind-preview") and args.output is None:
        parser.error("--output is required")
    if args.command in ("verify", "restore") and args.archive is None:
        parser.error("--archive is required")
    if args.command == "restore" and args.epiq_global_dir is None:
        parser.error("--epiq-global-dir is required")
    if args.confirm and args.command not in ("restore", "handoff-publish", "journal-bind"):
        parser.error("--confirm is only available with restore, handoff-publish or journal-bind")
    if args.command == "handoff-publish" and args.preview is None:
        parser.error("--preview is required")
    if args.command == "journal-bind" and args.preview is None:
        parser.error("--preview is required")
    if args.command == "handoff-preview" and any(value is None for value in (
            args.issue_id, args.platform, args.host, args.target, args.visibility)):
        parser.error("--issue-id, --platform, --host, --target and --visibility are required")
    if args.command == "journal-bind-preview" and (args.candidate is None or
            (args.old_common_dir is None) == (args.archive is None)):
        parser.error("--candidate and exactly one of --old-common-dir or --archive are required")
    if args.prove and args.command != "verify":
        parser.error("--prove is only available with verify")
    if args.legacy_format and args.command != "handoff-preview":
        parser.error("--legacy-format is only available with handoff-preview")
    try:
        if args.command == "inventory":
            payload = inventory_project(args.project)
        elif args.command == "journal-candidates":
            from local_ticket_journal import journal_candidate_status
            identity = project_status(args.project)
            if identity["state"] != "initialized":
                raise InventoryError("journal-source-unknown: Epiq project identity is unavailable")
            payload = journal_candidate_status(args.project, identity["projectId"])
        elif args.command == "journal-bind-preview":
            from local_ticket_bind import preview_binding
            payload = preview_binding(
                args.project, args.candidate, args.output, args.runtime_dir,
                old_common_dir=args.old_common_dir, archive=args.archive,
            )
        elif args.command == "journal-bind":
            from local_ticket_bind import bind_journal
            payload = bind_journal(args.project, args.preview, args.runtime_dir,
                                   confirm=args.confirm)
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
