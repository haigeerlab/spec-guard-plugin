"""Pure mainline Proposal review policy; it never reads Git or writes tracker state."""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

from capability_map import MapError, parse_map
from proposal_review import review
from proposal_publication import read_published_pool
from proposal_tracker_read import read_tracker


HARD_CONFLICTS = frozenset((
    "package-boundary-conflict",
    "public-contract-conflict",
    "anchor-conflict",
))
OBSERVATION_KINDS = HARD_CONFLICTS | frozenset((
    "unmerged-public-contract-change",
    "dependency-suggestion",
    "anchor-suggestion",
))
DECISIONS = {
    "accept": "accepted-candidate",
    "needs-revision": "needs-revision",
    "defer": "deferred",
    "reject": "rejected-candidate",
}
ATTESTATION_FIELDS = frozenset((
    "schemaVersion", "proposalId", "revision", "reviewCommit", "policyDigest",
    "authorityId", "decision",
))
POLICY_FIELDS = frozenset((
    "schemaVersion", "authorityId", "remote", "reviewRef", "workflowId",
))
# 只有稳定诊断码可以出现在输出里；发布层的说明文字和原始异常一律退回 mainline-<state>。
DIAGNOSTIC_CODE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")


class MainlineReview(object):
    def __init__(self, state, proposal_id=None, revision=None, review_commit=None,
                 authority_id=None, current_module_id=None, reason_codes=(),
                 diagnostic=None, candidates=(), skipped=()):
        self.state = state
        self.proposal_id = proposal_id
        self.revision = revision
        self.review_commit = review_commit
        self.authority_id = authority_id
        self.current_module_id = current_module_id
        self.reason_codes = tuple(reason_codes)
        self.diagnostic = diagnostic
        self.candidates = tuple(candidates)
        self.skipped = tuple(skipped)


def as_json(result):
    """Serialize only stable mainline-review identifiers and reason codes."""
    data = {"state": result.state}
    for key, value in (("proposalId", result.proposal_id), ("revision", result.revision),
                       ("reviewCommit", result.review_commit),
                       ("authorityId", result.authority_id),
                       ("currentModuleId", result.current_module_id)):
        if value is not None:
            data[key] = value
    if result.candidates:
        data["candidates"] = list(result.candidates)
    if result.skipped:
        data["skipped"] = [{"proposalId": proposal_id, "reason": reason}
                           for proposal_id, reason in result.skipped]
    if result.reason_codes:
        data["reasonCodes"] = list(result.reason_codes)
    if result.state in ("blocked", "invalid", "unknown", "stale",
                        "legacy-revision-required"):
        code = result.diagnostic
        data["diagnostic"] = (code if isinstance(code, str) and DIAGNOSTIC_CODE.match(code)
                              else "mainline-%s" % result.state)
    return data


def _unusable_pool(pool):
    """Report an unreadable or invalid snapshot before any policy or Git check."""
    state = getattr(pool, "state", None)
    if state == "published":
        return None
    state = state if state in ("invalid", "unknown") else "unknown"
    return MainlineReview(state, diagnostic="proposal-pool-%s" % state)


def _result(state, publication, context=None, reason_codes=(), diagnostic=None,
            authority_id=None):
    proposal = getattr(publication, "proposal", None)
    return MainlineReview(
        state,
        proposal_id=getattr(proposal, "proposal_id", None),
        revision=getattr(proposal, "revision", None),
        review_commit=getattr(publication, "review_commit", None),
        authority_id=(context.get("authorityId") if isinstance(context, dict)
                      else authority_id),
        current_module_id=context.get("currentModuleId") if isinstance(context, dict) else None,
        reason_codes=reason_codes,
        diagnostic=diagnostic,
    )


def _matching_context(policy, context):
    required_policy = ("authorityId", "remote", "reviewRef", "workflowId")
    required_context = ("authorityId", "branch", "upstream", "workflowId", "currentModuleId")
    if (not isinstance(policy, dict) or not isinstance(context, dict) or
            any(not isinstance(policy.get(key), str) or not policy[key]
                for key in required_policy) or
            any(not isinstance(context.get(key), str) or not context[key]
                for key in required_context)):
        return False
    return (context["authorityId"] == policy["authorityId"] and
            context["branch"] == policy["reviewRef"] and
            context["upstream"] == "%s/%s" % (
                policy["remote"], policy["reviewRef"][len("refs/heads/"):]) and
            context["workflowId"] == policy["workflowId"])


def _contains_current_module(publication, context):
    try:
        with tempfile.TemporaryDirectory(prefix="sg-mainline-review-") as temp:
            path = Path(temp) / "review-map.md"
            path.write_text(publication.review_map, encoding="utf-8")
            return context["currentModuleId"] in parse_map(path).order
    except (AttributeError, MapError, OSError, UnicodeError):
        return None


def _pool_contains_current_module(pool, context):
    review_map = getattr(pool, "review_map", None)
    if not isinstance(review_map, str):
        return None
    try:
        with tempfile.TemporaryDirectory(prefix="sg-mainline-review-") as temp:
            path = Path(temp) / "review-map.md"
            path.write_text(review_map, encoding="utf-8")
            return context["currentModuleId"] in parse_map(path).order
    except (MapError, OSError, UnicodeError):
        return None


def _observation_codes(publication, context, observations):
    if not isinstance(observations, (tuple, list)):
        return None
    proposal = getattr(publication, "proposal", None)
    change = getattr(proposal, "change", None)
    if change is None:
        return None
    related_module_ids = set((context["currentModuleId"], change.module_id))
    related_module_ids.update(change.depends_on)
    if change.anchor != "end":
        related_module_ids.add(change.anchor[len("after:"):])
    codes = []
    for item in observations:
        if (not isinstance(item, dict) or set(item) - {"kind", "moduleIds"} or
                not isinstance(item.get("kind"), str) or
                item["kind"] not in OBSERVATION_KINDS or
                not isinstance(item.get("moduleIds"), list) or
                not item["moduleIds"] or
                any(not isinstance(module_id, str) or not module_id
                    for module_id in item["moduleIds"]) or
                any(module_id not in related_module_ids for module_id in item["moduleIds"])):
            return None
        codes.append(item["kind"])
    return tuple(sorted(set(codes)))


def policy_digest(policy):
    """Return the canonical digest used by an immutable acceptance attestation."""
    if not isinstance(policy, dict):
        return None
    try:
        encoded = json.dumps(policy, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True).encode("utf-8")
    except (TypeError, ValueError):
        return None
    return hashlib.sha256(encoded).hexdigest()


def policy_from_pool(pool):
    """Parse the policy read from the same fixed snapshot as a Proposal pool."""
    text = getattr(pool, "policy_text", None)
    try:
        policy = json.loads(text)
    except (TypeError, ValueError):
        return None
    if (not isinstance(policy, dict) or set(policy) != POLICY_FIELDS or
            policy.get("schemaVersion") != 1 or
            any(not isinstance(policy.get(key), str) or not policy[key]
                for key in POLICY_FIELDS - {"schemaVersion"}) or
            not policy["reviewRef"].startswith("refs/heads/")):
        return None
    return policy


def _git_text(project, args):
    try:
        result = subprocess.run(["git", "-C", str(project)] + args, text=True,
                                capture_output=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _local_mainline_context(project, pool, authority_id, boundary, current_module_id):
    """Return (context, None) or (None, stable diagnostic code) for this worktree."""
    policy = policy_from_pool(pool)
    if boundary not in ("module-deliver", "module-advance"):
        return None, "mainline-boundary-invalid"
    if policy is None:
        return None, "mainline-policy-invalid"
    if (not isinstance(authority_id, str) or
            not isinstance(current_module_id, str) or not current_module_id):
        return None, "mainline-input-invalid"
    if authority_id != policy["authorityId"]:
        return None, "mainline-authority-mismatch"
    branch = _git_text(project, ["symbolic-ref", "-q", "HEAD"])
    upstream = _git_text(project, ["rev-parse", "--abbrev-ref",
                                   "--symbolic-full-name", "@{upstream}"])
    if branch is None or upstream is None:
        return None, "mainline-branch-unavailable"
    context = {
        "authorityId": authority_id,
        "branch": branch,
        "upstream": upstream,
        "workflowId": policy["workflowId"],
        "currentModuleId": current_module_id,
    }
    if not _matching_context(policy, context):
        return None, "mainline-context-invalid"
    try:
        topology = subprocess.run(
            ["git", "-C", str(project), "merge-base", "--is-ancestor",
             pool.review_commit, "HEAD"], text=True, capture_output=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None, "mainline-topology-unavailable"
    if topology.returncode == 1:
        return None, "mainline-review-commit-not-ancestor"
    if topology.returncode != 0:
        return None, "mainline-topology-unavailable"
    return context, None


def local_mainline_context(project, pool, authority_id, boundary, current_module_id):
    """Read only this worktree's Git topology against a remote-snapshot policy."""
    return _local_mainline_context(project, pool, authority_id, boundary, current_module_id)[0]


def accepted(publication, tracker, platform, target, policy, attestation):
    """Require a fresh accepted Issue fact and an exact immutable attestation."""
    proposal = getattr(publication, "proposal", None)
    if getattr(proposal, "version", None) != "v2" or not getattr(proposal, "revision", None):
        return _result("legacy-revision-required", publication)
    if not isinstance(policy, dict):
        return _result("blocked", publication, diagnostic="mainline-policy-invalid")
    facts = review(publication, tracker, platform, target)
    if facts.state != "accepted":
        return _result(facts.state, publication, diagnostic=facts.diagnostic)
    if (not isinstance(attestation, dict) or set(attestation) != ATTESTATION_FIELDS or
            attestation.get("schemaVersion") != 1 or
            attestation.get("proposalId") != proposal.proposal_id or
            attestation.get("revision") != proposal.revision or
            attestation.get("reviewCommit") != publication.review_commit or
            attestation.get("policyDigest") != policy_digest(policy) or
            attestation.get("authorityId") != policy.get("authorityId") or
            attestation.get("decision") != "accept"):
        return _result("blocked", publication, diagnostic="acceptance-attestation-invalid")
    return _result("accepted", publication, authority_id=policy["authorityId"])


def accepted_from_pool(pool, publication, tracker, platform, target):
    """Read acceptance evidence only from the pool's remote-default snapshot."""
    policy = policy_from_pool(pool)
    proposal = getattr(publication, "proposal", None)
    text = (getattr(pool, "attestation_texts", {}) or {}).get(
        getattr(proposal, "proposal_id", None))
    try:
        attestation = json.loads(text)
    except (TypeError, ValueError):
        attestation = None
    return accepted(publication, tracker, platform, target, policy, attestation)


def discover_from_pool(project, pool, tracker_for, platform, target, authority_id,
                       boundary, current_module_id):
    """Discover candidates only after reading policy and Git context locally."""
    unusable = _unusable_pool(pool)
    if unusable is not None:
        return unusable
    context, code = _local_mainline_context(project, pool, authority_id, boundary,
                                            current_module_id)
    if context is None:
        return MainlineReview("blocked", diagnostic=code)
    return discover(pool, tracker_for, platform, target, policy_from_pool(pool), context,
                    boundary)


def discover(pool, tracker_for, platform, target, policy, context, boundary):
    """Return a complete, sorted mainline candidate list from already-read facts."""
    if boundary not in ("module-deliver", "module-advance"):
        return MainlineReview("blocked", diagnostic="mainline-boundary-invalid")
    if not _matching_context(policy, context):
        return MainlineReview("blocked", diagnostic="mainline-context-invalid")
    if getattr(pool, "state", None) != "published":
        return MainlineReview(getattr(pool, "state", "unknown"),
                              diagnostic=getattr(pool, "diagnostic", None))
    if not callable(tracker_for):
        return MainlineReview("unknown", diagnostic="tracker-reader-unavailable")
    current_module = _pool_contains_current_module(pool, context)
    if current_module is None:
        return MainlineReview("unknown", diagnostic="review-map-unavailable")
    if not current_module:
        return MainlineReview("invalid", diagnostic="current-module-is-not-in-review-map")
    candidates = []
    skipped = []
    for publication in getattr(pool, "publications", ()):
        proposal = getattr(publication, "proposal", None)
        if (getattr(proposal, "version", None) != "v2" or
                not getattr(proposal, "revision", None)):
            skipped.append((proposal.proposal_id, "legacy-revision-required"))
            continue
        tracker = tracker_for(proposal)
        facts = review(publication, tracker, platform, target)
        if facts.state in ("awaiting-review", "in-review"):
            candidates.append(proposal.proposal_id)
        elif facts.state in ("invalid", "unknown"):
            return MainlineReview(facts.state, diagnostic="candidate-facts-%s" % facts.state)
        else:
            skipped.append((proposal.proposal_id, "review-%s" % facts.state))
    return MainlineReview("candidate-list", authority_id=context["authorityId"],
                          current_module_id=context["currentModuleId"],
                          candidates=tuple(sorted(candidates)), skipped=tuple(sorted(skipped)))


def evaluate(publication, tracker, platform, target, policy, context, decision, observations):
    """Evaluate remote facts plus explicit, bounded local review input.

    The caller is responsible for obtaining policy/context facts.  This function
    deliberately has no transport or write capability, so no result can mutate
    a Proposal Issue, branch, or capability map.
    """
    if not _matching_context(policy, context):
        return _result("blocked", publication, context, diagnostic="mainline-context-invalid")
    proposal = getattr(publication, "proposal", None)
    if getattr(proposal, "version", None) != "v2" or not getattr(proposal, "revision", None):
        return _result("legacy-revision-required", publication, context)
    current_module = _contains_current_module(publication, context)
    if current_module is None:
        return _result("unknown", publication, context, diagnostic="review-map-unavailable")
    if not current_module:
        return _result("invalid", publication, context, diagnostic="current-module-is-not-in-review-map")
    facts = review(publication, tracker, platform, target)
    if facts.state not in ("awaiting-review", "in-review"):
        return _result(facts.state, publication, context, diagnostic=facts.diagnostic)
    codes = _observation_codes(publication, context, observations)
    if codes is None:
        return _result("invalid", publication, context, diagnostic="local-observation-invalid")
    if any(code in HARD_CONFLICTS for code in codes):
        return _result("needs-revision", publication, context, codes)
    state = DECISIONS.get(decision)
    if state is None:
        return _result("invalid", publication, context, codes, "mainline-decision-invalid")
    return _result(state, publication, context, codes)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only mainline Proposal candidates.")
    parser.add_argument("--project", default=".")
    parser.add_argument("--platform", choices=("github", "gitlab"), required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--authority-id", required=True)
    parser.add_argument("--boundary", choices=("module-deliver", "module-advance"),
                        required=True)
    parser.add_argument("--current-module-id", required=True)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--proposal-id")
    parser.add_argument("--decision", choices=tuple(DECISIONS))
    parser.add_argument("--observations-json", default="[]")
    args = parser.parse_args(argv)
    target = int(args.target) if args.platform == "gitlab" and args.target.isdigit() else args.target
    pool = read_published_pool(args.project, args.remote)
    if args.decision is None:
        if args.proposal_id is not None:
            parser.error("--proposal-id requires --decision")
        result = discover_from_pool(
            args.project, pool,
            lambda proposal: read_tracker(proposal, args.platform, target),
            args.platform, target, args.authority_id, args.boundary, args.current_module_id)
    else:
        if args.proposal_id is None:
            parser.error("--decision requires --proposal-id")
        try:
            observations = json.loads(args.observations_json)
        except ValueError:
            observations = None
        result = _unusable_pool(pool)
        if result is None:
            context, code = _local_mainline_context(args.project, pool, args.authority_id,
                                                    args.boundary, args.current_module_id)
            publication = next((item for item in getattr(pool, "publications", ())
                                if item.proposal.proposal_id == args.proposal_id), None)
            if context is None:
                result = MainlineReview("blocked", diagnostic=code)
            elif publication is None:
                result = MainlineReview("invalid", diagnostic="proposal-not-published")
            else:
                result = evaluate(publication,
                                  read_tracker(publication.proposal, args.platform, target),
                                  args.platform, target, policy_from_pool(pool), context,
                                  args.decision, observations)
    print(json.dumps(as_json(result), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
