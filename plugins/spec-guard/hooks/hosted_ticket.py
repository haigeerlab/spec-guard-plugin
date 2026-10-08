"""Explicit, single-Issue preview and publish entry for hosted tickets."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from hosted_ticket_provider import GitHubIssues, GitLabIssues, HostedTicketError, public_result
from hosted_ticket_write import draft_preview, make_preview, publish_preview


INTENT_ROOT = Path.home() / ".local" / "state" / "spec-guard" / "hosted-ticket-intents"


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview or publish one hosted Issue")
    parser.add_argument("action", choices=("preview", "publish"))
    parser.add_argument("--platform", choices=("github", "gitlab"), required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--visibility", choices=("public", "internal", "private"),
                        required=True)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--body-file", type=Path, required=True)
    parser.add_argument("--expected-digest")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--root-cause-reviewed", action="store_true")
    args = parser.parse_args()
    try:
        if args.body_file.is_symlink() or args.body_file.stat().st_size > 100_000:
            raise HostedTicketError("content-invalid: body file is unsafe or too large")
        body = args.body_file.read_text(encoding="utf-8")
        provider = (GitHubIssues(args.host, args.target) if args.platform == "github"
                    else GitLabIssues(args.host, args.target))
        if args.action == "preview":
            result = make_preview(provider, args.visibility, args.request_id,
                                  args.title, body)
        elif not args.expected_digest or not args.confirm:
            result = {"state": "confirmation-required",
                      "diagnostic": "publish needs preview digest and --confirm"}
        else:
            target = provider.target_facts()
            if target["visibility"] != args.visibility:
                result = {"state": "unknown", "diagnostic": "target-visibility-changed"}
            else:
                preview = draft_preview(target, args.request_id, args.title, body)
                if preview.get("digest") != args.expected_digest:
                    result = {"state": "preview-stale"}
                else:
                    result = publish_preview(preview, provider, INTENT_ROOT,
                                             confirm=args.confirm,
                                             root_cause_reviewed=args.root_cause_reviewed)
    except (HostedTicketError, OSError, UnicodeError) as error:
        diagnostic = str(error) if isinstance(error, HostedTicketError) else "input-unavailable"
        result = {"state": "unknown", "diagnostic": diagnostic}
    print(json.dumps(public_result(result), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
