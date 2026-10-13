"""Link a session directory to the project it works on (linked-project-root).

A session may run in a directory that is not the project -- a requirements folder, say -- while the
work happens in a repository elsewhere.  The phase hook only looks at the session directory, so it
stays silent there.  One file in the session directory, `.agent/spec-guard-link.json`, declares the
project; the hook then reports that project's phase.  Nothing is inferred: without the file an
unrelated directory stays silent.
"""
from __future__ import annotations

import json
from pathlib import Path

LINK_PATH = Path(".agent") / "spec-guard-link.json"


def resolve(session_root) -> tuple:
    """(`none`, None), (`ok`, target), (`invalid`, None) or (`missing`, target) for the link under `session_root`.

    `invalid` is about the file itself; `missing` means the file is fine and the directory it names is
    not there.  Whether the target has the convention enabled is the caller's question.
    """
    root = Path(session_root).resolve()
    path = root / LINK_PATH
    if not path.exists() and not path.is_symlink():
        return "none", None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "invalid", None
    if not isinstance(data, dict) or set(data) != {"version", "project"}:
        return "invalid", None
    version, project = data["version"], data["project"]
    if version != 1 or isinstance(version, bool):
        return "invalid", None
    if not isinstance(project, str) or not project.strip() or "\n" in project or "\r" in project or "\0" in project:
        return "invalid", None
    target = Path(project)
    target = (target if target.is_absolute() else root / target).resolve()
    return ("ok" if target.is_dir() else "missing"), target
