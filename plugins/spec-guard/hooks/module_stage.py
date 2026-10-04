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

from capability_map import MODULE_ID, MapError, parse_map

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


FRAGMENT_LIMIT = 80
STRUCTURE_CHARS = str.maketrans("", "", "`\\")


def safe_fragment(value, limit: int = FRAGMENT_LIMIT) -> str:
    """Make a value from the repository safe to name in the injected phase context.

    `describe()` output reaches an agent every turn, so a value carrying a newline can
    forge a heading and one carrying a backtick can forge a code fence.  This keeps the
    words -- the point is a usable diagnostic, not redaction -- while removing the
    characters that let a value pretend to be structure, and bounds the length so a
    long one cannot bury the real message.

    80 is measured, not guessed: the longest module id in this repository's capability
    map is 29 characters, so a legitimate diagnostic is never truncated.

    No HTML or Markdown escaping: the destination is an agent's context, not a browser,
    and escapes would only make the diagnostic harder to read.
    """
    if not isinstance(value, str) or not value:
        return ""
    cleaned = " ".join(value.translate(STRUCTURE_CHARS).split())
    return cleaned if len(cleaned) <= limit else cleaned[:limit] + "\u2026"


def _state(root: Path) -> dict:
    try:
        value = json.loads((root / ".agent" / "state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def active_module_state(root: Path) -> tuple:
    """(value, state) where state is `absent`, `invalid` or `present`.

    `invalid` is kept distinct from `absent` on purpose: the user did set something, and
    silently ignoring it would let them believe it took effect.  The value itself is a
    repository-controlled string, so only this state -- never the string -- is safe to
    report without passing through `safe_fragment`.
    """
    active = _state(root).get("activeModule")
    if not isinstance(active, str) or not active:
        return None, "absent"
    if not MODULE_ID.match(active):
        return active, "invalid"
    return active, "present"


def active_module(root: Path) -> str | None:
    """The current module pointer, or None when unset or not a module id."""
    value, state = active_module_state(root)
    return value if state == "present" else None


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
        # The message carries the offending cell, which is the whole diagnostic value --
        # without it nobody knows which row is broken. It is also repository content, so
        # it goes through the sanitiser rather than being dropped or trusted.
        return ("当前阶段: **MAP_INVALID**\n\n- Capability map: present but invalid (%s)\n\n"
                "Suggested next step: run `/spec-guard:verify-artifacts` and fix the capability map."
                % safe_fragment(str(error)))
    order = list(parsed.order) or [row.module_id for row in parsed.rows]
    states = [module_state(root, module_id) for module_id in order]
    by_id = {state["id"]: state for state in states}
    active, active_state = active_module_state(root)
    active = active if active_state == "present" else None
    stage, current, source, pending = project_stage(states, active)
    notes = []
    if active_state == "invalid":
        # Report it, but never echo it: the value is repository content, and the note
        # itself is enough for the user to find what they typed.
        notes.append("- `.agent/state.json` 的 activeModule 不是有效的 module id；"
                     "按 Build order 取当前模块。")
    elif active and active not in by_id:
        notes.append("- activeModule `%s` is not in the capability map; using Build order."
                     % safe_fragment(active))
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
        count, ref = unmerged[0], safe_fragment(unmerged[1])
        hint = "- This branch has %d commit(s) not yet in `%s` (as last fetched)." % (count, ref)
        push_first = ("push this branch and merge its %d commit(s) into `%s` first; then "
                      % (count, ref))
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
