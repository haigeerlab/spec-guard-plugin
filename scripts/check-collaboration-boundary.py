#!/usr/bin/env python3
"""Fail when Spec Guard code refers to collaboration internals outside the collaboration-owned files.

Spec Guard reaches collaboration only through `hooks/agent_relay_probe.py` and agent-relay skill names
(docs/collaboration-interface.md section 11). Everything else that names a collaboration module, skill,
command, mailbox tool, MCP server, or state path is a call site that would break when the code moves to
agent-relay, so it fails here instead of in a reviewer's memory.

Scope: the shipped plugin tree, scripts, evals, and the marketplace manifest. User-facing repository docs join
the scope in collaboration-dependency; spec/, tasks/, docs/ records and CHANGELOG.md describe the past and are
never in scope. This file and the owned list define the boundary, so they are the only other exemptions.
"""
from pathlib import Path
import re
import sys

OWNED_LIST = "scripts/collaboration-owned.txt"
SELF = "scripts/check-collaboration-boundary.py"
SCOPE = ("plugins/spec-guard", "scripts", "evals", ".claude-plugin", ".agents")
SKIP_DIRS = {".git", "__pycache__", "node_modules"}

MAILBOX_TOOLS = (
    "register", "send", "inbox", "ack", "outbox", "agents", "sessions", "wake_status", "thread", "wait",
    "retire", "orchestrate_codex", "continue_codex", "orchestration_wait", "orchestration_status",
)
FORBIDDEN = (
    ("module or file name", re.compile(
        r"native_collaboration_\w+|(?<![A-Za-z0-9])session_(?:routing|delegation)\w*"
        r"|collaboration-runtime\.md|collaboration-protocol\.md")),
    ("skill or command path", re.compile(
        r"skills/(?:collab|collaboration-ops|session-routing|session-delegation)\b(?![\w-])"
        r"|commands/collaboration\.md")),
    ("skill or command name", re.compile(
        r"(?<!agent-relay:)(?<![\w/.-])(?:collab|collaboration-ops|session-routing|session-delegation)(?![\w/-])"
        r"|/spec-guard:collaboration(?![\w-])")),
    ("mailbox tool", re.compile(
        r"(?<![A-Za-z0-9])bridge_(?:" + "|".join(MAILBOX_TOOLS) + r")(?![A-Za-z0-9_])"
        r"|(?<![A-Za-z0-9])(?:ask_codex|review_with_codex)(?![A-Za-z0-9_])")),
    ("MCP server name", re.compile(
        r"spec-guard-native-collaboration|spec_guard_native_collaboration"
        r"|mcp__agent-relay__|mcp_servers\.agent_relay\b")),
    ("state path", re.compile(
        r"\.spec-guard/native-collaboration|\.spec-guard/session-delegation|[~/]\.agent-relay\b")),
)


def load_owned(root: Path) -> tuple[list[str], list[str]]:
    owned, missing = [], []
    for raw in (root / OWNED_LIST).read_text(encoding="utf-8").splitlines():
        entry = raw.strip()
        if not entry or entry.startswith("#"):
            continue
        owned.append(entry)
        if not (root / entry.rstrip("/")).exists():
            missing.append(entry)
    return owned, missing


def is_owned(rel: str, owned: list[str]) -> bool:
    return any(rel.startswith(entry) if entry.endswith("/") else rel == entry for entry in owned)


def scan(root: Path, owned: list[str]) -> list[str]:
    hits = []
    for top in SCOPE:
        base = root / top
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or SKIP_DIRS.intersection(path.relative_to(root).parts):
                continue
            rel = path.relative_to(root).as_posix()
            if rel in (SELF, OWNED_LIST) or is_owned(rel, owned):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                for kind, pattern in FORBIDDEN:
                    for match in pattern.finditer(line):
                        hits.append(f"{rel}:{lineno}: {kind} `{match.group(0)}`")
    return hits


def main() -> int:
    # 可传入另一个仓库根（测试夹具用），默认检查本仓库。
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    if not (root / OWNED_LIST).is_file():
        print(f"  ❌ missing {OWNED_LIST}: nothing defines the collaboration-owned files")
        return 1
    owned, missing = load_owned(root)
    if not owned:
        print(f"  ❌ {OWNED_LIST} lists no paths: that is not a clean boundary, it is no boundary")
        return 1
    for entry in missing:
        print(f"  ❌ owned path does not exist: {entry} (a stale list widens the exemption)")
    hits = scan(root, owned)
    for hit in hits:
        print(f"  ❌ {hit}")
    if missing or hits:
        print("  Reach collaboration only through hooks/agent_relay_probe.py and agent-relay skill names "
              "(docs/collaboration-interface.md section 11).")
        return 1
    print(f"  ✅ collaboration boundary: no internal reference outside {len(owned)} owned paths")
    return 0


if __name__ == "__main__":
    sys.exit(main())
