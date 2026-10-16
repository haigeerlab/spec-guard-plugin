"""Suspend or resume a started module by one marker line in its todo.md (module-suspend).

Suspending records that the module is parked and, with `--reason`, one line saying why in
the user's words (map-view shows it); no date or condition, and nothing ever resumes it except
an explicit `--resume`.  Whether it is suspended is decided
by `module_stage` alone; this script only adds or removes the marker, previews the effect
on the current module, and writes only with `--confirm`.
"""
from __future__ import annotations

import argparse
import difflib
from pathlib import Path

from capability_map import MODULE_ID, MapError, parse_map
from module_stage import SUSPEND_MARKER, active_module, module_state, project_stage
from tracker_default import _write_atomic

# map-view: an optional reason sits on its own line right after the marker, so versions that only
# know the marker still read the module as suspended and simply ignore this line.
REASON_PREFIX = "<!-- spec-guard: suspended-reason: "
REASON_SUFFIX = " -->"
REASON_LIMIT = 120


def reason_line(reason: str) -> str:
    return REASON_PREFIX + reason + REASON_SUFFIX


def _drop_marker(text: str, keep_marker: bool) -> str:
    """Remove the reason line that follows the marker, and the marker too unless kept."""
    lines = text.splitlines(keepends=True)
    out = []
    skip_reason = False
    for line in lines:
        if skip_reason and line.strip().startswith(REASON_PREFIX):
            skip_reason = False
            continue
        skip_reason = False
        if line.strip() == SUSPEND_MARKER:
            skip_reason = True
            if not keep_marker:
                continue
        out.append(line)
    return "".join(out)


def _states(root: Path) -> list:
    parsed = parse_map(root / "spec" / "CAPABILITY-MAP.md")
    order = list(parsed.order) or [row.module_id for row in parsed.rows]
    return [module_state(root, module_id) for module_id in order]


def _current_after(states: list, module_id: str, suspended: bool, root: Path) -> dict | None:
    simulated = [dict(state, suspended=suspended, half=state["half"] and not suspended)
                 if state["id"] == module_id else state for state in states]
    return project_stage(simulated, active_module(root))[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Suspend or resume a started module (preview unless --confirm).")
    parser.add_argument("--project", default=".")
    parser.add_argument("--suspend", metavar="MODULE")
    parser.add_argument("--resume", metavar="MODULE")
    parser.add_argument("--reason", help="one line in the user's words; only with --suspend")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    if (args.suspend is None) == (args.resume is None):
        print("usage: give exactly one of --suspend MODULE or --resume MODULE")
        return 2
    reason = None
    if args.reason is not None:
        if args.resume is not None:
            print("usage: --reason only goes with --suspend")
            return 2
        reason = args.reason.strip()
        if not reason or "\n" in reason or "\r" in reason or "-->" in reason or len(reason) > REASON_LIMIT:
            print("bad-reason: one non-empty line of at most %d characters, without -->" % REASON_LIMIT)
            return 2
    suspending = args.suspend is not None
    module_id = args.suspend if suspending else args.resume
    root = Path(args.project)
    if not MODULE_ID.fullmatch(module_id):
        print("not-a-module-id: use the id from the capability map")
        return 2
    try:
        states = _states(root)
    except (OSError, MapError, UnicodeError):
        print("map-unreadable: run /spec-guard:verify-artifacts first")
        return 2
    state = next((s for s in states if s["id"] == module_id), None)
    if state is None:
        print("not-in-map: %s is not in spec/CAPABILITY-MAP.md" % module_id)
        return 2
    if not state["plan"] or not state["todo"]:
        print("no-plan-or-todo: only a started module (plan and todo) can be suspended or resumed")
        return 2
    path = root / "tasks" / module_id / "todo.md"
    before = path.read_text(encoding="utf-8")
    marked = any(line.strip() == SUSPEND_MARKER for line in before.splitlines())
    if suspending:
        if not state["open"]:
            print("nothing-open: %s has no unchecked item; it already counts as done" % module_id)
            return 2
        if marked and reason is None:
            print("already-suspended: %s already carries the marker" % module_id)
            return 2
        if marked:
            lines = _drop_marker(before, keep_marker=True).splitlines(keepends=True)
            at = next(i for i, line in enumerate(lines) if line.strip() == SUSPEND_MARKER)
            if not lines[at].endswith("\n"):
                lines[at] += "\n"
            lines.insert(at + 1, reason_line(reason) + "\n")
            after = "".join(lines)
        else:
            after = (before + ("" if before.endswith("\n") or not before else "\n") + SUSPEND_MARKER + "\n"
                     + (reason_line(reason) + "\n" if reason is not None else ""))
    else:
        if not marked:
            print("not-suspended: %s carries no suspend marker" % module_id)
            return 2
        after = _drop_marker(before, keep_marker=False)
    relative = "tasks/%s/todo.md" % module_id
    print("".join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                                       fromfile=relative + " (current)", tofile=relative + " (proposed)")))
    current = _current_after(states, module_id, suspending, root)
    label = "suspending" if suspending else "resuming"
    print("current module after %s: %s" % (label, current["id"] if current else "none (all done)"))
    if not suspending and current is not None and current["id"] != module_id and current["half"]:
        print("%s is half done: %s will show as paused and comes back after %s, as with an interrupt."
              % (current["id"], module_id, current["id"]))
    if not args.confirm:
        print("\npreview only; nothing was written. Re-run with --confirm to apply.")
        return 0
    try:
        _write_atomic(path, after)
    except OSError:
        print("todo-unwritable: %s could not be written" % relative)
        return 2
    if module_state(root, module_id)["suspended"] != suspending:
        print("readback-mismatch: %s does not read back as %s" % (relative, "suspended" if suspending else "resumed"))
        return 2
    print("\n%s %s" % ("suspended" if suspending else "resumed", module_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
