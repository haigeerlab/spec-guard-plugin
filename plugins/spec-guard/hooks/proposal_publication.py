"""Read one published Proposal from a fixed remote-default Git snapshot."""
import argparse
import json
import subprocess
import tempfile
import time
from contextlib import ExitStack, contextmanager
from pathlib import Path

from capability_map import MapError, parse_map
from proposal_contract import COMMIT, ContractError, PROPOSAL_ID, parse_proposal, validate_proposal


MAX_POOL_SIZE = 100
SNAPSHOT_ATTEMPTS = 3
SNAPSHOT_BACKOFF_SECONDS = 0.2
# A probe that could not read and a tip that actually moved used to share one string,
# so no caller could tell a retry from a real moving target.
HEAD_UNAVAILABLE = "remote default branch is unavailable"
FETCH_FAILED = "remote default branch fetch failed"
TIP_MOVED = "remote default branch moved between observation and fetch"
SNAPSHOT_FAILED = "temporary Git snapshot failed"
# Stable codes for the same four facts.  Layers that emit only code-shaped
# diagnostics cannot carry the strings above, and folding them into one state code
# loses what the snapshot just established: whether this is worth running again.
PROBE_CODES = {
    HEAD_UNAVAILABLE: "snapshot-head-unavailable",
    FETCH_FAILED: "snapshot-fetch-failed",
    TIP_MOVED: "snapshot-tip-moved",
    SNAPSHOT_FAILED: "snapshot-temp-repo-failed",
}
BASELINE_REMOTE_MISMATCH = "Proposal baseline remote or default branch differs"
BASELINE_UNAVAILABLE = "Proposal baseline commit is not on remote default branch"
_SKIPPED_CODES = {
    BASELINE_REMOTE_MISMATCH: "proposal-baseline-remote-mismatch",
    BASELINE_UNAVAILABLE: "proposal-baseline-unavailable",
}


def probe_code(failure):
    """Map a `fixed_snapshot` failure to its stable code, or None for anything else.

    None keeps a caller's own fallback, so an unrecognized diagnostic -- a contract
    error, a raw transport message -- is never dressed up as a snapshot verdict.
    """
    return PROBE_CODES.get(failure)


def skipped_as_json(skipped):
    """Serialize `PublicationPool.skipped` as stable codes; raw errors never leave here."""
    return [{"proposalId": proposal_id, "diagnostic": _SKIPPED_CODES.get(error, "proposal-invalid")}
            for proposal_id, error in skipped]


class Publication(object):
    def __init__(self, state, review_commit=None, proposal=None, baseline_map=None,
                 review_map=None, diagnostic=None):
        self.state = state
        self.review_commit = review_commit
        self.proposal = proposal
        self.baseline_map = baseline_map
        self.review_map = review_map
        self.diagnostic = diagnostic


class PublicationPool(object):
    def __init__(self, state, review_commit=None, publications=(), review_map=None,
                 diagnostic=None, skipped=()):
        self.state = state
        self.review_commit = review_commit
        self.publications = tuple(publications)
        self.review_map = review_map
        self.diagnostic = diagnostic
        self.skipped = tuple(skipped)


def as_json(result):
    """Serialize safe publication facts without transport or temporary paths."""
    data = {"state": result.state, "reviewCommit": result.review_commit}
    if result.proposal is not None:
        data["proposalId"] = result.proposal.proposal_id
        data["baselineCommit"] = result.proposal.baseline.commit
    if result.diagnostic:
        data["diagnostic"] = result.diagnostic
    return data


def _run(args, cwd=None):
    try:
        result = subprocess.run(args, cwd=str(cwd) if cwd else None, text=True,
                                capture_output=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result if result.returncode == 0 else None


def _remote(project, name):
    result = _run(["git", "-C", str(project), "remote", "get-url", name])
    return result.stdout.strip() if result and result.stdout.strip() else None


# remote-credential-redaction: the remote URL may carry credentials, so it is never a git argument -- the head is
# listed by remote name in the project, and the fetch goes through a remote written into the snapshot's own config.
SNAPSHOT_REMOTE = "spec-guard-source"


def _head(project, remote):
    result = _run(["git", "-C", str(project), "ls-remote", "--symref", remote, "HEAD"])
    if not result:
        return None
    branch = None
    commit = None
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[0] == "ref:" and fields[2] == "HEAD":
            ref = fields[1]
            if ref.startswith("refs/heads/"):
                branch = ref[len("refs/heads/"):]
        elif len(fields) == 2 and fields[1] == "HEAD":
            commit = fields[0]
    return (branch, commit) if branch and COMMIT.fullmatch(commit or "") else None


class Snapshot(object):
    def __init__(self, failure=None, repo=None, temp=None, url=None, branch=None, commit=None):
        self.failure = failure
        self.repo = repo
        self.temp = temp
        self.url = url
        self.branch = branch
        self.commit = commit


@contextmanager
def fixed_snapshot(project, remote, prefix):
    """Fetch the remote default tip once into a temporary bare repository.

    Yields a Snapshot whose `failure` names why no snapshot exists, or whose
    repo/branch/commit are pinned to the tip observed before the fetch.  A tip
    that moves between observation and fetch is a failure, never a new snapshot.

    An attempt only reads the remote into a throwaway temporary repository --
    nothing in the project or on the remote is written -- so a probe that could
    not read is retried up to SNAPSHOT_ATTEMPTS times: `_head` reading nothing
    (HEAD_UNAVAILABLE), or the fetch or its `rev-parse` failing (FETCH_FAILED).
    One closeout chains three of these snapshots, and a single intermittent probe
    made the reader re-run a write command to get past a read problem.

    A tip that moved is never retried.  Pinning the observed tip is the entire
    guarantee here, so the moment two reads that both succeeded disagree -- a
    re-observed head, or a FETCH_HEAD that is not the tip observed before it --
    this fails with TIP_MOVED instead of snapshotting the newer tip.
    """
    url = _remote(Path(project), remote)
    with ExitStack() as stack:
        yield _snapshot(stack, Path(project), remote, url, prefix) if url else Snapshot(HEAD_UNAVAILABLE)


def _add_snapshot_remote(repo, url):
    """Write the snapshot remote into the bare repository's config file, never onto a command line."""
    if "\n" in url or "\r" in url or "\0" in url:
        return False
    value = url.replace("\\", "\\\\").replace('"', '\\"')
    try:
        repo.mkdir(parents=True, exist_ok=True)
        with open(repo / "config", "a", encoding="utf-8") as config:
            config.write('[remote "%s"]\n\turl = "%s"\n' % (SNAPSHOT_REMOTE, value))
    except OSError:
        return False
    return True


def _snapshot(stack, project, remote, url, prefix):
    """Observe and fetch the tip, retrying probe failures only (see fixed_snapshot).

    A successful snapshot's temporary directory is handed to `stack` so it outlives
    this call; a failed attempt's is removed before the next one.
    """
    observed = None
    failure = HEAD_UNAVAILABLE
    for attempt in range(SNAPSHOT_ATTEMPTS):
        if attempt:
            time.sleep(SNAPSHOT_BACKOFF_SECONDS * attempt)
        fresh = _head(project, remote)
        if not fresh:
            failure = HEAD_UNAVAILABLE
            continue
        if observed is not None and fresh != observed:
            # Both reads succeeded and disagree: the tip is moving under the retry.
            return Snapshot(TIP_MOVED)
        observed = fresh
        branch, commit = observed
        attempt_stack = ExitStack()
        with attempt_stack:
            temp = Path(attempt_stack.enter_context(
                tempfile.TemporaryDirectory(prefix=prefix)))
            repo = temp / "snapshot.git"
            if not _run(["git", "init", "--bare", str(repo)]) or not _add_snapshot_remote(repo, url):
                return Snapshot(SNAPSHOT_FAILED)
            # No auto-maintenance: fetch would detach a background `git maintenance`
            # that can still write into the snapshot while the temp dir is removed.
            fetched = _run(["git", "-c", "maintenance.auto=false", "-c", "gc.auto=0",
                            "-C", str(repo), "fetch", "--no-tags", SNAPSHOT_REMOTE,
                            "refs/heads/%s" % branch])
            tip = _run(["git", "-C", str(repo), "rev-parse", "FETCH_HEAD"])
            if not fetched or not tip:
                failure = FETCH_FAILED
                continue
            if tip.stdout.strip() != commit:
                # Both reads succeeded and disagree: moved, not a probe that failed.
                return Snapshot(TIP_MOVED)
            stack.push(attempt_stack.pop_all())
            return Snapshot(repo=repo, temp=temp, url=url, branch=branch, commit=commit)
    return Snapshot(failure)


def _show(repo, commit, path):
    result = _run(["git", "-C", str(repo), "show", "%s:%s" % (commit, path)])
    return result.stdout if result else None


def read_published(project, proposal_id, remote="origin"):
    """Return only remote-default facts; never read consumer proposal/map files."""
    if not isinstance(proposal_id, str) or not PROPOSAL_ID.fullmatch(proposal_id):
        return Publication("invalid", diagnostic="proposal id is invalid")
    with fixed_snapshot(project, remote, "sg-proposal-publication-") as snapshot:
        if snapshot.failure:
            return Publication("unknown", diagnostic=snapshot.failure)
        repo, temp, branch, observed_commit = snapshot.repo, snapshot.temp, snapshot.branch, snapshot.commit
        proposal_text = _show(repo, observed_commit, "spec/proposals/%s.md" % proposal_id)
        if proposal_text is None:
            return Publication("absent", review_commit=observed_commit)
        review_map = _show(repo, observed_commit, "spec/CAPABILITY-MAP.md")
        if review_map is None:
            return Publication("invalid", review_commit=observed_commit,
                               diagnostic="review capability map is missing")
        proposal_path = Path(temp) / "proposal.md"
        review_path = Path(temp) / "review-map.md"
        proposal_path.write_text(proposal_text, encoding="utf-8")
        review_path.write_text(review_map, encoding="utf-8")
        try:
            proposal = parse_proposal(proposal_path)
            if proposal.baseline.remote != remote or proposal.baseline.default_branch != branch:
                raise ContractError(BASELINE_REMOTE_MISMATCH)
            ancestor = _run(["git", "-C", str(repo), "merge-base", "--is-ancestor",
                             proposal.baseline.commit, observed_commit])
            baseline_map = _show(repo, proposal.baseline.commit, "spec/CAPABILITY-MAP.md")
            if not ancestor or baseline_map is None:
                raise ContractError(BASELINE_UNAVAILABLE)
            baseline_path = Path(temp) / "baseline-map.md"
            baseline_path.write_text(baseline_map, encoding="utf-8")
            validate_proposal(proposal_path, baseline_path)
            parse_map(review_path)
        except (ContractError, MapError, OSError, UnicodeError) as error:
            return Publication("invalid", review_commit=observed_commit, diagnostic=str(error))
        return Publication("published", review_commit=observed_commit, proposal=proposal,
                           baseline_map=baseline_map, review_map=review_map)


def read_published_pool(project, remote="origin"):
    """Read every Proposal from one remote-default snapshot, never a worktree."""
    with fixed_snapshot(project, remote, "sg-proposal-publication-") as snapshot:
        if snapshot.failure:
            return PublicationPool("unknown", diagnostic=snapshot.failure)
        repo, temp, branch, observed_commit = snapshot.repo, snapshot.temp, snapshot.branch, snapshot.commit
        listed = _run(["git", "-C", str(repo), "ls-tree", "-r", "--name-only",
                       observed_commit, "spec/proposals"])
        review_map = _show(repo, observed_commit, "spec/CAPABILITY-MAP.md")
        if not listed or review_map is None:
            return PublicationPool("invalid", review_commit=observed_commit,
                                   diagnostic="review capability map is missing")
        try:
            review_path = Path(temp) / "review-map.md"
            review_path.write_text(review_map, encoding="utf-8")
            review_module_ids = {row.module_id for row in parse_map(review_path).rows}
        except (MapError, OSError, UnicodeError):
            return PublicationPool("invalid", review_commit=observed_commit,
                                   diagnostic="review capability map is invalid")
        publications = []
        skipped = []
        proposal_ids = set()
        prefix = "spec/proposals/"
        paths = sorted(line for line in listed.stdout.splitlines()
                       if line.startswith(prefix) and line.endswith(".md"))
        if len(paths) > MAX_POOL_SIZE:
            return PublicationPool("unknown", review_commit=observed_commit,
                                   diagnostic="proposal pool exceeds the fixed limit")
        for path in paths:
            proposal_path = Path(temp) / "proposal.md"
            proposal_text = _show(repo, observed_commit, path)
            proposal_path.write_text(proposal_text, encoding="utf-8")
            try:
                proposal = parse_proposal(proposal_path)
            except (ContractError, OSError, UnicodeError) as error:
                return PublicationPool("invalid", review_commit=observed_commit, diagnostic=str(error))
            try:
                if proposal.baseline.remote != remote or proposal.baseline.default_branch != branch:
                    raise ContractError(BASELINE_REMOTE_MISMATCH)
                ancestor = _run(["git", "-C", str(repo), "merge-base", "--is-ancestor",
                                 proposal.baseline.commit, observed_commit])
                baseline_map = _show(repo, proposal.baseline.commit, "spec/CAPABILITY-MAP.md")
                if not ancestor or baseline_map is None:
                    raise ContractError(BASELINE_UNAVAILABLE)
                baseline_path = Path(temp) / "baseline-map.md"
                baseline_path.write_text(baseline_map, encoding="utf-8")
                validate_proposal(proposal_path, baseline_path)
            except (ContractError, OSError, UnicodeError) as error:
                if proposal.change.module_id in review_module_ids:
                    skipped.append((proposal.proposal_id, str(error)))
                    continue
                return PublicationPool("invalid", review_commit=observed_commit, diagnostic=str(error))
            if proposal.proposal_id in proposal_ids:
                return PublicationPool("invalid", review_commit=observed_commit,
                                       diagnostic="proposal pool contains a duplicate id")
            proposal_ids.add(proposal.proposal_id)
            publications.append(Publication("published", review_commit=observed_commit,
                                            proposal=proposal, baseline_map=baseline_map,
                                            review_map=review_map))
        return PublicationPool("published", review_commit=observed_commit,
                               publications=publications, review_map=review_map,
                               skipped=skipped)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".")
    parser.add_argument("--proposal-id", required=True)
    parser.add_argument("--remote", default="origin")
    args = parser.parse_args(argv)
    print(json.dumps(as_json(read_published(args.project, args.proposal_id, args.remote)),
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
