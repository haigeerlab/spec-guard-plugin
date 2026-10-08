"""Explicit comment and post-delivery close entry for hosted Issues.

This is the CLI. The operations live in `hosted_ticket_actions.py` -- plural, one
letter apart. Same split as `hosted_ticket.py` (CLI) over `hosted_ticket_write.py`,
but with a name that greps and autocompletes almost identically, so check which of
the two you have open before editing. Renaming it is not free: dated audit records
under `docs/reports/` cite the plural file by line number.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from hosted_ticket import INTENT_ROOT
from hosted_ticket_actions import (close_issue, make_close_preview,
                                   make_comment_preview, publish_comment)
from hosted_ticket_provider import GitHubIssues, GitLabIssues, HostedTicketError, public_result


def _read(path: Path) -> str:
    if path.is_symlink() or path.stat().st_size > 100_000:
        raise HostedTicketError("content-invalid: file is unsafe or too large")
    return path.read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview or perform one hosted Issue action")
    parser.add_argument("action", choices=("comment-preview", "comment-publish",
                                           "close-preview", "close-publish"))
    parser.add_argument("--platform", choices=("github", "gitlab"), required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--visibility", choices=("public", "internal", "private"),
                        required=True)
    parser.add_argument("--issue-id", type=int, required=True)
    parser.add_argument("--event-id")
    parser.add_argument("--body-file", type=Path)
    parser.add_argument("--delivery-id", type=int)
    parser.add_argument("--coverage-complete", action="store_true")
    parser.add_argument("--validation-file", type=Path)
    parser.add_argument("--expected-digest")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    try:
        provider = (GitHubIssues(args.host, args.target) if args.platform == "github"
                    else GitLabIssues(args.host, args.target))
        target = provider.target_facts()
        if target["visibility"] != args.visibility:
            result = {"state": "unknown", "diagnostic": "target-visibility-changed"}
        elif args.action.startswith("comment"):
            if not args.event_id or not args.body_file:
                result = {"state": "preview-invalid", "diagnostic": "comment-input-missing"}
            else:
                preview = make_comment_preview(provider, args.issue_id, args.event_id,
                                               _read(args.body_file))
                if args.action == "comment-preview" or preview["state"] != "preview":
                    result = preview
                elif not args.confirm or not args.expected_digest:
                    result = {"state": "confirmation-required"}
                elif preview["digest"] != args.expected_digest:
                    result = {"state": "preview-stale"}
                else:
                    result = publish_comment(preview, provider, INTENT_ROOT, confirm=True)
        elif not args.delivery_id or not args.validation_file:
            result = {"state": "preview-invalid", "diagnostic": "delivery-input-missing"}
        else:
            preview = make_close_preview(provider, args.issue_id, args.delivery_id,
                                         args.coverage_complete,
                                         _read(args.validation_file))
            if args.action == "close-preview" or preview["state"] != "preview":
                result = preview
            elif not args.confirm or not args.expected_digest:
                result = {"state": "confirmation-required"}
            elif preview["digest"] != args.expected_digest:
                result = {"state": "preview-stale"}
            else:
                result = close_issue(preview, provider, confirm=True)
    except (HostedTicketError, OSError, UnicodeError) as error:
        diagnostic = str(error) if isinstance(error, HostedTicketError) else "input-unavailable"
        result = {"state": "unknown", "diagnostic": diagnostic}
    print(json.dumps(public_result(result), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
