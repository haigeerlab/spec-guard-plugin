"""Complete and validate a Proposal draft from the remote default-branch snapshot.

The draft's `## Capability map baseline` section and the revision in its v2 marker
are computed here; every other byte of the draft is preserved.  Nothing is written
unless `--confirm` is given, and then only the draft file itself is rewritten.
"""
from __future__ import annotations

import argparse
import difflib
import os
import shlex
import sys
import tempfile
from pathlib import Path

from capability_map import _visible_lines
from proposal_contract import (
    HEADING, V1_MARKER, V2_MARKER, ContractError, _build_order, compute, compute_revision,
    parse_proposal, validate_proposal)
from proposal_publication import _run, _show, fixed_snapshot, read_published_pool

MAP_PATH = "spec/CAPABILITY-MAP.md"
PROPOSALS_DIR = "spec/proposals/"
BASELINE_HEADING = "Capability map baseline"
ZERO_REVISION = "0" * 64
ISSUE_LABELS = ("proposal", "proposal-stage:published")


class SubmitError(Exception):
    """A draft cannot be completed; nothing was written."""


def _read_draft(project, draft):
    project = Path(project)
    relative = os.path.normpath(os.path.relpath(draft, str(project))
                                if os.path.isabs(draft) else draft)
    path = project / relative
    if path.is_symlink() or not path.is_file():
        raise SubmitError("draft must be a readable regular file: %s" % draft)
    try:
        text = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeError) as error:
        raise SubmitError("cannot read draft: %s" % error)
    return path, relative.replace(os.sep, "/"), text


def _marker_line(lines):
    candidates = [index for index, line in enumerate(lines)
                  if line.strip().startswith("<!-- spec-guard-proposal:")]
    if len(candidates) != 1:
        raise SubmitError("draft must contain exactly one Proposal marker")
    index = candidates[0]
    match = V2_MARKER.fullmatch(lines[index].rstrip("\r\n"))
    if not match:
        raise SubmitError("draft marker must be a complete v2 marker")
    return index, match.group(1), match.group(2)


def _headings(lines):
    """Yield (index, title) for `## ` headings outside fenced code blocks."""
    fence = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if fence is None and stripped.startswith(("```", "~~~")):
            fence = stripped[:3]
        elif fence is not None and stripped.startswith(fence):
            fence = None
        elif fence is None:
            match = HEADING.match(stripped)
            if match:
                yield index, match.group(1)


def _baseline_section(remote, snapshot, map_path):
    digest = compute(str(map_path))
    if digest["goalDigest"] is None:
        raise SubmitError("remote %s has no `## 目标` (or `## Goal`) section; "
                          "a Proposal baseline needs its goal digest" % MAP_PATH)
    rows = "\n".join("| %s | %s |" % (item["id"], item["rowDigest"]) for item in digest["rows"])
    return "\n".join((
        "## " + BASELINE_HEADING,
        "",
        "| Field | Value |",
        "| --- | --- |",
        "| Remote | %s |" % remote,
        "| Default branch | %s |" % snapshot.branch,
        "| Commit | %s |" % snapshot.commit,
        "| Capability map | %s |" % MAP_PATH,
        "| Goal digest | %s |" % digest["goalDigest"],
        "| Build order | %s |" % _build_order(map_path),
        "",
        "### Module digests",
        "",
        "| Module id | Row digest |",
        "| --- | --- |",
        rows,
        "",
        ""))


def _replace_baseline(lines, section):
    heads = list(_headings(lines))
    for position, (index, title) in enumerate(heads):
        if title == BASELINE_HEADING:
            end = heads[position + 1][0] if position + 1 < len(heads) else len(lines)
            return lines[:index] + [section] + lines[end:]
    for index, title in heads:
        if title == "Change":
            return lines[:index] + [section] + lines[index:]
    raise SubmitError("draft has no ## Change section to place the baseline before")


def _published_ids(snapshot):
    """Map every Proposal id declared on the remote default branch to its paths."""
    listed = _run(["git", "-C", str(snapshot.repo), "ls-tree", "-r", "--name-only",
                   snapshot.commit, PROPOSALS_DIR.rstrip("/")])
    if listed is None:
        raise SubmitError("cannot list remote proposals")
    found = {}
    for path in sorted(listed.stdout.splitlines()):
        if not (path.startswith(PROPOSALS_DIR) and path.endswith(".md")):
            continue
        text = _show(snapshot.repo, snapshot.commit, path)
        for line in _visible_lines((text or "").splitlines()):
            match = V1_MARKER.fullmatch(line.strip()) or V2_MARKER.fullmatch(line.strip())
            if match:
                revision = match.group(2) if match.re is V2_MARKER else None
                found.setdefault(match.group(1), {})[path] = revision
    return found


def _next_steps(platform, title, marker, summary, revision_of):
    if platform == "github":
        create = "gh issue create --title %s --label proposal --label %s --body %s" % (
            shlex.quote(title), shlex.quote(ISSUE_LABELS[1]), shlex.quote(marker + "\n\n" + summary))
        labels = ["gh label create %s" % shlex.quote(label) for label in ISSUE_LABELS]
    else:
        create = "glab issue create --title %s --label %s --description %s" % (
            shlex.quote(title), shlex.quote(",".join(ISSUE_LABELS)),
            shlex.quote(marker + "\n\n" + summary))
        labels = ["glab label create --name %s" % shlex.quote(label) for label in ISSUE_LABELS]
    out = ["", "Next steps (nothing below has been run):",
           "1. Publish: merge the draft into the default branch through a pull request."]
    if revision_of:
        out.append("2. This replaces an already published revision: update the marker line in the "
                   "existing Issue body to the new marker below (do not open a new Issue):")
        out.append("   " + marker)
    else:
        out.append("2. After the merge, open the Issue (title is the document title):")
        out.append("   " + create)
    out.append("3. If the labels do not exist yet, create them first:")
    out.extend("   " + line for line in labels)
    out.append("4. Review with /spec-guard:proposal-review; relabel the Issue to "
               "proposal-stage:accepted to accept it.")
    return out


def _summary(text):
    lines = text.splitlines()
    for index, title in _headings(lines):
        if title == "Summary":
            paragraph = []
            for line in lines[index + 1:]:
                if HEADING.match(line.strip()):
                    break
                if line.strip():
                    paragraph.append(line.strip())
                elif paragraph:
                    break
            return " ".join(paragraph)
    return ""


def _write_atomic(path, data):
    fd, temp = tempfile.mkstemp(prefix=".proposal-submit-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.chmod(temp, path.stat().st_mode & 0o7777)
        os.replace(temp, str(path))
    except BaseException:
        if os.path.exists(temp):
            os.unlink(temp)
        raise


def submit(project, draft, remote, platform, confirm):
    path, relative, original = _read_draft(project, draft)
    lines = original.splitlines(keepends=True)
    marker_index, proposal_id, _ = _marker_line(lines)
    if relative != "%s%s.md" % (PROPOSALS_DIR, proposal_id):
        raise SubmitError("draft path must be %s%s.md for id %s" % (PROPOSALS_DIR, proposal_id,
                                                                   proposal_id))
    with fixed_snapshot(project, remote, "sg-proposal-submit-") as snapshot:
        if snapshot.failure:
            raise SubmitError(snapshot.failure)
        map_text = _show(snapshot.repo, snapshot.commit, MAP_PATH)
        if map_text is None:
            raise SubmitError("remote default branch has no %s" % MAP_PATH)
        map_path = snapshot.temp / "baseline-map.md"
        map_path.write_text(map_text, encoding="utf-8")
        try:
            section = _baseline_section(remote, snapshot, map_path)
        except (ContractError, OSError, UnicodeError, KeyError, ValueError) as error:
            raise SubmitError("invalid remote capability map: %s" % error)
        completed = _replace_baseline(lines, section)
        marker_index = next(index for index, line in enumerate(completed)
                            if line.strip().startswith("<!-- spec-guard-proposal:"))
        ending = completed[marker_index][len(completed[marker_index].rstrip("\r\n")):]
        completed[marker_index] = ("<!-- spec-guard-proposal:v2 id=%s revision=sha256:%s -->%s"
                                   % (proposal_id, ZERO_REVISION, ending))
        candidate = snapshot.temp / "proposal.md"
        candidate.write_bytes("".join(completed).encode("utf-8"))
        try:
            revision = compute_revision(candidate)
            completed[marker_index] = completed[marker_index].replace(ZERO_REVISION, revision)
            final = "".join(completed)
            candidate.write_bytes(final.encode("utf-8"))
            proposal = validate_proposal(candidate, map_path)
        except ContractError as error:
            raise SubmitError(str(error))
        pool = read_published_pool(project, remote)
        if pool.state != "published":
            raise SubmitError("remote proposal pool is unavailable: %s" %
                              (pool.diagnostic or pool.state))
        declared = _published_ids(snapshot).get(proposal_id, {})
        others = sorted(other for other in declared if other != relative)
        if others:
            raise SubmitError("id %s is already declared by another remote file: %s" %
                              (proposal_id, ", ".join(others)))
        is_revision = relative in declared

    diff = list(difflib.unified_diff(original.splitlines(keepends=True),
                                     final.splitlines(keepends=True),
                                     "a/" + relative, "b/" + relative))
    if confirm:
        _write_atomic(path, final.encode("utf-8"))
    out = ["%s %s" % ("Wrote" if confirm else "Preview (no file written; rerun with --confirm) for",
                      relative)]
    out.append("".join(line if line.endswith("\n") else line + "\n" for line in diff)
               .rstrip("\n") if diff else "(no changes: the draft is already complete)")
    out.append("")
    out.append("Revision: sha256:%s" % revision)
    out.append("Baseline commit: %s (%s/%s)" % (proposal.baseline.commit, remote,
                                                proposal.baseline.default_branch))
    out.append("Revision of a published Proposal: %s" % (
        "yes (replaces the version already on the remote default branch)" if is_revision else "no"))
    # Issue title: the document title verbatim (parse_proposal guarantees "# Proposal: ...").
    title = next(line[2:].strip() for line in final.splitlines() if line.startswith("# "))
    out.extend(_next_steps(platform, title, proposal.marker, _summary(final), is_revision))
    return "\n".join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".")
    parser.add_argument("--draft", required=True)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--platform", required=True, choices=("github", "gitlab"))
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args(argv)
    try:
        print(submit(args.project, args.draft, args.remote, args.platform, args.confirm))
    except SubmitError as error:
        print("proposal-submit: rejected: %s" % error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
