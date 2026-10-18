"""Record where the review of a module's Spec or Plan stands, by one marker line (review-approval-marker).

`pending` says the file is waiting for the user's review; `approved` records an approval the user
gave in the conversation, or relayed in the session-protocol format by a registered decision hub (hub-relayed-approval).  A Spec approval carries the digest of the Spec's text, so a later edit
reads back as `revised`.  The states are decided by `module_stage` alone; this script only adds or
replaces the marker line, previews the change, and writes only with `--confirm`.  It cannot check
that the user approved anything: the marker is a record for later sessions, not a source of authority.
"""
from __future__ import annotations

import argparse
import difflib
from pathlib import Path

from capability_map import MODULE_ID, MapError, parse_map
from module_stage import (REVIEW_APPROVED, REVIEW_PENDING, file_review_state, review_approved_line, review_digest,
                          review_marker_lines, review_state)
from tracker_default import _write_atomic


def _with_marker(text: str, marker: str) -> str:
    """The text with `marker` as its one marker line: replaced in place, else put after the title line."""
    lines = text.splitlines(keepends=True)
    found = review_marker_lines(text)
    if found:
        line = lines[found[0]]
        lines[found[0]] = marker + line[len(line.rstrip("\r\n")):]
        return "".join(lines)
    if lines and lines[0].startswith("#"):
        return lines[0] + "\n" + marker + "\n" + "".join(lines[1:])
    return marker + "\n\n" + text


def _marked(text: str, kind: str, state: str) -> str:
    if state == "pending":
        return _with_marker(text, REVIEW_PENDING)
    if kind == "plan":
        return _with_marker(text, REVIEW_APPROVED)
    # The digest leaves the marker line out, so it is the same before and after the real line goes in.
    return _with_marker(text, review_approved_line(review_digest(_with_marker(text, REVIEW_PENDING))))


def main() -> int:
    parser = argparse.ArgumentParser(description="Mark a module's Spec or Plan review state (preview unless --confirm).")
    parser.add_argument("--project", default=".")
    parser.add_argument("--module", required=True)
    parser.add_argument("--target", required=True, choices=["spec", "plan", "both"])
    parser.add_argument("--state", required=True, choices=["pending", "approved"])
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    root, module_id = Path(args.project), args.module
    if not MODULE_ID.fullmatch(module_id):
        print("not-a-module-id: use the id from the capability map")
        return 2
    try:
        parsed = parse_map(root / "spec" / "CAPABILITY-MAP.md")
    except (OSError, MapError, UnicodeError):
        print("map-unreadable: run /spec-guard:verify-artifacts first")
        return 2
    if module_id not in [row.module_id for row in parsed.rows]:
        print("not-in-map: %s is not in spec/CAPABILITY-MAP.md" % module_id)
        return 2
    relative = {"spec": "spec/%s.md" % module_id, "plan": "tasks/%s/plan.md" % module_id}
    kinds = ["spec", "plan"] if args.target == "both" else [args.target]
    before = {}
    for kind in kinds:
        path = root / relative[kind]
        if not path.is_file():
            print("file-missing: %s does not exist" % relative[kind])
            return 2
        try:
            before[kind] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            print("file-unreadable: %s could not be read" % relative[kind])
            return 2
        if review_state(before[kind], kind) == "invalid":
            print("marker-invalid: %s has more than one review marker or a malformed one; fix it by hand "
                  "(run /spec-guard:verify-artifacts to see it)" % relative[kind])
            return 2
    unmarked_spec = False
    if args.state == "approved" and kinds == ["plan"]:
        # No marker means the Spec is not tracked, which must not block anything; a Spec that is
        # tracked and not approved does.
        spec_state = file_review_state(root / relative["spec"], "spec")
        unmarked_spec = spec_state == "none"
        if spec_state not in ("approved", "none"):
            print("spec-not-approved: %s reads as %s. Approving a Spec needs the user's own explicit approval of "
                  "that Spec; the Plan's approval or an earlier \"continue\" does not cover it. Show the user the "
                  "Spec first, then use --target both if they approve both." % (relative["spec"], spec_state))
            return 2
    after = {kind: _marked(before[kind], kind, args.state) for kind in kinds}
    changed = [kind for kind in kinds if after[kind] != before[kind]]
    for kind in kinds:
        if kind not in changed:
            print("%s: already %s; nothing to change" % (relative[kind], args.state))
            continue
        print("".join(difflib.unified_diff(before[kind].splitlines(keepends=True), after[kind].splitlines(keepends=True),
                                           fromfile=relative[kind] + " (current)",
                                           tofile=relative[kind] + " (proposed)")))
    if "spec" in kinds:
        print("Spec digest: %s (text of %s without the marker line)" % (review_digest(after["spec"]), relative["spec"]))
    print("review state after: " + ", ".join("%s %s" % (relative[kind], review_state(after[kind], kind))
                                             for kind in kinds))
    if unmarked_spec:
        print("%s has no review marker; this records the Plan's approval only and leaves the Spec as it is."
              % relative["spec"])
    if args.state == "approved":
        # review-handoff-content: an approval only means something if the user saw what they approved.  This cannot
        # be checked here, so it is a reminder and never a refusal.
        for kind in kinds:
            print("%s: %d line(s)" % (relative[kind], len(before[kind].splitlines())))
        print("Before --confirm, make sure the user has seen the content of %s in the conversation (or in the message "
              "sent to the hub) -- its points, or the whole text when it is short. If they were given only a link or a one-line summary, that is not a "
              "review: show the content first and ask again." % " and ".join(relative[kind] for kind in kinds))
        print("`approved` records the user's explicit approval: given in this conversation, or relayed by the registered "
              "decision hub in the session-protocol format, with the hub's item number and the user's own words. Do not "
              "write it to clear a phase hint; the marker is a record for later sessions, not a source of authority.")
    if not changed:
        return 0
    if not args.confirm:
        print("\npreview only; nothing was written. Re-run with --confirm to apply.")
        return 0
    for kind in changed:
        path = root / relative[kind]
        try:
            _write_atomic(path, after[kind])
        except OSError:
            print("file-unwritable: %s could not be written" % relative[kind])
            return 2
        if review_state(path.read_text(encoding="utf-8"), kind) != args.state:
            print("readback-mismatch: %s does not read back as %s" % (relative[kind], args.state))
            return 2
    print("\nmarked %s: %s" % (args.state, ", ".join(relative[kind] for kind in changed)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
