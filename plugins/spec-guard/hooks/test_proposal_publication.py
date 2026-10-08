"""Publication reads a local bare remote, never the consumer worktree."""
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import proposal_publication
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
    @classmethod
    def setUpClass(cls):
        """Build the git fixture once; each test copies it (see setUp)."""
        super().setUpClass()
        cls._template = Path(tempfile.mkdtemp(prefix="sg-proposal-publication-template-"))
        try:
            builder = cls("setUp")
            builder.root = cls._template
            builder.seed = builder.root / "seed"
            builder.remote = builder.root / "remote.git"
            builder.consumer = builder.root / "consumer"
            builder.build()
            cls.baseline = builder.baseline
        except BaseException:
            shutil.rmtree(cls._template, ignore_errors=True)
            raise

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._template, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sg-proposal-publication-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        shutil.copytree(self._template, self.root, symlinks=True, dirs_exist_ok=True)
        self.seed = self.root / "seed"
        self.remote = self.root / "remote.git"
        self.consumer = self.root / "consumer"
        self.git(self.seed, "remote", "set-url", "origin", str(self.remote))
        self.git(self.consumer, "remote", "set-url", "origin", str(self.remote))

    def build(self):
        self.git(self.root, "init", "--bare", "-b", "trunk", str(self.remote))
        self.git(self.root, "init", "-b", "trunk", str(self.seed))
        self.git(self.seed, "config", "user.email", "test@example.invalid")
        self.git(self.seed, "config", "user.name", "test")
        (self.seed / "spec").mkdir()
        (self.seed / "spec/CAPABILITY-MAP.md").write_text(MAP, encoding="utf-8")
        self.git(self.seed, "add", "spec/CAPABILITY-MAP.md")
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

    # remote-credential-redaction: the remote URL never appears in a git argv.

    def argv_while_reading(self, project):
        seen = []
        real = proposal_publication._run

        def recording(args, cwd=None):
            seen.append(list(args))
            return real(args, cwd=cwd)
        with patch("proposal_publication._run", side_effect=recording):
            result = read_published(project, "gamma")
        return result, seen

    def test_no_git_argv_carries_the_remote_url(self):
        result, seen = self.argv_while_reading(self.consumer)
        self.assertEqual(result.state, "published")
        self.assertTrue(any("ls-remote" in args for args in seen))
        self.assertTrue(any("fetch" in args for args in seen))
        for args in seen:
            self.assertFalse(any(str(self.remote) in arg for arg in args), args)

    def test_a_remote_path_with_spaces_quotes_and_backslashes_still_snapshots(self):
        odd = self.root / 'odd "remote" \\ dir.git'
        shutil.copytree(self.remote, odd)
        self.git(self.consumer, "remote", "set-url", "origin", str(odd))
        result, seen = self.argv_while_reading(self.consumer)
        self.assertEqual(result.state, "published")
        for args in seen:
            self.assertFalse(any(str(odd) in arg for arg in args), args)

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
            SimpleNamespace(stdout="ref: refs/heads/trunk HEAD\n%s HEAD\n" % ("a" * 40)),
            SimpleNamespace(stdout=""), SimpleNamespace(stdout=""),
            SimpleNamespace(stdout="%s\n" % ("d" * 40)),
        ))
        with patch("proposal_publication._run", side_effect=lambda *args, **kwargs: next(replies)):
            result = read_published(self.consumer, "gamma")
        self.assertEqual(result.state, "unknown")
        self.assertEqual(result.diagnostic, proposal_publication.TIP_MOVED)
        self.assertIsNone(result.review_commit)

    def test_malformed_remote_head_is_unavailable_before_any_snapshot(self):
        # A head that cannot be read is retried, so the script answers every attempt.
        replies = iter((SimpleNamespace(stdout="/tmp/remote\n"),) + tuple(
            SimpleNamespace(stdout="ref: refs/heads/trunk HEAD\nnot-a-commit HEAD\n")
            for _ in range(proposal_publication.SNAPSHOT_ATTEMPTS)))
        with patch("proposal_publication._run", side_effect=lambda *args, **kwargs: next(replies)), \
                patch("proposal_publication.SNAPSHOT_BACKOFF_SECONDS", 0):
            result = read_published(self.consumer, "gamma")
        self.assertEqual(result.state, "unknown")
        self.assertEqual(result.diagnostic, proposal_publication.HEAD_UNAVAILABLE)

    def test_pool_reads_only_published_remote_proposals_from_one_snapshot(self):
        dirty = self.consumer / "spec/proposals/local-only.md"
        dirty.parent.mkdir(exist_ok=True)
        dirty.write_text("not a published Proposal", encoding="utf-8")

        pool = read_published_pool(self.consumer)

        self.assertEqual(pool.state, "published")
        self.assertEqual(pool.review_commit, read_published(self.consumer, "gamma").review_commit)
        self.assertEqual([item.proposal.proposal_id for item in pool.publications], ["gamma"])
        self.assertEqual(dirty.read_text(encoding="utf-8"), "not a published Proposal")
        self.assertFalse(hasattr(pool, "policy_text"))
        self.assertFalse(hasattr(pool, "attestation_texts"))

    def test_pool_rejects_two_remote_files_with_the_same_proposal_identity(self):
        duplicate = self.seed / "spec/proposals/duplicate.md"
        duplicate.write_text((self.seed / "spec/proposals/gamma.md").read_text(encoding="utf-8"),
                             encoding="utf-8")
        self.git(self.seed, "add", "spec/proposals/duplicate.md")
        self.git(self.seed, "commit", "-m", "duplicate proposal identity")
        self.git(self.seed, "push", "origin", "trunk")
        self.assertEqual(read_published_pool(self.consumer).state, "invalid")

    def publish_broken_baseline(self, proposal_id, module_id):
        """Publish a parseable Proposal whose baseline commit is not on the default branch."""
        text = (self.seed / "spec/proposals/gamma.md").read_text(encoding="utf-8")
        text = text.replace("| Module id | gamma |", "| Module id | %s |" % module_id)
        text = text.replace("gamma", proposal_id).replace(self.baseline, "0" * 40)
        (self.seed / ("spec/proposals/%s.md" % proposal_id)).write_text(text, encoding="utf-8")
        self.git(self.seed, "add", "spec/proposals/%s.md" % proposal_id)
        self.git(self.seed, "commit", "-m", "publish %s" % proposal_id)
        self.git(self.seed, "push", "origin", "trunk")

    def test_pool_isolates_promoted_proposal_with_broken_baseline(self):
        self.publish_broken_baseline("beta", "alpha")
        pool = read_published_pool(self.consumer)
        self.assertEqual(pool.state, "published")
        self.assertEqual([item.proposal.proposal_id for item in pool.publications], ["gamma"])
        self.assertEqual(pool.skipped, (
            ("beta", "Proposal baseline commit is not on remote default branch"),))

    def test_pool_rejects_unpromoted_proposal_with_broken_baseline(self):
        self.publish_broken_baseline("beta", "delta")
        pool = read_published_pool(self.consumer)
        self.assertEqual(pool.state, "invalid")
        self.assertEqual(pool.diagnostic, "Proposal baseline commit is not on remote default branch")
        self.assertEqual(pool.skipped, ())

    def test_pool_rejects_unparseable_proposal_even_when_others_are_fine(self):
        (self.seed / "spec/proposals/aaa-broken.md").write_text("not a proposal", encoding="utf-8")
        self.git(self.seed, "add", "spec/proposals/aaa-broken.md")
        self.git(self.seed, "commit", "-m", "unparseable proposal")
        self.git(self.seed, "push", "origin", "trunk")
        pool = read_published_pool(self.consumer)
        self.assertEqual(pool.state, "invalid")
        self.assertEqual(pool.skipped, ())

    def test_pool_keeps_healthy_promoted_proposal_and_skips_nothing(self):
        (self.seed / "spec/CAPABILITY-MAP.md").write_text(
            MAP.replace("| alpha | First | — |", "| alpha | First | — |\n| gamma | Gamma. | alpha |")
               .replace("Build order: alpha", "Build order: alpha, gamma"), encoding="utf-8")
        self.git(self.seed, "add", "spec/CAPABILITY-MAP.md")
        self.git(self.seed, "commit", "-m", "promote gamma")
        self.git(self.seed, "push", "origin", "trunk")
        pool = read_published_pool(self.consumer)
        self.assertEqual(pool.state, "published")
        self.assertEqual([item.proposal.proposal_id for item in pool.publications], ["gamma"])
        self.assertEqual(pool.skipped, ())

    def test_pool_without_bad_proposals_has_no_skipped_entries(self):
        pool = read_published_pool(self.consumer)
        self.assertEqual(pool.state, "published")
        self.assertEqual([item.proposal.proposal_id for item in pool.publications], ["gamma"])
        self.assertIsNone(pool.diagnostic)
        self.assertEqual(pool.skipped, ())

    def publish_v2_proposal(self):
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

    def commit_and_push(self, message, *paths):
        self.git(self.seed, "add", *paths)
        self.git(self.seed, "commit", "-m", message)
        self.git(self.seed, "push", "origin", "trunk")
        return self.git(self.seed, "rev-parse", "HEAD").strip()

    def test_v2_attestation_pinning_is_ignored(self):
        self.publish_v2_proposal()
        earlier = self.git(self.seed, "rev-parse", "HEAD").strip()
        earlier_map = (self.seed / "spec/CAPABILITY-MAP.md").read_text(encoding="utf-8")
        revision = read_published(self.consumer, "gamma").proposal.revision
        acceptance = self.seed / "spec/proposal-acceptances"
        acceptance.mkdir()
        (acceptance / ("gamma-%s.json" % revision)).write_text(json.dumps({
            "schemaVersion": 1, "proposalId": "gamma", "revision": revision,
            "reviewCommit": earlier, "decision": "accept"}), encoding="utf-8")
        (self.seed / "spec/CAPABILITY-MAP.md").write_text(
            MAP.replace("Test remote facts.", "Changed remote facts."), encoding="utf-8")
        tip = self.commit_and_push("attest and drift", "spec/proposal-acceptances",
                                   "spec/CAPABILITY-MAP.md")
        tip_map = (self.seed / "spec/CAPABILITY-MAP.md").read_text(encoding="utf-8")
        self.assertNotEqual(earlier_map, tip_map)

        publication = read_published(self.consumer, "gamma")
        pool = read_published_pool(self.consumer)
        self.assertEqual(publication.state, "published")
        self.assertEqual(publication.review_commit, tip)
        self.assertEqual(publication.review_map, tip_map)
        self.assertEqual(pool.review_commit, tip)
        self.assertEqual(len(pool.publications), 1)
        self.assertEqual(pool.publications[0].review_commit, tip)
        self.assertEqual(pool.publications[0].review_map, tip_map)

    def test_invalid_remote_policy_file_still_reads_as_published(self):
        self.commit_and_push("invalid policy", self._write("spec/proposal-mainline-policy.json",
                                                            "not json"))
        self.assertEqual(read_published(self.consumer, "gamma").state, "published")
        pool = read_published_pool(self.consumer)
        self.assertEqual(pool.state, "published")
        self.assertEqual([item.proposal.proposal_id for item in pool.publications], ["gamma"])

    def _write(self, rel, text):
        (self.seed / rel).write_text(text, encoding="utf-8")
        return rel


class SnapshotProbeRetryTests(unittest.TestCase):
    """A probe that could not read is retried; a tip that moved is never retried.

    One `proposal_closeout close` makes six git network round trips across three
    independent snapshots. Measured against the real remote on 2026-10-04, a single
    snapshot succeeded 9 times in 10 while the machine was quiet, and far less often
    under concurrent git activity -- one issue needed eight `close --confirm` attempts.
    Every failure was safe, but it made the reader re-run a *write* command to get past
    a *read* problem.

    Retrying the probe is safe: it only reads the remote into a throwaway temporary
    repository. Retrying a moved tip would not be safe -- pinning the tip observed
    before the fetch is the entire guarantee this snapshot provides, so two reads that
    both succeeded and disagree must stay a failure rather than becoming a fresh
    snapshot of the newer tip.
    """

    PROJECT = "/project-need-not-exist"
    A = "a" * 40
    B = "b" * 40

    @staticmethod
    def head(commit, branch="trunk"):
        return SimpleNamespace(stdout="ref: refs/heads/%s HEAD\n%s HEAD\n" % (branch, commit))

    @staticmethod
    def tip(commit):
        return SimpleNamespace(stdout="%s\n" % commit)

    OK = SimpleNamespace(stdout="")

    def runner(self, heads, fetches, tips):
        """Answer `_run` from one queue per git subcommand; the last reply repeats.

        `None` is a probe that failed. Nothing here reaches a network or a real
        repository, so `self.seen` counts exactly the probes the code attempted.
        """
        queues = {"ls-remote": list(heads), "fetch": list(fetches), "rev-parse": list(tips)}
        self.seen = dict.fromkeys(queues, 0)

        def run(args, cwd=None):
            if "get-url" in args:
                return SimpleNamespace(stdout="/remote.git\n")
            for key, queue in queues.items():
                if key in args:
                    self.seen[key] += 1
                    return queue.pop(0) if len(queue) > 1 else queue[0]
            return self.OK  # git init --bare
        return run

    def snapshot(self, heads, fetches=None, tips=None):
        """Record the backoff instead of serving it, so these tests stay instant."""
        self.slept = []
        with patch("proposal_publication._run",
                   side_effect=self.runner(heads, fetches or [self.OK],
                                           tips or [self.tip(self.A)])), \
                patch("proposal_publication.time.sleep", self.slept.append):
            with proposal_publication.fixed_snapshot(self.PROJECT, "origin", "sg-test-") as result:
                return result

    def test_a_credential_bearing_remote_url_never_reaches_a_git_argv(self):
        secret = "https://user:SECRET@example.invalid/remote.git"
        seen = []
        inner = self.runner([self.head(self.A)], [self.OK], [self.tip(self.A)])

        def run(args, cwd=None):
            seen.append(list(args))
            if "get-url" in args:
                return SimpleNamespace(stdout=secret + "\n")
            return inner(args, cwd)
        with patch("proposal_publication._run", side_effect=run), \
                patch("proposal_publication.time.sleep", lambda _: None):
            with proposal_publication.fixed_snapshot(self.PROJECT, "origin", "sg-test-") as snapshot:
                self.assertIsNone(snapshot.failure)
                self.assertEqual(snapshot.commit, self.A)
        self.assertTrue(seen)
        for args in seen:
            self.assertFalse(any("SECRET" in arg or "example.invalid" in arg for arg in args), args)

    def test_a_failed_fetch_is_retried_and_still_pins_the_observed_tip(self):
        snapshot = self.snapshot([self.head(self.A)], fetches=[None, self.OK])
        self.assertIsNone(snapshot.failure)
        self.assertEqual(snapshot.commit, self.A)
        self.assertEqual(self.seen["fetch"], 2)

    def test_a_failed_head_probe_is_retried(self):
        snapshot = self.snapshot([None, None, self.head(self.A)])
        self.assertIsNone(snapshot.failure)
        self.assertEqual(snapshot.commit, self.A)
        self.assertEqual(self.seen["ls-remote"], 3)

    def test_a_failed_rev_parse_is_retried(self):
        snapshot = self.snapshot([self.head(self.A)], tips=[None, self.tip(self.A)])
        self.assertIsNone(snapshot.failure)
        self.assertEqual(snapshot.commit, self.A)
        self.assertEqual(self.seen["rev-parse"], 2)

    def test_retries_are_bounded_and_name_the_probe_that_failed(self):
        snapshot = self.snapshot([None])
        self.assertEqual(snapshot.failure, proposal_publication.HEAD_UNAVAILABLE)
        self.assertEqual(self.seen["ls-remote"], proposal_publication.SNAPSHOT_ATTEMPTS)

    def test_attempts_are_separated_by_a_short_growing_backoff(self):
        backoff = proposal_publication.SNAPSHOT_BACKOFF_SECONDS
        self.assertGreater(backoff, 0)
        self.snapshot([None])
        self.assertEqual(self.slept, [backoff * n for n in
                                      range(1, proposal_publication.SNAPSHOT_ATTEMPTS)])

    def test_a_persistent_fetch_failure_is_not_reported_as_a_moved_tip(self):
        snapshot = self.snapshot([self.head(self.A)], fetches=[None])
        self.assertEqual(snapshot.failure, proposal_publication.FETCH_FAILED)
        self.assertNotEqual(snapshot.failure, proposal_publication.TIP_MOVED)
        self.assertEqual(self.seen["fetch"], proposal_publication.SNAPSHOT_ATTEMPTS)

    def test_a_moved_tip_fails_at_once_and_is_never_retried(self):
        snapshot = self.snapshot([self.head(self.A)], tips=[self.tip(self.B)])
        self.assertEqual(snapshot.failure, proposal_publication.TIP_MOVED)
        self.assertIsNone(snapshot.repo)
        self.assertIsNone(snapshot.commit)
        self.assertEqual(self.seen["fetch"], 1)
        self.assertEqual(self.slept, [])

    def test_a_tip_that_moves_between_retries_is_never_snapshotted(self):
        """The retry must not quietly re-observe and snapshot the newer tip."""
        snapshot = self.snapshot([self.head(self.A), self.head(self.B)],
                                 fetches=[None, self.OK], tips=[self.tip(self.B)])
        self.assertEqual(snapshot.failure, proposal_publication.TIP_MOVED)
        self.assertIsNone(snapshot.repo)
        self.assertIsNone(snapshot.commit)
        self.assertEqual(self.seen["ls-remote"], 2)


if __name__ == "__main__":
    unittest.main()
