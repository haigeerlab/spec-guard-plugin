"""Read one published Proposal from a fixed remote-default Git snapshot."""
import argparse
import json
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path

from capability_map import MapError, parse_map
from proposal_contract import COMMIT, ContractError, PROPOSAL_ID, parse_proposal, validate_proposal


MAX_POOL_SIZE = 100
ATTESTATION_PATH_TEMPLATE = "spec/proposal-acceptances/%s-%s.json"


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
                 policy_text=None, attestation_texts=None, diagnostic=None):
        self.state = state
        self.review_commit = review_commit
        self.publications = tuple(publications)
        self.review_map = review_map
        self.policy_text = policy_text
        self.attestation_texts = dict(attestation_texts or {})
        self.diagnostic = diagnostic


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


def _head(url):
    result = _run(["git", "ls-remote", "--symref", url, "HEAD"])
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
    """
    url = _remote(Path(project), remote)
    observed = _head(url) if url else None
    if not observed:
        yield Snapshot("remote default branch is unavailable")
        return
    branch, commit = observed
    with tempfile.TemporaryDirectory(prefix=prefix) as temp:
        repo = Path(temp) / "snapshot.git"
        if not _run(["git", "init", "--bare", str(repo)]):
            yield Snapshot("temporary Git snapshot failed")
            return
        fetched = _run(["git", "-C", str(repo), "fetch", "--no-tags", url,
                        "refs/heads/%s" % branch])
        tip = _run(["git", "-C", str(repo), "rev-parse", "FETCH_HEAD"])
        if not fetched or not tip or tip.stdout.strip() != commit:
            yield Snapshot("remote default branch moved or fetch failed")
            return
        yield Snapshot(repo=repo, temp=Path(temp), url=url, branch=branch, commit=commit)


def _show(repo, commit, path):
    result = _run(["git", "-C", str(repo), "show", "%s:%s" % (commit, path)])
    return result.stdout if result else None


def _attested_review_commit(repo, observed_commit, proposal, proposal_text, policy_text):
    """Keep a v2 attestation's prior snapshot only while all reviewed facts match."""
    if getattr(proposal, "version", None) != "v2":
        return observed_commit
    attestation_path = ATTESTATION_PATH_TEMPLATE % (
        proposal.proposal_id, proposal.revision)
    try:
        attestation = json.loads(_show(repo, observed_commit, attestation_path))
    except (TypeError, ValueError):
        return observed_commit
    review_commit = attestation.get("reviewCommit") if isinstance(attestation, dict) else None
    if not isinstance(review_commit, str) or not COMMIT.fullmatch(review_commit):
        return observed_commit
    ancestor = _run(["git", "-C", str(repo), "merge-base", "--is-ancestor",
                     review_commit, observed_commit])
    paths = (
        ("spec/proposals/%s.md" % proposal.proposal_id, proposal_text),
        ("spec/proposal-mainline-policy.json", policy_text),
    )
    if not ancestor or any(_show(repo, review_commit, path) != text for path, text in paths):
        return observed_commit
    return review_commit


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
                raise ContractError("Proposal baseline remote or default branch differs")
            ancestor = _run(["git", "-C", str(repo), "merge-base", "--is-ancestor",
                             proposal.baseline.commit, observed_commit])
            baseline_map = _show(repo, proposal.baseline.commit, "spec/CAPABILITY-MAP.md")
            if not ancestor or baseline_map is None:
                raise ContractError("Proposal baseline commit is not on remote default branch")
            baseline_path = Path(temp) / "baseline-map.md"
            baseline_path.write_text(baseline_map, encoding="utf-8")
            validate_proposal(proposal_path, baseline_path)
            parse_map(review_path)
        except (ContractError, MapError, OSError, UnicodeError) as error:
            return Publication("invalid", review_commit=observed_commit, diagnostic=str(error))
        policy_text = _show(repo, observed_commit, "spec/proposal-mainline-policy.json")
        review_commit = _attested_review_commit(repo, observed_commit, proposal, proposal_text,
                                                policy_text)
        review_map = _show(repo, review_commit, "spec/CAPABILITY-MAP.md")
        if review_map is None:
            return Publication("unknown", diagnostic="attested review map is unavailable")
        return Publication("published", review_commit=review_commit, proposal=proposal,
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
            parse_map(review_path)
        except (MapError, OSError, UnicodeError):
            return PublicationPool("invalid", review_commit=observed_commit,
                                   diagnostic="review capability map is invalid")
        publications = []
        proposal_ids = set()
        policy_text = _show(repo, observed_commit, "spec/proposal-mainline-policy.json")
        attestation_texts = {}
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
                if proposal.baseline.remote != remote or proposal.baseline.default_branch != branch:
                    raise ContractError("Proposal baseline remote or default branch differs")
                ancestor = _run(["git", "-C", str(repo), "merge-base", "--is-ancestor",
                                 proposal.baseline.commit, observed_commit])
                baseline_map = _show(repo, proposal.baseline.commit, "spec/CAPABILITY-MAP.md")
                if not ancestor or baseline_map is None:
                    raise ContractError("Proposal baseline commit is not on remote default branch")
                baseline_path = Path(temp) / "baseline-map.md"
                baseline_path.write_text(baseline_map, encoding="utf-8")
                validate_proposal(proposal_path, baseline_path)
            except (ContractError, OSError, UnicodeError) as error:
                return PublicationPool("invalid", review_commit=observed_commit, diagnostic=str(error))
            if proposal.proposal_id in proposal_ids:
                return PublicationPool("invalid", review_commit=observed_commit,
                                       diagnostic="proposal pool contains a duplicate id")
            proposal_ids.add(proposal.proposal_id)
            review_commit = _attested_review_commit(repo, observed_commit, proposal,
                                                     proposal_text, policy_text)
            publication_map = _show(repo, review_commit, "spec/CAPABILITY-MAP.md")
            if publication_map is None:
                return PublicationPool("unknown", review_commit=observed_commit,
                                       diagnostic="attested review map is unavailable")
            publications.append(Publication("published", review_commit=review_commit,
                                            proposal=proposal, baseline_map=baseline_map,
                                            review_map=publication_map))
            if proposal.version == "v2":
                attestation_path = ATTESTATION_PATH_TEMPLATE % (
                    proposal.proposal_id, proposal.revision)
                text = _show(repo, observed_commit, attestation_path)
                if text is not None:
                    attestation_texts[proposal.proposal_id] = text
        return PublicationPool("published", review_commit=observed_commit,
                               publications=publications, review_map=review_map,
                               policy_text=policy_text,
                               attestation_texts=attestation_texts)


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
