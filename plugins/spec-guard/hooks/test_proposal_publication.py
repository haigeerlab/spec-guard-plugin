"""Publication reads a local bare remote, never the consumer worktree."""
import importlib.util
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from proposal_contract import compute_revision
from proposal_publication import as_json, read_published, read_published_pool


HOOKS = Path(__file__).parent
_digest_spec = importlib.util.spec_from_file_location("proposal_digest", HOOKS / "spec-digest.py")
_digest = importlib.util.module_from_spec(_digest_spec)
_digest_spec.loader.exec_module(_digest)

MAP = """# Capability Map: test

## 目标

Test remote facts.

## 模块

| Module id | Responsibility | Depends on |
| --- | --- | --- |
| alpha | First | — |

Build order: alpha
"""


class ProposalPublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sg-proposal-publication-")
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
        (self.seed / "spec/CAPABILITY-MAP.md").write_text(MAP, encoding="utf-8")
        (self.seed / "spec/proposal-mainline-policy.json").write_text(
            '{"authorityId":"mainline","remote":"origin","reviewRef":"refs/heads/integration/mainline","schemaVersion":1,"workflowId":"capability-map-integration"}',
            encoding="utf-8")
        self.git(self.seed, "add", "spec/CAPABILITY-MAP.md", "spec/proposal-mainline-policy.json")
        self.git(self.seed, "commit", "-m", "baseline")
        self.baseline = self.git(self.seed, "rev-parse", "HEAD").strip()
        self.write_proposal(remote="origin")
        self.git(self.seed, "add", "spec/proposals/gamma.md")
        self.git(self.seed, "commit", "-m", "publish proposal")
        self.git(self.seed, "remote", "add", "origin", str(self.remote))
        self.git(self.seed, "push", "origin", "trunk")
        self.git(self.root, "clone", str(self.remote), str(self.consumer))

    def git(self, cwd, *args):
        result = subprocess.run(["git", "-C", str(cwd)] + list(args), text=True,
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def write_proposal(self, remote):
        digest = _digest.compute(str(self.seed / "spec/CAPABILITY-MAP.md"))
        rows = "\n".join("| %s | %s |" % (item["id"], item["rowDigest"])
                         for item in digest["rows"])
        proposal = """# Proposal: Add gamma
<!-- spec-guard-proposal:v1 id=gamma -->

## Summary

Gamma is separate.

## Capability map baseline

| Field | Value |
| --- | --- |
| Remote | %s |
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
""" % (remote, self.baseline, digest["goalDigest"], rows)
        (self.seed / "spec/proposals").mkdir(exist_ok=True)
        (self.seed / "spec/proposals/gamma.md").write_text(proposal, encoding="utf-8")

    def test_published_snapshot_ignores_dirty_consumer_files(self):
        dirty = self.consumer / "spec/proposals/gamma.md"
        dirty.parent.mkdir(exist_ok=True)
        dirty.write_text("not the remote Proposal", encoding="utf-8")
        result = read_published(self.consumer, "gamma")
        self.assertEqual(result.state, "published")
        self.assertEqual(result.proposal.proposal_id, "gamma")
        self.assertNotEqual(result.review_map, "not the remote Proposal")
        self.assertEqual(dirty.read_text(encoding="utf-8"), "not the remote Proposal")

    def test_missing_remote_proposal_is_absent(self):
        self.assertEqual(read_published(self.consumer, "missing").state, "absent")

    def test_mismatched_baseline_remote_is_invalid(self):
        self.write_proposal(remote="elsewhere")
        self.git(self.seed, "add", "spec/proposals/gamma.md")
        self.git(self.seed, "commit", "-m", "bad provenance")
        self.git(self.seed, "push", "origin", "trunk")
        self.assertEqual(read_published(self.consumer, "gamma").state, "invalid")

    def test_invalid_proposal_id_is_rejected_before_any_git_transport(self):
        with patch("proposal_publication._remote") as remote:
            result = read_published(self.consumer, "../CAPABILITY-MAP")
        self.assertEqual(result.state, "invalid")
        remote.assert_not_called()

    def test_json_result_exposes_commit_without_remote_url(self):
        result = read_published(self.consumer, "gamma")
        data = as_json(result)
        self.assertEqual(data["state"], "published")
        self.assertEqual(data["reviewCommit"], result.review_commit)
        self.assertNotIn(str(self.remote), str(data))

    def test_changed_remote_tip_is_unknown_not_a_new_snapshot(self):
        replies = iter((
            SimpleNamespace(stdout="/tmp/remote\n"),
            SimpleNamespace(stdout="ref: refs/heads/trunk HEAD\nabc HEAD\n"),
            SimpleNamespace(stdout=""), SimpleNamespace(stdout=""),
            SimpleNamespace(stdout="def\n"),
        ))
        with patch("proposal_publication._run", side_effect=lambda *args, **kwargs: next(replies)):
            result = read_published(self.consumer, "gamma")
        self.assertEqual(result.state, "unknown")
        self.assertIsNone(result.review_commit)

    def test_pool_reads_only_published_remote_proposals_from_one_snapshot(self):
        dirty = self.consumer / "spec/proposals/local-only.md"
        dirty.parent.mkdir(exist_ok=True)
        dirty.write_text("not a published Proposal", encoding="utf-8")
        local_policy = self.consumer / "spec/proposal-mainline-policy.json"
        local_policy.write_text("not a remote policy", encoding="utf-8")

        pool = read_published_pool(self.consumer)

        self.assertEqual(pool.state, "published")
        self.assertEqual(pool.review_commit, read_published(self.consumer, "gamma").review_commit)
        self.assertEqual([item.proposal.proposal_id for item in pool.publications], ["gamma"])
        self.assertEqual(dirty.read_text(encoding="utf-8"), "not a published Proposal")
        self.assertIn('"schemaVersion":1', pool.policy_text)
        self.assertEqual(local_policy.read_text(encoding="utf-8"), "not a remote policy")

    def test_pool_rejects_two_remote_files_with_the_same_proposal_identity(self):
        duplicate = self.seed / "spec/proposals/duplicate.md"
        duplicate.write_text((self.seed / "spec/proposals/gamma.md").read_text(encoding="utf-8"),
                             encoding="utf-8")
        self.git(self.seed, "add", "spec/proposals/duplicate.md")
        self.git(self.seed, "commit", "-m", "duplicate proposal identity")
        self.git(self.seed, "push", "origin", "trunk")
        self.assertEqual(read_published_pool(self.consumer).state, "invalid")

    def test_v2_attestation_keeps_its_pre_acceptance_review_snapshot(self):
        digest = _digest.compute(str(self.seed / "spec/CAPABILITY-MAP.md"))
        rows = "\n".join("| %s | %s |" % (item["id"], item["rowDigest"])
                         for item in digest["rows"])
        path = self.seed / "spec/proposals/gamma.md"
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
        path.write_text(text, encoding="utf-8")
        path.write_text(text.replace("0" * 64, compute_revision(path)), encoding="utf-8")
        self.git(self.seed, "add", "spec/proposals/gamma.md")
        self.git(self.seed, "commit", "-m", "publish v2 proposal")
        self.git(self.seed, "push", "origin", "trunk")

        reviewed = read_published(self.consumer, "gamma")
        policy = json.loads((self.seed / "spec/proposal-mainline-policy.json").read_text(
            encoding="utf-8"))
        acceptance = self.seed / "spec/proposal-acceptances"
        acceptance.mkdir()
        (acceptance / ("gamma-%s.json" % reviewed.proposal.revision)).write_text(
            json.dumps({
                "schemaVersion": 1, "proposalId": "gamma",
                "revision": reviewed.proposal.revision,
                "reviewCommit": reviewed.review_commit,
                "policyDigest": hashlib.sha256(json.dumps(
                    policy, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
                        "utf-8")).hexdigest(),
                "authorityId": "mainline", "decision": "accept",
            }), encoding="utf-8")
        self.git(self.seed, "add", "spec/proposal-acceptances")
        self.git(self.seed, "commit", "-m", "record gamma acceptance")
        self.git(self.seed, "push", "origin", "trunk")

        publication = read_published(self.consumer, "gamma")
        pool = read_published_pool(self.consumer)
        self.assertEqual(publication.review_commit, reviewed.review_commit)
        self.assertEqual(pool.publications[0].review_commit, reviewed.review_commit)
        self.assertNotEqual(pool.review_commit, reviewed.review_commit)

        (self.seed / "spec/CAPABILITY-MAP.md").write_text(
            MAP.replace("Test remote facts.", "Changed remote facts."), encoding="utf-8")
        self.git(self.seed, "add", "spec/CAPABILITY-MAP.md")
        self.git(self.seed, "commit", "-m", "drift capability map")
        self.git(self.seed, "push", "origin", "trunk")
        self.assertNotEqual(read_published(self.consumer, "gamma").review_commit,
                            reviewed.review_commit)


if __name__ == "__main__":
    unittest.main()
