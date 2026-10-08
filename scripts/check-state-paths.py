#!/usr/bin/env python3
"""Keep machine-level paths in one place (runtime-state-layout).

`plugins/spec-guard/hooks/state_paths.py` is the only source of the plugin's machine state
locations (`~/.spec-guard`, or SPEC_GUARD_STATE_DIR); docs/design.md "File layout" lists them.
Before 2026-10-08 nothing stopped a script from growing another home-directory root, and two
did (`~/.local/state/spec-guard`).

Rule, deliberately literal: in a non-test Python file under `plugins/spec-guard/hooks/`, other
than state_paths.py, every line that uses `Path.home()`, `expanduser(` or a `"~/` literal must
also name an allowed home location -- the hosts' own configuration (`.claude`, `.codex`) or
epiq's own directory (`.epiq-global`).  Those are read, never spec-guard state.  Comment lines
are skipped.  Zero Python files is "not found", not "clean" (docs/lenses.md A5).

Usage: check-state-paths.py [repo-root]
"""
import pathlib
import re
import sys

HOME_USE = re.compile(r"Path\.home\(\)|expanduser\(|[\"']~/")
ALLOWED = ('".claude"', '".codex"', '".epiq-global"')
OWNER = "state_paths.py"


def main():
    root = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parents[1]
    folder = root / "plugins/spec-guard/hooks"
    files = sorted(folder.glob("*.py")) if folder.is_dir() else []
    if not files:
        print("  ❌ 0 个 Python 文件 —— 这是没找到，不是没问题", file=sys.stderr)
        return 1
    bad = []
    for path in files:
        if path.name == OWNER or path.name.startswith(("test_", "test-")):
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("#") or not HOME_USE.search(line):
                continue
            if not any(token in line for token in ALLOWED):
                bad.append("%s:%d" % (path.name, number))
    if bad:
        for item in bad:
            print("  ❌ %s 用到家目录但不在允许清单内；本机状态请经 state_paths.py 取得" % item, file=sys.stderr)
        return 1
    print("  ✅ %d 个 Python 文件，家目录用法都经 state_paths.py 或在允许清单内" % len(files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
