"""Summarize declared documentation delivery without asserting content truth."""
import argparse
import json
from pathlib import Path
import re
import subprocess

from documentation_baseline import _visible_lines, parse_baseline
from documentation_impact import ImpactError, _cells, _regular, _table, parse_impact


OUTCOMES = frozenset(("delivered", "deferred", "pending"))
# doc-chain (D15): an Authority with a scheme is an external document; git cannot see it.
EXTERNAL = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")


class VerificationError(ValueError):
    """The declared documentation outcome cannot safely be interpreted."""


class Outcome(object):
    def __init__(self, concern, outcome, evidence, rationale):
        self.concern = concern
        self.outcome = outcome
        self.evidence = evidence
        self.rationale = rationale
        self.check = "not-checked"
        self.added = None
        self.removed = None


class Verification(object):
    def __init__(self, state, outcomes, attention):
        self.state = state
        self.outcomes = outcomes
        self.attention = attention


def _empty(value):
    value = value.strip().strip("`").strip()
    return None if value in ("", "-", "—") else value


def _has_outcome_table(path):
    try:
        lines = _visible_lines(path.read_text(encoding="utf-8").splitlines())
    except (OSError, UnicodeError) as error:
        raise VerificationError("cannot read module plan: %s" % error)
    headers = ["concern", "outcome", "evidence", "rationale"]
    return sum(1 for line in lines if _cells(line) and
               [cell.lower() for cell in _cells(line)] == headers)


def _outcomes(path, required):
    count = _has_outcome_table(path)
    if count == 0:
        return {}
    if count != 1:
        raise VerificationError("module plan must contain exactly one Documentation outcome table")
    entries = {}
    for concern, outcome, evidence, rationale in _table(
            _regular(path, "module plan"),
            ("Concern", "Outcome", "Evidence", "Rationale"), "Documentation outcome"):
        if concern in entries:
            raise VerificationError("duplicate outcome concern: %s" % concern)
        if concern not in required:
            raise VerificationError("outcome is only allowed for update/create: %s" % concern)
        if outcome not in OUTCOMES:
            raise VerificationError("unknown outcome: %s" % outcome)
        evidence = _empty(evidence)
        if outcome == "delivered" and evidence is None:
            raise VerificationError("delivered outcome requires evidence for %s" % concern)
        if not rationale:
            raise VerificationError("outcome rationale is required for %s" % concern)
        entries[concern] = Outcome(concern, outcome, evidence, rationale)
    return entries


def _git(project, *args):
    """Run a read-only git command; (stdout, None) or (None, why it failed)."""
    try:
        done = subprocess.run(["git", "-C", str(project), *args], capture_output=True, text=True,
                              timeout=10, check=False)
    except (OSError, subprocess.SubprocessError) as error:
        return None, "git could not run (%s)" % error
    if done.returncode != 0:
        return None, "git %s failed: %s" % (args[0], (done.stderr or "").strip() or done.returncode)
    return done.stdout, None


def _changes(project, module, path):
    """(added, removed, None) for `path` since the module Spec first landed; (None, None, why) when git cannot tell."""
    out, why = _git(project, "log", "--diff-filter=A", "--format=%H", "--", "spec/%s.md" % module)
    if why:
        return None, None, why
    commits = out.split()
    if not commits:
        return None, None, "spec/%s.md is not committed yet" % module
    out, why = _git(project, "diff", "--numstat", commits[-1], "--", path)
    if why:
        return None, None, why
    added = removed = 0
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            return None, None, "unexpected git diff output"
        if parts[0] == "-":  # binary: changed, line counts unknown
            return -1, -1, None
        added, removed = added + int(parts[0]), removed + int(parts[1])
    return added, removed, None


def _check(project, module, outcome, entry, attention):
    """doc-chain (D15): what git says about one delivered update, by the baseline status of its document."""
    authority = entry.authority or ""
    if EXTERNAL.match(authority):
        outcome.check = "unverified"
        return
    path = authority.split("#", 1)[0]
    added, removed, why = _changes(project, module, path)
    if why:
        outcome.check = "unknown"
        attention.append("%s: cannot tell whether %s changed: %s" % (outcome.concern, path, why))
        return
    changed = bool(added or removed)
    if changed and added >= 0:
        outcome.added, outcome.removed = added, removed
    if entry.status == "target":
        outcome.check = "target-changed" if changed else "target-unchanged"
        if changed and removed != 0:
            attention.append("%s: target document %s has deletions; deleting or changing a goal not yet built is a "
                             "requirement change and needs the user's separate approval" % (outcome.concern, path))
    elif changed:
        outcome.check = "changed"
    else:
        outcome.check = "unchanged"
        attention.append("%s is declared delivered, but %s has no change since spec/%s.md was first committed"
                         % (outcome.concern, path, module))


def _check_created(project, outcome, artifact, attention):
    """review-residual-fixes (C2): a delivered `create` only claims the document exists; nothing about its content."""
    if EXTERNAL.match(artifact):
        outcome.check = "unverified"
        return
    path = artifact.split("#", 1)[0]
    target = project / path
    try:
        inside = target.resolve().is_relative_to(project.resolve())
    except (OSError, RuntimeError):
        inside = False
    if inside and not target.is_symlink() and target.is_file():
        outcome.check = "present"
        return
    outcome.check = "missing"
    attention.append("%s is declared delivered, but %s does not exist in the project" % (outcome.concern, path))


def verify_documentation(project, module):
    """Return conservative declared-document facts for a module."""
    project = Path(project)
    try:
        impact = parse_impact(project, module)
    except ImpactError as error:
        raise VerificationError(str(error))
    if impact.state == "absent":
        return Verification("absent", {}, [])
    required = set(concern for concern, decision in impact.decisions.items()
                   if decision.decision in ("update", "create"))
    plan = project / "tasks" / module / "plan.md"
    outcomes = _outcomes(plan, required)
    baseline = parse_baseline(project / "docs" / "DOCUMENTATION-BASELINE.md")
    attention = []
    for concern, decision in sorted(impact.decisions.items()):
        if decision.decision == "pending":
            attention.append("%s has a pending documentation decision" % concern)
    for concern in sorted(required):
        outcome = outcomes.get(concern)
        if outcome is None:
            attention.append("%s has no declared documentation outcome" % concern)
        elif outcome.outcome != "delivered":
            attention.append("%s is declared %s" % (concern, outcome.outcome))
        elif impact.decisions[concern].decision == "update":
            _check(project, module, outcome, baseline.entries[concern], attention)
        else:
            _check_created(project, outcome, impact.delivery[concern].artifact, attention)
    return Verification("attention" if attention else "ready", outcomes, attention)


def _as_json(result):
    return {
        "state": result.state,
        "outcomes": dict((concern, {
            "outcome": item.outcome,
            "evidence": item.evidence,
            "rationale": item.rationale,
            "check": item.check,
            "added": item.added,
            "removed": item.removed,
        }) for concern, item in sorted(result.outcomes.items())),
        "attention": result.attention,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".")
    parser.add_argument("--module", required=True)
    parser.add_argument("--format", choices=("json",), default="json")
    args = parser.parse_args(argv)
    try:
        result = verify_documentation(args.project, args.module)
    except (VerificationError, OSError, UnicodeError) as error:
        print(json.dumps({"state": "invalid", "error": str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps(_as_json(result), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
