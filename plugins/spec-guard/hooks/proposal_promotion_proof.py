"""Read-only remote-default proof that a Proposal module was promoted."""
import argparse
import json
import subprocess
from pathlib import Path

from capability_map import MapError, parse_map
from proposal_contract import COMMIT
from proposal_mainline_review import DIAGNOSTIC_CODE, accepted_from_pool
from proposal_publication import fixed_snapshot, read_published_pool
from proposal_tracker_read import read_tracker


class Proof(object):
    def __init__(self, state, review_commit=None, proposal_id=None, module_id=None,
                 promotion_commit=None, diagnostic=None):
        self.state = state
        self.review_commit = review_commit
        self.proposal_id = proposal_id
        self.module_id = module_id
        self.promotion_commit = promotion_commit
        self.diagnostic = diagnostic


class Preflight(object):
    def __init__(self, state, proposal_id=None, revision=None, base_commit=None,
                 diagnostic=None):
        self.state = state
        self.proposal_id = proposal_id
        self.revision = revision
        self.base_commit = base_commit
        self.diagnostic = diagnostic


def preflight_as_json(result):
    data = {"state": result.state}
    for key, value in (("proposalId", result.proposal_id), ("revision", result.revision),
                       ("baseCommit", result.base_commit)):
        if value is not None:
            data[key] = value
    if result.state != "ready":
        code = result.diagnostic
        data["diagnostic"] = (code if isinstance(code, str) and DIAGNOSTIC_CODE.match(code)
                              else "promotion-preflight-%s" % result.state)
    return data


def as_json(result):
    """Serialize safe proof identifiers without remote, map, or raw-error data."""
    data = {"state": result.state}
    for key, value in (("reviewCommit", result.review_commit),
                       ("proposalId", result.proposal_id),
                       ("moduleId", result.module_id),
                       ("promotionCommit", result.promotion_commit)):
        if value is not None:
            data[key] = value
    if result.state == "not-promoted":
        data["diagnostic"] = result.diagnostic or "promotion-not-found"
    elif result.state in ("invalid", "unknown", "not-accepted"):
        code = result.diagnostic
        data["diagnostic"] = (code if isinstance(code, str) and DIAGNOSTIC_CODE.match(code)
                              else "promotion-%s" % result.state)
    return data


def _run(args):
    try:
        result = subprocess.run(args, text=True, capture_output=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result if result.returncode == 0 else None


def _show(repo, commit, path):
    result = _run(["git", "-C", str(repo), "show", "%s:%s" % (commit, path)])
    return result.stdout if result else None


def _map(repo, commit, temp):
    text = _show(repo, commit, "spec/CAPABILITY-MAP.md")
    if text is None:
        return "invalid"
    path = Path(temp) / ("map-%s.md" % commit)
    try:
        path.write_text(text, encoding="utf-8")
        return parse_map(path)
    except (MapError, OSError, UnicodeError):
        return "invalid"


def _matches(proposal, capability_map):
    rows = dict((row.module_id, row) for row in capability_map.rows)
    row = rows.get(proposal.change.module_id)
    if (row is None or row.responsibility != proposal.change.responsibility or
            tuple(row.depends_on) != tuple(proposal.change.depends_on)):
        return False
    position = capability_map.order.index(proposal.change.module_id)
    if proposal.change.anchor == "end":
        return position == len(capability_map.order) - 1
    anchor = proposal.change.anchor[len("after:"):]
    return (anchor in capability_map.order and
            position == capability_map.order.index(anchor) + 1)


def _first_parent(repo, commit):
    result = _run(["git", "-C", str(repo), "rev-list", "--parents", "-n", "1", commit])
    if not result:
        return None
    fields = result.stdout.split()
    return fields[1] if len(fields) >= 2 and fields[0] == commit else "invalid"


def _promotion_paths(repo, parent, commit):
    result = _run(["git", "-C", str(repo), "diff-tree", "--no-commit-id",
                   "--name-only", "-r", parent, commit])
    return set(result.stdout.splitlines()) if result else None


def _has_module_artifacts(repo, commit, proposal):
    module_id = proposal.change.module_id
    spec = _show(repo, commit, "spec/%s.md" % module_id)
    plan = _show(repo, commit, "tasks/%s/plan.md" % module_id)
    return (isinstance(spec, str) and spec.startswith("# Spec: %s" % module_id) and
            isinstance(plan, str) and plan.startswith("# Plan:"))


def _blocked(state, diagnostic=None):
    return Proof(state, diagnostic=diagnostic)


def preflight(project, proposal_id, platform, target, remote="origin", tracker_reader=None):
    """Freshly require remote policy, Issue and attestation before branch creation."""
    pool = read_published_pool(project, remote)
    pool_state = getattr(pool, "state", None)
    if pool_state != "published":
        state = pool_state if pool_state in ("invalid", "unknown") else "unknown"
        return Preflight(state, diagnostic="proposal-pool-%s" % state)
    publication = next((item for item in pool.publications
                        if item.proposal.proposal_id == proposal_id), None)
    if publication is None:
        return Preflight("absent", diagnostic="publication-absent")
    if publication.review_map != pool.review_map:
        return Preflight("stale", proposal_id=proposal_id,
                         revision=getattr(publication.proposal, "revision", None),
                         diagnostic="proposal-stale")
    reader = read_tracker if tracker_reader is None else tracker_reader
    tracker = reader(publication.proposal, platform, target)
    acceptance = accepted_from_pool(pool, publication, tracker, platform, target)
    if acceptance.state != "accepted":
        return Preflight(acceptance.state, proposal_id=proposal_id,
                         revision=getattr(publication.proposal, "revision", None),
                         diagnostic=acceptance.diagnostic)
    return Preflight("ready", proposal_id=proposal_id,
                     revision=publication.proposal.revision,
                     base_commit=pool.review_commit)


def prove(project, publication, review_result, remote="origin"):
    """Prove the first matching module commit from a fresh remote-default snapshot."""
    publication_state = getattr(publication, "state", None)
    if publication_state in ("absent", "invalid", "unknown"):
        return _blocked(publication_state, getattr(publication, "diagnostic", None))
    if publication_state != "published":
        return _blocked("unknown")
    review_state = getattr(review_result, "state", None)
    review_diagnostic = getattr(review_result, "diagnostic", None)
    if review_state in ("invalid", "unknown"):
        return _blocked(review_state, review_diagnostic)
    if review_state != "accepted":
        return _blocked("not-accepted", review_diagnostic)
    proposal = getattr(publication, "proposal", None)
    review_commit = getattr(publication, "review_commit", None)
    if (proposal is None or not isinstance(review_commit, str) or
            not COMMIT.fullmatch(review_commit) or
            getattr(proposal, "version", None) != "v2" or
            not isinstance(getattr(proposal, "revision", None), str) or
            getattr(review_result, "review_commit", None) != review_commit or
            getattr(review_result, "proposal_id", None) != proposal.proposal_id or
            getattr(review_result, "revision", None) != proposal.revision or
            not isinstance(getattr(review_result, "authority_id", None), str)):
        return _blocked("invalid")
    with fixed_snapshot(project, remote, "sg-proposal-promotion-proof-") as snapshot:
        if snapshot.failure:
            return _blocked("unknown")
        repo, temp, observed_commit = snapshot.repo, snapshot.temp, snapshot.commit
        ancestor = _run(["git", "-C", str(repo), "merge-base", "--is-ancestor",
                         review_commit, observed_commit])
        if not ancestor:
            return _blocked("invalid")
        commits = _run(["git", "-C", str(repo), "rev-list", "--first-parent",
                        "--reverse", "%s..%s" % (review_commit, observed_commit)])
        if not commits:
            return _blocked("unknown")
        for commit in commits.stdout.splitlines():
            capability_map = _map(repo, commit, temp)
            if capability_map == "invalid":
                return _blocked("invalid")
            if proposal.change.module_id not in capability_map.order:
                continue
            parent = _first_parent(repo, commit)
            if parent is None:
                return _blocked("unknown")
            if parent == "invalid":
                return _blocked("invalid")
            parent_map = _map(repo, parent, temp)
            if parent_map == "invalid":
                return _blocked("invalid")
            required_paths = {
                "spec/CAPABILITY-MAP.md",
                "spec/%s.md" % proposal.change.module_id,
                "tasks/%s/plan.md" % proposal.change.module_id,
            }
            allowed_paths = required_paths | {"tasks/%s/todo.md" % proposal.change.module_id}
            paths = _promotion_paths(repo, parent, commit)
            if (proposal.change.module_id in parent_map.order or
                    not _matches(proposal, capability_map) or
                    paths is None or not required_paths.issubset(paths) or
                    not paths.issubset(allowed_paths) or
                    not _has_module_artifacts(repo, commit, proposal)):
                return _blocked("invalid")
            return Proof("proved", review_commit=review_commit, proposal_id=proposal.proposal_id,
                         module_id=proposal.change.module_id, promotion_commit=commit)
    return Proof("not-promoted", proposal_id=proposal.proposal_id,
                 module_id=proposal.change.module_id, diagnostic="promotion-not-found")


def prove_from_remote(project, proposal_id, platform, target, remote="origin",
                      tracker_reader=None):
    """Re-establish acceptance from fresh remote facts, then prove; nothing is written."""
    pool = read_published_pool(project, remote)
    state = getattr(pool, "state", None)
    if state != "published":
        state = state if state in ("invalid", "unknown") else "unknown"
        return _blocked(state, "proposal-pool-%s" % state)
    publication = next((item for item in pool.publications
                        if item.proposal.proposal_id == proposal_id), None)
    if publication is None:
        return Proof("absent", proposal_id=proposal_id)
    reader = read_tracker if tracker_reader is None else tracker_reader
    tracker = reader(publication.proposal, platform, target)
    acceptance = accepted_from_pool(pool, publication, tracker, platform, target)
    return prove(project, publication, acceptance, remote)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Read-only Proposal promotion preflight, or post-merge proof with --prove.")
    parser.add_argument("--project", default=".")
    parser.add_argument("--proposal-id", required=True)
    parser.add_argument("--platform", choices=("github", "gitlab"), required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--prove", action="store_true",
                        help="prove the merged promotion instead of previewing its base")
    args = parser.parse_args(argv)
    target = int(args.target) if args.platform == "gitlab" and args.target.isdigit() else args.target
    if args.prove:
        print(json.dumps(as_json(prove_from_remote(
            args.project, args.proposal_id, args.platform, target, args.remote)),
            ensure_ascii=False))
        return 0
    print(json.dumps(preflight_as_json(preflight(
        args.project, args.proposal_id, args.platform, target, args.remote)),
        ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
