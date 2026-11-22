"""Record where the review of a module's Spec or Plan stands, by one marker line (review-approval-marker).

`pending` says the file is waiting for the user's review; `approved` records an approval the user
gave -- where approvals may come from follows the installed collaboration plugin, else only the current conversation
(review-residual-fixes).  A Spec approval carries the digest of the Spec's text, so a later edit
reads back as `revised`.  The states are decided by `module_stage` alone; this script only adds or
replaces the marker line, previews the change, and writes only with `--confirm`.  It cannot check
that the user approved anything: the marker is a record for later sessions, not a source of authority.

`--target acceptance` (codex-final-acceptance) is separate: for a merge=auto module it records Codex's final
acceptance of HEAD -- final review, a non-author's check evidence and HEAD agreeing -- as a JSON file in the git
directory, so recording it does not move HEAD.
"""
from __future__ import annotations

import argparse
import datetime
import difflib
import hashlib
import json
from pathlib import Path

from capability_map import MODULE_ID, MapError, parse_map
from codex_review import inspect as inspect_report, inspect_check, inspect_final
from module_stage import (EXTERNAL_REVIEW_HEADING, _git, acceptance_path, REVIEW_APPROVED, REVIEW_PENDING, codex_rounds, codex_route, effective_review,
                          file_review_state,
                          review_approved_line, review_body, review_codex_digest, review_codex_line, review_digest, review_marker_lines,
                          review_state, spec_baseline)
from tracker_default import _write_atomic


def _eol(line: str) -> str:
    """The line ending a line carries, or a plain newline when it carries none (files are read with universal newlines)."""
    return line[len(line.rstrip("\r\n")):] or "\n"


def _with_marker(text: str, marker: str) -> str:
    """The text with `marker` as its one marker line: replaced in place, else put after the title line.

    review-marker-blank-line: the marker line always gets a blank line on both sides (none before it at the start of
    the file, none after it at the end), as Markdown formatters such as oxfmt require; blank lines already there are
    kept and none is added twice. The caller computes the Spec digest from this text, so the digest includes them.
    """
    lines = text.splitlines(keepends=True)
    found = review_marker_lines(text)
    if found:
        at = found[0]
        lines[at] = marker + lines[at][len(lines[at].rstrip("\r\n")):]
    elif lines and lines[0].startswith("#"):
        eol = _eol(lines[0])
        lines[0] = lines[0].rstrip("\r\n") + eol
        lines[1:1] = [eol, marker + eol]
        at = 2
    else:
        eol = _eol(lines[0]) if lines else "\n"
        lines[0:0] = [marker + eol, eol]
        at = 0
    eol = _eol(lines[at])
    if at + 1 < len(lines) and lines[at + 1].strip():
        lines.insert(at + 1, eol)
    if at > 0 and lines[at - 1].strip():
        lines.insert(at, eol)
    return "".join(lines)


def _marked(text: str, kind: str, state: str) -> str:
    if state == "pending":
        return _with_marker(text, REVIEW_PENDING)
    if kind == "plan":
        return _with_marker(text, REVIEW_APPROVED)
    # The digest leaves the marker line out, so it is the same before and after the real line goes in.
    return _with_marker(text, review_approved_line(review_digest(_with_marker(text, REVIEW_PENDING))))


ROUND_CAP = 2  # codex-approval: blocking rounds before the file goes to the user


def _with_round(text: str, line: str) -> str:
    """The text with `line` appended to its external review section, made at the end when there is none."""
    lines = text.splitlines(keepends=True)
    heading = next((index for index, item in enumerate(lines) if EXTERNAL_REVIEW_HEADING.match(item.rstrip("\r\n"))), None)
    if heading is None:
        body = text if text.endswith("\n") or not text else text + "\n"
        return body + "\n## 外部审查意见\n\n" + line + "\n"
    end = next((index for index in range(heading + 1, len(lines)) if lines[index].startswith("## ")), len(lines))
    while end > heading + 1 and not lines[end - 1].strip():
        end -= 1
    insert = [line + "\n"]
    if end == heading + 1:
        insert = ["\n"] + insert
    elif not lines[end - 1].endswith("\n"):
        lines[end - 1] += "\n"
    lines[end:end] = insert
    return "".join(lines)


def _codex(root: Path, relative: str, kind: str, state: str, report: str | None, text: str):
    """codex-approval: (new text, message) or (None, refusal) for a Codex round from a delegate report."""
    if report is None:
        return None, "review-missing: --state %s needs --review <the /delegate:review JSON saved to a file>" % state
    found = inspect_report(report, root, relative)
    if found["status"] != "ok":
        return None, "report-invalid: %s" % found["reason"]
    rounds = codex_rounds(text)
    if sum(1 for _, blocking in rounds if blocking) >= ROUND_CAP and rounds[-1][1]:
        return None, ("codex-rounds-exhausted: %s already had two rounds with blocking findings; hand them to the user, "
                      "who approves it with --state approved or sends it back" % relative)
    if state == "codex-approved" and found["blocking"]:
        return None, ("codex-blocking: the report has %d blocking finding(s); fix them and review again, or record this "
                      "round with --state codex-reviewed" % found["blocking"])
    line = "<!-- spec-guard: codex-review round=%d blocking=%d sha256=%s -->" % (
        len(rounds) + 1, found["blocking"], found["sha256"][:12])
    updated = _with_round(text, line)
    if state == "codex-approved":
        updated = _with_marker(updated, review_codex_line(review_codex_digest(_with_marker(updated, REVIEW_PENDING))))
    note = ("round %d: %d blocking, %d suggestion(s). Codex's review is not the user's approval: it counts only where "
            "the module's takeover gives this step to codex." % (len(rounds) + 1, found["blocking"], found["suggestions"]))
    return updated, note


def _outside(root: Path, module_id: str) -> str | None:
    """takeover-scope-check reused: why the module's changes cannot be accepted as in scope, or None when they are."""
    from module_scope import ScopeError, classify, default_base, parse
    try:
        scope = parse((root / "spec" / ("%s.md" % module_id)).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ScopeError):
        scope = None
    if scope is None:
        return "spec/%s.md has no usable concurrency boundary" % module_id
    base = default_base(root, module_id)
    rows = classify(root, module_id, scope, base) if base else None
    if rows is None:
        return "no base commit to compare with"
    outside = [row["path"] for row in rows if row["scope"] == "outside"]
    return "%d file(s) outside: %s" % (len(outside), ", ".join(outside[:5])) if outside else None


def _merge_at_base(root: Path, module_id: str) -> str:
    """M3 rework (Q14 A): the module's merge item as of the commit before it started, read by the one config reader."""
    import tempfile
    from module_scope import default_base
    from project_config import module_takeover
    base = default_base(root, module_id)
    if not base:
        return "unknown (no commit before the module)"
    if _git(root, "cat-file", "-e", "%s:.agent/config.json" % base) is None:
        return "human"  # no config then: the default takeover
    text = _git(root, "show", "%s:.agent/config.json" % base)
    if text is None:
        return "unknown (config unreadable)"
    with tempfile.TemporaryDirectory(prefix="spec-guard-base-") as folder:
        (Path(folder) / ".agent").mkdir()
        (Path(folder) / ".agent" / "config.json").write_text(text + "\n", encoding="utf-8")
        return module_takeover(Path(folder), module_id)[0].get("merge")


def _acceptance(root: Path, module_id: str, state: str, report: str | None, confirm: bool) -> int:
    """codex-final-acceptance: record Codex's final acceptance of HEAD in the git directory, or say why not."""
    from project_config import module_takeover
    if state != "codex-approved":
        print("acceptance-state: --target acceptance records only codex-approved; the user's own final acceptance "
              "is the final gate in tasks/%s/todo.md" % module_id)
        return 2
    if report is None:
        print("review-missing: --target acceptance needs --review <the /delegate:review JSON of the final patch>")
        return 2
    takeover = module_takeover(root, module_id)[0]
    if takeover.get("merge") != "auto":
        print("acceptance-not-auto: %s's takeover has merge=%s; only a merge=auto module is accepted by Codex, "
              "others wait for the user" % (module_id, takeover.get("merge")))
        return 2
    base_merge = _merge_at_base(root, module_id)
    if base_merge != "auto":
        print("acceptance-not-auto-at-base: before %s started, its takeover had merge=%s; Codex accepts only a module "
              "whose merge was automatic from the start, so a patch cannot grant it to itself (Q14 A)"
              % (module_id, base_merge))
        return 2
    status = _git(root, "status", "--porcelain")
    if status is None:
        print("git-unreadable: could not read the working tree status")
        return 2
    if status:
        print("acceptance-uncommitted: the working tree has uncommitted changes; the evidence must be about HEAD alone")
        return 2
    final = inspect_final(report, root, module_id)
    if final["status"] != "ok":
        print("report-invalid: %s" % final["reason"])
        return 2
    check = inspect_check(root)
    if check["status"] != "ok":
        print("check-invalid: %s" % check["reason"])
        return 2
    if final["head"] != check["head"]:
        print("acceptance-head-moved: the review and the check evidence are about different commits")
        return 2
    outside = _outside(root, module_id)
    if outside:
        print("acceptance-out-of-scope: %s" % outside)
        return 2
    path = acceptance_path(root, module_id)
    if path is None:
        print("git-unreadable: could not find the git directory")
        return 2
    report_path = Path(report).resolve()
    record = {"marker": "codex-approved", "sha": final["head"], "module": module_id,
              "report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(), "report": str(report_path),
              "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    text = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    print("Codex final acceptance of %s at %s: final review %s, check evidence %s, nothing out of scope."
          % (module_id, final["head"][:12], report_path, check["path"]))
    print("record (git directory, not tracked, not committed): %s" % path)
    print(text, end="")
    print("The final gate in tasks/%s/todo.md is not ticked now: the phase hint reads it as passed while this record's "
          "commit is HEAD or an ancestor of it; tick it after the merge. A drafted reply is not sent." % module_id)
    if not confirm:
        print("\npreview only; nothing was written. Re-run with --confirm to apply.")
        return 0
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_atomic(path, text)
        if json.loads(path.read_text(encoding="utf-8")) != record:
            raise ValueError
    except (OSError, ValueError):
        print("file-unwritable: %s could not be written or read back" % path)
        return 2
    print("\nrecorded codex-approved acceptance: %s" % path)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Mark a module's Spec or Plan review state (preview unless --confirm).")
    parser.add_argument("--project", default=".")
    parser.add_argument("--module", required=True)
    parser.add_argument("--target", required=True, choices=["spec", "plan", "both", "acceptance"])
    parser.add_argument("--state", required=True, choices=["pending", "approved", "codex-approved", "codex-reviewed"])
    parser.add_argument("--review", help="codex states: the /delegate:review JSON report saved to a file")
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
    if args.target == "acceptance":
        return _acceptance(root, module_id, args.state, args.review, args.confirm)
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
    if args.state.startswith("codex-"):
        if args.target == "both":
            print("codex-one-target: a Codex round is recorded for one file at a time (--target spec or plan)")
            return 2
        kind = kinds[0]
        if args.state == "codex-approved":
            route = codex_route(root, module_id, kind)
            if route:
                print("codex-route-%s: %s requires the user's approval under the module's takeover settings; "
                      "record this round with --state codex-reviewed, then have the user approve it with --state approved."
                      % (route, relative[kind]))
                return 2
        updated, message = _codex(root, relative[kind], kind, args.state, args.review, before[kind])
        print(message)
        if updated is None:
            return 2
        print("".join(difflib.unified_diff(before[kind].splitlines(keepends=True), updated.splitlines(keepends=True),
                                           fromfile=relative[kind] + " (current)", tofile=relative[kind] + " (proposed)")))
        if not args.confirm:
            print("\npreview only; nothing was written. Re-run with --confirm to apply.")
            return 0
        try:
            _write_atomic(root / relative[kind], updated)
        except OSError:
            print("file-unwritable: %s could not be written" % relative[kind])
            return 2
        if args.state == "codex-approved" and review_state((root / relative[kind]).read_text(encoding="utf-8"), kind) != args.state:
            print("readback-mismatch: %s does not read back as codex-approved" % relative[kind])
            return 2
        print("\nrecorded %s: %s" % (args.state, relative[kind]))
        return 0
    unmarked_spec = False
    if args.state == "approved" and kinds == ["plan"]:
        # No marker means the Spec is not tracked, which must not block anything; a Spec that is
        # tracked and not approved does.
        # codex-approval: a Spec Codex approved under the takeover counts as approved here too.
        spec_state = effective_review(root, module_id, "spec", file_review_state(root / relative["spec"], "spec"))[0]
        unmarked_spec = spec_state == "none"
        if spec_state not in ("approved", "none"):
            print("spec-not-approved: %s reads as %s. Approving a Spec needs the user's own explicit approval of "
                  "that Spec; the Plan's approval or an earlier \"continue\" does not cover it. Show the user the "
                  "Spec first, then use --target both if they approve both." % (relative["spec"], spec_state))
            if spec_state == "revised":
                print("Before the build the revision can be approved with the Plan: show the user the Spec's cumulative "
                      "diff against its approved baseline (preview this command with --target both to print it), then "
                      "record both with --target both.")
            return 2
    if args.state == "approved" and "spec" in kinds and review_state(before["spec"], "spec") == "revised":
        # pre-build-spec-batch: the user approves the revision itself, so they must see what changed since approval.
        baseline = spec_baseline(root, module_id)
        if baseline["status"] == "found":
            print("Spec changes since it was approved (show this diff to the user verbatim):")
            print("".join(difflib.unified_diff(review_body(baseline["text"]).splitlines(keepends=True),
                                               review_body(before["spec"]).splitlines(keepends=True),
                                               fromfile="%s (approved %s)" % (relative["spec"], baseline["commit"][:7]),
                                               tofile=relative["spec"] + " (now)")))
        else:
            reason = ("no approved baseline in git" if baseline["status"] == "absent"
                      else "the approved baseline could not be checked (%s)" % baseline["reason"])
            print("%s: %s; show the user the whole revised Spec, not a summary of the changes."
                  % (relative["spec"], reason))
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
              "the installed collaboration plugin relays) -- its points, or the whole text when it is short. If they were given only a link or a one-line summary, that is not a "
              "review: show the content first and ask again." % " and ".join(relative[kind] for kind in kinds))
        print("`approved` records the user's explicit approval: where approvals may come from follows the installed "
              "collaboration plugin; without one, only an explicit approval in the current conversation counts. Do not "
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
