"""Link a session directory to the project it works on (linked-project-root).

A session may run in a directory that is not the project -- a requirements folder, say -- while the
work happens in a repository elsewhere.  The phase hook only looks at the session directory, so it
stays silent there.  One file in the session directory, `.agent/spec-guard-link.json`, declares the
project; the hook then reports that project's phase.  Nothing is inferred: without the file an
unrelated directory stays silent.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

LINK_PATH = Path(".agent") / "spec-guard-link.json"
PATH_SHOWN = 1024


SESSION_ID = re.compile(r"[A-Za-z0-9_-]{1,128}")


def _path_ok(value) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not any(c in value for c in "\n\r\0")


def read_link(session_root) -> tuple:
    """(`none`, None), (`invalid`, None) or (`ok`, {"project": str | None, "sessions": {id: path}}).

    Version 1 holds one directory-level `project`.  Version 2 (link-per-session) adds `sessions`: one
    project per session id, for sessions that share a directory and work on different projects.
    """
    path = Path(session_root).resolve() / LINK_PATH
    if not path.exists() and not path.is_symlink():
        return "none", None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "invalid", None
    if not isinstance(data, dict) or isinstance(data.get("version"), bool):
        return "invalid", None
    if data.get("version") == 1:
        if set(data) != {"version", "project"} or not _path_ok(data["project"]):
            return "invalid", None
        return "ok", {"project": data["project"], "sessions": {}}
    if data.get("version") != 2 or not set(data) <= {"version", "project", "sessions"}:
        return "invalid", None
    sessions = data.get("sessions")
    if not isinstance(sessions, dict):
        return "invalid", None
    if "project" in data and not _path_ok(data["project"]):
        return "invalid", None
    if not sessions and "project" not in data:
        return "invalid", None
    for key, value in sessions.items():
        if not isinstance(key, str) or not SESSION_ID.fullmatch(key) or not _path_ok(value):
            return "invalid", None
    return "ok", {"project": data.get("project"), "sessions": dict(sessions)}


def _target(root: Path, value: str) -> Path:
    target = Path(value)
    return (target if target.is_absolute() else root / target).resolve()


def resolve_for(session_root, session_ids=()) -> tuple:
    """(state, target, source): this session's own entry first, then the directory-level link, else `none`.

    `source` is `session` or `directory`, None when there is no target.  `invalid` is about the file;
    `missing` means the file is fine and the directory it names is not there.  Whether the target has
    the convention enabled is the caller's question.
    """
    root = Path(session_root).resolve()
    state, link = read_link(root)
    if state != "ok":
        return state, None, None
    for session_id in session_ids:
        if session_id in link["sessions"]:
            target = _target(root, link["sessions"][session_id])
            return ("ok" if target.is_dir() else "missing"), target, "session"
    if link["project"] is None:
        return "none", None, None
    target = _target(root, link["project"])
    return ("ok" if target.is_dir() else "missing"), target, "directory"


_TRAILING_UUID = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$")


def session_ids_from_hook_input(text: str) -> list:
    """Candidate ids of the session a hook input belongs to; [] when it says nothing usable.

    Both hosts name the transcript after the session: Claude Code uses the id as the file name, Codex ends
    the rollout file name with it.  `session_id` is taken too when the input carries one.
    """
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        return []
    if not isinstance(data, dict):
        return []
    found = []
    session_id = data.get("session_id")
    if isinstance(session_id, str):
        found.append(session_id)
    transcript = data.get("transcript_path")
    if isinstance(transcript, str) and transcript:
        stem = Path(transcript).name
        stem = stem[:-len(".jsonl")] if stem.endswith(".jsonl") else stem
        found.append(stem)
        tail = _TRAILING_UUID.search(stem)
        if tail:
            found.append(tail.group(0))
    return [value for value in dict.fromkeys(found) if SESSION_ID.fullmatch(value)]


def resolve(session_root) -> tuple:
    """The directory-level link only: (`none`, None), (`ok`, target), (`invalid`, None) or (`missing`, target)."""
    return resolve_for(session_root)[:2]


# The activation signals, as phase-guard.sh reads them (has_block / has_state); the two are held together
# by a regression that feeds the same directories to both.
_BLOCKS = (("CLAUDE.md", re.compile(r"^\s*<!-- BEGIN:agent-skills-convention -->\s*$")),
           ("AGENTS.md", re.compile(r"^\s*<!-- BEGIN:spec-guard-codex-convention -->\s*$")))
_STATE = re.compile(r'"activeModule"\s*:')


def _lines(path: Path) -> list:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def enabled(root) -> bool:
    """Whether `root` carries one of the plugin's own activation signals."""
    root = Path(root)
    return (any(pattern.match(line) for name, pattern in _BLOCKS for line in _lines(root / name))
            or any(_STATE.search(line) for line in _lines(root / ".agent" / "state.json")))


def status(session_root) -> tuple:
    """`resolve`, with `ok` split into `ok` and `not-enabled`."""
    state, target = resolve(session_root)
    if state == "ok" and not enabled(target):
        state = "not-enabled"
    return state, target


def _phase(target: Path) -> str:
    """The phase line the hook gives for `target`, or "" when it cannot be had."""
    env = {key: value for key, value in os.environ.items()
           if key not in ("PLUGIN_ROOT", "SPEC_GUARD_HOST", "CLAUDE_CODE_SESSION_ATTENDED")}
    env["CLAUDE_PROJECT_DIR"] = str(target)
    try:
        done = subprocess.run(["bash", str(Path(__file__).with_name("phase-guard.sh"))], stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=30, env=env)
        text = json.loads(done.stdout)["hookSpecificOutput"]["additionalContext"]
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
        return ""
    return next((line for line in text.splitlines() if line.startswith("当前阶段")), "")


# link-shared-directory-note: the link is keyed by directory, so every session there follows it.
SHARED = ("The link applies to every session that runs in this directory. When several sessions share it and work on "
          "different projects, do not link: open each session in its own project directory, or pass the project path "
          "explicitly.")

WHY = {"invalid": "the file is not a JSON object with exactly `version` (1) and `project` (a path)",
       "missing": "the directory it names does not exist or is not a directory",
       "not-enabled": "the directory it names has no spec-guard convention (no convention block, no "
                      "`.agent/state.json` with activeModule)"}


def _show(session: Path) -> int:
    state, target = status(session)
    where = session / LINK_PATH
    if state == "none":
        print("no link: %s does not exist" % where)
    elif state == "ok":
        print("link valid: %s -> %s" % (where, target))
        print(SHARED)
        phase = _phase(target)
        if phase:
            print(phase)
    else:
        print("link %s: %s%s" % (state, WHY[state], " (%s)" % target if target is not None else ""))
        print("fix it with `set --project <path>` after `unset`, or remove it with `unset`.")
    return 0


def _set(session: Path, project: str, confirm: bool) -> int:
    from tracker_default import _write_atomic

    if enabled(session):
        print("session-enabled: %s has the convention itself, so its own phase is reported; a link is not needed"
              % session)
        return 2
    if resolve(session)[0] == "invalid":
        print("link-invalid: the existing %s is malformed; remove it with `unset --confirm` first" % LINK_PATH)
        return 2
    if not project.strip() or "\n" in project or "\r" in project or "\0" in project:
        print("target-missing: give the project directory as one path")
        return 2
    target = Path(project)
    target = (target if target.is_absolute() else session / target).resolve()
    if not target.is_dir():
        print("target-missing: %s does not exist or is not a directory" % target)
        return 2
    if target == session:
        print("target-is-session: the project is the session directory itself")
        return 2
    if not enabled(target):
        print("target-not-enabled: %s has no spec-guard convention; run setup-convention there first" % target)
        return 2
    content = json.dumps({"version": 1, "project": project}, ensure_ascii=False) + "\n"
    path = session / LINK_PATH
    try:
        current = path.read_text(encoding="utf-8") if path.is_file() else None
    except (OSError, UnicodeError):
        current = None
    print("link file: %s" % path)
    print("content:   %s" % content.strip())
    print("project:   %s" % target)
    phase = _phase(target)
    if phase:
        print("its phase: %s" % phase)
    print(SHARED)
    if current == content:
        print("\nalready linked to this project; nothing to change.")
        return 0
    print("The file holds a path on this machine. Keep it out of version control (add `%s` to .gitignore) unless "
          "the path is relative and meant to be shared; this command does not edit .gitignore." % LINK_PATH.as_posix())
    if not confirm:
        print("\npreview only; nothing was written. Re-run with --confirm to apply.")
        return 0
    try:
        path.parent.mkdir(exist_ok=True)
        _write_atomic(path, content)
    except OSError:
        print("link-unwritable: %s could not be written" % path)
        return 2
    if status(session) != ("ok", target):
        print("readback-mismatch: %s does not read back as a valid link to %s" % (path, target))
        return 2
    print("\nlinked %s -> %s" % (session, target))
    return 0


def _unset(session: Path, confirm: bool) -> int:
    path = session / LINK_PATH
    if not path.exists() and not path.is_symlink():
        print("no-link: %s does not exist" % path)
        return 2
    if path.is_dir() and not path.is_symlink():
        print("link-unwritable: %s is a directory; remove it by hand" % path)
        return 2
    print("will remove: %s" % path)
    if not confirm:
        print("\npreview only; nothing was removed. Re-run with --confirm to apply.")
        return 0
    try:
        path.unlink()
    except OSError:
        print("link-unwritable: %s could not be removed" % path)
        return 2
    print("\nunlinked %s (the `.agent` directory is left in place)" % session)
    return 0


def main(argv=None) -> int:
    import argparse
    from module_stage import safe_fragment

    parser = argparse.ArgumentParser(description="Link a session directory to the project it works on.")
    sub = parser.add_subparsers(dest="action", required=True)
    probe = sub.add_parser("resolve", help="for the phase hook: status, target, then both paths made safe to print")
    show = sub.add_parser("show", help="report the link and whether it is valid")
    setter = sub.add_parser("set", help="write the link (preview unless --confirm)")
    setter.add_argument("--project", required=True)
    unsetter = sub.add_parser("unset", help="remove the link (preview unless --confirm)")
    probe.add_argument("--hook-input", action="store_true", help="read the hook input (JSON) from stdin for the session id")
    for command in (probe, show, setter, unsetter):
        command.add_argument("--from", dest="session", default=".")
    for command in (setter, unsetter):
        command.add_argument("--confirm", action="store_true")
    args = parser.parse_args(argv)
    session = Path(args.session).resolve()
    if args.action == "resolve":
        ids = session_ids_from_hook_input(sys.stdin.read()) if args.hook_input else []
        state, target, source = resolve_for(session, ids)
        print(state)
        print(target if state == "ok" else "")
        # The agent is told to pass this path on, so it must arrive whole: bound it by the path limit, not by the
        # 200 characters meant for diagnostics.
        print(safe_fragment(str(target), PATH_SHOWN) if target is not None else "")
        print(safe_fragment(str(session), PATH_SHOWN))
        print(source or "")
        return 0
    if not session.is_dir():
        print("session-missing: %s is not a directory" % session)
        return 2
    if args.action == "show":
        return _show(session)
    if args.action == "set":
        return _set(session, args.project, args.confirm)
    return _unset(session, args.confirm)


if __name__ == "__main__":
    raise SystemExit(main())
