#!/usr/bin/env python3
"""Fail if collaboration comes back into Spec Guard after it moved to agent-relay.

Spec Guard reaches collaboration only through `hooks/agent_relay_probe.py` and agent-relay skill names
(docs/collaboration-interface.md sections 11-12; the transitional handoff command was removed in 0.54.0). The check fails when
any path on the removed list exists again, or when anything in scope names a collaboration module, skill, mailbox
tool, MCP server, or state path (collaboration-dependency, decision D17).

Scope: the shipped plugin tree, scripts, evals, the marketplace manifest, and the user-facing docs below. spec/,
tasks/, docs/ records, the migration document and CHANGELOG.md describe the past and are never in scope. This file
and the removed list define the rule, so they are the only other exemptions.
"""
from pathlib import Path
import re
import sys

OWNED_LIST = "scripts/collaboration-owned.txt"
SELF = "scripts/check-collaboration-boundary.py"
SCOPE = ("plugins/spec-guard", "scripts", "evals", ".claude-plugin", ".agents")
USER_DOCS = ("README.md", "CLAUDE.md", "AGENTS.md", "docs/optional-features.md", "docs/workflow.md")
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
        r"skills/(?:collab|collaboration-ops|session-routing|session-delegation)\b(?![\w-])")),
    ("skill or command name", re.compile(
        r"(?<!agent-relay:)(?<![\w/.-])(?:collab|collaboration-ops|session-routing|session-delegation)(?![\w/-])")),
    ("mailbox tool", re.compile(
        r"(?<![A-Za-z0-9])bridge_(?:" + "|".join(MAILBOX_TOOLS) + r")(?![A-Za-z0-9_])"
        r"|(?<![A-Za-z0-9])(?:ask_codex|review_with_codex)(?![A-Za-z0-9_])")),
    ("MCP server name", re.compile(
        r"spec-guard-native-collaboration|spec_guard_native_collaboration"
        r"|mcp__agent-relay__|mcp_servers\.agent_relay\b")),
    ("state path", re.compile(
        r"\.spec-guard/native-collaboration|\.spec-guard/session-delegation|[~/]\.agent-relay\b")),
)


def load_removed(root: Path) -> tuple[list[str], list[str]]:
    removed, present = [], []
    for raw in (root / OWNED_LIST).read_text(encoding="utf-8").splitlines():
        entry = raw.strip()
        if not entry or entry.startswith("#"):
            continue
        removed.append(entry)
        if (root / entry.rstrip("/")).exists():
            present.append(entry)
    return removed, present


def files_in_scope(root: Path):
    for top in SCOPE:
        base = root / top
        if base.exists():
            yield from sorted(path for path in base.rglob("*") if path.is_file())
    for name in USER_DOCS:
        if (root / name).is_file():
            yield root / name


def scan(root: Path) -> list[str]:
    hits = []
    for path in files_in_scope(root):
        if SKIP_DIRS.intersection(path.relative_to(root).parts):
            continue
        rel = path.relative_to(root).as_posix()
        if rel in (SELF, OWNED_LIST):
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
        print(f"  ❌ missing {OWNED_LIST}: nothing records what moved to agent-relay")
        return 1
    removed, present = load_removed(root)
    if not removed:
        print(f"  ❌ {OWNED_LIST} lists no paths: an empty list checks nothing")
        return 1
    for entry in present:
        print(f"  ❌ removed from Spec Guard but present again: {entry}")
    hits = scan(root)
    for hit in hits:
        print(f"  ❌ {hit}")
    if present or hits:
        print("  Collaboration lives in agent-relay; reach it only through hooks/agent_relay_probe.py and agent-relay "
              "skill names (docs/collaboration-interface.md sections 11-12).")
        return 1
    print(f"  ✅ collaboration removed: {len(removed)} moved paths absent, no internal reference in scope")
    return 0


if __name__ == "__main__":
    sys.exit(main())
