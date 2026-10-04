#!/usr/bin/env python3
"""Describe where the current module stands, for the phase-guard injection.

The current module is `.agent/state.json` activeModule when it names a mapped module,
otherwise the first module in Build order that is not done. A module needs a spec
(`spec/<id>.md`), then a plan (`tasks/<id>/plan.md`), then has open work while
`tasks/<id>/todo.md` has unchecked items; it is done once a plan exists and no
unchecked item remains. Read-only: this never writes a file.
"""
from __future__ import annotations
import json
from pathlib import Path
import re
import subprocess
import sys

from capability_map import MapError, parse_map

UNCHECKED = re.compile(r"^\s*[-*+]\s+\[ \]", re.MULTILINE)
CHECKED = re.compile(r"^\s*[-*+]\s+\[[xX]\]", re.MULTILINE)


def module_state(root: Path, module_id: str) -> dict:
    has_spec = (root / "spec" / f"{module_id}.md").is_file()
    has_plan = (root / "tasks" / module_id / "plan.md").is_file()
    todo = root / "tasks" / module_id / "todo.md"
    text = todo.read_text(encoding="utf-8") if todo.is_file() else ""
    open_items = len(UNCHECKED.findall(text))
    half = bool(open_items) and bool(CHECKED.search(text))
    if not has_spec:
        stage = "NEEDS_SPEC"
    elif not has_plan:
        stage = "NEEDS_PLAN"
    elif open_items:
        stage = "BUILDING"
    else:
        stage = "DONE"
    return {"id": module_id, "stage": stage, "spec": has_spec, "plan": has_plan, "open": open_items,
            "half": half, "todo": todo.is_file()}


def _state(root: Path) -> dict:
    try:
        value = json.loads((root / ".agent" / "state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def active_module(root: Path) -> str | None:
    active = _state(root).get("activeModule")
    return active if isinstance(active, str) and active else None


def project_stage(states: list, active: str | None) -> tuple:
    """Project-level stage: (stage, current, source, pending).

    `pending` is the first module in Build order that is not done, or None when all are.
    `current` is the activeModule's state when it names a mapped module, else `pending`.
    `stage` is DONE only when every module is done; MODULE_DONE when the current module
    is done but `pending` is not None; otherwise the current module's own stage.
    """
    by_id = {state["id"]: state for state in states}
    pending = next((state for state in states if state["stage"] != "DONE"), None)
    if active and active in by_id:
        current, source = by_id[active], "activeModule"
    else:
        current, source = pending, "next in Build order"
    if pending is None:
        return "DONE", current, source, None
    return ("MODULE_DONE" if current["stage"] == "DONE" else current["stage"]), current, source, pending


def paused_modules(states: list, current: dict | None) -> list:
    """Modules other than `current` whose todo is half done, in Build order."""
    return [state for state in states if state["half"] and state is not current]


def _git(root: Path, *args: str) -> str | None:
    try:
        done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def unmerged_commits(root: Path) -> tuple | None:
    """(count, ref short name) of HEAD commits not in the locally known origin default branch, else None.

    Read-only and offline: only compares local remote-tracking refs, never fetches.
    """
    ref = _git(root, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    if not ref:
        ref = next((c for c in ("refs/remotes/origin/main", "refs/remotes/origin/master")
                    if _git(root, "rev-parse", "--verify", "--quiet", c)), None)
    if not ref:
        return None
    count = _git(root, "rev-list", "--count", ref + "..HEAD")
    if count is None or not count.isdigit():
        return None
    prefix = "refs/remotes/"
    return int(count), ref[len(prefix):] if ref.startswith(prefix) else ref


def describe(root: Path) -> str:
    root = Path(root)
    try:
        parsed = parse_map(root / "spec" / "CAPABILITY-MAP.md")
    except MapError as error:
        return ("当前阶段: **MAP_INVALID**\n\n- Capability map: present but invalid (%s)\n\n"
                "Suggested next step: run `/spec-guard:verify-artifacts` and fix the capability map." % error)
    order = list(parsed.order) or [row.module_id for row in parsed.rows]
    states = [module_state(root, module_id) for module_id in order]
    by_id = {state["id"]: state for state in states}
    active = active_module(root)
    stage, current, source, pending = project_stage(states, active)
    notes = []
    if active and active not in by_id:
        notes.append("- activeModule `%s` is not in the capability map; using Build order." % active)
    active_state = by_id.get(active) if active else None
    no_todo_note = ""
    if active_state and active_state["stage"] == "DONE" and not active_state["todo"]:
        no_todo_note = ("- activeModule `%s` has a plan but no `tasks/%s/todo.md`, so it counts as done; "
                        "add the todo if work remains." % (active, active))
    counts = "- Modules %d · Specs %d · Plans %d · In progress %d · Done %d" % (
        len(states), sum(s["spec"] for s in states), sum(s["plan"] for s in states),
        sum(s["stage"] == "BUILDING" for s in states), sum(s["stage"] == "DONE" for s in states))
    if stage == "DONE":
        missing_todo = sum(s["plan"] and not s["todo"] for s in states)
        if missing_todo:
            counts += ("\n- Plan without todo: %d module(s) counted as done; "
                       "run /spec-guard:verify-artifacts to review." % missing_todo)
    paused = paused_modules(states, current) if stage != "DONE" else []
    unmerged = unmerged_commits(root) if stage in ("DONE", "MODULE_DONE") else None
    push_first = ""
    if unmerged and unmerged[0] > 0:
        hint = ("- This branch has %d commit(s) not yet in `%s` (as last fetched)." % unmerged)
        push_first = "push this branch and merge its %d commit(s) into `%s` first; then " % unmerged
    else:
        hint = ""
    if stage == "DONE":
        if no_todo_note:
            notes.append(no_todo_note)
        if current is not None:
            notes.append("- activeModule `%s` is already done and can be cleared." % current["id"])
        if hint:
            notes.append(hint)
        if push_first:
            return ("当前阶段: **DONE**\n\n- Capability map: present\n" + counts + "\n" + "".join(n + "\n" for n in notes) +
                    "\nSuggested next step: every mapped module has a plan and no open todo item; " + push_first +
                    "for new work, insert a module with /spec-guard:add-module "
                    "(Codex: spec-guard-ops add-module); "
                    "use a Proposal when the addition needs a recorded, reviewed decision.")
        return ("当前阶段: **DONE**\n\n- Capability map: present\n" + counts + "\n" + "".join(n + "\n" for n in notes) +
                "\nSuggested next step: every mapped module has a plan and no open todo item. "
                "For new work, insert a module with /spec-guard:add-module "
                "(Codex: spec-guard-ops add-module) at this checkpoint; "
                "use a Proposal when the addition needs a recorded, reviewed decision.")
    module = current["id"]
    if no_todo_note:
        counts += "\n" + no_todo_note
    if hint:
        counts += "\n" + hint
    counts += "".join("\n- Paused: `%s` (%d unchecked item(s)); resume it after `%s`." % (p["id"], p["open"], module)
                      for p in paused)
    if stage == "MODULE_DONE" and paused:
        resume = paused[0]
        module_done = ("`%s` is done; resume paused module `%s` (%s). Set activeModule to it."
                       % (module, resume["id"], resume["stage"]))
    else:
        module_done = ("`%s` is done; next unfinished module in Build order is `%s` (%s). "
                       "Set activeModule to it before building." % (module, pending["id"], pending["stage"]))
    next_step = {
        "NEEDS_SPEC": "write and review `spec/%s.md`." % module,
        "NEEDS_PLAN": "create `tasks/%s/plan.md` and `tasks/%s/todo.md` (for example with `/plan`)." % (module, module),
        "BUILDING": "continue `/build` on `%s`: %d unchecked item(s) in `tasks/%s/todo.md`." % (module, current["open"], module),
        "MODULE_DONE": push_first + module_done,
    }[stage]
    return ("当前阶段: **%s**\n\n- Capability map: present\n- Current module: `%s` (%s)\n%s\n%s"
            "\nSuggested next step: %s" % (stage, module, source, counts,
                                          "".join(n + "\n" for n in notes), next_step))


if __name__ == "__main__":
    print(describe(Path(sys.argv[1] if len(sys.argv) > 1 else ".")))
