#!/usr/bin/env python3
"""Paste-ready handoff text for starting a new session (session-handoff spec).

Facts only, from the repository and git: where the work is, the stage and module counts,
the current branch's unmerged commits and the latest release evidence still marked
not-verified. It ends with a blank for the user's own next step. Read-only: it never
writes a file and never reads a session transcript.
"""
from __future__ import annotations
import json
import re
import subprocess
import sys
from pathlib import Path

from capability_map import MapError, parse_map
from module_stage import active_module_state, module_state, project_stage, safe_fragment, unmerged_commits

UNKNOWN = "未知"
EVIDENCE_NAME = re.compile(r"^v(\d+(?:\.\d+)*)-[^/]+\.json$")


def _git(root: Path, *args: str) -> str | None:
    try:
        done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 and done.stdout.strip() else None


def _header(root: Path) -> str:
    top = _git(root, "rev-parse", "--show-toplevel")
    where = Path(top) if top else root.resolve()
    # The repository is named after the main checkout, which a linked worktree's own folder is not.
    common = _git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    name = Path(common).parent.name if common and top else where.name
    branch = _git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    head = _git(root, "rev-parse", "--short", "HEAD")
    if branch:
        branch_text = "分支 %s" % safe_fragment(branch)
    elif top and head:
        branch_text = "分离 HEAD"
    else:
        branch_text = "分支 %s" % UNKNOWN
    return "%s 仓库（%s，%s，HEAD %s）。" % (
        safe_fragment(name), safe_fragment(str(where)), branch_text, safe_fragment(head) if head else UNKNOWN)


def _stage(root: Path) -> str:
    map_path = root / "spec" / "CAPABILITY-MAP.md"
    if not map_path.is_file():
        return "阶段 IDLE；没有能力图。"
    if not any(p.name != "CAPABILITY-MAP.md" for p in (root / "spec").glob("*.md")):
        return "阶段 MAP_ONLY；有能力图，没有模块 Spec。"
    try:
        parsed = parse_map(map_path)
    except MapError:
        return "阶段 MAP_INVALID；能力图无法解析，运行 verify-artifacts 查看。"
    order = list(parsed.order) or [row.module_id for row in parsed.rows]
    states = [module_state(root, module_id) for module_id in order]
    active, status = active_module_state(root)
    stage, current, _, _ = project_stage(states, active if status == "present" else None)
    return "阶段 %s；模块 %d，Spec %d，Plan %d，进行中 %d，完成 %d；当前模块 %s。" % (
        stage, len(states), sum(s["spec"] for s in states), sum(s["plan"] for s in states),
        sum(s["stage"] == "BUILDING" for s in states), sum(s["stage"] == "DONE" for s in states),
        current["id"] if current else "无")


def _unmerged(root: Path) -> str:
    found = unmerged_commits(root)
    if found is None:
        return "未合并提交：%s（没有本地已知的远端默认分支）" % UNKNOWN
    count, ref = found
    return "未合并提交：%s（相对 %s）" % ("%d 个" % count if count else "无", safe_fragment(ref))


def _evidence(root: Path) -> str:
    folder = root / "docs" / "releases"
    versions = {}
    for path in folder.glob("v*.json") if folder.is_dir() else []:
        match = EVIDENCE_NAME.match(path.name)
        if match:
            versions.setdefault(tuple(int(p) for p in match.group(1).split(".")), []).append(path)
    if not versions:
        return "发布证据：无"
    latest = max(versions)
    subjects = []
    for path in sorted(versions[latest]):
        try:
            records = json.loads(path.read_text(encoding="utf-8")).get("records", [])
        except (OSError, ValueError, AttributeError):
            continue
        for record in records if isinstance(records, list) else []:
            if isinstance(record, dict) and record.get("status") == "not-verified":
                subject = record.get("subject")
                if isinstance(subject, str) and subject:
                    subjects.append(safe_fragment(subject))
    return "发布证据 v%s 中 not-verified：%s" % (".".join(map(str, latest)), "、".join(subjects) or "无")


def handoff_text(root) -> str:
    root = Path(root)
    return "\n".join([
        _header(root),
        "## 现状",
        _stage(root),
        _unmerged(root),
        _evidence(root),
        "## 下一步",
        "下一步：____",
    ])


# Exact commands only: a natural-language status question is never intercepted (spec item 6).
TRIGGERS = frozenset({"/spec-guard:handoff", "spec-guard handoff"})


def is_trigger(prompt) -> bool:
    return isinstance(prompt, str) and prompt.strip() in TRIGGERS


def hook_answer(hook_input: str, host: str, root) -> str | None:
    """The UserPromptSubmit block JSON when the prompt is a trigger, else None.

    Codex rejects fields it does not know -- a Claude-only `hookSpecificOutput` turns the
    block into a failed hook and the prompt goes to the model -- so each host gets its own shape.
    """
    if host not in ("claude", "codex"):
        return None
    try:
        data = json.loads(hook_input)
    except (TypeError, ValueError):
        return None
    if not isinstance(data, dict) or not is_trigger(data.get("prompt")):
        return None
    answer = {"decision": "block", "reason": handoff_text(root)}
    if host == "claude":
        answer["hookSpecificOutput"] = {"hookEventName": "UserPromptSubmit", "suppressOriginalPrompt": True}
    return json.dumps(answer, ensure_ascii=False)


def main() -> None:
    if len(sys.argv) > 3 and sys.argv[1] == "--hook":
        from session_context import read_hook_input
        answer = hook_answer(read_hook_input(sys.stdin.fileno()), sys.argv[2], sys.argv[3])
        if answer:
            print(answer)
        return
    print(handoff_text(sys.argv[1] if len(sys.argv) > 1 else "."))


if __name__ == "__main__":
    main()
