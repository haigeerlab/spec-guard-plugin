"""Read-only remote-default proof that a Proposal module was promoted."""
import argparse
import copy
import json
import re
import subprocess
from pathlib import Path

from capability_map import MapError, parse_map
from proposal_contract import COMMIT
from proposal_publication import (
    Publication, fixed_snapshot, read_published_pool, skipped_as_json)
from proposal_review import STAGES, Review, review
from proposal_tracker_read import read_tracker

# 只有稳定诊断码可以出现在输出里；说明文字和原始异常一律退回 promotion-<state>。
DIAGNOSTIC_CODE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")


class Proof(object):
    def __init__(self, state, review_commit=None, proposal_id=None, module_id=None,
                 promotion_commit=None, diagnostic=None, skipped_proposals=()):
        self.skipped_proposals = tuple(skipped_proposals)
        self.state = state
        self.review_commit = review_commit
        self.proposal_id = proposal_id
        self.module_id = module_id
        self.promotion_commit = promotion_commit
        self.diagnostic = diagnostic


class Preflight(object):
    def __init__(self, state, proposal_id=None, revision=None, base_commit=None,
                 diagnostic=None, skipped_proposals=()):
        self.skipped_proposals = tuple(skipped_proposals)
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
    if result.skipped_proposals:
        data["skippedProposals"] = skipped_as_json(result.skipped_proposals)
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
    elif result.state in ("invalid", "unknown", "not-accepted", "stale"):
        code = result.diagnostic
        data["diagnostic"] = (code if isinstance(code, str) and DIAGNOSTIC_CODE.match(code)
                              else "promotion-%s" % result.state)
    if result.skipped_proposals:
        data["skippedProposals"] = skipped_as_json(result.skipped_proposals)
    return data


def accepted(publication, tracker, platform, target):
    """A published v2 Proposal whose Issue stage is accepted and whose review is fresh."""
    proposal = getattr(publication, "proposal", None)
    if getattr(proposal, "version", None) != "v2" or not getattr(proposal, "revision", None):
        return Review("legacy-revision-required",
                      review_commit=getattr(publication, "review_commit", None),
                      proposal_id=getattr(proposal, "proposal_id", None),
                      revision=getattr(proposal, "revision", None))
    return review(publication, tracker, platform, target)


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


def _rows(capability_map):
    return dict((row.module_id, (row.responsibility, tuple(row.depends_on)))
                for row in capability_map.rows)


def _only_adds(module_id, parent_map, commit_map):
    """The commit adds exactly this module row and leaves every other row untouched."""
    parent_rows, commit_rows = _rows(parent_map), _rows(commit_map)
    commit_rows.pop(module_id, None)
    return (parent_rows == commit_rows and
            [item for item in commit_map.order if item != module_id] == list(parent_map.order))


def _blocked(state, diagnostic=None):
    return Proof(state, diagnostic=diagnostic)


def preflight(project, proposal_id, platform, target, remote="origin", tracker_reader=None):
    """Freshly require an accepted Issue stage and a fresh review before branch creation."""
    return promotion_base(project, proposal_id, platform, target, remote, tracker_reader)[0]


def promotion_base(project, proposal_id, platform, target, remote="origin", tracker_reader=None):
    """Run the preflight once and, when ready, also return the base map text and Proposal."""
    pool = read_published_pool(project, remote)
    result = _preflight(pool, proposal_id, platform, target, tracker_reader)
    if getattr(pool, "state", None) == "published":
        result.skipped_proposals = tuple(getattr(pool, "skipped", ()))
    if result.state != "ready":
        return result, None, None
    publication = next(item for item in pool.publications
                       if item.proposal.proposal_id == proposal_id)
    return result, pool.review_map, publication.proposal


def _preflight(pool, proposal_id, platform, target, tracker_reader):
    pool_state = getattr(pool, "state", None)
    if pool_state != "published":
        state = pool_state if pool_state in ("invalid", "unknown") else "unknown"
        return Preflight(state, diagnostic="proposal-pool-%s" % state)
    publication = next((item for item in pool.publications
                        if item.proposal.proposal_id == proposal_id), None)
    if publication is None:
        return Preflight("absent", diagnostic="publication-absent")
    reader = read_tracker if tracker_reader is None else tracker_reader
    tracker = reader(publication.proposal, platform, target)
    acceptance = accepted(publication, tracker, platform, target)
    if acceptance.state != "accepted":
        return Preflight(acceptance.state, proposal_id=proposal_id,
                         revision=getattr(publication.proposal, "revision", None),
                         diagnostic=acceptance.diagnostic)
    return Preflight("ready", proposal_id=proposal_id,
                     revision=publication.proposal.revision,
                     base_commit=pool.review_commit)


def prove(project, publication, tracker, platform, target, remote="origin"):
    """Prove the first matching module commit from a fresh remote-default snapshot."""
    publication_state = getattr(publication, "state", None)
    if publication_state in ("absent", "invalid", "unknown"):
        return _blocked(publication_state, getattr(publication, "diagnostic", None))
    if publication_state != "published":
        return _blocked("unknown")
    tracker_state = getattr(tracker, "state", None)
    if tracker_state != "verified":
        state = tracker_state if tracker_state in ("absent", "invalid") else "unknown"
        return _blocked(state, "tracker-%s" % state)
    proposal = getattr(publication, "proposal", None)
    if (proposal is None or getattr(proposal, "version", None) != "v2" or
            not isinstance(getattr(proposal, "revision", None), str) or
            not COMMIT.fullmatch(str(getattr(proposal.baseline, "commit", None))) or
            getattr(tracker, "proposal_id", None) != proposal.proposal_id or
            getattr(tracker, "platform", None) != platform or
            getattr(tracker, "target", None) != target):
        return _blocked("invalid")
    if tracker.stage not in ("proposal-stage:accepted", "proposal-stage:promoted"):
        if tracker.stage not in STAGES:
            return _blocked("invalid")
        return _blocked("not-accepted")
    baseline_commit = proposal.baseline.commit
    module_id = proposal.change.module_id
    with fixed_snapshot(project, remote, "sg-proposal-promotion-proof-") as snapshot:
        if snapshot.failure:
            return _blocked("unknown")
        repo, temp, observed_commit = snapshot.repo, snapshot.temp, snapshot.commit
        ancestor = _run(["git", "-C", str(repo), "merge-base", "--is-ancestor",
                         baseline_commit, observed_commit])
        if not ancestor:
            return _blocked("invalid")
        commits = _run(["git", "-C", str(repo), "rev-list", "--first-parent",
                        "--reverse", "%s..%s" % (baseline_commit, observed_commit)])
        if not commits:
            return _blocked("unknown")
        for commit in commits.stdout.splitlines():
            capability_map = _map(repo, commit, temp)
            if capability_map == "invalid":
                return _blocked("invalid")
            if module_id not in capability_map.order:
                continue
            parent = _first_parent(repo, commit)
            if parent is None:
                return _blocked("unknown")
            if parent == "invalid":
                return _blocked("invalid")
            parent_map = _map(repo, parent, temp)
            parent_text = _show(repo, parent, "spec/CAPABILITY-MAP.md")
            if parent_map == "invalid" or parent_text is None:
                return _blocked("invalid")
            if (module_id in parent_map.order or
                    not _matches(proposal, capability_map) or
                    not _only_adds(module_id, parent_map, capability_map)):
                return _blocked("invalid")
            # 晋级那一刻的新鲜度：在父提交的能力图上评审，accepted 与 promoted 阶段等价。
            at_parent = Publication(
                "published", review_commit=parent, proposal=proposal,
                baseline_map=getattr(publication, "baseline_map", None), review_map=parent_text)
            facts = review(at_parent, _as_accepted(tracker), platform, target)
            if facts.state == "stale":
                return _blocked("stale", facts.diagnostic)
            if facts.state != "accepted":
                return _blocked(facts.state if facts.state in ("invalid", "unknown")
                                else "unknown", facts.diagnostic)
            return Proof("proved", review_commit=parent, proposal_id=proposal.proposal_id,
                         module_id=module_id, promotion_commit=commit)
    return Proof("not-promoted", proposal_id=proposal.proposal_id,
                 module_id=module_id, diagnostic="promotion-not-found")


def _as_accepted(tracker):
    relaxed = copy.copy(tracker)
    relaxed.stage = "proposal-stage:accepted"
    return relaxed


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
        result = Proof("absent", proposal_id=proposal_id)
    else:
        reader = read_tracker if tracker_reader is None else tracker_reader
        tracker = reader(publication.proposal, platform, target)
        result = prove(project, publication, tracker, platform, target, remote)
    result.skipped_proposals = tuple(getattr(pool, "skipped", ()))
    return result


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
