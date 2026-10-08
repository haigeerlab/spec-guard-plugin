"""Decide whether a Proposal's tracker item may be closed out.

This is the whole judgement, shared by the Local, GitHub and GitLab backends: only the
provider adapters differ.  It is a pure function on three observed facts, and it
deliberately cannot reach a project root, a provider or a filesystem path.

That restriction is the point.  A module with a plan and no `tasks/<id>/todo.md` counts
as done (see `spec/plan-without-todo.md`), so a module looks finished the instant it is
promoted -- long before anyone has written its Spec.  Closing a Proposal on that basis
would be wrong, and with nothing in reach to read a module stage from, this function
cannot make that mistake even by accident.
"""
from __future__ import annotations

import fcntl
import hashlib
import stat
import json
import os
import re
from pathlib import Path

from proposal_promotion_proof import prove_from_remote
from proposal_publication import read_published, read_published_pool, skipped_as_json
from defect_guard import is_defect
from state_paths import legacy_root, state_dir
from proposal_tracker_read import (
    CONTRACT_INVALID, MARKER_AMBIGUOUS, issue_identity, recover_tracker_issue,
)

JOURNAL_ROOT = state_dir("proposal-closeout", legacy_root() / "proposal-closeout")

PROMOTED_STAGE = "proposal-stage:promoted"
ACCEPTED_STAGE = "proposal-stage:accepted"
CLOSEABLE_STAGES = (ACCEPTED_STAGE, PROMOTED_STAGE)
PROVED = "proved"
# A proof that could not read, as opposed to one that read and refused.  The distinction
# has to survive into the state, because that is what callers branch on.
PROOF_UNREADABLE = "unknown"


class Decision(object):
    """`eligible`, `already-closed`, `not-eligible` or `unknown`."""

    def __init__(self, state, target_stage=None, needs_stage_change=None,
                 diagnostic=None):
        self.state = state
        self.target_stage = target_stage
        self.needs_stage_change = needs_stage_change
        self.diagnostic = diagnostic


def closeout_decision(stage, closed, proof_state, proof_diagnostic=None):
    """Judge one Proposal item.  Closed first, then the proof, then the stage.

    `already-closed` wins over everything so a rerun after a successful closeout -- or
    after a human closed the item -- reports the fact and writes nothing.  The proof is
    checked before the stage so a caller learns why the promotion is not provable rather
    than being told its stage is wrong.

    A proof that could not read is `unknown`, not `not-eligible`.  Both write nothing,
    so the two differ only in what they tell the reader to do -- and that is the whole
    point: `not-eligible` reads as a verdict about the Proposal, so it sends someone to
    investigate a document that never moved, when the fix is to retry.  Four of
    `prove()`'s `unknown` paths carry no diagnostic at all, so the state is all the
    reader has.  That is this repo's invariant: a failed probe degrades, it is not
    reported as a broken link.
    """
    if closed is True:
        return Decision("already-closed")
    if proof_state == PROOF_UNREADABLE:
        return Decision("unknown",
                        diagnostic=proof_diagnostic or "promotion-unknown")
    if proof_state != PROVED:
        return Decision("not-eligible",
                        diagnostic=proof_diagnostic or "promotion-not-proved")
    if stage not in CLOSEABLE_STAGES:
        return Decision("not-eligible", diagnostic="stage-not-closeable")
    return Decision("eligible", target_stage=PROMOTED_STAGE,
                    needs_stage_change=stage != PROMOTED_STAGE)


MARKER_NAMESPACE = "spec-guard-proposal-closeout:v1"
REVISION_DIGITS = 12
# Stable codes for the two read layers, so a missing Proposal, a missing item and an
# unreadable container stay distinguishable even where the state would coincide.
TRACKER_CODES = {"absent": "tracker-absent", "unknown": "tracker-unknown"}
RECORD = (
    "Proposal `%(id)s` is promoted.\n"
    "\n"
    "The change this Proposal declared is in the capability map on the remote default\n"
    "branch as of `%(promotion)s`, proved against `%(review)s`.\n"
    "\n"
    "This item records a **design decision**, and that decision is now carried out. It\n"
    "does not represent delivery of the module: its Spec, Plan, todo, implementation\n"
    "and acceptance are tracked by the module's own task list or by ordinary tracker\n"
    "items, not here. Closing this item says the decision landed, nothing more.\n"
    "\n"
    "<!-- %(namespace)s %(id)s/%(short)s -->"
)


def short_revision(revision):
    """The marker carries a short revision: enough to bind one published content."""
    digest = revision.split(":")[-1] if isinstance(revision, str) else ""
    return digest[:REVISION_DIGITS]


def closeout_marker(proposal_id, revision):
    return "<!-- %s %s/%s -->" % (MARKER_NAMESPACE, proposal_id,
                                  short_revision(revision))


def closeout_record(proposal_id, revision, promotion_commit, review_commit):
    """The comment written on closeout, ending in exactly one stable marker."""
    return RECORD % {"id": proposal_id, "promotion": promotion_commit,
                     "review": review_commit, "namespace": MARKER_NAMESPACE,
                     "short": short_revision(revision)}


def preview_digest(preview):
    """Bind every previewed fact, so an authorized preview cannot be swapped."""
    payload = json.dumps(preview, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def adapter_tracker_reader(adapter):
    """Read the tracker through the closeout adapter.

    `prove_from_remote` accepts a reader, so the proof judges the same candidate set the
    preview saw -- one listing, one verdict -- instead of each side reading separately
    and possibly disagreeing. It is also what lets the Local backend be proved at all:
    the default reader only speaks the GitHub and GitLab CLIs.
    """
    def reader(proposal, platform, target):
        try:
            page = adapter.list_issues()
        except Exception as error:
            if is_defect(error):
                raise
            return recover_tracker_issue(proposal, platform, target,
                                         {"complete": False, "issues": []})
        return recover_tracker_issue(proposal, platform, target, page)
    return reader


def _rejection(error):
    """A platform that said no outright, rather than a result we could not read.

    Duck-typed on `status_code` so any adapter can report one without this module
    importing a transport.  Folding a definite 4xx into `partial` or `unknown` would
    claim the outcome is in doubt when the platform already answered, and would leave
    a journal entry implying an attempt that never landed.
    """
    status = getattr(error, "status_code", None)
    if isinstance(status, int) and 400 <= status < 500:
        return {"state": "rejected", "statusCode": status}
    return None


def _blocked(state, diagnostic=None):
    result = {"state": state}
    if diagnostic:
        result["diagnostic"] = diagnostic
    return result


def build_preview(project, proposal_id, backend, target, adapter, remote="origin",
                  source="explicit", host=None, publication_reader=None,
                  tracker_reader=None, prover=None):
    """Read the Proposal, locate its item, prove the promotion, then preview.

    The proof is taken inside this call rather than accepted from a caller: a proof
    produced earlier says the promotion was provable then, not now.  Nothing here
    writes, and no module stage is consulted -- only the Proposal, the item and Git.
    """
    publication_reader = publication_reader or read_published
    prover = prover or prove_from_remote
    reader = tracker_reader or adapter_tracker_reader(adapter)

    publication = publication_reader(project, proposal_id, remote)
    if getattr(publication, "state", None) != "published":
        state = getattr(publication, "state", None)
        # Carry the reason: a bare {"state": "unknown"} cannot be told apart from a
        # broken link, and this plugin's rule is that a failed probe degrades with
        # something the reader can act on.
        return _blocked(state if state in ("absent", "invalid") else "unknown",
                        getattr(publication, "diagnostic", None))
    proposal = publication.proposal
    if not getattr(proposal, "revision", None):
        return _blocked("not-eligible", "legacy-revision-required")

    tracker = reader(proposal, backend, target)
    if getattr(tracker, "state", None) != "verified":
        state = getattr(tracker, "state", None)
        if state == "invalid":
            code = getattr(tracker, "code", None) or CONTRACT_INVALID
            # Several items carrying the marker is not a malformed container: it is a
            # choice only a human can make, so say conflict rather than invalid.
            return _blocked("conflict" if code == MARKER_AMBIGUOUS else "invalid", code)
        state = state if state in TRACKER_CODES else "unknown"
        return _blocked(state, TRACKER_CODES[state])

    proof = prover(project, proposal_id, backend, target, remote,
                   tracker_reader=reader)
    decision = closeout_decision(tracker.stage, tracker.closed,
                                 getattr(proof, "state", None),
                                 getattr(proof, "diagnostic", None))
    if decision.state != "eligible":
        return _blocked(decision.state, decision.diagnostic)

    try:
        facts = adapter.target_facts()
        content = content_digest(backend, adapter.get_issue(tracker.issue_id))
    except Exception as error:
        if is_defect(error):
            raise
        return _blocked("unknown", "target-unreadable")

    actions = ["comment"] + (["stage"] if decision.needs_stage_change else []) + ["close"]
    preview = {
        "state": "preview", "backend": backend, "exactTarget": facts,
        "proposalId": proposal_id, "revision": proposal.revision,
        "issueId": tracker.issue_id, "currentStage": tracker.stage,
        "issueContentDigest": content,
        "targetStage": decision.target_stage,
        "promotionCommit": proof.promotion_commit,
        "reviewCommit": proof.review_commit,
        "record": closeout_record(proposal_id, proposal.revision,
                                  proof.promotion_commit, proof.review_commit),
        "actions": actions, "source": source,
    }
    preview["digest"] = preview_digest(preview)
    return preview


def scan(project, backend, target, adapter, remote="origin", source="explicit", host=None,
         pool_reader=None, tracker_reader=None, prover=None):
    """Judge every published Proposal the way `preview` would; read-only.

    A Proposal item is closed only by step 4, and nothing reminded anyone to run it: a
    stage label changed by hand is allowed but closes nothing, so a promoted item can
    sit open indefinitely.  This lists the ones `preview` would accept.  The pool is
    read once and each Proposal goes through `build_preview` with that publication, so
    the judgement cannot drift from the one that guards the write.  Nothing is kept
    from a preview but its state: writing still needs `preview` and an authorization.
    """
    pool = (pool_reader or read_published_pool)(project, remote)
    state = getattr(pool, "state", None)
    if state != "published":
        state = state if state == "invalid" else "unknown"
        return {"state": state, "diagnostic": "proposal-pool-%s" % state}
    items = []
    pending = []
    for publication in pool.publications:
        proposal_id = publication.proposal.proposal_id
        result = build_preview(project, proposal_id, backend, target, adapter,
                               remote=remote, source=source, host=host,
                               publication_reader=lambda *a, _p=publication, **k: _p,
                               tracker_reader=tracker_reader, prover=prover)
        entry = {"proposalId": proposal_id}
        if result.get("state") == "preview":
            entry["state"] = "closeout-pending"
            entry["issueId"] = result["issueId"]
            pending.append(proposal_id)
        else:
            entry["state"] = result.get("state")
            if result.get("diagnostic"):
                entry["diagnostic"] = result["diagnostic"]
        items.append(entry)
    report = {"state": "scanned", "backend": backend, "source": source,
              "items": items, "pending": pending}
    if pool.skipped:
        report["skippedProposals"] = skipped_as_json(pool.skipped)
    return report


def content_digest(backend, raw_issue):
    """Digest the body and label set, so an item edited after the preview is refused.

    Platform shapes differ, so the fields come from the same extraction the identity
    rules use rather than from a second, drifting copy of that knowledge.
    """
    fields = issue_identity(backend, raw_issue)
    if fields is None:
        raise ValueError("issue shape is unreadable")
    _issue_id, _container, body, labels, _closed = fields
    return preview_digest({"body": body, "labels": sorted(labels)})


def _journal_path(root, proposal_id, revision):
    key = hashlib.sha256(("%s/%s" % (proposal_id, revision)).encode("utf-8")).hexdigest()
    return Path(root) / (key + ".json")


def _private_root(root):
    """A real directory we own, never a link someone else planted."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    if root.is_symlink() or not stat.S_ISDIR(root.lstat().st_mode):
        raise OSError("journal root is not a directory")
    os.chmod(root, 0o700)
    return root


def _read_journal(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _write_journal(path, record):
    descriptor = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC
                         | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, sort_keys=True)
    os.chmod(path, 0o600)


def _valid_preview(preview):
    if not isinstance(preview, dict) or preview.get("state") != "preview":
        return False
    expected = {key: value for key, value in preview.items() if key != "digest"}
    required = ("backend", "exactTarget", "proposalId", "revision", "issueId",
                "currentStage", "targetStage", "promotionCommit", "reviewCommit",
                "record", "actions", "issueContentDigest")
    if any(preview.get(key) is None for key in required):
        return False
    marker = closeout_marker(preview["proposalId"], preview["revision"])
    if preview["record"].splitlines()[-1] != marker:
        return False
    return preview.get("digest") == preview_digest(expected)


def close_preview(preview, project, adapter, confirm=False, journal_root=None,
                  remote="origin", publication_reader=None, tracker_reader=None,
                  prover=None):
    """Re-check everything the preview asserted, then write, then read back.

    Nothing here trusts the preview: between showing it and this call the Proposal may
    have been revised, the item edited, closed or relabelled, and the promotion may no
    longer be provable.  Each step is skipped when its result is already present, so a
    rerun after a lost response reconciles instead of writing a second time.
    """
    if not confirm:
        return {"state": "confirmation-required"}
    if not _valid_preview(preview):
        return _blocked("preview-invalid")

    publication_reader = publication_reader or read_published
    prover = prover or prove_from_remote
    reader = tracker_reader or adapter_tracker_reader(adapter)
    backend, target = preview["backend"], preview["exactTarget"]["target"]
    root = _private_root(journal_root or JOURNAL_ROOT)
    path = _journal_path(root, preview["proposalId"], preview["revision"])

    lock = os.open(str(path) + ".lock",
                   os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(lock, "r+") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            earlier = _read_journal(path)
            if earlier and earlier.get("exactTarget") != preview["exactTarget"]:
                return _blocked("conflict", "binding-target-changed")
            return _close_locked(preview, project, adapter, path, backend, target,
                                 remote, publication_reader, reader, prover)
    except OSError:
        return _blocked("unknown", "journal-unavailable")
    finally:
        try:
            os.unlink(str(path) + ".lock")
        except OSError:
            pass


def _close_locked(preview, project, adapter, path, backend, target, remote,
                  publication_reader, reader, prover):
    publication = publication_reader(project, preview["proposalId"], remote)
    state = getattr(publication, "state", None)
    # Three different things used to collapse into `proposal-revision-changed`, and
    # only one of them is about a revision. A probe that could not read is a retry;
    # saying the revision moved sends the reader to diff a document that never changed.
    if state != "published":
        if state in ("absent", "invalid"):
            return _blocked("preview-stale", "proposal-%s" % state)
        return _blocked("unknown",
                        getattr(publication, "diagnostic", None) or "proposal-pool-unknown")
    proposal = getattr(publication, "proposal", None)
    if getattr(proposal, "marker", None) is None:
        return _blocked("preview-stale", "proposal-marker-missing")
    if getattr(proposal, "revision", None) != preview["revision"]:
        return _blocked("preview-stale", "proposal-revision-changed")

    try:
        if adapter.target_facts() != preview["exactTarget"]:
            return _blocked("unknown", "target-changed")
    except Exception as error:
        if is_defect(error):
            raise
        return _rejection(error) or _blocked("unknown", "target-unreadable")

    tracker = reader(proposal, backend, target)
    if getattr(tracker, "state", None) != "verified":
        state = getattr(tracker, "state", None)
        if state == "invalid":
            code = getattr(tracker, "code", None) or CONTRACT_INVALID
            return _blocked("conflict" if code == MARKER_AMBIGUOUS else "invalid", code)
        return _blocked(state if state in TRACKER_CODES else "unknown",
                        TRACKER_CODES.get(state, "tracker-unknown"))
    if tracker.issue_id != preview["issueId"]:
        return _blocked("conflict", "issue-changed")

    try:
        current = adapter.get_issue(tracker.issue_id)
        if content_digest(backend, current) != preview["issueContentDigest"]:
            return _blocked("conflict", "issue-content-changed")
    except Exception as error:
        if is_defect(error):
            raise
        return _rejection(error) or _blocked("unknown", "issue-unreadable")

    proof = prover(project, preview["proposalId"], backend, target, remote,
                   tracker_reader=reader)
    decision = closeout_decision(tracker.stage, tracker.closed,
                                 getattr(proof, "state", None),
                                 getattr(proof, "diagnostic", None))
    if decision.state == "already-closed":
        return _blocked("already-closed")
    if decision.state != "eligible":
        return _blocked(decision.state, decision.diagnostic)
    if getattr(proof, "promotion_commit", None) != preview["promotionCommit"]:
        return _blocked("not-eligible", "proof-changed")
    # `record` is the one previewed field whose bytes get posted, so it is rebuilt from
    # the facts just re-established rather than taken on trust. Everything else in the
    # preview is compared against a live source; without this, anyone able to edit the
    # preview file between the two commands could publish arbitrary text as us.
    if preview["record"] != closeout_record(preview["proposalId"], proposal.revision,
                                            proof.promotion_commit,
                                            proof.review_commit):
        return _blocked("preview-invalid")

    return _apply(preview, adapter, tracker, decision, path, backend)


def _apply(preview, adapter, tracker, decision, path, backend):
    """Write each step only when its result is not already present, then read back."""
    issue_id, marker = tracker.issue_id, closeout_marker(preview["proposalId"],
                                                         preview["revision"])
    record = {"version": 1, "backend": preview["backend"],
              "exactTarget": preview["exactTarget"],
              "proposalId": preview["proposalId"], "revision": preview["revision"],
              "digest": preview["digest"], "issueId": issue_id, "attempted": True}
    _write_journal(path, record)

    try:
        comments = adapter.list_comments(issue_id)
        if comments.get("complete") is not True:
            return _blocked("unknown", "comments-incomplete")
        # The marker is derivable from the Issue body anyone can read, so "ends with
        # the marker" is not evidence that we wrote it. Only our own record, byte for
        # byte, counts as already done; anything else wearing the marker is a conflict
        # for a human, never a reason to skip writing the real one.
        wearing = [_text(item.get("body")) for item in comments["comments"]
                   if _text(item.get("body")).splitlines()[-1:] == [marker]]
        if any(body != _text(preview["record"]) for body in wearing):
            return _blocked("conflict", "closeout-marker-not-ours")
        if not wearing:
            adapter.create_comment(issue_id, preview["record"])
    except Exception as error:
        if is_defect(error):
            raise
        refusal = _rejection(error)
        if refusal is not None:
            _clear(path)
            return refusal
        return _partial(path, record, "comment-result-uncertain")

    try:
        if decision.needs_stage_change:
            adapter.set_stage(issue_id, tracker.stage, decision.target_stage)
    except Exception as error:
        if is_defect(error):
            raise
        refusal = _rejection(error)
        if refusal is not None:
            return refusal
        return _partial(path, record, "stage-result-uncertain")

    refusal = None
    try:
        adapter.set_closed(issue_id)
    except Exception as error:
        if is_defect(error):
            raise
        refusal = _rejection(error)

    try:
        fields = issue_identity(backend, adapter.get_issue(issue_id))
    except Exception as error:
        if is_defect(error):
            raise
        fields = None
    if fields is None:
        return refusal or _partial(path, record, "close-result-uncertain")
    _issue_id, _container, _body, labels, closed = fields
    if not closed or decision.target_stage not in labels:
        return refusal or _partial(path, record, "close-result-uncertain")
    # The record is the point of the whole exercise, so read it back too: stage and
    # closed alone would let a backend that accepted the comment and dropped it still
    # be reported as verified.
    try:
        final = adapter.list_comments(issue_id)
        ours = [item for item in final.get("comments", [])
                if _text(item.get("body")) == _text(preview["record"])]
    except Exception as error:
        if is_defect(error):
            raise
        return _partial(path, record, "record-not-readable")
    if final.get("complete") is not True or len(ours) != 1:
        return _partial(path, record, "record-not-readable")
    _clear(path)
    return {"state": "verified", "issueId": issue_id,
            "stage": decision.target_stage, "closed": True,
            "promotionCommit": preview["promotionCommit"]}


def _text(value):
    """Compare comment bodies without being defeated by line endings."""
    return str(value or "").replace("\r\n", "\n").strip()


def _clear(path):
    try:
        os.unlink(path)
    except OSError:
        pass


def _partial(path, record, diagnostic):
    """Keep the attempt on record and stop: the next run reconciles, never resends."""
    _write_journal(path, dict(record, attempted=True))
    return {"state": "partial", "diagnostic": diagnostic}


def build_adapter(backend, target, host=None, project=None, runtime_dir=None):
    """Construct the adapter for one backend, or raise with a stable reason."""
    if backend == "local":
        from proposal_closeout_local import LocalCloseout
        return LocalCloseout(target, project=project, runtime_dir=runtime_dir)
    if backend == "github":
        from proposal_closeout_github import GitHubCloseout
        return GitHubCloseout(host or "github.com", target)
    from proposal_closeout_gitlab import GitLabCloseout
    return GitLabCloseout(host or "gitlab.com", target)


def _resolved(args):
    """Explicit backend and target, else the project default; never a guess."""
    from tracker_default import read_default, resolve

    target = args.target
    # `str.isdigit()` is true for characters like "²" that `int()` rejects, so an
    # ASCII-only bound keeps a stray argument from becoming an uncaught traceback.
    if (target is not None and args.backend == "gitlab" and
            re.fullmatch(r"[0-9]{1,18}", str(target))):
        target = int(target)
    explicit = None
    # Build the explicit target whenever one was given, even without a backend, so
    # `resolve` can answer `backend-unselected` instead of this function quietly
    # dropping it and labelling the project default as the chosen one.
    if target is not None and not args.backend:
        return None, {"state": "target-unselected", "diagnostic": "backend-unselected"}
    if args.backend and target is not None:
        explicit = ({"host": args.host or "github.com", "repo": target}
                    if args.backend == "github" else
                    {"host": args.host or "gitlab.com", "projectId": target}
                    if args.backend == "gitlab" else {"projectId": target})
    outcome = resolve(args.backend, explicit, read_default(Path(args.project)))
    if outcome.state != "resolved":
        return None, {"state": "target-unselected",
                      "diagnostic": outcome.diagnostic, "source": None}
    container = (outcome.target.get("repo") if outcome.backend == "github"
                 else outcome.target.get("projectId"))
    return (outcome.backend, container, outcome.target.get("host"),
            outcome.source), None


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(
        description="Preview, and after explicit authorization perform, a Proposal "
                    "closeout. The preview is read-only; `close` re-checks everything "
                    "it asserted before writing anything.")
    commands = parser.add_subparsers(dest="command", required=True)

    preview = commands.add_parser("preview", help="read-only")
    preview.add_argument("--project", default=".")
    preview.add_argument("--proposal-id", required=True)
    preview.add_argument("--backend", choices=("local", "github", "gitlab"))
    preview.add_argument("--host")
    preview.add_argument("--target")
    preview.add_argument("--remote", default="origin")
    preview.add_argument("--output", required=True)

    scanner = commands.add_parser("scan", help="read-only: list promoted items still open")
    scanner.add_argument("--project", default=".")
    scanner.add_argument("--backend", choices=("local", "github", "gitlab"))
    scanner.add_argument("--host")
    scanner.add_argument("--target")
    scanner.add_argument("--remote", default="origin")

    closer = commands.add_parser("close", help="write, only with --confirm")
    closer.add_argument("--project", default=".")
    closer.add_argument("--preview", required=True)
    closer.add_argument("--remote", default="origin")
    closer.add_argument("--confirm", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "scan":
        resolved, failure = _resolved(args)
        if failure is not None:
            print(json.dumps(failure, ensure_ascii=False, sort_keys=True))
            return 2
        backend, container, host, source = resolved
        try:
            adapter = build_adapter(backend, container, host=host,
                                    project=Path(args.project))
        except Exception as error:
            if is_defect(error):
                raise
            print(json.dumps({"state": "unknown", "diagnostic": "target-unreadable"},
                             sort_keys=True))
            return 2
        result = scan(args.project, backend, container, adapter, remote=args.remote,
                      source=source, host=host)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result.get("state") == "scanned" else 2

    if args.command == "preview":
        resolved, failure = _resolved(args)
        if failure is not None:
            print(json.dumps(failure, ensure_ascii=False, sort_keys=True))
            return 2
        backend, container, host, source = resolved
        try:
            adapter = build_adapter(backend, container, host=host,
                                    project=Path(args.project))
        except Exception as error:
            if is_defect(error):
                raise
            print(json.dumps({"state": "unknown", "diagnostic": "target-unreadable"},
                             sort_keys=True))
            return 2
        result = build_preview(args.project, args.proposal_id, backend, container,
                               adapter, remote=args.remote, source=source, host=host)
        if result.get("state") == "preview":
            # The preview is read back by `close` and acted on, so it is created
            # exclusively and never through a link someone else planted. O_EXCL also
            # makes a leftover preview from an earlier run an explicit failure rather
            # than a silent overwrite.
            try:
                descriptor = os.open(args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                                     | getattr(os, "O_NOFOLLOW", 0), 0o600)
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    handle.write(json.dumps(result, ensure_ascii=False, indent=2,
                                            sort_keys=True) + "\n")
            except OSError:
                print(json.dumps({"state": "unknown",
                                  "diagnostic": "preview-output-unwritable"},
                                 sort_keys=True))
                return 2
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result.get("state") == "preview" else 2

    try:
        view = json.loads(Path(args.preview).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        view = None
    if not isinstance(view, dict):
        print(json.dumps({"state": "preview-invalid"}, sort_keys=True))
        return 2
    if not args.confirm:
        print(json.dumps({"state": "confirmation-required"}, sort_keys=True))
        return 2
    try:
        adapter = build_adapter(view.get("backend"),
                                (view.get("exactTarget") or {}).get("target"),
                                host=(view.get("exactTarget") or {}).get("host"),
                                project=Path(args.project))
    except Exception as error:
        if is_defect(error):
            raise
        print(json.dumps({"state": "unknown", "diagnostic": "target-unreadable"},
                         sort_keys=True))
        return 2
    result = close_preview(view, args.project, adapter, confirm=True,
                           remote=args.remote)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("state") in ("verified", "already-closed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
