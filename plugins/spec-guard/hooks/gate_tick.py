"""Tick a module's final acceptance checkbox in its todo.md (gate-tick).

For consumer plugins (for example a merge run) that record an accepted module: the final gate is found by
module_stage alone (`gate_checkpoints`, `at_final_gate`), the same criterion as the stage hint's final gate, so
this file has no checkpoint pattern of its own.  It previews by default and writes only with `--confirm`, and then
changes that one `[ ]` to `[x]` and nothing else; it never commits.  It cannot check that the user approved the
acceptance: the caller must already hold that approval.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from capability_map import MODULE_ID, MapError, parse_map
from module_stage import OPEN_ITEM, at_final_gate, gate_checkpoints
from tracker_default import _write_atomic

BOX = re.compile(r"\[ \]")


def main() -> int:
    parser = argparse.ArgumentParser(description="Tick a module's final acceptance checkbox (preview unless --confirm).")
    parser.add_argument("--project", default=".")
    parser.add_argument("--module", required=True)
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    root, module_id = Path(args.project), args.module
    if not MODULE_ID.fullmatch(module_id):
        print("not-a-module-id: use the id from the capability map")
        return 2
    try:
        parsed = parse_map(root / "spec" / "CAPABILITY-MAP.md")
    except (OSError, MapError, UnicodeError):
        print("map-unreadable: run /spec-guard:verify-artifacts first")
        return 2
    if module_id not in [row.module_id for row in parsed.rows]:
        print("not-in-map: %s is not in spec/CAPABILITY-MAP.md" % module_id)
        return 2
    relative = "tasks/%s/todo.md" % module_id
    path = root / relative
    if not path.is_file():
        print("todo-missing: %s does not exist" % relative)
        return 2
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            text = handle.read()
    except (OSError, UnicodeError):
        print("todo-unreadable: %s could not be read" % relative)
        return 2
    gates = gate_checkpoints(text)
    if not gates:
        print("no-gate: %s has no gate checkpoint" % relative)
        return 2
    lines = text.splitlines(keepends=True)
    open_items = [index for index, line in enumerate(lines) if OPEN_ITEM.match(line)]
    if all(checked for _, _, checked in gates):
        print("%s: the final gate is already ticked; nothing to change (%d unchecked item(s) left)"
              % (relative, len(open_items)))
        return 0
    if not at_final_gate(root, module_id):
        first = lines[open_items[0]].strip() if open_items else ""
        print("not-at-final-gate: the first unchecked item of %s is not its last gate: %s" % (relative, first))
        return 2
    at = open_items[0]
    lines[at] = BOX.sub("[x]", lines[at], count=1)
    left = len(open_items) - 1
    print("%s line %d: %s" % (relative, at + 1, lines[at].strip()))
    if not args.confirm:
        print("preview only: add --confirm to tick it (%d unchecked item(s) left after)" % left)
        return 0
    _write_atomic(path, "".join(lines))
    print("ticked; %d unchecked item(s) left" % left)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
