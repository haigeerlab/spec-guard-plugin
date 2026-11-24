#!/usr/bin/env python3
"""检查 Git 跟踪的文本文件，阻止写入本机登录名及用户名路径。"""
from __future__ import annotations  # `re.Pattern | None` on Python 3.9

import getpass
import os
from pathlib import Path
import re
import subprocess
import sys

ALLOWED_NAMES = frozenset({
    "someone", "user", "username", "name", "me", "you", "example", "...", "$user", "${user}",
})
GENERIC_LOGIN_NAMES = frozenset({
    "runner", "root", "ubuntu", "admin", "user", "vagrant", "ci", "nobody", "buildbot", "jenkins",
})
# 分开书写前缀，避免检查器源码本身构成待检查的路径；不豁免任何文件。
PATH_PATTERNS = (
    re.compile(r"/Users" r"/([^/\r\n]+)/"),
    re.compile(r"-Users" r"-(<[^<>/\r\n]+>|[^/\s-]+)-"),
)


def login_name_pattern() -> re.Pattern | None:
    name = os.environ.get("SPEC_GUARD_LOGIN_NAME")
    if name is None:
        try:
            name = getpass.getuser()
        except Exception:
            return None
    if not name or len(name) < 3 or name.lower() in ALLOWED_NAMES | GENERIC_LOGIN_NAMES:
        return None
    return re.compile(r"(?<!\w)" + re.escape(name) + r"(?!\w)", re.IGNORECASE)


def scan(root: Path) -> list[str]:
    login_pattern = login_name_pattern()
    tracked = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z"])
    found = []
    for entry in tracked.split(b"\0"):
        if not entry:
            continue
        relative = os.fsdecode(entry)
        try:
            data = (root / relative).read_bytes()
            if b"\0" in data:
                continue
            text = data.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for pattern in PATH_PATTERNS:
                for match in pattern.finditer(line):
                    name = match.group(1)
                    if name.lower() in ALLOWED_NAMES or re.fullmatch(r"<[^<>]+>", name):
                        continue
                    found.append(f"{relative}:{lineno}: {match.group(0)}")
            if login_pattern is not None:
                for match in login_pattern.finditer(line):
                    found.append(f"{relative}:{lineno}: {match.group(0)}")
    return found


def main() -> int:
    try:
        root = Path(subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True, stderr=subprocess.PIPE).strip())
        found = scan(root)
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"  ❌ 无法读取 Git 跟踪文件：{error}", file=sys.stderr)
        return 1
    for item in found:
        print("  ❌ " + item)
    if found:
        return 1
    print("  ✅ Git 跟踪的文本文件中没有本机登录名或带本机用户名的路径")
    return 0


if __name__ == "__main__":
    sys.exit(main())
