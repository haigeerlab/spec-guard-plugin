"""Proposal closeout: the backend-neutral decision. No I/O, no network, no ledger."""
import inspect
import unittest

from proposal_closeout import CLOSEABLE_STAGES, PROMOTED_STAGE, closeout_decision

ACCEPTED = "proposal-stage:accepted"
OTHER_STAGES = ("proposal-stage:draft", "proposal-stage:published",
                "proposal-stage:in-review", "proposal-stage:needs-revision",
                "proposal-stage:deferred", "proposal-stage:rejected")
UNPROVED = ("not-promoted", "stale", "invalid", "unknown", "not-accepted")


class DecisionTests(unittest.TestCase):
    """Spec C1: closed, then proof, then stage -- in that order."""

    def test_an_accepted_proved_proposal_is_eligible_and_needs_the_stage_moved(self):
        decision = closeout_decision(ACCEPTED, False, "proved")
        self.assertEqual(decision.state, "eligible")
        self.assertEqual(decision.target_stage, PROMOTED_STAGE)
        self.assertTrue(decision.needs_stage_change)
        self.assertIsNone(decision.diagnostic)

    def test_an_already_promoted_proved_proposal_is_eligible_without_a_stage_change(self):
        decision = closeout_decision(PROMOTED_STAGE, False, "proved")
        self.assertEqual(decision.state, "eligible")
        self.assertFalse(decision.needs_stage_change)

    def test_a_closed_issue_is_already_closed_whatever_else_holds(self):
        for stage in (ACCEPTED, PROMOTED_STAGE) + OTHER_STAGES:
            for proof in ("proved",) + UNPROVED:
                decision = closeout_decision(stage, True, proof)
                self.assertEqual(decision.state, "already-closed", (stage, proof))

    def test_every_unproved_state_blocks_and_passes_its_diagnostic_through(self):
        for proof in UNPROVED:
            decision = closeout_decision(ACCEPTED, False, proof,
                                         proof_diagnostic="promotion-" + proof)
            self.assertEqual(decision.state, "not-eligible", proof)
            self.assertEqual(decision.diagnostic, "promotion-" + proof, proof)

    def test_an_unproved_state_without_a_diagnostic_still_blocks(self):
        decision = closeout_decision(ACCEPTED, False, "not-promoted")
        self.assertEqual(decision.state, "not-eligible")
        self.assertEqual(decision.diagnostic, "promotion-not-proved")

    def test_stages_outside_accepted_and_promoted_are_not_closeable(self):
        for stage in OTHER_STAGES:
            decision = closeout_decision(stage, False, "proved")
            self.assertEqual(decision.state, "not-eligible", stage)
            self.assertEqual(decision.diagnostic, "stage-not-closeable", stage)

    def test_an_unknown_stage_string_is_not_closeable(self):
        decision = closeout_decision("proposal-stage:invented", False, "proved")
        self.assertEqual(decision.state, "not-eligible")
        self.assertEqual(decision.diagnostic, "stage-not-closeable")

    def test_closeable_stages_are_exactly_accepted_and_promoted(self):
        self.assertEqual(set(CLOSEABLE_STAGES), {ACCEPTED, PROMOTED_STAGE})

    def test_the_decision_cannot_reach_a_project_a_provider_or_a_module_stage(self):
        """Spec Assumption 2: the plan-without-todo rule counts a module with a plan and
        no todo.md as done, so a new module looks finished the moment it is promoted.
        Closing a Proposal on that basis is the trap this signature forecloses: with no
        project root and no provider in reach, the function cannot read a module stage
        even by mistake."""
        names = list(inspect.signature(closeout_decision).parameters)
        self.assertEqual(names, ["stage", "closed", "proof_state", "proof_diagnostic"])
        for forbidden in ("project", "root", "provider", "path", "module"):
            self.assertNotIn(forbidden, names)


if __name__ == "__main__":
    unittest.main()
