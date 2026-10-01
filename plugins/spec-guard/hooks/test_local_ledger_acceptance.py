"""Optional isolated acceptance for the pinned Epiq local-ticket ledger.

Run only with SPEC_GUARD_EPIQ_RUNTIME pointing at an already verified runtime.  This test never
downloads packages or touches the caller's repository, configuration, or Epiq global directory.
"""
import json
import os
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from local_ledger_runtime import (
    MCP_RELATIVE_PATH,
    STATE_BRANCH,
    RuntimeContractError,
    initialize_project,
    mcp_tool_call,
    node_status,
    project_status,
    runtime_status,
)


def _git(directory: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(directory), *arguments], check=True, capture_output=True, text=True,
    )
    return completed.stdout


def _open_swimlane(command: list[str], project_dir: Path) -> str:
    swimlanes = mcp_tool_call(command, "epiq_swimlane_list", {
        "repoRoot": str(project_dir),
    })["value"]
    open_swimlane = next((lane for lane in swimlanes if not lane["isClosed"]), None)
    if open_swimlane:
        return open_swimlane["id"]
    boards = mcp_tool_call(command, "epiq_board_list", {"repoRoot": str(project_dir)})["value"]
    board_id = boards[0]["id"] if boards else mcp_tool_call(command, "epiq_board_create", {
        "repoRoot": str(project_dir), "title": "Acceptance",
    })["value"]["id"]
    return mcp_tool_call(command, "epiq_swimlane_create", {
        "repoRoot": str(project_dir), "boardId": board_id, "title": "Open",
    })["value"]["id"]


def run(runtime_dir: Path) -> dict[str, str]:
    runtime_dir = Path(runtime_dir)
    if runtime_status(runtime_dir)["state"] != "ready":
        raise RuntimeContractError("acceptance runtime does not match the pinned local-ledger contract")
    node = node_status()
    if node["state"] != "ready":
        raise RuntimeContractError("acceptance requires a compatible Node executable")
    command = [node["path"], str(runtime_dir / MCP_RELATIVE_PATH)]

    with tempfile.TemporaryDirectory(prefix="sg-local-ledger-acceptance-") as temporary:
        root = Path(temporary) / "repository"
        worker_a = Path(temporary) / "worker-a"
        worker_b = Path(temporary) / "worker-b"
        global_dir = Path(temporary) / "epiq-global"
        root.mkdir()
        _git(root, "init", "-q")
        _git(root, "config", "user.email", "acceptance@example.invalid")
        _git(root, "config", "user.name", "Spec Guard acceptance")
        (root / "README.md").write_text("acceptance\n", encoding="utf-8")
        _git(root, "add", "README.md")
        _git(root, "commit", "-qm", "initial")

        previous_global = os.environ.get("EPIQ_GLOBAL_DIR")
        os.environ["EPIQ_GLOBAL_DIR"] = str(global_dir)
        try:
            initialized = initialize_project(
                runtime_dir, root, "Spec Guard acceptance", "true", False,
            )
            if project_status(root)["state"] != "initialized":
                raise RuntimeContractError("Epiq did not create the expected project identity")
            _git(root, "ls-files", "--error-unmatch", ".epiq/project.json")
            if _git(root, "status", "--porcelain", "--untracked-files=all"):
                raise RuntimeContractError("Epiq initialization left the acceptance worktree dirty")
            _git(root, "show-ref", "--verify", "refs/heads/" + STATE_BRANCH)
            if (root / "node_modules").exists():
                raise RuntimeContractError("project-local node_modules was unexpectedly created")

            _git(root, "worktree", "add", "-q", "-b", "ledger-worker-a", str(worker_a), "HEAD")
            _git(root, "worktree", "add", "-q", "-b", "ledger-worker-b", str(worker_b), "HEAD")
            swimlane_id = _open_swimlane(command, worker_a)
            issue = mcp_tool_call(command, "epiq_issue_create", {
                "repoRoot": str(worker_a),
                "parentId": swimlane_id,
                "title": "acceptance: shared ticket",
                "description": "Created from worker A.",
            })["value"]
            issue_id = issue["id"]
            decision = "Decision: replace the initial scope after review."
            effective = "Revised scope after the recorded decision."
            mcp_tool_call(command, "epiq_issue_comment_add", {
                "repoRoot": str(worker_a), "issueId": issue_id, "body": decision,
            })
            mcp_tool_call(command, "epiq_issue_description_edit", {
                "repoRoot": str(worker_a), "issueId": issue_id, "description": effective,
            })
            before_comments = mcp_tool_call(command, "epiq_issue_get", {
                "repoRoot": str(worker_b), "idOrRef": issue["ref"],
            })["value"]
            if before_comments["id"] != issue_id or before_comments["description"] != effective:
                raise RuntimeContractError("worker B could not read the current ticket requirement")
            if decision not in {comment["body"] for comment in before_comments["comments"]}:
                raise RuntimeContractError("worker B could not read the supersession decision")
            state = mcp_tool_call(command, "epiq_state_get", {"repoRoot": str(worker_b)})["value"]
            descriptions = [
                event["payload"]["md"] for event in state["eventLog"]
                if event["action"] == "edit.description" and event["payload"]["id"] == issue_id
            ]
            if descriptions != [issue["description"], effective]:
                raise RuntimeContractError("Epiq event history lost a requirement version")

            def add_comment(worker: Path, body: str) -> None:
                mcp_tool_call(command, "epiq_issue_comment_add", {
                    "repoRoot": str(worker), "issueId": issue_id, "body": body,
                })

            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(add_comment, worker_a, "concurrent comment from worker A"),
                    executor.submit(add_comment, worker_b, "concurrent comment from worker B"),
                ]
                for future in futures:
                    future.result()
            restarted_read = mcp_tool_call(command, "epiq_issue_get", {
                "repoRoot": str(worker_a), "idOrRef": issue_id,
            })["value"]
            bodies = {comment["body"] for comment in restarted_read["comments"]}
            expected = {"concurrent comment from worker A", "concurrent comment from worker B"}
            if not expected.issubset(bodies):
                raise RuntimeContractError("concurrent comments did not survive a fresh MCP process")
            evidence = "Delivery: synthetic commit; verification: fixture checks passed."
            add_comment(worker_a, evidence)
            mcp_tool_call(command, "epiq_issue_close", {
                "repoRoot": str(worker_a), "issueId": issue_id,
            })
            closed = mcp_tool_call(command, "epiq_issue_get", {
                "repoRoot": str(worker_b), "idOrRef": issue_id,
            })["value"]
            if not closed["isClosed"] or evidence not in {c["body"] for c in closed["comments"]}:
                raise RuntimeContractError("verified closure or delivery evidence was not readable")
            listed = mcp_tool_call(command, "epiq_issue_list", {
                "repoRoot": str(worker_b), "includeClosed": True, "brief": True,
            })["value"]
            if not any(ticket["id"] == issue_id for ticket in listed):
                raise RuntimeContractError("closed ticket was missing from intake lookup")
            mcp_tool_call(command, "epiq_issue_reopen", {
                "repoRoot": str(worker_a), "issueId": issue_id,
            })
            reopened = mcp_tool_call(command, "epiq_issue_get", {
                "repoRoot": str(worker_b), "idOrRef": issue_id,
            })["value"]
            if reopened["isClosed"]:
                raise RuntimeContractError("reopened ticket still appeared closed")
        finally:
            if previous_global is None:
                os.environ.pop("EPIQ_GLOBAL_DIR", None)
            else:
                os.environ["EPIQ_GLOBAL_DIR"] = previous_global
    return {
        "state": "passed",
        "projectId": initialized["projectId"],
        "stateBranch": initialized["stateBranch"],
    }


def main() -> int:
    configured_runtime = os.environ.get("SPEC_GUARD_EPIQ_RUNTIME")
    if not configured_runtime:
        print(json.dumps({
            "state": "skipped",
            "diagnostic": "set SPEC_GUARD_EPIQ_RUNTIME to an already-installed pinned runtime",
        }, sort_keys=True))
        # 2 = 环境未就绪：没有运行任何验收，不能与通过（0）混为一谈。
        return 2
    try:
        result = run(Path(configured_runtime))
    except (RuntimeContractError, subprocess.CalledProcessError) as error:
        print(json.dumps({"state": "failed", "diagnostic": str(error)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
