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
import sys

from capability_map import MapError, parse_map

UNCHECKED = re.compile(r"^\s*[-*+]\s+\[ \]", re.MULTILINE)


def module_state(root: Path, module_id: str) -> dict:
    has_spec = (root / "spec" / f"{module_id}.md").is_file()
    has_plan = (root / "tasks" / module_id / "plan.md").is_file()
    todo = root / "tasks" / module_id / "todo.md"
    open_items = len(UNCHECKED.findall(todo.read_text(encoding="utf-8"))) if todo.is_file() else 0
    if not has_spec:
        stage = "NEEDS_SPEC"
    elif not has_plan:
        stage = "NEEDS_PLAN"
    elif open_items:
        stage = "BUILDING"
    else:
        stage = "DONE"
    return {"id": module_id, "stage": stage, "spec": has_spec, "plan": has_plan, "open": open_items}


def active_module(root: Path) -> str | None:
    try:
        value = json.loads((root / ".agent" / "state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    active = value.get("activeModule") if isinstance(value, dict) else None
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
    counts = "- Modules %d · Specs %d · Plans %d · In progress %d · Done %d" % (
        len(states), sum(s["spec"] for s in states), sum(s["plan"] for s in states),
        sum(s["stage"] == "BUILDING" for s in states), sum(s["stage"] == "DONE" for s in states))
    if stage == "DONE":
        if current is not None:
            notes.append("- activeModule `%s` is already done and can be cleared." % current["id"])
        return ("当前阶段: **DONE**\n\n- Capability map: present\n" + counts + "\n" + "".join(n + "\n" for n in notes) +
                "\nSuggested next step: every mapped module has a plan and no open todo item. "
                "For new work, insert a module with /spec-guard:add-module "
                "(Codex: spec-guard-ops add-module) at this checkpoint; "
                "use a Proposal when the addition needs a recorded, reviewed decision.")
    module = current["id"]
    next_step = {
        "NEEDS_SPEC": "write and review `spec/%s.md`." % module,
        "NEEDS_PLAN": "create `tasks/%s/plan.md` and `tasks/%s/todo.md` (for example with `/plan`)." % (module, module),
        "BUILDING": "continue `/build` on `%s`: %d unchecked item(s) in `tasks/%s/todo.md`." % (module, current["open"], module),
        "MODULE_DONE": "`%s` is done; next unfinished module in Build order is `%s` (%s). "
                       "Set activeModule to it before building." % (module, pending["id"], pending["stage"]),
    }[stage]
    return ("当前阶段: **%s**\n\n- Capability map: present\n- Current module: `%s` (%s)\n%s\n%s"
            "\nSuggested next step: %s" % (stage, module, source, counts,
                                          "".join(n + "\n" for n in notes), next_step))


if __name__ == "__main__":
    print(describe(Path(sys.argv[1] if len(sys.argv) > 1 else ".")))
