"""Proposal closeout: the backend-neutral decision and the preview that precedes a
write. No I/O, no network, no ledger -- publication, proof and transport are injected.
"""
import inspect
import json
import pathlib
import tempfile
import unittest

from proposal_closeout import (
    CLOSEABLE_STAGES, PROMOTED_STAGE, build_preview, close_preview, closeout_record,
    closeout_decision, preview_digest,
)
from proposal_contract import Baseline, Change, Proposal
from proposal_publication import Publication
from proposal_promotion_proof import Proof
from proposal_tracker_read import TrackerRead

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


PROPOSAL_ID = "gamma"
REVISION = "sha256:" + "ab" * 32
MARKER = "<!-- spec-guard-proposal:v2 id=gamma revision=" + REVISION + " -->"
PROMOTION = "9507532400192d9e3e983028d863375d8ac2b0ac"
REVIEW = "4f163fc6fbee356aeb90ff60091331b08846c91c"


def proposal(revision=REVISION):
    return Proposal(PROPOSAL_ID, MARKER,
                    Baseline("origin", "main", "0" * 40, "0" * 12, {}, "alpha"),
                    Change(PROPOSAL_ID, "Gamma.", ("alpha",), "end"),
                    version="v2", revision=revision)


class FakeAdapter:
    """Only what the preview needs; the write methods must stay untouched here."""

    def __init__(self, issues=(), complete=True, facts=None, comments=()):
        self.page = {"complete": complete, "issues": list(issues)}
        self.facts = facts or {"platform": "github", "host": "github.com",
                               "target": "octo/repo", "targetId": 1,
                               "visibility": "private"}
        self.comments = list(comments)
        self.writes = []

    def target_facts(self):
        return dict(self.facts)

    def get_issue(self, issue_id):
        return {"number": issue_id, "state": "open", "body": "body",
                "labels": [{"name": ACCEPTED}, {"name": "proposal"}],
                "url": "u", "repository": {"full_name": "octo/repo"}}

    def list_issues(self):
        return {"complete": self.page["complete"],
                "issues": list(self.page["issues"])}

    def list_comments(self, issue_id):
        return {"complete": True, "comments": [{"body": body}
                                               for body in self.comments]}

    def create_comment(self, *a):
        self.writes.append("create_comment")

    def set_stage(self, *a):
        self.writes.append("set_stage")

    def set_closed(self, *a):
        self.writes.append("set_closed")


def preview(tracker=None, publication=None, proof=None, adapter=None, **kwargs):
    tracker = tracker or TrackerRead(
        "verified", issue_id=149, stage=ACCEPTED, proposal_id=PROPOSAL_ID,
        platform="github", target="octo/repo", closed=False)
    publication = publication or Publication("published", review_commit=REVIEW,
                                             proposal=proposal())
    proof = proof or Proof("proved", review_commit=REVIEW, proposal_id=PROPOSAL_ID,
                           module_id=PROPOSAL_ID, promotion_commit=PROMOTION)
    adapter = adapter if adapter is not None else FakeAdapter()
    return build_preview(
        ".", PROPOSAL_ID, "github", "octo/repo", adapter,
        publication_reader=lambda *a, **k: publication,
        tracker_reader=lambda *a, **k: tracker,
        prover=lambda *a, **k: proof, **kwargs)


class PreviewTests(unittest.TestCase):
    def test_a_proved_accepted_proposal_previews_every_fact_the_decision_rests_on(self):
        result = preview()
        self.assertEqual(result["state"], "preview")
        self.assertEqual(result["backend"], "github")
        self.assertEqual(result["exactTarget"],
                         {"platform": "github", "host": "github.com",
                          "target": "octo/repo", "targetId": 1,
                          "visibility": "private"})
        self.assertEqual(result["proposalId"], PROPOSAL_ID)
        self.assertEqual(result["revision"], REVISION)
        self.assertEqual(result["issueId"], 149)
        self.assertEqual(result["currentStage"], ACCEPTED)
        self.assertEqual(result["targetStage"], PROMOTED_STAGE)
        self.assertEqual(result["promotionCommit"], PROMOTION)
        self.assertEqual(result["reviewCommit"], REVIEW)
        self.assertEqual(result["actions"], ["comment", "stage", "close"])
        self.assertEqual(result["source"], "explicit")
        # The record carries the closeout marker and must not echo the Proposal's own:
        # two namespaces in one container is how marker ambiguity starts.
        self.assertIn("spec-guard-proposal-closeout:v1", result["record"])
        self.assertNotIn("spec-guard-proposal:v2", result["record"])

    def test_the_record_ends_with_the_stable_marker_and_names_its_boundary(self):
        record = preview()["record"]
        self.assertEqual(record.splitlines()[-1],
                         "<!-- spec-guard-proposal-closeout:v1 gamma/abababababab -->")
        self.assertIn(PROMOTION, record)
        # The record must say what closing does *not* mean, or a reader takes a closed
        # Proposal for a delivered module.
        self.assertIn("Spec", record)
        self.assertIn("todo", record.lower())

    def test_the_digest_covers_every_field_but_itself(self):
        result = preview()
        without = {key: value for key, value in result.items() if key != "digest"}
        self.assertEqual(result["digest"], preview_digest(without))
        changed = dict(without, promotionCommit="0" * 40)
        self.assertNotEqual(result["digest"], preview_digest(changed))

    def test_an_already_promoted_proposal_still_previews_without_a_stage_change(self):
        tracker = TrackerRead("verified", issue_id=125, stage=PROMOTED_STAGE,
                              proposal_id=PROPOSAL_ID, platform="github",
                              target="octo/repo", closed=False)
        result = preview(tracker=tracker)
        self.assertEqual(result["state"], "preview")
        self.assertEqual(result["actions"], ["comment", "close"])

    def test_a_closed_issue_previews_nothing_and_reports_already_closed(self):
        tracker = TrackerRead("verified", issue_id=125, stage=PROMOTED_STAGE,
                              proposal_id=PROPOSAL_ID, platform="github",
                              target="octo/repo", closed=True)
        result = preview(tracker=tracker)
        self.assertEqual(result["state"], "already-closed")
        self.assertNotIn("digest", result)

    def test_an_unproved_promotion_blocks_and_keeps_the_proof_diagnostic(self):
        for state, diagnostic in (("not-promoted", "promotion-not-found"),
                                  ("stale", "proposal-baseline-drifted"),
                                  ("invalid", "promotion-row-mismatch"),
                                  ("unknown", "promotion-unknown"),
                                  ("not-accepted", "tracker-absent")):
            result = preview(proof=Proof(state, proposal_id=PROPOSAL_ID,
                                         diagnostic=diagnostic))
            self.assertEqual(result["state"], "not-eligible", state)
            self.assertEqual(result["diagnostic"], diagnostic, state)
            self.assertNotIn("digest", result)

    def test_publication_states_other_than_published_pass_straight_through(self):
        for state in ("absent", "invalid", "unknown"):
            result = preview(publication=Publication(state, diagnostic="x"))
            self.assertEqual(result["state"], state)
            self.assertNotIn("digest", result)

    def test_a_v1_proposal_cannot_be_closed_out(self):
        result = preview(publication=Publication(
            "published", review_commit=REVIEW,
            proposal=Proposal(PROPOSAL_ID, MARKER,
                              Baseline("origin", "main", "0" * 40, "0" * 12, {}, "a"),
                              Change(PROPOSAL_ID, "G.", (), "end"))))
        self.assertEqual(result["state"], "not-eligible")
        self.assertEqual(result["diagnostic"], "legacy-revision-required")

    def test_tracker_states_other_than_verified_pass_through_with_a_stable_code(self):
        for state, diagnostic in (("absent", "tracker-absent"),
                                  ("invalid", "tracker-contract-invalid"),
                                  ("unknown", "tracker-unknown")):
            result = preview(tracker=TrackerRead(state, diagnostic="raw detail"))
            self.assertEqual(result["state"], state)
            self.assertEqual(result["diagnostic"], diagnostic)
            self.assertNotIn("raw detail", json.dumps(result))

    def test_several_items_carrying_the_marker_are_a_conflict_to_resolve(self):
        """Not just `invalid`: a human has to pick, and the preview should say so."""
        result = preview(tracker=TrackerRead("invalid", diagnostic="raw prose",
                                             code="tracker-marker-ambiguous"))
        self.assertEqual(result["state"], "conflict")
        self.assertEqual(result["diagnostic"], "tracker-marker-ambiguous")
        self.assertNotIn("raw prose", json.dumps(result))

    def test_other_invalid_codes_stay_invalid_and_keep_their_own_code(self):
        for code in ("tracker-marker-foreign-container", "tracker-legacy-marker",
                     "tracker-contract-invalid"):
            result = preview(tracker=TrackerRead("invalid", code=code))
            self.assertEqual(result["state"], "invalid", code)
            self.assertEqual(result["diagnostic"], code, code)

    def test_the_preview_never_writes(self):
        adapter = FakeAdapter()
        preview(adapter=adapter)
        self.assertEqual(adapter.writes, [])

    def test_the_preview_leaks_no_body_marker_or_raw_error(self):
        result = preview()
        serialized = json.dumps(result)
        self.assertNotIn(MARKER, serialized)
        self.assertNotIn("/private/", serialized)
        self.assertNotIn("http", serialized)

    def test_the_source_of_the_target_is_always_named(self):
        for source in ("explicit", "project-default", "project-default-target"):
            self.assertEqual(preview(source=source)["source"], source)


class RecordTests(unittest.TestCase):
    def test_the_marker_is_the_last_line_and_appears_exactly_once(self):
        record = closeout_record(PROPOSAL_ID, REVISION, PROMOTION, REVIEW)
        lines = record.splitlines()
        markers = [line for line in lines
                   if line.startswith("<!-- spec-guard-proposal-closeout:v1 ")]
        self.assertEqual(len(markers), 1)
        self.assertEqual(lines[-1], markers[0])

    def test_the_marker_binds_the_proposal_to_its_revision(self):
        other = closeout_record(PROPOSAL_ID, "sha256:" + "cd" * 32, PROMOTION, REVIEW)
        self.assertNotEqual(closeout_record(PROPOSAL_ID, REVISION, PROMOTION,
                                            REVIEW).splitlines()[-1],
                            other.splitlines()[-1])


class WritingAdapter(FakeAdapter):
    """Records writes and can be told to fail or to lose a response."""

    def __init__(self, issue=None, lose=(), fail=(), **kwargs):
        super().__init__(**kwargs)
        self.issue = issue or {"number": 149, "state": "open", "body": "body",
                               "labels": [{"name": ACCEPTED}, {"name": "proposal"}],
                               "url": "u", "repository": {"full_name": "octo/repo"}}
        self.lose, self.fail = set(lose), set(fail)
        self.calls = []

    def get_issue(self, issue_id):
        return dict(self.issue)

    def _record(self, name):
        self.calls.append(name)
        self.writes.append(name)
        if name in self.fail:
            raise RuntimeError("provider exploded")

    def create_comment(self, issue_id, body):
        self._record("comment")
        if "comment" not in self.lose:
            self.comments.append(body)

    def set_stage(self, issue_id, from_stage, to_stage):
        self._record("stage")
        if "stage" not in self.lose:
            self.issue["labels"] = [{"name": to_stage}, {"name": "proposal"}]

    def set_closed(self, issue_id):
        self._record("close")
        if "close" not in self.lose:
            self.issue["state"] = "closed"


OPEN_TRACKER = dict(issue_id=149, stage=ACCEPTED, proposal_id=PROPOSAL_ID,
                    platform="github", target="octo/repo", closed=False)


def tracker_read(**overrides):
    return TrackerRead("verified", **dict(OPEN_TRACKER, **overrides))


def good_proof():
    return Proof("proved", review_commit=REVIEW, proposal_id=PROPOSAL_ID,
                 module_id=PROPOSAL_ID, promotion_commit=PROMOTION)


def published():
    return Publication("published", review_commit=REVIEW, proposal=proposal())


def closing(adapter, journal, confirm=True, tracker=None, proof=None,
            publication=None, mutate=None, before_close=None):
    """Preview against healthy facts, then close against possibly different ones.

    The two phases take separate readers on purpose: every interesting case here is
    something that changed *between* showing the preview and writing, which a single
    set of readers could never express.
    """
    view = build_preview(
        ".", PROPOSAL_ID, "github", "octo/repo", adapter,
        publication_reader=lambda *a, **k: published(),
        tracker_reader=lambda *a, **k: tracker_read(),
        prover=lambda *a, **k: good_proof())
    if mutate:
        view = mutate(dict(view))
    if before_close:
        before_close(adapter)
    return close_preview(
        view, ".", adapter, confirm=confirm, journal_root=journal,
        publication_reader=lambda *a, **k: publication or published(),
        tracker_reader=lambda *a, **k: tracker or tracker_read(),
        prover=lambda *a, **k: proof or good_proof())


class CloseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.journal = pathlib.Path(self.tmp.name) / "journal"

    def tearDown(self):
        self.tmp.cleanup()

    def test_without_confirmation_nothing_is_written(self):
        adapter = WritingAdapter()
        result = closing(adapter, self.journal, confirm=False)
        self.assertEqual(result["state"], "confirmation-required")
        self.assertEqual(adapter.writes, [])

    def test_a_full_closeout_comments_stages_closes_and_reads_back(self):
        adapter = WritingAdapter()
        result = closing(adapter, self.journal)
        self.assertEqual(result["state"], "verified")
        self.assertEqual(adapter.writes, ["comment", "stage", "close"])
        self.assertEqual(result["promotionCommit"], PROMOTION)
        self.assertEqual(result["stage"], PROMOTED_STAGE)
        self.assertTrue(result["closed"])

    def test_a_rerun_writes_nothing_and_reports_already_closed(self):
        adapter = WritingAdapter()
        closing(adapter, self.journal)
        adapter.writes = []
        again = closing(adapter, self.journal,
                        tracker=tracker_read(stage=PROMOTED_STAGE, closed=True))
        self.assertEqual(again["state"], "already-closed")
        self.assertEqual(adapter.writes, [])

    def test_each_step_is_skipped_when_it_already_landed(self):
        adapter = WritingAdapter()
        adapter.comments = [closeout_record(PROPOSAL_ID, REVISION, PROMOTION, REVIEW)]
        adapter.issue["labels"] = [{"name": PROMOTED_STAGE}, {"name": "proposal"}]
        result = closing(adapter, self.journal,
                         tracker=tracker_read(stage=PROMOTED_STAGE))
        self.assertEqual(result["state"], "verified")
        self.assertEqual(adapter.writes, ["close"])

    def test_a_tampered_preview_is_refused(self):
        adapter = WritingAdapter()
        for change in ({"promotionCommit": "0" * 40}, {"issueId": 999},
                       {"record": "something else"}, {"digest": "0" * 64}):
            result = closing(adapter, self.journal,
                             mutate=lambda view, c=change: dict(view, **c))
            self.assertEqual(result["state"], "preview-invalid", change)
            self.assertEqual(adapter.writes, [])

    def test_a_revision_that_moved_between_preview_and_write_is_stale(self):
        adapter = WritingAdapter()
        moved = Publication("published", review_commit=REVIEW,
                            proposal=proposal(revision="sha256:" + "cd" * 32))
        view = build_preview(".", PROPOSAL_ID, "github", "octo/repo", adapter,
                             publication_reader=lambda *a, **k: Publication(
                                 "published", review_commit=REVIEW, proposal=proposal()),
                             tracker_reader=lambda *a, **k: TrackerRead(
                                 "verified", issue_id=149, stage=ACCEPTED,
                                 proposal_id=PROPOSAL_ID, platform="github",
                                 target="octo/repo", closed=False),
                             prover=lambda *a, **k: Proof(
                                 "proved", review_commit=REVIEW,
                                 proposal_id=PROPOSAL_ID, module_id=PROPOSAL_ID,
                                 promotion_commit=PROMOTION))
        result = close_preview(view, ".", adapter, confirm=True,
                               journal_root=self.journal,
                               publication_reader=lambda *a, **k: moved,
                               tracker_reader=lambda *a, **k: TrackerRead(
                                   "verified", issue_id=149, stage=ACCEPTED,
                                   proposal_id=PROPOSAL_ID, platform="github",
                                   target="octo/repo", closed=False),
                               prover=lambda *a, **k: Proof(
                                   "proved", review_commit=REVIEW,
                                   proposal_id=PROPOSAL_ID, module_id=PROPOSAL_ID,
                                   promotion_commit=PROMOTION))
        self.assertEqual(result["state"], "preview-stale")
        self.assertEqual(adapter.writes, [])

    def test_a_proof_that_no_longer_holds_blocks_the_write(self):
        adapter = WritingAdapter()
        for proof in (Proof("not-promoted", proposal_id=PROPOSAL_ID),
                      Proof("proved", review_commit=REVIEW, proposal_id=PROPOSAL_ID,
                            module_id=PROPOSAL_ID, promotion_commit="0" * 40)):
            result = closing(adapter, self.journal, proof=proof)
            self.assertIn(result["state"], ("not-eligible",))
            self.assertEqual(adapter.writes, [])

    def test_a_target_that_moved_after_the_preview_stops_before_writing(self):
        adapter = WritingAdapter()
        def move(target):
            target.facts = dict(target.facts, target="octo/other")
        result = closing(adapter, self.journal, before_close=move)
        self.assertEqual(result["state"], "unknown")
        self.assertEqual(result["diagnostic"], "target-changed")
        self.assertEqual(adapter.writes, [])

    def test_an_item_edited_after_the_preview_is_a_conflict(self):
        adapter = WritingAdapter()
        def edit(target):
            target.issue["body"] = "somebody rewrote this"
        result = closing(adapter, self.journal, before_close=edit)
        self.assertEqual(result["state"], "conflict")
        self.assertEqual(result["diagnostic"], "issue-content-changed")
        self.assertEqual(adapter.writes, [])

    def test_a_lost_close_response_that_actually_closed_reconciles_to_verified(self):
        class Flaky(WritingAdapter):
            def set_closed(self, issue_id):
                self.calls.append("close")
                self.writes.append("close")
                self.issue["state"] = "closed"
                raise RuntimeError("response lost")
        adapter = Flaky()
        result = closing(adapter, self.journal)
        self.assertEqual(result["state"], "verified")

    def test_a_lost_close_response_that_did_not_close_is_partial_and_never_retried(self):
        adapter = WritingAdapter(lose=("close",), fail=("close",))
        result = closing(adapter, self.journal)
        self.assertEqual(result["state"], "partial")
        first = list(adapter.writes)
        adapter.writes = []
        repeat = closing(adapter, self.journal)
        self.assertEqual(repeat["state"], "partial")
        # The comment already carries its marker, so a retry must not add a second one.
        self.assertNotIn("comment", adapter.writes)
        self.assertEqual(first.count("comment"), 1)

    def test_a_binding_recorded_for_another_target_is_a_conflict(self):
        adapter = WritingAdapter(lose=("close",), fail=("close",))
        closing(adapter, self.journal)
        other = WritingAdapter()
        other.facts = dict(other.facts, target="octo/elsewhere")
        tracker = TrackerRead("verified", issue_id=149, stage=ACCEPTED,
                              proposal_id=PROPOSAL_ID, platform="github",
                              target="octo/elsewhere", closed=False)
        result = closing(other, self.journal, tracker=tracker)
        self.assertEqual(result["state"], "conflict")
        self.assertEqual(result["diagnostic"], "binding-target-changed")
        self.assertEqual(other.writes, [])

    def test_an_unfinished_attempt_is_journalled_privately(self):
        adapter = WritingAdapter(lose=("close",), fail=("close",))
        self.assertEqual(closing(adapter, self.journal)["state"], "partial")
        entries = [item for item in self.journal.iterdir()
                   if item.suffix == ".json"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.journal.stat().st_mode & 0o777, 0o700)

    def test_a_finished_closeout_leaves_no_journal_entry_or_lock(self):
        adapter = WritingAdapter()
        self.assertEqual(closing(adapter, self.journal)["state"], "verified")
        self.assertEqual(list(self.journal.iterdir()), [])

    def test_the_result_leaks_no_body_or_raw_error(self):
        adapter = WritingAdapter(fail=("comment",))
        result = closing(adapter, self.journal)
        self.assertNotIn("provider exploded", json.dumps(result))


class ProofRemainsReadOnlyTests(unittest.TestCase):
    """The proof command must stay read-only. Closeout imports it as a caller; a
    `--close`-style switch on a diagnostic command is one flag away from writing to a
    remote tracker by accident, so its surface is pinned here rather than trusted."""

    def test_the_proof_cli_exposes_no_write_switch(self):
        import argparse
        import proposal_promotion_proof as proof_module

        parsers = []
        original = argparse.ArgumentParser.parse_args

        def capture(self, *args, **kwargs):
            parsers.append(self)
            raise SystemExit(0)

        argparse.ArgumentParser.parse_args = capture
        try:
            try:
                proof_module.main(["--proposal-id", "x", "--platform", "github",
                                   "--target", "o/r"])
            except SystemExit:
                pass
        finally:
            argparse.ArgumentParser.parse_args = original
        self.assertEqual(len(parsers), 1)
        options = sorted(option for action in parsers[0]._actions
                         for option in action.option_strings)
        self.assertEqual(options, ["--help", "--platform", "--project",
                                   "--proposal-id", "--prove", "--remote", "--target",
                                   "-h"])

    def test_the_proof_vocabulary_has_no_written_outcome(self):
        import proposal_promotion_proof as proof_module

        source = pathlib.Path(proof_module.__file__).read_text(encoding="utf-8")
        for writing in ("create_comment", "set_closed", "set_stage", "--method",
                        "gh issue", "glab issue", "epiq_issue_"):
            self.assertNotIn(writing, source, writing)


if __name__ == "__main__":
    unittest.main()
