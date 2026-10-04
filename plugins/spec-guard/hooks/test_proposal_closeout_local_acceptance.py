"""Optional isolated acceptance for the Local closeout adapter.

Runs only with SPEC_GUARD_EPIQ_RUNTIME pointing at an already verified pinned runtime.
It builds its own temporary Git repository and its own Epiq global directory, and never
touches the caller's repository, host configuration or Epiq data.

The faked-transport tests pin what the adapter sends.  Only this one shows that the real
epiq@1.11.0 accepts those exact parameter names -- `parentId` on create, `idOrRef` on
read, `tagName` to add a tag and `tagId` to remove one -- and that a closed issue is
absent from a listing until `includeClosed` is set.
"""
import json
import os
import subprocess
import tempfile
from pathlib import Path

from local_ledger_runtime import (
    MCP_RELATIVE_PATH, RuntimeContractError, initialize_project, mcp_tool_call,
    node_status, project_status, runtime_status,
)
from proposal_closeout import PROMOTED_STAGE, closeout_decision
from proposal_closeout_local import LocalCloseout, LocalCloseoutError

ACCEPTED = "proposal-stage:accepted"
MARKER = "<!-- spec-guard-proposal-closeout:v1 acceptance/0123456789ab -->"
BODY = ("<!-- spec-guard-proposal:v2 id=acceptance revision=sha256:" + "0" * 64 + " -->")


def _git(directory: Path, *arguments: str) -> str:
    return subprocess.run(["git", "-C", str(directory), *arguments], check=True,
                          capture_output=True, text=True).stdout


def _open_lane(call) -> str:
    lanes = call("epiq_swimlane_list")
    lane = next((item for item in lanes if not item["isClosed"]), None)
    if lane:
        return lane["id"]
    boards = call("epiq_board_list")
    board = boards[0]["id"] if boards else call("epiq_board_create",
                                                title="Acceptance")["id"]
    return call("epiq_swimlane_create", boardId=board, title="Open")["id"]


def run(runtime_dir: Path) -> dict[str, object]:
    runtime_dir = Path(runtime_dir)
    if runtime_status(runtime_dir)["state"] != "ready":
        raise RuntimeContractError("acceptance runtime does not match the pinned contract")
    node = node_status()
    if node["state"] != "ready":
        raise RuntimeContractError("acceptance requires a compatible Node executable")
    command = [node["path"], str(runtime_dir / MCP_RELATIVE_PATH)]

    with tempfile.TemporaryDirectory(prefix="sg-closeout-acceptance-") as temporary:
        root = Path(temporary) / "repository"
        global_dir = Path(temporary) / "epiq-global"
        root.mkdir()
        _git(root, "init", "-q")
        _git(root, "config", "user.email", "acceptance@example.invalid")
        _git(root, "config", "user.name", "Spec Guard acceptance")
        (root / "README.md").write_text("acceptance\n", encoding="utf-8")
        _git(root, "add", "README.md")
        _git(root, "commit", "-qm", "initial")

        previous = os.environ.get("EPIQ_GLOBAL_DIR")
        os.environ["EPIQ_GLOBAL_DIR"] = str(global_dir)
        try:
            initialize_project(runtime_dir, root, "Spec Guard acceptance", "true", False)
            identity = project_status(root)
            if identity["state"] != "initialized":
                raise RuntimeContractError("Epiq did not create a project identity")

            def call(name, **arguments):
                return mcp_tool_call(command, name, {
                    "repoRoot": str(root), **arguments,
                }, environment=dict(os.environ))["value"]

            issue = call("epiq_issue_create", parentId=_open_lane(call),
                         title="Proposal: acceptance", description=BODY)
            call("epiq_issue_tag_add", issueId=issue["id"], tagName="proposal")
            call("epiq_issue_tag_add", issueId=issue["id"], tagName=ACCEPTED)

            closeout = LocalCloseout(identity["projectId"], project=root,
                                     runtime_dir=runtime_dir)
            listed = closeout.list_issues()
            found = [item for item in listed["issues"] if item["id"] == issue["id"]]
            if len(found) != 1 or sorted(found[0]["labels"]) != ["proposal", ACCEPTED]:
                raise RuntimeContractError("the open Proposal item did not read back")
            if found[0]["isClosed"]:
                raise RuntimeContractError("a fresh item reported itself closed")

            decision = closeout_decision(ACCEPTED, found[0]["isClosed"], "proved")
            if decision.state != "eligible" or not decision.needs_stage_change:
                raise RuntimeContractError("the shared decision did not allow closeout")

            closeout.create_comment(issue["id"], MARKER)
            closeout.set_stage(issue["id"], ACCEPTED, decision.target_stage)
            closeout.set_closed(issue["id"])

            after = closeout.get_issue(issue["id"])
            comments = closeout.list_comments(issue["id"])["comments"]
            markers = [item for item in comments if item["body"].endswith(MARKER)]
            if (not after["isClosed"] or PROMOTED_STAGE not in after["labels"] or
                    ACCEPTED in after["labels"] or len(markers) != 1):
                raise RuntimeContractError("the closeout did not read back as promoted, "
                                           "closed and marked exactly once")

            # Observed: a closed issue is absent from a listing that does not ask for
            # closed items, which is why the adapter always sets includeClosed.
            default_listing = call("epiq_issue_list")
            if any(item["id"] == issue["id"] for item in default_listing):
                raise RuntimeContractError("a closed item appeared in a default listing; "
                                           "the includeClosed requirement no longer holds")
            if not any(item["id"] == issue["id"]
                       for item in closeout.list_issues()["issues"]):
                raise RuntimeContractError("the adapter's listing lost the closed item")

            repeat = closeout_decision(PROMOTED_STAGE, after["isClosed"], "proved")
            if repeat.state != "already-closed":
                raise RuntimeContractError("a rerun did not report already-closed")

            return {"state": "verified", "issueRef": after["ref"],
                    "stage": PROMOTED_STAGE, "closed": True, "markers": len(markers)}
        finally:
            if previous is None:
                os.environ.pop("EPIQ_GLOBAL_DIR", None)
            else:
                os.environ["EPIQ_GLOBAL_DIR"] = previous


def main() -> int:
    configured = os.environ.get("SPEC_GUARD_EPIQ_RUNTIME")
    if not configured:
        print(json.dumps({
            "state": "skipped",
            "diagnostic": "set SPEC_GUARD_EPIQ_RUNTIME to an already-installed pinned runtime",
        }, sort_keys=True))
        # 2 = 环境未就绪：没有运行任何验收，不能与通过（0）混为一谈。
        return 2
    try:
        print(json.dumps(run(Path(configured)), sort_keys=True))
    except (RuntimeContractError, LocalCloseoutError,
            subprocess.CalledProcessError) as error:
        print(json.dumps({"state": "failed", "diagnostic": str(error)}, sort_keys=True))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
