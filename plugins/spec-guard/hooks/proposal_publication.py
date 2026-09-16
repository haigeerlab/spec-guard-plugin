"""Read one published Proposal from a fixed remote-default Git snapshot."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from capability_map import MapError, parse_map
from proposal_contract import ContractError, PROPOSAL_ID, parse_proposal, validate_proposal


MAX_POOL_SIZE = 100


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
    return (branch, commit) if branch and commit else None


def _show(repo, commit, path):
    result = _run(["git", "-C", str(repo), "show", "%s:%s" % (commit, path)])
    return result.stdout if result else None


def read_published(project, proposal_id, remote="origin"):
    """Return only remote-default facts; never read consumer proposal/map files."""
    if not isinstance(proposal_id, str) or not PROPOSAL_ID.fullmatch(proposal_id):
        return Publication("invalid", diagnostic="proposal id is invalid")
    project = Path(project)
    url = _remote(project, remote)
    observed = _head(url) if url else None
    if not observed:
        return Publication("unknown", diagnostic="remote default branch is unavailable")
    branch, observed_commit = observed
    with tempfile.TemporaryDirectory(prefix="sg-proposal-publication-") as temp:
        repo = Path(temp) / "snapshot.git"
        if not _run(["git", "init", "--bare", str(repo)]):
            return Publication("unknown", diagnostic="temporary Git snapshot failed")
        fetched = _run(["git", "-C", str(repo), "fetch", "--no-tags", url,
                        "refs/heads/%s" % branch])
        tip = _run(["git", "-C", str(repo), "rev-parse", "FETCH_HEAD"])
        if not fetched or not tip or tip.stdout.strip() != observed_commit:
            return Publication("unknown", diagnostic="remote default branch moved or fetch failed")
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
        return Publication("published", review_commit=observed_commit, proposal=proposal,
                           baseline_map=baseline_map, review_map=review_map)


def read_published_pool(project, remote="origin"):
    """Read every Proposal from one remote-default snapshot, never a worktree."""
    project = Path(project)
    url = _remote(project, remote)
    observed = _head(url) if url else None
    if not observed:
        return PublicationPool("unknown", diagnostic="remote default branch is unavailable")
    branch, observed_commit = observed
    with tempfile.TemporaryDirectory(prefix="sg-proposal-publication-") as temp:
        repo = Path(temp) / "snapshot.git"
        if not _run(["git", "init", "--bare", str(repo)]):
            return PublicationPool("unknown", diagnostic="temporary Git snapshot failed")
        fetched = _run(["git", "-C", str(repo), "fetch", "--no-tags", url,
                        "refs/heads/%s" % branch])
        tip = _run(["git", "-C", str(repo), "rev-parse", "FETCH_HEAD"])
        if not fetched or not tip or tip.stdout.strip() != observed_commit:
            return PublicationPool("unknown", diagnostic="remote default branch moved or fetch failed")
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
            proposal_path.write_text(_show(repo, observed_commit, path), encoding="utf-8")
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
            publications.append(Publication("published", review_commit=observed_commit,
                                            proposal=proposal, baseline_map=baseline_map,
                                            review_map=review_map))
            if proposal.version == "v2":
                attestation_path = "spec/proposal-acceptances/%s-%s.json" % (
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
