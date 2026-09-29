"""Mainline-review fixtures; no tracker writes."""
import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from proposal_contract import Baseline, Change, Proposal, compute
from proposal_publication import Publication, PublicationPool, read_published_pool
from proposal_mainline_review import (
    ATTESTATION_FIELDS, MainlineReview, as_json,
    accepted, accepted_from_pool, attestation_for, attestation_path_for, discover,
    discover_from_pool, evaluate, local_mainline_context, main, policy_digest,
    policy_from_pool)
from proposal_tracker_read import TrackerRead
from test_proposal_promotion_proof import PromotionFixture, REMOTE_POLICY


MAP = """# Capability Map: fixture

## 目标

Review candidates.

## 模块

| Module id | Responsibility | Depends on |
| --- | --- | --- |
| alpha | Existing capability | — |

Build order: alpha
"""


def publication():
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "map.md"
        path.write_text(MAP, encoding="utf-8")
        digest = compute(str(path))
    proposal = Proposal(
        "gamma", "<!-- spec-guard-proposal:v2 id=gamma revision=sha256:%s -->" % ("b" * 64),
        Baseline("origin", "main", "a" * 40, digest["goalDigest"],
                 {row["id"]: row["rowDigest"] for row in digest["rows"]}, "alpha"),
        Change("gamma", "Gamma.", ("alpha",), "after:alpha"), "v2", "b" * 64)
    return Publication("published", review_commit="a" * 40, proposal=proposal,
                       baseline_map=MAP, review_map=MAP)


POLICY = {
    "authorityId": "mainline",
    "remote": "origin",
    "reviewRef": "refs/heads/integration/mainline",
    "workflowId": "capability-map-integration",
}
CONTEXT = {
    "authorityId": "mainline",
    "branch": "refs/heads/integration/mainline",
    "upstream": "origin/integration/mainline",
    "workflowId": "capability-map-integration",
    "currentModuleId": "alpha",
}
REPO_ROOT = Path(__file__).resolve().parents[3]


class ProposalMainlineReviewTests(unittest.TestCase):
    def tracker(self):
        return TrackerRead("verified", issue_id=7, stage="proposal-stage:published",
                           proposal_id="gamma", platform="github", target="octo/repo")

    def test_repository_policy_matches_the_canonical_single_authority_contract(self):
        path = REPO_ROOT / "spec" / "proposal-mainline-policy.json"
        self.assertTrue(path.is_file(), "repository mainline policy must exist")
        policy = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(policy, dict(POLICY, schemaVersion=1))
        pool = PublicationPool("published", review_commit="a" * 40,
                               review_map=MAP, policy_text=json.dumps(policy))
        self.assertEqual(policy_from_pool(pool), policy)

    def test_only_a_matching_mainline_context_can_create_an_accept_candidate(self):
        result = evaluate(publication(), self.tracker(), "github", "octo/repo",
                          POLICY, CONTEXT, "accept", ())
        self.assertEqual((result.state, result.revision), ("accepted-candidate", "b" * 64))

        foreign = dict(CONTEXT, branch="refs/heads/feature/proposal")
        self.assertEqual(evaluate(publication(), self.tracker(), "github", "octo/repo",
                                  POLICY, foreign, "accept", ()).state, "blocked")

    def test_hard_local_conflict_overrides_an_accept_decision_without_writing(self):
        observation = {"kind": "package-boundary-conflict", "moduleIds": ["alpha"]}
        result = evaluate(publication(), self.tracker(), "github", "octo/repo",
                          POLICY, CONTEXT, "accept", (observation,))
        self.assertEqual(result.state, "needs-revision")

    def test_local_observations_reject_free_text_kinds_and_unrelated_module_ids(self):
        free_text = {"kind": "read this uncommitted code", "moduleIds": ["alpha"]}
        unrelated = {"kind": "anchor-conflict", "moduleIds": ["unrelated"]}
        for observation in (free_text, unrelated):
            result = evaluate(publication(), self.tracker(), "github", "octo/repo",
                              POLICY, CONTEXT, "accept", (observation,))
            self.assertEqual(result.state, "invalid")

    def test_bounded_anchor_suggestion_remains_a_nonshared_review_input(self):
        observation = {"kind": "anchor-suggestion", "moduleIds": ["alpha", "gamma"]}
        result = evaluate(publication(), self.tracker(), "github", "octo/repo",
                          POLICY, CONTEXT, "accept", (observation,))
        self.assertEqual((result.state, result.reason_codes),
                         ("accepted-candidate", ("anchor-suggestion",)))

    def test_only_mainline_module_boundaries_discover_sorted_candidates(self):
        pool = PublicationPool("published", review_commit="a" * 40,
                               publications=(publication(),), review_map=MAP)
        result = discover(pool, lambda ignored: self.tracker(), "github", "octo/repo",
                          POLICY, CONTEXT, "module-deliver")
        self.assertEqual((result.state, result.candidates), ("candidate-list", ("gamma",)))
        blocked = discover(pool, lambda ignored: self.tracker(), "github", "octo/repo",
                           POLICY, CONTEXT, "task-progress")
        self.assertEqual(blocked.state, "blocked")
        missing_module = discover(pool, lambda ignored: self.tracker(), "github", "octo/repo",
                                  POLICY, dict(CONTEXT, currentModuleId="missing"),
                                  "module-deliver")
        self.assertEqual(missing_module.state, "invalid")

    def test_legacy_published_proposal_remains_visible_but_is_not_a_candidate(self):
        legacy = publication()
        legacy.proposal.version = "v1"
        legacy.proposal.revision = None
        pool = PublicationPool("published", review_commit="a" * 40,
                               publications=(legacy,), review_map=MAP)
        result = discover(pool, lambda ignored: self.tracker(), "github", "octo/repo",
                          POLICY, CONTEXT, "module-deliver")
        self.assertEqual((result.state, result.candidates), ("candidate-list", ()))
        self.assertEqual(as_json(result)["skipped"],
                         [{"proposalId": "gamma", "reason": "legacy-revision-required"}])

    def test_discovery_names_each_proposal_it_does_not_list(self):
        pool = PublicationPool("published", review_commit="a" * 40,
                               publications=(publication(),), review_map=MAP)
        for tracker, reason in (
                (TrackerRead("absent", proposal_id="gamma", platform="github",
                             target="octo/repo"), "review-absent"),
                (TrackerRead("verified", issue_id=7, stage="proposal-stage:deferred",
                             proposal_id="gamma", platform="github", target="octo/repo"),
                 "review-deferred")):
            with self.subTest(reason=reason):
                result = discover(pool, lambda ignored: tracker, "github", "octo/repo",
                                  POLICY, CONTEXT, "module-deliver")
                data = as_json(result)
                self.assertEqual(data["state"], "candidate-list")
                self.assertNotIn("candidates", data)
                self.assertEqual(data["skipped"], [{"proposalId": "gamma", "reason": reason}])
        empty = discover(PublicationPool("published", review_commit="a" * 40, review_map=MAP),
                         lambda ignored: self.tracker(), "github", "octo/repo",
                         POLICY, CONTEXT, "module-deliver")
        self.assertNotIn("skipped", as_json(empty))

    def test_accepted_requires_issue_stage_and_exact_attestation(self):
        accepted_tracker = TrackerRead(
            "verified", issue_id=7, stage="proposal-stage:accepted",
            proposal_id="gamma", platform="github", target="octo/repo")
        self.assertEqual(accepted(publication(), accepted_tracker, "github", "octo/repo",
                                  POLICY, {}).state, "blocked")
        evidence = {
            "schemaVersion": 1,
            "proposalId": "gamma",
            "revision": "b" * 64,
            "reviewCommit": "a" * 40,
            "policyDigest": policy_digest(POLICY),
            "authorityId": "mainline",
            "decision": "accept",
        }
        result = accepted(publication(), accepted_tracker, "github", "octo/repo",
                          POLICY, evidence)
        self.assertEqual((result.state, result.authority_id), ("accepted", "mainline"))
        wrong = {
            "schemaVersion": 2, "proposalId": "delta", "revision": "c" * 64,
            "reviewCommit": "d" * 40, "policyDigest": "0" * 64,
            "authorityId": "other", "decision": "reject",
        }
        self.assertEqual(set(wrong), set(evidence))
        for field, value in sorted(wrong.items()):
            with self.subTest(field=field):
                result = accepted(publication(), accepted_tracker, "github", "octo/repo",
                                  POLICY, dict(evidence, **{field: value}))
                self.assertEqual((result.state, result.diagnostic),
                                 ("blocked", "acceptance-attestation-invalid"))
        result = accepted(publication(), accepted_tracker, "github", "octo/repo",
                          POLICY, dict(evidence, note="extra"))
        self.assertEqual(result.state, "blocked")

    def test_acceptance_evidence_and_policy_are_read_only_pool_facts(self):
        remote_policy = dict(POLICY, schemaVersion=1)
        evidence = {
            "schemaVersion": 1, "proposalId": "gamma", "revision": "b" * 64,
            "reviewCommit": "a" * 40, "policyDigest": policy_digest(remote_policy),
            "authorityId": "mainline", "decision": "accept",
        }
        pool = PublicationPool(
            "published", review_commit="a" * 40, publications=(publication(),),
            review_map=MAP, policy_text=json.dumps(remote_policy),
            attestation_texts={"gamma": json.dumps(evidence)})
        self.assertEqual(policy_from_pool(pool), remote_policy)
        tracker = TrackerRead("verified", issue_id=7, stage="proposal-stage:accepted",
                              proposal_id="gamma", platform="github", target="octo/repo")
        self.assertEqual(accepted_from_pool(pool, publication(), tracker, "github",
                                            "octo/repo").state, "accepted")
        pool.attestation_texts["gamma"] = "{}"
        self.assertEqual(accepted_from_pool(pool, publication(), tracker, "github",
                                            "octo/repo").state, "blocked")

    def test_context_reads_this_worktree_topology_instead_of_caller_branch_text(self):
        remote_policy = dict(POLICY, schemaVersion=1)
        pool = PublicationPool("published", review_commit="a" * 40, review_map=MAP,
                               policy_text=json.dumps(remote_policy))
        with patch("proposal_mainline_review._git_text",
                   side_effect=("refs/heads/integration/mainline",
                                "origin/integration/mainline")), patch(
                       "proposal_mainline_review.subprocess.run",
                       return_value=SimpleNamespace(returncode=0)):
            context = local_mainline_context("/fixture", pool, "mainline",
                                             "module-deliver", "alpha")
        self.assertEqual(context, CONTEXT)
        with patch("proposal_mainline_review._git_text",
                   side_effect=("refs/heads/feature/proposal",
                                "origin/integration/mainline")):
            self.assertIsNone(local_mainline_context("/fixture", pool, "mainline",
                                                     "module-deliver", "alpha"))

    def test_discovery_wrapper_cannot_use_a_callers_forged_context(self):
        remote_policy = dict(POLICY, schemaVersion=1)
        pool = PublicationPool("published", review_commit="a" * 40,
                               publications=(publication(),), review_map=MAP,
                               policy_text=json.dumps(remote_policy))
        with patch("proposal_mainline_review.local_mainline_context", return_value=None):
            result = discover_from_pool("/fixture", pool, lambda ignored: self.tracker(),
                                        "github", "octo/repo", "mainline",
                                        "module-deliver", "alpha")
        self.assertEqual(result.state, "blocked")

    def test_unusable_pool_is_reported_before_any_git_or_policy_check(self):
        for state in ("unknown", "invalid"):
            pool = PublicationPool(state, diagnostic="remote default branch is unavailable")
            with self.subTest(state=state), patch(
                    "proposal_mainline_review._git_text",
                    side_effect=AssertionError("must not read Git")):
                result = discover_from_pool("/fixture", pool, lambda ignored: self.tracker(),
                                            "github", "octo/repo", "mainline",
                                            "module-deliver", "alpha")
                self.assertEqual(as_json(result),
                                 {"state": state, "diagnostic": "proposal-pool-%s" % state})
        # 结果状态只能取自 spec 的允许集合；陌生的池状态一律按 unknown 报告。
        for pool in (None, PublicationPool("absent")):
            with self.subTest(pool=pool):
                result = discover_from_pool("/fixture", pool, lambda ignored: self.tracker(),
                                            "github", "octo/repo", "mainline",
                                            "module-deliver", "alpha")
                self.assertEqual(as_json(result),
                                 {"state": "unknown", "diagnostic": "proposal-pool-unknown"})

    def test_context_failures_keep_distinct_diagnostic_codes(self):
        remote_policy = dict(POLICY, schemaVersion=1)
        good = PublicationPool("published", review_commit="a" * 40, review_map=MAP,
                               publications=(publication(),),
                               policy_text=json.dumps(remote_policy))
        no_policy = PublicationPool("published", review_commit="a" * 40, review_map=MAP,
                                    publications=(publication(),))
        mainline = ("refs/heads/integration/mainline", "origin/integration/mainline")
        cases = (
            ("policy", no_policy, "mainline", mainline, 0, "mainline-policy-invalid"),
            ("authority", good, "someone-else", mainline, 0, "mainline-authority-mismatch"),
            ("detached", good, "mainline", (None, None), 0, "mainline-branch-unavailable"),
            ("branch", good, "mainline", ("refs/heads/feature/x", mainline[1]), 0,
             "mainline-context-invalid"),
            ("behind", good, "mainline", mainline, 1, "mainline-review-commit-not-ancestor"),
            ("git-error", good, "mainline", mainline, 128, "mainline-topology-unavailable"),
        )
        for name, pool, authority, git_text, returncode, code in cases:
            with self.subTest(name), patch("proposal_mainline_review._git_text",
                                           side_effect=git_text), patch(
                    "proposal_mainline_review.subprocess.run",
                    return_value=SimpleNamespace(returncode=returncode)):
                result = discover_from_pool("/fixture", pool, lambda ignored: self.tracker(),
                                            "github", "octo/repo", authority,
                                            "module-deliver", "alpha")
                self.assertEqual(as_json(result), {"state": "blocked", "diagnostic": code})

    def run_main(self, pool, *extra, context=(None, "mainline-context-invalid"),
                 boundary="module-deliver"):
        output = io.StringIO()
        with patch("proposal_mainline_review.read_published_pool", return_value=pool), patch(
                "proposal_mainline_review._local_mainline_context", return_value=context), patch(
                "proposal_mainline_review.read_tracker", return_value=self.tracker()), \
                redirect_stdout(output):
            self.assertEqual(main(["--platform", "github", "--target", "octo/repo",
                                   "--authority-id", "mainline", "--boundary", boundary,
                                   "--current-module-id", "alpha"] + list(extra)), 0)
        return json.loads(output.getvalue())

    def test_cli_reports_the_pool_state_in_both_modes(self):
        pool = PublicationPool("unknown", diagnostic="remote default branch moved or fetch failed")
        expected = {"state": "unknown", "diagnostic": "proposal-pool-unknown"}
        self.assertEqual(self.run_main(pool), expected)
        self.assertEqual(self.run_main(pool, "--proposal-id", "gamma", "--decision", "accept"),
                         expected)

    def test_cli_decision_distinguishes_context_and_missing_proposal(self):
        remote_policy = dict(POLICY, schemaVersion=1)
        pool = PublicationPool("published", review_commit="a" * 40, review_map=MAP,
                               publications=(publication(),),
                               policy_text=json.dumps(remote_policy))
        decide = ("--proposal-id", "gamma", "--decision", "accept")
        self.assertEqual(
            self.run_main(pool, *decide, context=(None, "mainline-review-commit-not-ancestor")),
            {"state": "blocked", "diagnostic": "mainline-review-commit-not-ancestor"})
        self.assertEqual(
            self.run_main(pool, "--proposal-id", "missing", "--decision", "accept",
                          context=(CONTEXT, None)),
            {"state": "invalid", "diagnostic": "proposal-not-published"})
        self.assertEqual(self.run_main(pool, *decide, context=(CONTEXT, None))["state"],
                         "accepted-candidate")

    def test_skipped_proposals_are_reported_beside_candidates_and_decisions(self):
        remote_policy = dict(POLICY, schemaVersion=1)
        skipped = (("beta", "Proposal baseline commit is not on remote default branch"),)
        expected = [{"proposalId": "beta", "diagnostic": "proposal-baseline-unavailable"}]
        pool = PublicationPool("published", review_commit="a" * 40, review_map=MAP,
                               publications=(publication(),), skipped=skipped,
                               policy_text=json.dumps(remote_policy))
        healthy = PublicationPool("published", review_commit="a" * 40, review_map=MAP,
                                  publications=(publication(),),
                                  policy_text=json.dumps(remote_policy))
        listing = self.run_main(pool, context=(CONTEXT, None))
        self.assertEqual(listing, dict(self.run_main(healthy, context=(CONTEXT, None)),
                                       skippedProposals=expected))
        self.assertNotIn("skippedProposals", self.run_main(healthy, context=(CONTEXT, None)))
        self.assertNotIn("skipped", listing)
        decide = ("--proposal-id", "gamma", "--decision", "accept")
        self.assertEqual(self.run_main(pool, *decide, context=(CONTEXT, None))["skippedProposals"],
                         expected)
        # Querying the excluded proposal is the ordinary "not in pool" result.
        excluded = self.run_main(pool, "--proposal-id", "beta", "--decision", "accept",
                                 context=(CONTEXT, None))
        self.assertEqual((excluded["state"], excluded["diagnostic"]),
                         ("invalid", "proposal-not-published"))
        self.assertEqual(excluded["skippedProposals"], expected)

    def test_json_keeps_only_code_shaped_diagnostics(self):
        self.assertEqual(as_json(MainlineReview("blocked", diagnostic="mainline-policy-invalid")),
                         {"state": "blocked", "diagnostic": "mainline-policy-invalid"})
        for raw in ("review capability map is missing", "Traceback: /tmp/x", None,
                    "Mainline-Blocked", "code-"):
            with self.subTest(raw=raw):
                self.assertEqual(as_json(MainlineReview("unknown", diagnostic=raw)),
                                 {"state": "unknown", "diagnostic": "mainline-unknown"})

    def test_json_omits_policy_observations_and_raw_diagnostics(self):
        result = evaluate(publication(), self.tracker(), "github", "octo/repo",
                          POLICY, CONTEXT, "accept", ())
        data = as_json(result)
        self.assertEqual(data["state"], "accepted-candidate")
        dumped = __import__("json").dumps(data)
        # The digest, not the raw policy fields, is allowed to appear (it is the
        # copyable attestation's policyDigest, the whole point of this result).
        self.assertNotIn(POLICY["remote"], dumped)
        self.assertNotIn(POLICY["reviewRef"], dumped)
        self.assertNotIn(POLICY["workflowId"], dumped)
        self.assertNotIn("octo/repo", dumped)

    def test_accepted_candidate_json_carries_a_copyable_attestation_and_path(self):
        result = evaluate(publication(), self.tracker(), "github", "octo/repo",
                          POLICY, CONTEXT, "accept", ())
        self.assertEqual(result.state, "accepted-candidate")
        data = as_json(result)
        self.assertEqual(data["attestationPath"],
                         "spec/proposal-acceptances/gamma-%s.json" % ("b" * 64))
        attestation = data["attestation"]
        self.assertEqual(set(attestation), ATTESTATION_FIELDS)
        self.assertEqual(attestation, {
            "schemaVersion": 1,
            "proposalId": "gamma",
            "revision": "b" * 64,
            "reviewCommit": "a" * 40,
            "policyDigest": policy_digest(POLICY),
            "authorityId": "mainline",
            "decision": "accept",
        })
        self.assertEqual(attestation_for(publication(), POLICY), attestation)
        self.assertEqual(attestation_path_for(publication()), data["attestationPath"])

    def test_emitted_attestation_round_trips_through_the_accepted_checker(self):
        result = evaluate(publication(), self.tracker(), "github", "octo/repo",
                          POLICY, CONTEXT, "accept", ())
        accepted_tracker = TrackerRead(
            "verified", issue_id=7, stage="proposal-stage:accepted",
            proposal_id="gamma", platform="github", target="octo/repo")
        outcome = accepted(publication(), accepted_tracker, "github", "octo/repo",
                           POLICY, result.attestation)
        self.assertEqual(outcome.state, "accepted")

    def test_only_accepted_candidate_state_carries_attestation_fields(self):
        for decision, expected_state in (("reject", "rejected-candidate"),
                                         ("defer", "deferred"),
                                         ("needs-revision", "needs-revision")):
            with self.subTest(decision=decision):
                result = evaluate(publication(), self.tracker(), "github", "octo/repo",
                                  POLICY, CONTEXT, decision, ())
                self.assertEqual(result.state, expected_state)
                data = as_json(result)
                self.assertNotIn("attestation", data)
                self.assertNotIn("attestationPath", data)
        observation = {"kind": "package-boundary-conflict", "moduleIds": ["alpha"]}
        needs_revision = evaluate(publication(), self.tracker(), "github", "octo/repo",
                                  POLICY, CONTEXT, "accept", (observation,))
        self.assertEqual(needs_revision.state, "needs-revision")
        blocked_data = as_json(needs_revision)
        self.assertNotIn("attestation", blocked_data)
        self.assertNotIn("attestationPath", blocked_data)
        blocked = evaluate(publication(), self.tracker(), "github", "octo/repo",
                           POLICY, dict(CONTEXT, branch="refs/heads/feature/proposal"),
                           "accept", ())
        self.assertEqual(blocked.state, "blocked")
        self.assertNotIn("attestation", as_json(blocked))
        self.assertNotIn("attestationPath", as_json(blocked))

    BOUNDARIES = ("module-deliver", "module-advance", "module-interrupt")

    def test_boundary_set_is_defined_once_and_matches_the_guidance_set(self):
        import proposal_mainline_review as review_module
        from proposal_boundary_guidance import REMINDER_BOUNDARIES
        self.assertEqual(review_module.MAINLINE_BOUNDARIES, frozenset(self.BOUNDARIES))
        self.assertEqual(REMINDER_BOUNDARIES, review_module.MAINLINE_BOUNDARIES)

    def test_module_interrupt_is_treated_exactly_like_module_advance(self):
        remote_policy = dict(POLICY, schemaVersion=1)
        pool = PublicationPool("published", review_commit="a" * 40,
                               publications=(publication(),), review_map=MAP,
                               policy_text=json.dumps(remote_policy))
        mainline = ("refs/heads/integration/mainline", "origin/integration/mainline")
        contexts = {}
        discovered = {}
        for boundary in ("module-advance", "module-interrupt"):
            with patch("proposal_mainline_review._git_text", side_effect=mainline), patch(
                    "proposal_mainline_review.subprocess.run",
                    return_value=SimpleNamespace(returncode=0)):
                contexts[boundary] = local_mainline_context(
                    "/fixture", pool, "mainline", boundary, "alpha")
            with patch("proposal_mainline_review._git_text", side_effect=mainline), patch(
                    "proposal_mainline_review.subprocess.run",
                    return_value=SimpleNamespace(returncode=0)):
                discovered[boundary] = as_json(discover_from_pool(
                    "/fixture", pool, lambda ignored: self.tracker(), "github",
                    "octo/repo", "mainline", boundary, "alpha"))
        self.assertEqual(contexts["module-interrupt"], CONTEXT)
        self.assertEqual(contexts["module-interrupt"], contexts["module-advance"])
        self.assertEqual(discovered["module-interrupt"]["state"], "candidate-list")
        self.assertEqual(discovered["module-interrupt"], discovered["module-advance"])
        self.assertEqual(discover(pool, lambda ignored: self.tracker(), "github", "octo/repo",
                                  POLICY, CONTEXT, "module-interrupt").candidates, ("gamma",))

    def test_unknown_boundary_is_still_invalid_in_every_entry(self):
        remote_policy = dict(POLICY, schemaVersion=1)
        pool = PublicationPool("published", review_commit="a" * 40,
                               publications=(publication(),), review_map=MAP,
                               policy_text=json.dumps(remote_policy))
        self.assertIsNone(local_mainline_context("/fixture", pool, "mainline",
                                                 "module-pause", "alpha"))
        result = discover_from_pool("/fixture", pool, lambda ignored: self.tracker(),
                                    "github", "octo/repo", "mainline", "module-pause", "alpha")
        self.assertEqual(as_json(result),
                         {"state": "blocked", "diagnostic": "mainline-boundary-invalid"})
        blocked = discover(pool, lambda ignored: self.tracker(), "github", "octo/repo",
                           POLICY, CONTEXT, "module-pause")
        self.assertEqual(as_json(blocked),
                         {"state": "blocked", "diagnostic": "mainline-boundary-invalid"})
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(["--platform", "github", "--target", "octo/repo", "--authority-id",
                  "mainline", "--boundary", "module-pause", "--current-module-id", "alpha"])

    def test_cli_accepts_module_interrupt(self):
        pool = PublicationPool("unknown", diagnostic="remote default branch moved or fetch failed")
        output = io.StringIO()
        with patch("proposal_mainline_review.read_published_pool", return_value=pool), \
                redirect_stdout(output):
            self.assertEqual(main(["--platform", "github", "--target", "octo/repo",
                                   "--authority-id", "mainline", "--boundary",
                                   "module-interrupt", "--current-module-id", "alpha"]), 0)
        self.assertEqual(json.loads(output.getvalue()),
                         {"state": "unknown", "diagnostic": "proposal-pool-unknown"})

    def test_boundary_never_enters_the_attestation_or_policy_digest(self):
        import inspect
        self.assertNotIn("boundary", inspect.signature(evaluate).parameters)
        self.assertNotIn("boundary", inspect.signature(attestation_for).parameters)
        self.assertNotIn("boundary", inspect.signature(policy_digest).parameters)
        self.assertNotIn("boundary", inspect.signature(attestation_path_for).parameters)
        self.assertNotIn("boundary", CONTEXT)
        results = [self.run_main(
            PublicationPool("published", review_commit="a" * 40, review_map=MAP,
                            publications=(publication(),),
                            policy_text=json.dumps(dict(POLICY, schemaVersion=1))),
            "--proposal-id", "gamma", "--decision", "accept", context=(CONTEXT, None),
            boundary=boundary) for boundary in self.BOUNDARIES]
        self.assertEqual(results[0]["state"], "accepted-candidate")
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0], results[2])
        self.assertNotIn("boundary", json.dumps(results[0]["attestation"]))
        self.assertNotIn("module-", json.dumps(results[0]["attestation"]))
        self.assertNotIn("module-", results[0]["attestationPath"])


class EmittedAttestationPoolReaderTests(PromotionFixture):
    """Confirm `attestation_path_for` names the exact path the pool reader loads."""

    skip_promotion = True

    def test_attestation_path_matches_where_the_pool_reader_loads_it(self):
        (self.seed / "spec/proposal-mainline-policy.json").write_text(
            json.dumps(REMOTE_POLICY), encoding="utf-8")
        self.git(self.seed, "add", "spec/proposal-mainline-policy.json")
        self.git(self.seed, "commit", "-m", "add mainline policy")
        self.git(self.seed, "push", "origin", "trunk")

        published_tracker = TrackerRead(
            "verified", issue_id=42, stage="proposal-stage:published",
            proposal_id="gamma", platform="github", target="octo/spec-guard")
        result = evaluate(self.publication, published_tracker, "github", "octo/spec-guard",
                          REMOTE_POLICY, CONTEXT, "accept", ())
        self.assertEqual(result.state, "accepted-candidate")

        target_path = self.seed / result.attestation_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(json.dumps(result.attestation), encoding="utf-8")
        self.git(self.seed, "add", result.attestation_path)
        self.git(self.seed, "commit", "-m", "attest gamma with the emitted attestation")
        self.git(self.seed, "push", "origin", "trunk")

        pool = read_published_pool(self.consumer, "origin")
        self.assertEqual(pool.state, "published")
        self.assertEqual(json.loads(pool.attestation_texts["gamma"]), result.attestation)

        accepted_tracker = TrackerRead(
            "verified", issue_id=42, stage="proposal-stage:accepted",
            proposal_id="gamma", platform="github", target="octo/spec-guard")
        outcome = accepted_from_pool(pool, self.publication, accepted_tracker,
                                     "github", "octo/spec-guard")
        self.assertEqual(outcome.state, "accepted")


if __name__ == "__main__":
    unittest.main()
