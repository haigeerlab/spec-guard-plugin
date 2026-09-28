"""In-memory Proposal review precedence fixtures; no Git or tracker transport."""
import unittest
import io
import json
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from proposal_contract import Baseline, Change, Proposal, compute
from proposal_publication import Publication
from proposal_review import as_json, main, review
from proposal_tracker_read import TrackerRead


BASE_MAP = """# Capability Map: review fixture

## 目标

Keep review facts explicit.

## 模块

| Module id | Responsibility | Depends on |
| --- | --- | --- |
| alpha | Existing capability | — |

Build order: alpha
"""

REVIEW_MAP = BASE_MAP
ABSORBED_MAP = BASE_MAP.replace(
    "| alpha | Existing capability | — |",
    "| alpha | Existing capability | — |\n| gamma | Proposed capability | alpha |").replace(
        "Build order: alpha", "Build order: alpha → gamma")
UNRELATED_MAP = BASE_MAP.replace(
    "| alpha | Existing capability | — |",
    "| alpha | Existing capability | — |\n| beta | Unrelated capability | alpha |").replace(
        "Build order: alpha", "Build order: alpha → beta")
ANCHOR_MAP = BASE_MAP.replace(
    "| alpha | Existing capability | — |",
    "| alpha | Existing capability | — |\n| beta | Anchor capability | — |").replace(
        "Build order: alpha", "Build order: alpha → beta")
REORDERED_ANCHOR_MAP = ANCHOR_MAP.replace("Build order: alpha → beta", "Build order: beta → alpha")


def proposal():
    with tempfile.TemporaryDirectory(prefix="sg-proposal-review-fixture-") as temp:
        path = Path(temp) / "baseline.md"
        path.write_text(BASE_MAP, encoding="utf-8")
        digest = compute(str(path))
    return Proposal("gamma", "<!-- spec-guard-proposal:v1 id=gamma -->",
                    Baseline("origin", "trunk", "0" * 40, digest["goalDigest"],
                             {row["id"]: row["rowDigest"] for row in digest["rows"]}, "alpha"),
                    Change("gamma", "Proposed capability.", ("alpha",), "after:alpha"))


def published(review_map=REVIEW_MAP):
    return Publication("published", review_commit="a" * 40, proposal=proposal(),
                       baseline_map=BASE_MAP, review_map=review_map)


def anchor_published(review_map=ANCHOR_MAP):
    with tempfile.TemporaryDirectory(prefix="sg-proposal-review-fixture-") as temp:
        path = Path(temp) / "baseline.md"
        path.write_text(ANCHOR_MAP, encoding="utf-8")
        digest = compute(str(path))
    item = Proposal("gamma", "<!-- spec-guard-proposal:v1 id=gamma -->",
                    Baseline("origin", "trunk", "0" * 40, digest["goalDigest"],
                             {row["id"]: row["rowDigest"] for row in digest["rows"]},
                             "alpha → beta"),
                    Change("gamma", "Proposed capability.", ("alpha",), "after:beta"))
    return Publication("published", review_commit="a" * 40, proposal=item,
                       baseline_map=ANCHOR_MAP, review_map=review_map)


def verified(stage):
    return TrackerRead("verified", issue_id=42, stage=stage, proposal_id="gamma",
                       platform="github", target="octo/spec-guard")


class ProposalReviewFixtures(unittest.TestCase):
    def test_interprets_each_verified_fresh_stage_without_side_effects(self):
        expected = {
            "proposal-stage:draft": "awaiting-review",
            "proposal-stage:published": "awaiting-review",
            "proposal-stage:in-review": "in-review",
            "proposal-stage:accepted": "accepted",
            "proposal-stage:rejected": "rejected",
            "proposal-stage:promoted": "promoted-claim",
        }
        for stage, state in expected.items():
            result = review(published(), verified(stage), "github", "octo/spec-guard")
            self.assertEqual((result.state, result.review_commit, result.issue_id, result.stage),
                             (state, "a" * 40, 42, stage))

    def test_publication_and_tracker_blocking_states_take_precedence(self):
        self.assertEqual(review(Publication("absent"), verified("proposal-stage:accepted"),
                                "github", "octo/spec-guard").state, "absent")
        self.assertEqual(review(Publication("invalid"), verified("proposal-stage:accepted"),
                                "github", "octo/spec-guard").state, "invalid")
        self.assertEqual(review(Publication("unknown"), verified("proposal-stage:accepted"),
                                "github", "octo/spec-guard").state, "unknown")
        self.assertEqual(review(published(), TrackerRead("absent"), "github",
                                "octo/spec-guard").state, "absent")
        self.assertEqual(review(published(), TrackerRead("invalid"), "github",
                                "octo/spec-guard").state, "invalid")
        self.assertEqual(review(published(), TrackerRead("unknown"), "github",
                                "octo/spec-guard").state, "unknown")

    def test_json_names_which_layer_blocked_the_review(self):
        missing = as_json(review(Publication("absent"), None, "github", "octo/spec-guard"))
        self.assertEqual(missing, {"state": "absent", "diagnostic": "publication-absent"})
        no_issue = as_json(review(published(), TrackerRead("absent"), "github", "octo/spec-guard"))
        self.assertEqual((no_issue["state"], no_issue["diagnostic"], no_issue["proposalId"]),
                         ("absent", "tracker-absent", "gamma"))
        self.assertEqual(no_issue["reviewCommit"], "a" * 40)
        for state in ("invalid", "unknown"):
            with self.subTest(state=state):
                self.assertEqual(as_json(review(Publication(state), None, "github",
                                                "octo/spec-guard"))["diagnostic"],
                                 "publication-%s" % state)
                self.assertEqual(as_json(review(published(), TrackerRead(state), "github",
                                                "octo/spec-guard"))["diagnostic"],
                                 "tracker-%s" % state)
        self.assertEqual(as_json(review(published(), None, "github", "octo/spec-guard")),
                         {"state": "unknown", "reviewCommit": "a" * 40, "proposalId": "gamma",
                          "diagnostic": "tracker-unknown"})

    def test_absorbed_module_is_stale_before_an_accepted_stage(self):
        tracker = TrackerRead("verified", issue_id=42, stage="proposal-stage:accepted",
                              proposal_id="gamma", platform="gitlab", target=17)
        result = review(published(ABSORBED_MAP), tracker, "gitlab", 17)
        self.assertEqual(result.state, "stale")

    def test_goal_drift_is_stale_but_unrelated_new_module_is_fresh(self):
        drifted = BASE_MAP.replace("Keep review facts explicit.", "Changed review facts.")
        self.assertEqual(review(published(drifted), verified("proposal-stage:accepted"),
                                "github", "octo/spec-guard").state, "stale")
        self.assertEqual(review(published(UNRELATED_MAP), verified("proposal-stage:accepted"),
                                "github", "octo/spec-guard").state, "accepted")

    def test_anchor_that_precedes_a_dependency_is_stale_even_when_rows_match(self):
        self.assertEqual(review(anchor_published(REORDERED_ANCHOR_MAP),
                                verified("proposal-stage:accepted"), "github",
                                "octo/spec-guard").state, "stale")

    def test_json_exposes_safe_review_identity_without_diagnostics(self):
        result = review(published(), verified("proposal-stage:accepted"), "github",
                        "octo/spec-guard")
        data = as_json(result)
        self.assertEqual(data["state"], "accepted")
        self.assertEqual(data["reviewCommit"], "a" * 40)
        self.assertEqual(data["proposalId"], "gamma")
        self.assertEqual(data["issueId"], 42)
        self.assertNotIn("Capability Map", json.dumps(data))

    def test_invalid_map_and_mismatched_tracker_identity_are_invalid(self):
        self.assertEqual(review(published("not a capability map"),
                                verified("proposal-stage:accepted"), "github",
                                "octo/spec-guard").state, "invalid")
        wrong = TrackerRead("verified", issue_id=42, stage="proposal-stage:accepted",
                            proposal_id="other", platform="github", target="octo/spec-guard")
        self.assertEqual(review(published(), wrong, "github", "octo/spec-guard").state,
                         "invalid")

    def test_review_keeps_a_v2_proposal_revision_in_its_safe_output(self):
        item = proposal()
        item.version = "v2"
        item.revision = "b" * 64
        publication = Publication("published", review_commit="a" * 40, proposal=item,
                                  baseline_map=BASE_MAP, review_map=REVIEW_MAP)

        result = review(publication, verified("proposal-stage:published"),
                        "github", "octo/spec-guard")

        self.assertEqual(result.revision, "b" * 64)
        self.assertEqual(as_json(result)["revision"], "b" * 64)



class ProposalReviewCliTests(unittest.TestCase):
    def run_cli(self, publication, tracker, *target):
        output = io.StringIO()
        with patch("proposal_publication.read_published", return_value=publication) as read, \
                patch("proposal_tracker_read.read_tracker", return_value=tracker) as tracker_read, \
                redirect_stdout(output):
            self.assertEqual(main(["--proposal-id", "gamma"] + list(target or
                                   ("--platform", "github", "--target", "octo/spec-guard"))), 0)
        return json.loads(output.getvalue()), read, tracker_read

    def test_cli_composes_publication_tracker_and_review(self):
        result, read, tracker_read = self.run_cli(published(), verified("proposal-stage:in-review"))
        self.assertEqual(result["state"], "in-review")
        self.assertEqual(result["issueId"], 42)
        self.assertEqual(read.call_args.args, (".", "gamma", "origin"))
        self.assertEqual(tracker_read.call_args.args[1:], ("github", "octo/spec-guard"))

    def test_cli_does_not_read_the_tracker_for_an_unpublished_proposal(self):
        for state in ("absent", "unknown", "invalid"):
            with self.subTest(state=state):
                result, _, tracker_read = self.run_cli(Publication(state), None)
                self.assertEqual(result["state"], state)
                tracker_read.assert_not_called()

    def test_cli_passes_a_numeric_gitlab_project_id(self):
        _, _, tracker_read = self.run_cli(published(), verified("proposal-stage:published"),
                                          "--platform", "gitlab", "--target", "42")
        self.assertEqual(tracker_read.call_args.args[1:], ("gitlab", 42))


if __name__ == "__main__":
    unittest.main()
