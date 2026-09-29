"""Promotion-proof fixtures begin with safe input-state precedence."""
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from capability_map import parse_map
from proposal_contract import Change, compute, compute_revision
from proposal_publication import (
    Publication, PublicationPool, read_published, skipped_as_json)
import proposal_promotion_proof
from proposal_promotion_proof import (
    Preflight, Proof, _matches, as_json, main, preflight, preflight_as_json, prove)
from proposal_tracker_read import TrackerRead


_HOOKS = Path(__file__).parent
_DIGEST_SPEC = importlib.util.spec_from_file_location("proposal_digest", _HOOKS / "spec-digest.py")
_DIGEST = importlib.util.module_from_spec(_DIGEST_SPEC)
_DIGEST_SPEC.loader.exec_module(_DIGEST)

BASE_MAP = """# Capability Map: promotion fixture

## 目标

Keep promotion facts explicit.

## 模块

| Module id | Responsibility | Depends on |
| --- | --- | --- |
| alpha | Existing capability | — |

Build order: alpha
"""

PROMOTION_MAP = BASE_MAP.replace(
    "| alpha | Existing capability | — |",
    "| alpha | Existing capability | — |\n| gamma | Gamma. | alpha |").replace(
        "Build order: alpha", "Build order: alpha → gamma")


DRIFT_MAP = BASE_MAP.replace("Existing capability", "Changed capability")

LEGACY_POLICY = "{ this is not valid policy json"

class PromotionFixture(unittest.TestCase):
    promotion_map = PROMOTION_MAP
    merge_promotion = False
    include_artifacts = True
    include_extra_file = False
    skip_promotion = False
    legacy_files = False
    drift_map = None

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sg-proposal-promotion-proof-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.seed = self.root / "seed"
        self.remote = self.root / "remote.git"
        self.consumer = self.root / "consumer"
        self.git(self.root, "init", "--bare", "-b", "trunk", str(self.remote))
        self.git(self.root, "init", "-b", "trunk", str(self.seed))
        self.git(self.seed, "config", "user.email", "test@example.invalid")
        self.git(self.seed, "config", "user.name", "test")
        (self.seed / "spec").mkdir()
        (self.seed / "spec/CAPABILITY-MAP.md").write_text(BASE_MAP, encoding="utf-8")
        self.git(self.seed, "add", "spec/CAPABILITY-MAP.md")
        self.git(self.seed, "commit", "-m", "baseline")
        self.baseline = self.git(self.seed, "rev-parse", "HEAD").strip()
        self.write_proposal()
        self.git(self.seed, "add", "spec/proposals/gamma.md")
        if self.legacy_files:
            self.write_legacy_files()
        self.git(self.seed, "commit", "-m", "publish proposal")
        self.publish_commit = self.git(self.seed, "rev-parse", "HEAD").strip()
        self.git(self.seed, "remote", "add", "origin", str(self.remote))
        self.git(self.seed, "push", "origin", "trunk")
        self.git(self.root, "clone", str(self.remote), str(self.consumer))
        self.publication = read_published(self.consumer, "gamma")
        if self.drift_map is not None:
            (self.seed / "spec/CAPABILITY-MAP.md").write_text(self.drift_map, encoding="utf-8")
            self.git(self.seed, "add", "spec/CAPABILITY-MAP.md")
            self.git(self.seed, "commit", "-m", "drift alpha")
            self.drift_commit = self.git(self.seed, "rev-parse", "HEAD").strip()
        if self.skip_promotion:
            (self.seed / "README.md").write_text("still unpromoted\n", encoding="utf-8")
            self.git(self.seed, "add", "README.md")
            self.git(self.seed, "commit", "-m", "unrelated change")
            self.promotion_commit = None
        elif self.merge_promotion:
            self.git(self.seed, "checkout", "-b", "proposal-gamma")
            self.write_promotion_artifacts()
            self.git(self.seed, "commit", "-m", "prepare gamma")
            self.feature_commit = self.git(self.seed, "rev-parse", "HEAD").strip()
            self.git(self.seed, "checkout", "trunk")
            (self.seed / "README.md").write_text("mainline change\n", encoding="utf-8")
            self.git(self.seed, "add", "README.md")
            self.git(self.seed, "commit", "-m", "mainline change")
            self.pre_merge_commit = self.git(self.seed, "rev-parse", "HEAD").strip()
            self.git(self.seed, "merge", "--no-ff", "proposal-gamma", "-m", "merge gamma")
            self.promotion_commit = self.git(self.seed, "rev-parse", "HEAD").strip()
        else:
            self.parent_commit = self.git(self.seed, "rev-parse", "HEAD").strip()
            self.write_promotion_artifacts()
            self.git(self.seed, "commit", "-m", "promote gamma")
            self.promotion_commit = self.git(self.seed, "rev-parse", "HEAD").strip()
        self.git(self.seed, "push", "origin", "trunk")

    def tracker(self, stage="proposal-stage:accepted"):
        return TrackerRead("verified", issue_id=42, stage=stage, proposal_id="gamma",
                           platform="github", target="octo/spec-guard")

    def prove(self, stage="proposal-stage:accepted"):
        return prove(self.consumer, self.publication, self.tracker(stage),
                     "github", "octo/spec-guard")

    def write_legacy_files(self):
        """Leftover policy and acceptance record that must never influence anything."""
        (self.seed / "spec/proposal-mainline-policy.json").write_text(LEGACY_POLICY,
                                                                       encoding="utf-8")
        (self.seed / "spec/proposal-acceptances").mkdir()
        (self.seed / "spec/proposal-acceptances/gamma-stray.json").write_text(
            "{}", encoding="utf-8")
        self.git(self.seed, "add", "spec/proposal-mainline-policy.json",
                 "spec/proposal-acceptances")

    def git(self, cwd, *args):
        result = subprocess.run(["git", "-C", str(cwd)] + list(args), text=True,
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def write_proposal(self):
        digest = _DIGEST.compute(str(self.seed / "spec/CAPABILITY-MAP.md"))
        rows = "\n".join("| %s | %s |" % (item["id"], item["rowDigest"])
                         for item in digest["rows"])
        text = """# Proposal: Add gamma
<!-- spec-guard-proposal:v2 id=gamma revision=sha256:%s -->

## Summary

Gamma is separate.

## Integration intent

| Field | Value |
| --- | --- |
| Problem | Gamma is absent. |
| In scope | Gamma module. |
| Out of scope | Existing modules. |
| Safety boundaries | No automatic writes. |
| Initial dependency assumptions | alpha is stable. |
| Acceptance intent | Verify gamma. |

## Capability map baseline

| Field | Value |
| --- | --- |
| Remote | origin |
| Default branch | trunk |
| Commit | %s |
| Capability map | spec/CAPABILITY-MAP.md |
| Goal digest | %s |
| Build order | alpha |

### Module digests

| Module id | Row digest |
| --- | --- |
%s

## Change

| Field | Value |
| --- | --- |
| Type | new-module |
| Module id | gamma |
| Responsibility | Gamma. |
| Depends on | alpha |
| Build-order anchor | after:alpha |

## Tracker contract

| Field | Value |
| --- | --- |
| Proposal id | gamma |
| Identity label | proposal |
| Stage label namespace | proposal-stage: |
""" % ("0" * 64, self.baseline, digest["goalDigest"], rows)
        (self.seed / "spec/proposals").mkdir()
        path = self.seed / "spec/proposals/gamma.md"
        path.write_text(text, encoding="utf-8")
        path.write_text(text.replace("0" * 64, compute_revision(path)), encoding="utf-8")

    def write_promotion_artifacts(self):
        (self.seed / "spec/CAPABILITY-MAP.md").write_text(self.promotion_map,
                                                           encoding="utf-8")
        paths = ["spec/CAPABILITY-MAP.md"]
        if self.include_artifacts:
            (self.seed / "spec/gamma.md").write_text("# Spec: gamma\n", encoding="utf-8")
            (self.seed / "tasks/gamma").mkdir(parents=True)
            (self.seed / "tasks/gamma/plan.md").write_text("# Plan: gamma\n", encoding="utf-8")
            paths.extend(("spec/gamma.md", "tasks/gamma/plan.md"))
        if self.include_extra_file:
            (self.seed / "README.md").write_text("unrelated\n", encoding="utf-8")
            paths.append("README.md")
        self.git(self.seed, "add", *paths)


class PromotionProofStateTests(PromotionFixture):
    def test_unusable_tracker_or_stage_stops_before_remote_access(self):
        cases = (
            (TrackerRead("absent"), "absent"),
            (TrackerRead("invalid"), "invalid"),
            (TrackerRead("unknown"), "unknown"),
            (self.tracker("proposal-stage:in-review"), "not-accepted"),
            (self.tracker("proposal-stage:rejected"), "not-accepted"),
            (self.tracker("proposal-stage:made-up"), "invalid"),
            (TrackerRead("verified", issue_id=42, stage="proposal-stage:accepted",
                         proposal_id="other", platform="github",
                         target="octo/spec-guard"), "invalid"),
        )
        with patch("proposal_publication._remote") as remote:
            for tracker, expected in cases:
                with self.subTest(expected=expected, stage=getattr(tracker, "stage", None)):
                    result = prove(self.consumer, self.publication, tracker,
                                   "github", "octo/spec-guard")
                    self.assertEqual(result.state, expected)
        remote.assert_not_called()

    def test_v1_or_unpublished_input_never_proves(self):
        v1 = Publication("published", review_commit=self.publication.review_commit,
                         proposal=SimpleNamespace(version="v1", revision=None,
                                                  proposal_id="gamma"))
        self.assertEqual(prove(self.consumer, v1, self.tracker(), "github",
                               "octo/spec-guard").state, "invalid")
        self.assertEqual(prove(self.consumer, Publication("absent"), self.tracker(),
                               "github", "octo/spec-guard").state, "absent")


class PromotionProofRemoteTests(PromotionFixture):
    def test_proves_a_map_only_promotion_from_its_parent_without_policy_or_attestation(self):
        dirty = self.consumer / "spec/CAPABILITY-MAP.md"
        dirty.write_text("not shared remote fact", encoding="utf-8")
        (self.seed / "README.md").write_text("later unrelated commit\n", encoding="utf-8")
        self.git(self.seed, "add", "README.md")
        self.git(self.seed, "commit", "-m", "later change")
        self.git(self.seed, "push", "origin", "trunk")

        result = self.prove()

        self.assertEqual(result.state, "proved")
        self.assertEqual(result.review_commit, self.parent_commit)
        self.assertEqual(result.promotion_commit, self.promotion_commit)
        self.assertEqual((result.proposal_id, result.module_id), ("gamma", "gamma"))
        self.assertEqual(dirty.read_text(encoding="utf-8"), "not shared remote fact")

    def test_promoted_stage_still_proves(self):
        result = self.prove("proposal-stage:promoted")
        self.assertEqual((result.state, result.promotion_commit),
                         ("proved", self.promotion_commit))

    def test_unavailable_remote_is_unknown(self):
        with patch("proposal_publication._head", return_value=None):
            self.assertEqual(self.prove().state, "unknown")

    def test_json_exposes_only_safe_proof_identifiers(self):
        data = as_json(self.prove())
        self.assertEqual(data["state"], "proved")
        self.assertEqual(data["promotionCommit"], self.promotion_commit)
        self.assertEqual(data["reviewCommit"], self.parent_commit)
        self.assertEqual(data["proposalId"], "gamma")
        self.assertNotIn(str(self.remote), json.dumps(data))
        self.assertNotIn("Capability Map", json.dumps(data))


class LegacyFilesPromotionProofTests(PromotionFixture):
    legacy_files = True

    def test_invalid_policy_and_stray_attestation_do_not_change_the_proof(self):
        result = self.prove()
        self.assertEqual((result.state, result.promotion_commit),
                         ("proved", self.promotion_commit))


class MapOnlyPromotionProofTests(PromotionFixture):
    include_artifacts = False

    def test_promotion_changing_only_the_capability_map_is_proved(self):
        paths = self.git(self.seed, "diff-tree", "--no-commit-id", "--name-only", "-r",
                         self.promotion_commit).split()
        self.assertEqual(paths, ["spec/CAPABILITY-MAP.md"])
        result = self.prove()
        self.assertEqual((result.state, result.review_commit, result.promotion_commit),
                         ("proved", self.parent_commit, self.promotion_commit))


class InvalidPromotionProofRemoteTests(PromotionFixture):
    promotion_map = PROMOTION_MAP.replace("| gamma | Gamma. | alpha |",
                                          "| gamma | Different responsibility | alpha |")

    def test_mismatched_first_remote_module_is_invalid(self):
        self.assertEqual(self.prove().state, "invalid")


class MergePromotionProofRemoteTests(PromotionFixture):
    merge_promotion = True

    def test_proves_the_merge_commit_carrying_spec_plan_and_unrelated_files(self):
        parents = self.git(self.seed, "rev-list", "--parents", "-n", "1",
                           self.promotion_commit).split()
        self.assertEqual(len(parents), 3)
        merged = self.git(self.seed, "diff-tree", "--no-commit-id", "--name-only", "-r",
                          parents[1], self.promotion_commit).split()
        self.assertIn("spec/gamma.md", merged)
        self.assertIn("tasks/gamma/plan.md", merged)
        result = self.prove()
        self.assertEqual(result.state, "proved")
        self.assertEqual(result.promotion_commit, self.promotion_commit)
        self.assertNotEqual(result.promotion_commit, self.feature_commit)
        self.assertEqual(result.review_commit, self.pre_merge_commit)


class ExtraPromotionFileTests(PromotionFixture):
    include_extra_file = True

    def test_promotion_commit_may_carry_unrelated_files(self):
        self.assertEqual(self.prove().state, "proved")


class OtherRowPromotionTests(PromotionFixture):
    promotion_map = PROMOTION_MAP.replace("| alpha | Existing capability | — |",
                                          "| alpha | Rewritten capability | — |")

    def test_promotion_that_also_edits_another_module_row_is_invalid(self):
        self.assertEqual(self.prove().state, "invalid")


class DriftedBaselinePromotionTests(PromotionFixture):
    drift_map = DRIFT_MAP
    promotion_map = PROMOTION_MAP.replace("Existing capability", "Changed capability")

    def test_baseline_drifted_before_promotion_is_stale(self):
        result = self.prove()
        self.assertEqual((result.state, result.diagnostic),
                         ("stale", "proposal-baseline-drifted"))
        self.assertEqual(as_json(result),
                         {"state": "stale", "diagnostic": "proposal-baseline-drifted"})


class NotYetPromotedProofTests(PromotionFixture):
    skip_promotion = True

    def test_no_promotion_commit_yet_is_not_promoted_not_invalid(self):
        result = self.prove()
        self.assertEqual(result.state, "not-promoted")
        self.assertIsNone(self.promotion_commit)
        data = as_json(result)
        self.assertEqual(data["diagnostic"], "promotion-not-found")
        self.assertEqual(data["proposalId"], "gamma")
        self.assertEqual(data["moduleId"], "gamma")


class DependencyMismatchPromotionProofTests(PromotionFixture):
    promotion_map = PROMOTION_MAP.replace("| gamma | Gamma. | alpha |",
                                          "| gamma | Gamma. | — |")

    def test_dependency_mismatch_with_the_proposal_declaration_is_invalid(self):
        self.assertEqual(self.prove().state, "invalid")


class MatchesAnchorMutantTests(unittest.TestCase):
    """`_matches` 直接单测：end 锚点必须真的排在 Build order 最后，
    after:<id> 锚点必须真的紧跟在该 id 之后。这两条曾经是存活的变异体。"""

    def _proposal(self, anchor):
        stub = type("StubProposal", (), {})()
        stub.change = Change("gamma", "Gamma.", ("alpha",), anchor)
        return stub

    def _map(self, build_order):
        text = (
            "# Capability Map: matches fixture\n\n## 目标\n\nFixture.\n\n## 模块\n\n"
            "| Module id | Responsibility | Depends on |\n| --- | --- | --- |\n"
            "| alpha | Existing capability | — |\n"
            "| gamma | Gamma. | alpha |\n"
            "| delta | Existing capability | — |\n\n"
            "Build order: %s\n" % build_order)
        with tempfile.TemporaryDirectory(prefix="sg-matches-fixture-") as tmp:
            path = Path(tmp) / "map.md"
            path.write_text(text, encoding="utf-8")
            return parse_map(path)

    def test_end_anchor_requires_the_module_to_actually_be_last(self):
        capability_map = self._map("alpha → gamma → delta")
        self.assertFalse(_matches(self._proposal("end"), capability_map))

    def test_end_anchor_matches_when_the_module_is_last(self):
        capability_map = self._map("alpha → delta → gamma")
        self.assertTrue(_matches(self._proposal("end"), capability_map))

    def test_after_anchor_requires_the_module_to_immediately_follow_it(self):
        capability_map = self._map("alpha → delta → gamma")
        self.assertFalse(_matches(self._proposal("after:alpha"), capability_map))


class PromotionPreflightTests(PromotionFixture):
    skip_promotion = True

    def run_preflight(self, stage="proposal-stage:accepted"):
        return preflight(self.consumer, "gamma", "github", "octo/spec-guard",
                         tracker_reader=lambda *ignored: self.tracker(stage))

    def test_accepted_and_fresh_is_ready_without_policy_or_attestation(self):
        result = self.run_preflight()
        self.assertEqual((result.state, result.proposal_id, result.revision),
                         ("ready", "gamma", self.publication.proposal.revision))
        self.assertEqual(result.base_commit, self.git(self.seed, "rev-parse", "HEAD").strip())
        self.assertEqual(preflight_as_json(result)["state"], "ready")

    def test_only_the_accepted_stage_is_ready(self):
        for stage in ("proposal-stage:in-review", "proposal-stage:promoted",
                      "proposal-stage:rejected"):
            with self.subTest(stage=stage):
                result = self.run_preflight(stage)
                self.assertNotEqual(result.state, "ready")
                self.assertIsNone(result.base_commit)

    def test_v1_proposal_requires_a_revision(self):
        v1 = Publication("published", review_commit=self.publication.review_commit,
                         proposal=SimpleNamespace(version="v1", revision=None,
                                                  proposal_id="gamma"))
        result = proposal_promotion_proof.accepted(
            v1, self.tracker(), "github", "octo/spec-guard")
        self.assertEqual(result.state, "legacy-revision-required")

    def test_accepted_helper_passes_review_states_through(self):
        result = proposal_promotion_proof.accepted(
            self.publication, self.tracker("proposal-stage:in-review"),
            "github", "octo/spec-guard")
        self.assertEqual(result.state, "in-review")
        result = proposal_promotion_proof.accepted(
            self.publication, self.tracker(), "github", "octo/spec-guard")
        self.assertEqual(result.state, "accepted")

    def test_preflight_reports_publication_absent_diagnostic_for_missing_proposal(self):
        result = preflight(self.consumer, "missing", "github", "octo/spec-guard",
                           tracker_reader=lambda *ignored: TrackerRead("absent"))
        self.assertEqual((result.state, result.diagnostic), ("absent", "publication-absent"))

    def test_preflight_reports_tracker_absent_diagnostic_for_missing_issue(self):
        result = preflight(self.consumer, "gamma", "github", "octo/spec-guard",
                           tracker_reader=lambda *ignored: TrackerRead("absent"))
        self.assertEqual((result.state, result.diagnostic), ("absent", "tracker-absent"))


class LegacyFilesPreflightTests(PromotionPreflightTests):
    legacy_files = True

    def test_invalid_policy_and_stray_attestation_give_the_identical_ready_result(self):
        result = self.run_preflight()
        self.assertEqual((result.state, result.diagnostic), ("ready", None))
        self.assertEqual(preflight_as_json(result)["state"], "ready")


class DriftedPreflightTests(PromotionFixture):
    skip_promotion = True
    drift_map = DRIFT_MAP

    def test_baseline_drift_is_stale_and_never_returns_a_base(self):
        result = preflight(self.consumer, "gamma", "github", "octo/spec-guard",
                           tracker_reader=lambda *ignored: self.tracker())
        self.assertEqual((result.state, result.diagnostic, result.base_commit),
                         ("stale", "proposal-baseline-drifted", None))
        self.assertEqual(preflight_as_json(result)["diagnostic"], "proposal-baseline-drifted")


class PromotionProofDiagnosticFallbackTests(unittest.TestCase):
    """`as_json`/`preflight_as_json` 只透传码形态诊断，垃圾或缺失诊断退回旧的折叠字符串。"""

    def test_as_json_keeps_only_code_shaped_diagnostics(self):
        self.assertEqual(
            as_json(Proof("stale", diagnostic="proposal-baseline-drifted")),
            {"state": "stale", "diagnostic": "proposal-baseline-drifted"})
        self.assertEqual(as_json(Proof("stale")),
                         {"state": "stale", "diagnostic": "promotion-stale"})
        for raw in ("review capability map is missing", "Traceback: /tmp/x", None,
                    "Promotion-Invalid", "code-"):
            with self.subTest(raw=raw):
                self.assertEqual(as_json(Proof("unknown", diagnostic=raw)),
                                 {"state": "unknown", "diagnostic": "promotion-unknown"})

    def test_preflight_as_json_keeps_only_code_shaped_diagnostics(self):
        self.assertEqual(
            preflight_as_json(Preflight("blocked", diagnostic="mainline-policy-invalid")),
            {"state": "blocked", "diagnostic": "mainline-policy-invalid"})
        for raw in ("review capability map is missing", None, "Promotion-Preflight-Blocked"):
            with self.subTest(raw=raw):
                self.assertEqual(preflight_as_json(Preflight("blocked", diagnostic=raw)),
                                 {"state": "blocked", "diagnostic": "promotion-preflight-blocked"})


class PromotionProofCliTests(PromotionFixture):

    def run_cli(self, *extra, stage="proposal-stage:accepted"):
        tracker = TrackerRead("verified", issue_id=42, stage=stage,
                              proposal_id="gamma", platform="github", target="octo/spec-guard")
        output = io.StringIO()
        with patch("proposal_promotion_proof.read_tracker", return_value=tracker), \
                redirect_stdout(output):
            self.assertEqual(main(["--project", str(self.consumer), "--platform", "github",
                                   "--target", "octo/spec-guard"] + list(extra)), 0)
        return json.loads(output.getvalue())

    def test_prove_cli_proves_the_merged_promotion_from_fresh_remote_facts(self):
        result = self.run_cli("--proposal-id", "gamma", "--prove")
        self.assertEqual(result["state"], "proved")
        self.assertEqual(result["promotionCommit"], self.promotion_commit)
        self.assertEqual(result["moduleId"], "gamma")

    def test_prove_cli_requires_a_fresh_accepted_issue_stage(self):
        self.assertEqual(self.run_cli("--proposal-id", "gamma", "--prove",
                                      stage="proposal-stage:in-review"),
                         {"state": "not-accepted", "diagnostic": "promotion-not-accepted"})

    def test_prove_cli_still_proves_after_the_issue_is_labeled_promoted(self):
        result = self.run_cli("--proposal-id", "gamma", "--prove",
                              stage="proposal-stage:promoted")
        self.assertEqual(result["state"], "proved")
        self.assertEqual(result["reviewCommit"], self.parent_commit)

    def test_prove_cli_reports_a_missing_proposal_and_an_unreachable_remote(self):
        self.assertEqual(self.run_cli("--proposal-id", "missing", "--prove"),
                         {"state": "absent", "proposalId": "missing"})
        self.git(self.consumer, "remote", "set-url", "origin", str(self.root / "gone.git"))
        self.assertEqual(self.run_cli("--proposal-id", "gamma", "--prove"),
                         {"state": "unknown", "diagnostic": "proposal-pool-unknown"})

    def test_cli_without_prove_still_runs_only_the_preflight(self):
        with patch("proposal_promotion_proof.prove",
                   side_effect=AssertionError("preflight must not prove")):
            result = self.run_cli("--proposal-id", "gamma")
        # 晋级后能力图已变，preflight 只能报告 stale，绝不输出晋级证明。
        self.assertEqual((result["state"], result["diagnostic"]),
                         ("stale", "proposal-module-already-present"))
        self.assertNotIn("promotionCommit", result)


class SkippedProposalOutputTests(PromotionFixture):
    """A promoted, unusable historical Proposal is reported but never blocks others."""
    UNAVAILABLE = [{"proposalId": "beta", "diagnostic": "proposal-baseline-unavailable"}]

    run_cli = PromotionProofCliTests.run_cli

    def publish_broken_baseline(self, proposal_id="beta", module_id="alpha"):
        text = (self.seed / "spec/proposals/gamma.md").read_text(encoding="utf-8")
        text = text.replace("| Module id | gamma |", "| Module id | %s |" % module_id)
        text = text.replace("gamma", proposal_id).replace(self.baseline, "0" * 40)
        text = text.replace(self.publication.proposal.revision, "0" * 64)
        path = self.seed / ("spec/proposals/%s.md" % proposal_id)
        path.write_text(text, encoding="utf-8")
        path.write_text(text.replace("0" * 64, compute_revision(path)), encoding="utf-8")
        self.git(self.seed, "add", "spec/proposals/%s.md" % proposal_id)
        self.git(self.seed, "commit", "-m", "publish %s" % proposal_id)
        self.git(self.seed, "push", "origin", "trunk")

    def test_healthy_output_has_no_skipped_key(self):
        self.assertNotIn("skippedProposals", self.run_cli("--proposal-id", "gamma", "--prove"))
        self.assertNotIn("skippedProposals", self.run_cli("--proposal-id", "gamma"))
        self.assertEqual(preflight_as_json(Preflight("absent", diagnostic="publication-absent")),
                         {"state": "absent", "diagnostic": "publication-absent"})
        self.assertEqual(as_json(Proof("absent", proposal_id="x")),
                         {"state": "absent", "proposalId": "x"})

    def test_other_proposals_keep_their_state_and_report_the_skipped_one(self):
        proof_before = self.run_cli("--proposal-id", "gamma", "--prove")
        preflight_before = self.run_cli("--proposal-id", "gamma")
        self.publish_broken_baseline()
        proof = self.run_cli("--proposal-id", "gamma", "--prove")
        self.assertEqual(proof, dict(proof_before, skippedProposals=self.UNAVAILABLE))
        preflight_result = self.run_cli("--proposal-id", "gamma")
        self.assertEqual(preflight_result,
                         dict(preflight_before, skippedProposals=self.UNAVAILABLE))

    def test_querying_the_excluded_proposal_is_plainly_absent(self):
        self.publish_broken_baseline()
        proof = self.run_cli("--proposal-id", "beta", "--prove")
        self.assertEqual(proof, {"state": "absent", "proposalId": "beta",
                                 "skippedProposals": self.UNAVAILABLE})
        result = preflight(self.consumer, "beta", "github", "octo/spec-guard")
        self.assertEqual((result.state, result.diagnostic), ("absent", "publication-absent"))
        self.assertEqual(preflight_as_json(result)["skippedProposals"], self.UNAVAILABLE)

    def test_serializer_maps_each_raw_error_to_a_short_code_and_hides_the_text(self):
        raw = (
            ("a", "Proposal baseline remote or default branch differs"),
            ("b", "Proposal baseline commit is not on remote default branch"),
            ("c", "Proposal Module digests differ from /private/path"),
        )
        data = skipped_as_json(raw)
        self.assertEqual(data, [
            {"proposalId": "a", "diagnostic": "proposal-baseline-remote-mismatch"},
            {"proposalId": "b", "diagnostic": "proposal-baseline-unavailable"},
            {"proposalId": "c", "diagnostic": "proposal-invalid"}])
        self.assertNotIn("private", json.dumps(data))


if __name__ == "__main__":
    unittest.main()
