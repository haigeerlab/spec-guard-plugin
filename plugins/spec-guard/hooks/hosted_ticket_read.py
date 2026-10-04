"""Classify one hosted ticket identity after complete read-only enumeration."""
from __future__ import annotations

import argparse
import json
import re
from typing import Any

from hosted_ticket_provider import GitHubIssues, GitLabIssues, HostedTicketError


REQUEST_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{2,127}\Z")
MARKER = "spec-guard-hosted-ticket:v1"


def inspect_ticket(provider: Any, visibility: str, request_id: str,
                   title: str) -> dict[str, Any]:
    if not REQUEST_ID.fullmatch(request_id) or not title.strip():
        return {"state": "unknown", "diagnostic": "request-invalid"}
    try:
        target = provider.target_facts()
        if target.get("visibility") != visibility:
            return {"state": "unknown", "diagnostic": "target-visibility-changed"}
        listing = provider.list_issues()
        if listing.get("complete") is not True or not isinstance(listing.get("issues"), list):
            return {"state": "unknown", "diagnostic": "listing-incomplete"}
        issues = listing["issues"]
        marker = "<!-- " + MARKER + " " + request_id + " -->"
        matches, displaced, candidates = [], [], []
        for item in issues:
            if (not isinstance(item, dict) or not isinstance(item.get("body"), str) or
                    not isinstance(item.get("title"), str) or
                    not isinstance(item.get("id"), int) or not isinstance(item.get("url"), str)):
                return {"state": "unknown", "diagnostic": "listing-incomplete"}
            lines = item["body"].splitlines()
            if marker in item["body"]:
                (matches if lines.count(marker) == 1 and lines[-1] == marker
                 else displaced).append(item)
            elif item["title"].casefold().strip() == title.casefold().strip():
                candidates.append(item)
        summary = {"target": target, "scannedCount": len(issues)}
        if displaced or len(matches) > 1:
            return {**summary, "state": "conflict", "diagnostic": "marker-ambiguous",
                    "candidates": displaced + matches}
        if matches:
            return {**summary, "state": "found", "issue": matches[0]}
        if candidates:
            return {**summary, "state": "conflict", "diagnostic": "root-cause-candidate",
                    "candidates": candidates}
        return {**summary, "state": "absent", "rootCauseReviewRequired": True}
    except HostedTicketError as error:
        diagnostic = str(error)
        return {"state": "unknown", "diagnostic": diagnostic}


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only hosted Issue identity check")
    parser.add_argument("--platform", choices=("github", "gitlab"), required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--visibility", choices=("public", "internal", "private"),
                        required=True)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--title", required=True)
    args = parser.parse_args()
    try:
        provider = (GitHubIssues(args.host, args.target) if args.platform == "github"
                    else GitLabIssues(args.host, args.target))
        result = inspect_ticket(provider, args.visibility, args.request_id, args.title)
    except HostedTicketError as error:
        result = {"state": "unknown", "diagnostic": str(error)}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
