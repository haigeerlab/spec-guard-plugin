"""Pure aggregation of published Proposal and verified tracker facts."""
import argparse
import json
import tempfile
from pathlib import Path

from capability_map import MapError, parse_map
from proposal_contract import compute


STAGES = {
    "proposal-stage:draft": "awaiting-review",
    "proposal-stage:published": "awaiting-review",
    "proposal-stage:in-review": "in-review",
    "proposal-stage:accepted": "accepted",
    "proposal-stage:needs-revision": "needs-revision",
    "proposal-stage:deferred": "deferred",
    "proposal-stage:rejected": "rejected",
    "proposal-stage:promoted": "promoted-claim",
}


class Review(object):
    def __init__(self, state, review_commit=None, proposal_id=None, platform=None, target=None,
                 issue_id=None, stage=None, revision=None, diagnostic=None):
        self.state = state
        self.review_commit = review_commit
        self.proposal_id = proposal_id
        self.platform = platform
        self.target = target
        self.issue_id = issue_id
        self.stage = stage
        self.revision = revision
        self.diagnostic = diagnostic


def as_json(result):
    """Serialize stable review facts without snapshot, Issue, or error content."""
    data = {"state": result.state}
    for key, value in (("reviewCommit", result.review_commit),
                       ("proposalId", result.proposal_id), ("platform", result.platform),
                       ("target", result.target), ("issueId", result.issue_id),
                       ("stage", result.stage), ("revision", result.revision)):
        if value is not None:
            data[key] = value
    if result.diagnostic in LAYER_DIAGNOSTICS:
        data["diagnostic"] = result.diagnostic
    elif result.state in ("invalid", "unknown"):
        data["diagnostic"] = "review-%s" % result.state
    elif result.state == "stale":
        data["diagnostic"] = "proposal-stale"
    elif result.state == "in-map":
        data["diagnostic"] = "proposal-module-already-present"
    return data


def _blocked(state):
    return Review(state, diagnostic="review-input-%s" % state)


# 区分是远端没有这份 Proposal，还是 Proposal 已发布但 Issue 缺失或不可读。
LAYER_DIAGNOSTICS = frozenset("%s-%s" % (layer, state)
                              for layer in ("publication", "tracker")
                              for state in ("absent", "invalid", "unknown"))


def _review_map(baseline, review):
    if not isinstance(baseline, str) or not isinstance(review, str):
        return None
    with tempfile.TemporaryDirectory(prefix="sg-proposal-review-") as temp:
        baseline_path = Path(temp) / "baseline-map.md"
        review_path = Path(temp) / "review-map.md"
        baseline_path.write_text(baseline, encoding="utf-8")
        review_path.write_text(review, encoding="utf-8")
        try:
            return parse_map(review_path), compute(str(review_path))
        except MapError:
            return "invalid"
        except (OSError, UnicodeError):
            return None


def review(publication, tracker, platform, target):
    """Interpret already-read facts; never query or mutate Git/tracker state."""
    publication_state = getattr(publication, "state", None)
    if publication_state in ("absent", "invalid", "unknown"):
        return Review(publication_state, diagnostic="publication-%s" % publication_state)
    if publication_state != "published":
        return Review("unknown", diagnostic="publication-unknown")
    proposal = getattr(publication, "proposal", None)
    tracker_state = getattr(tracker, "state", None)
    if tracker_state not in ("verified", "absent", "invalid"):
        tracker_state = "unknown"
    if tracker_state != "verified":
        return Review(tracker_state, review_commit=getattr(publication, "review_commit", None),
                      proposal_id=getattr(proposal, "proposal_id", None),
                      revision=getattr(proposal, "revision", None),
                      diagnostic="tracker-%s" % tracker_state)
    review_commit = getattr(publication, "review_commit", None)
    reviewed = _review_map(getattr(publication, "baseline_map", None),
                           getattr(publication, "review_map", None))
    if reviewed == "invalid":
        return _blocked("invalid")
    if proposal is None or not isinstance(review_commit, str) or reviewed is None:
        return _blocked("unknown")
    if (getattr(tracker, "proposal_id", None) != proposal.proposal_id or
            getattr(tracker, "platform", None) != platform or
            getattr(tracker, "target", None) != target):
        return _blocked("invalid")
    review_map, digest = reviewed
    expected_rows = proposal.baseline.module_digests
    actual_rows = dict((row["id"], row["rowDigest"]) for row in digest["rows"])
    if (digest["goalDigest"] != proposal.baseline.goal_digest or
            any(actual_rows.get(module_id) != row_digest
                for module_id, row_digest in expected_rows.items())):
        return Review("stale", review_commit=review_commit, proposal_id=proposal.proposal_id,
                      platform=platform, target=target, issue_id=tracker.issue_id,
                      stage=tracker.stage, revision=getattr(proposal, "revision", None),
                      diagnostic="proposal-baseline-drifted")
    if proposal.change.module_id in review_map.order:
        # Not stale: a promoted Proposal's module is meant to be here.  Whether it is this
        # Proposal's own promotion or a clash with an existing module is the proof's call.
        return Review("in-map", review_commit=review_commit, proposal_id=proposal.proposal_id,
                      platform=platform, target=target, issue_id=tracker.issue_id,
                      stage=tracker.stage, revision=getattr(proposal, "revision", None),
                      diagnostic="proposal-module-already-present")
    positions = dict((module_id, index) for index, module_id in enumerate(review_map.order))
    dependencies = proposal.change.depends_on
    if any(dependency not in positions for dependency in dependencies):
        return Review("stale", review_commit=review_commit, proposal_id=proposal.proposal_id,
                      platform=platform, target=target, issue_id=tracker.issue_id,
                      stage=tracker.stage, revision=getattr(proposal, "revision", None),
                      diagnostic="proposal-dependency-missing")
    anchor = proposal.change.anchor
    if anchor != "end":
        anchor_id = anchor[len("after:"):]
        if (anchor_id not in positions or
                any(positions[dependency] > positions[anchor_id] for dependency in dependencies)):
            return Review("stale", review_commit=review_commit, proposal_id=proposal.proposal_id,
                          platform=platform, target=target, issue_id=tracker.issue_id,
                          stage=tracker.stage, revision=getattr(proposal, "revision", None),
                          diagnostic="proposal-anchor-drifted")
    state = STAGES.get(tracker.stage)
    if state is None:
        return _blocked("invalid")
    return Review(state, review_commit=review_commit, proposal_id=proposal.proposal_id,
                  platform=platform, target=target, issue_id=tracker.issue_id,
                  stage=tracker.stage, revision=getattr(proposal, "revision", None))


def main(argv=None):
    """Read one published Proposal and its Issue, then print the review result."""
    # 读取层只在 CLI 中引入；review() 本身保持为不接触 Git 或 tracker 的纯函数。
    from proposal_publication import read_published
    from proposal_tracker_read import read_tracker

    parser = argparse.ArgumentParser(description="Read-only Proposal freshness and stage review.")
    parser.add_argument("--project", default=".")
    parser.add_argument("--proposal-id", required=True)
    parser.add_argument("--platform", choices=("github", "gitlab"), required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--remote", default="origin")
    args = parser.parse_args(argv)
    target = int(args.target) if args.platform == "gitlab" and args.target.isdigit() else args.target
    publication = read_published(args.project, args.proposal_id, args.remote)
    tracker = (read_tracker(publication.proposal, args.platform, target)
               if getattr(publication, "state", None) == "published" else None)
    print(json.dumps(as_json(review(publication, tracker, args.platform, target)),
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
