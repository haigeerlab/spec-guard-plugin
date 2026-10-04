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
