"""Register the host MCP entries that Spec Guard installs.

Claude servers are added through the Claude CLI, never by editing its state files; `add` reports an existing name
itself. The removal helpers (`remove_codex_table`, `remove_claude_server`) were deleted on 2026-10-08 (audit F17):
after collaboration moved to agent-relay only their tests called them.
"""
from __future__ import annotations
import subprocess


def add_claude_server(claude_bin: str, arguments: list[str], name: str) -> None:
    """Register a user-scoped server; the Claude CLI itself refuses an existing name."""
    try:
        added = subprocess.run([claude_bin, "mcp", *arguments], check=False,
                               capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError("unable to run Claude MCP registration") from error
    if added.returncode == 0:
        return
    output = (added.stdout + added.stderr).strip()
    if "already exists" in output:
        raise ValueError("Claude MCP server %s already exists; refusing to overwrite it" % name)
    raise ValueError("Claude rejected MCP registration for %s: %s"
                     % (name, output.splitlines()[-1] if output else "no output"))
