"""Decide whether a Proposal's tracker item may be closed out.

This is the whole judgement, shared by the Local, GitHub and GitLab backends: only the
provider adapters differ.  It is a pure function on three observed facts, and it
deliberately cannot reach a project root, a provider or a filesystem path.

That restriction is the point.  A module with a plan and no `tasks/<id>/todo.md` counts
as done (see `spec/plan-without-todo.md`), so a module looks finished the instant it is
promoted -- long before anyone has written its Spec.  Closing a Proposal on that basis
would be wrong, and with nothing in reach to read a module stage from, this function
cannot make that mistake even by accident.
"""
from __future__ import annotations

import hashlib
import json

from proposal_promotion_proof import prove_from_remote
from proposal_publication import read_published
from proposal_tracker_read import (
    CONTRACT_INVALID, MARKER_AMBIGUOUS, recover_tracker_issue,
)

PROMOTED_STAGE = "proposal-stage:promoted"
ACCEPTED_STAGE = "proposal-stage:accepted"
CLOSEABLE_STAGES = (ACCEPTED_STAGE, PROMOTED_STAGE)
PROVED = "proved"


class Decision(object):
    """`eligible`, `already-closed` or `not-eligible`."""

    def __init__(self, state, target_stage=None, needs_stage_change=None,
                 diagnostic=None):
        self.state = state
        self.target_stage = target_stage
        self.needs_stage_change = needs_stage_change
        self.diagnostic = diagnostic


def closeout_decision(stage, closed, proof_state, proof_diagnostic=None):
    """Judge one Proposal item.  Closed first, then the proof, then the stage.

    `already-closed` wins over everything so a rerun after a successful closeout -- or
    after a human closed the item -- reports the fact and writes nothing.  The proof is
    checked before the stage so a caller learns why the promotion is not provable rather
    than being told its stage is wrong.
    """
    if closed is True:
        return Decision("already-closed")
    if proof_state != PROVED:
        return Decision("not-eligible",
                        diagnostic=proof_diagnostic or "promotion-not-proved")
    if stage not in CLOSEABLE_STAGES:
        return Decision("not-eligible", diagnostic="stage-not-closeable")
    return Decision("eligible", target_stage=PROMOTED_STAGE,
                    needs_stage_change=stage != PROMOTED_STAGE)


MARKER_NAMESPACE = "spec-guard-proposal-closeout:v1"
REVISION_DIGITS = 12
# Stable codes for the two read layers, so a missing Proposal, a missing item and an
# unreadable container stay distinguishable even where the state would coincide.
TRACKER_CODES = {"absent": "tracker-absent", "unknown": "tracker-unknown"}
RECORD = (
    "Proposal `%(id)s` is promoted.\n"
    "\n"
    "The change this Proposal declared is in the capability map on the remote default\n"
    "branch as of `%(promotion)s`, proved against `%(review)s`.\n"
    "\n"
    "This item records a **design decision**, and that decision is now carried out. It\n"
    "does not represent delivery of the module: its Spec, Plan, todo, implementation\n"
    "and acceptance are tracked by the module's own task list or by ordinary tracker\n"
    "items, not here. Closing this item says the decision landed, nothing more.\n"
    "\n"
    "<!-- %(namespace)s %(id)s/%(short)s -->"
)


def short_revision(revision):
    """The marker carries a short revision: enough to bind one published content."""
    digest = revision.split(":")[-1] if isinstance(revision, str) else ""
    return digest[:REVISION_DIGITS]


def closeout_marker(proposal_id, revision):
    return "<!-- %s %s/%s -->" % (MARKER_NAMESPACE, proposal_id,
                                  short_revision(revision))


def closeout_record(proposal_id, revision, promotion_commit, review_commit):
    """The comment written on closeout, ending in exactly one stable marker."""
    return RECORD % {"id": proposal_id, "promotion": promotion_commit,
                     "review": review_commit, "namespace": MARKER_NAMESPACE,
                     "short": short_revision(revision)}


def preview_digest(preview):
    """Bind every previewed fact, so an authorized preview cannot be swapped."""
    payload = json.dumps(preview, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def adapter_tracker_reader(adapter):
    """Read the tracker through the closeout adapter.

    `prove_from_remote` accepts a reader, so the proof judges the same candidate set the
    preview saw -- one listing, one verdict -- instead of each side reading separately
    and possibly disagreeing. It is also what lets the Local backend be proved at all:
    the default reader only speaks the GitHub and GitLab CLIs.
    """
    def reader(proposal, platform, target):
        try:
            page = adapter.list_issues()
        except Exception:
            return recover_tracker_issue(proposal, platform, target,
                                         {"complete": False, "issues": []})
        return recover_tracker_issue(proposal, platform, target, page)
    return reader


def _blocked(state, diagnostic=None):
    result = {"state": state}
    if diagnostic:
        result["diagnostic"] = diagnostic
    return result


def build_preview(project, proposal_id, backend, target, adapter, remote="origin",
                  source="explicit", host=None, publication_reader=None,
                  tracker_reader=None, prover=None):
    """Read the Proposal, locate its item, prove the promotion, then preview.

    The proof is taken inside this call rather than accepted from a caller: a proof
    produced earlier says the promotion was provable then, not now.  Nothing here
    writes, and no module stage is consulted -- only the Proposal, the item and Git.
    """
    publication_reader = publication_reader or read_published
    prover = prover or prove_from_remote
    reader = tracker_reader or adapter_tracker_reader(adapter)

    publication = publication_reader(project, proposal_id, remote)
    if getattr(publication, "state", None) != "published":
        state = getattr(publication, "state", None)
        return _blocked(state if state in ("absent", "invalid") else "unknown")
    proposal = publication.proposal
    if not getattr(proposal, "revision", None):
        return _blocked("not-eligible", "legacy-revision-required")

    tracker = reader(proposal, backend, target)
    if getattr(tracker, "state", None) != "verified":
        state = getattr(tracker, "state", None)
        if state == "invalid":
            code = getattr(tracker, "code", None) or CONTRACT_INVALID
            # Several items carrying the marker is not a malformed container: it is a
            # choice only a human can make, so say conflict rather than invalid.
            return _blocked("conflict" if code == MARKER_AMBIGUOUS else "invalid", code)
        state = state if state in TRACKER_CODES else "unknown"
        return _blocked(state, TRACKER_CODES[state])

    proof = prover(project, proposal_id, backend, target, remote,
                   tracker_reader=reader)
    decision = closeout_decision(tracker.stage, tracker.closed,
                                 getattr(proof, "state", None),
                                 getattr(proof, "diagnostic", None))
    if decision.state != "eligible":
        return _blocked(decision.state, decision.diagnostic)

    try:
        facts = adapter.target_facts()
    except Exception:
        return _blocked("unknown", "target-unreadable")

    actions = ["comment"] + (["stage"] if decision.needs_stage_change else []) + ["close"]
    preview = {
        "state": "preview", "backend": backend, "exactTarget": facts,
        "proposalId": proposal_id, "revision": proposal.revision,
        "issueId": tracker.issue_id, "currentStage": tracker.stage,
        "targetStage": decision.target_stage,
        "promotionCommit": proof.promotion_commit,
        "reviewCommit": proof.review_commit,
        "record": closeout_record(proposal_id, proposal.revision,
                                  proof.promotion_commit, proof.review_commit),
        "actions": actions, "source": source,
    }
    preview["digest"] = preview_digest(preview)
    return preview
