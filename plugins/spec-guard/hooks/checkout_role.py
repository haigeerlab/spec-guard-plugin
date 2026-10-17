"""The role of one checkout when several modules are developed at once (checkout-role).

With `moduleConcurrency` on, each checkout of a project -- the integration checkout and one worktree per
module -- may carry a role: `module <id>` or `coordinator`.  The marker lives in that checkout's own git
directory (`git rev-parse --git-path spec-guard/role`), so it is never committed and never travels to
another worktree.  The phase hint and `/map` only read it, and only through `role()`, which does not even
look while the switch is off.  Writing goes through this command, preview first.

The marker is local content that may reach an agent's context, so problems are fixed codes and its text is
never echoed.
"""
from __future__ import annotations

import argparse
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

from capability_map import MODULE_ID, MapError, parse_map
from project_config import module_concurrency
from tracker_default import _write_atomic

MARKER = "spec-guard/role"
MAX_BYTES = 256
ROLE_KINDS = ("module", "coordinator")  # interface.json checkoutRole.values.role
LINE = re.compile(r"^(?:module ([a-z0-9]+(?:-[a-z0-9]+)*)|(coordinator))$")


def _git(root: Path, *args: str) -> str | None:
    try:
        done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def role_path(root) -> Path | None:
    """Absolute path of this checkout's marker, or None when `root` is not the top of a non-bare checkout."""
    root = Path(root)
    top = _git(root, "rev-parse", "--show-toplevel")
    if not top or Path(top).resolve() != root.resolve():
        return None
    raw = _git(root, "rev-parse", "--git-path", MARKER)
    if not raw:
        return None
    path = Path(raw)
    return path if path.is_absolute() else root / path


def _describe(kind: str, module: str | None) -> str:
    return "module %s" % module if kind == "module" else kind


def read_marker(path: Path) -> tuple:
    """Read one marker file: links, special files, oversize and anything but one valid line are invalid."""
    if path.parent.is_symlink() or (os.path.lexists(path.parent) and not path.parent.is_dir()):
        return "invalid", None
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        descriptor = os.open(str(path), flags)
    except FileNotFoundError:
        return ("invalid", None) if os.path.lexists(path) else ("none", None)
    except OSError:
        return "invalid", None
    try:
        with os.fdopen(descriptor, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                return "invalid", None
            raw = stream.read(MAX_BYTES + 1)
    except OSError:
        return "invalid", None
    if len(raw) > MAX_BYTES:
        return "invalid", None
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        return "invalid", None
    match = LINE.match(lines[0]) if len(lines) == 1 else None
    if match is None:
        return "invalid", None
    module_kind, coordinator_kind = ROLE_KINDS
    return (module_kind, match.group(1)) if match.group(1) else (coordinator_kind, None)


def read_role(root) -> tuple:
    """("none"|"invalid"|"coordinator"|"module", id-or-None) for the checkout at `root`."""
    path = role_path(root)
    return ("none", None) if path is None else read_marker(path)


def role(root) -> tuple:
    """The role the phase hint and /map act on: always none while moduleConcurrency is not on."""
    if not module_concurrency(Path(root)):
        return "none", None
    return read_role(root)


def _unsafe(path: Path) -> bool:
    if path.parent.is_symlink() or (os.path.lexists(path.parent) and not path.parent.is_dir()):
        return True
    return os.path.lexists(path) and (path.is_symlink() or not stat.S_ISREG(path.lstat().st_mode))


def change(root, value: str | None, confirm: bool) -> tuple:
    """Set (`module <id>` or `coordinator`) or clear (None) the marker; (exit code, report)."""
    root = Path(root)
    path = role_path(root)
    if path is None:
        return 2, "not-a-checkout: the project is not the top of a non-bare git checkout"
    if not module_concurrency(root):
        return 3, "moduleConcurrency is not on in .agent/config.json; the checkout role is not used"
    if value is not None and value.startswith("module "):
        module = value[len("module "):]
        try:
            ids = {row.module_id for row in parse_map(root / "spec" / "CAPABILITY-MAP.md").rows}
        except (MapError, OSError, UnicodeError):
            return 2, "map-unreadable: the capability map could not be read"
        if not MODULE_ID.fullmatch(module) or module not in ids:
            return 2, "module-not-in-map: name a module of the capability map"
    if _unsafe(path):
        return 2, "marker-unsafe: the role marker or its directory is a link or not a regular file"
    before = _describe(*read_role(root))
    after = value or "none"
    report = "role: %s -> %s" % (before, after)
    if before == after:
        return 0, report + "\nno change"
    if not confirm:
        return 0, report + "\n\npreview only; nothing was written. Re-run with --confirm to apply."
    try:
        if value is None:
            path.unlink()
        else:
            path.parent.mkdir(exist_ok=True)
            if _unsafe(path):
                return 2, "marker-unsafe: the role marker or its directory is a link or not a regular file"
            _write_atomic(path, value + "\n")
    except OSError:
        return 2, "marker-unwritable: the role marker could not be written"
    if _describe(*read_role(root)) != after:
        return 4, report + "\nconcurrent-change: the marker does not read back as written; check it with show"
    return 0, report + "\nwrote the checkout role"


def main() -> int:
    parser = argparse.ArgumentParser(description="Show or set the role of this checkout (moduleConcurrency).")
    commands = parser.add_subparsers(dest="command", required=True)
    show = commands.add_parser("show", help="read-only")
    setter = commands.add_parser("set", help="preview, and with --confirm write")
    target = setter.add_mutually_exclusive_group(required=True)
    target.add_argument("--module")
    target.add_argument("--coordinator", action="store_true")
    setter.add_argument("--confirm", action="store_true")
    clearer = commands.add_parser("clear", help="preview, and with --confirm remove")
    clearer.add_argument("--confirm", action="store_true")
    for sub in (show, setter, clearer):
        sub.add_argument("--project", default=".")
    args = parser.parse_args()
    root = Path(args.project)
    if args.command == "show":
        kind, module = read_role(root)
        print("role: %s%s" % (_describe(kind, module),
                              "" if module_concurrency(root) else " (moduleConcurrency is not on, so it is not used)"))
        return 0
    if args.command == "set":
        value = "coordinator" if args.coordinator else "module %s" % args.module
    else:
        value = None
    code, report = change(root, value, args.confirm)
    print(report)
    return code


if __name__ == "__main__":
    sys.exit(main())
