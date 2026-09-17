#!/usr/bin/env python3
"""Generate non-secret MCP configuration fragments for collaboration hosts.

The output intentionally contains only a loopback endpoint, fixed package
version, helper path, and environment-variable *names*. Provisioning commands
are responsible for writing a private runtime and applying host configuration.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Any, Sequence

from collaboration_runtime import RuntimeConfig, default_config_dir, read_runtime_config


MCP_SERVER_NAME = "spec-guard-collaboration"
CHANNEL_SERVER_NAME = "spec-guard-collaboration-channel"
TOKEN_ENV_VAR = "SPEC_GUARD_COLLABORATION_TOKEN"
CODEX_TABLE_NAME = MCP_SERVER_NAME.replace("-", "_")


def mcp_url(config: RuntimeConfig) -> str:
    return f"http://{config.host}:{config.port}/mcp"


def claude_mcp_config(config: RuntimeConfig, include_channel: bool = False) -> dict[str, Any]:
    """Return Claude Code's no-secret HTTP configuration.

    The caller must launch Claude with ``TOKEN_ENV_VAR`` set from the private
    token file. The optional channel is a preview wake mechanism, not required
    for mailbox delivery.
    """
    url = mcp_url(config)
    servers: dict[str, Any] = {
        MCP_SERVER_NAME: {
            "type": "http",
            "url": url,
            "headers": {"Authorization": f"Bearer ${{{TOKEN_ENV_VAR}}}"},
        }
    }
    if include_channel:
        servers[CHANNEL_SERVER_NAME] = {
            "command": "npx",
            "args": [
                "-y", "-p", f"{config.package}@{config.package_version}",
                "cross-agent-teams-channel", "--daemon-url", url,
            ],
            "env": {"CROSS_AGENT_TEAMS_MCP_TOKEN": f"${{{TOKEN_ENV_VAR}}}"},
        }
    return {"mcpServers": servers}


def codex_toml_fragment(
    config: RuntimeConfig, header_helper: Path, config_dir: Path | None = None
) -> str:
    """Return a safe Codex HTTP MCP fragment using the header helper command."""
    runtime_dir = default_config_dir() if config_dir is None else Path(config_dir)
    command = shlex.join([
        "python3", str(header_helper.resolve()), "--config-dir", str(runtime_dir),
    ])
    return "\n".join([
        f"[mcp_servers.{CODEX_TABLE_NAME}]",
        f"url = {json.dumps(mcp_url(config))}",
        f"http_headers_helper = {json.dumps(command)}",
        "",
    ])


def install_codex_config(config: RuntimeConfig, header_helper: Path, runtime_dir: Path,
                         codex_config: Path) -> None:
    """Append this plugin's no-secret table without replacing user configuration."""
    codex_config = Path(codex_config)
    if codex_config.exists():
        metadata = codex_config.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise ValueError("Codex configuration must be a non-symlink regular file")
        existing = codex_config.read_text(encoding="utf-8")
        mode = stat.S_IMODE(metadata.st_mode)
    else:
        codex_config.parent.mkdir(parents=True, mode=0o700)
        existing = ""
        mode = 0o600
    table = re.compile(rf"^\s*\[mcp_servers\.{re.escape(CODEX_TABLE_NAME)}\]\s*$", re.MULTILINE)
    if table.search(existing):
        raise ValueError("Codex collaboration MCP table already exists; refusing to overwrite it")
    addition = codex_toml_fragment(config, header_helper, runtime_dir)
    content = existing.rstrip() + ("\n\n" if existing.strip() else "") + addition
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", prefix="config-", suffix=".tmp",
        dir=codex_config.parent, delete=False,
    ) as handle:
        temporary = Path(handle.name)
        handle.write(content)
    temporary.chmod(mode)
    temporary.replace(codex_config)


def install_claude_config(
    stdio_helper: Path, runtime_dir: Path, claude_bin: str, python_executable: str,
    npx_executable: str,
) -> None:
    """Add a user-scoped Claude stdio MCP server with no secret configuration."""
    read_runtime_config(runtime_dir)
    helper = Path(stdio_helper).resolve()
    npx_path = Path(npx_executable).resolve()
    if not helper.is_file():
        raise ValueError("Claude stdio helper is unavailable")
    if not npx_path.is_absolute() or not npx_path.is_file():
        raise ValueError("Claude stdio npx executable is unavailable")
    existing = subprocess.run(
        [claude_bin, "mcp", "get", MCP_SERVER_NAME], check=False,
        capture_output=True, text=True,
    )
    if existing.returncode == 0:
        raise ValueError("Claude collaboration MCP server already exists; refusing to overwrite it")
    command = [
        claude_bin, "mcp", "add", "--scope", "user", MCP_SERVER_NAME, "--",
        python_executable, "-B", str(helper), "--config-dir", str(Path(runtime_dir)),
        "--npx", str(npx_path),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as error:
        diagnostic = error.stderr.strip() or error.stdout.strip() or "Claude rejected MCP configuration"
        raise ValueError("unable to install Claude collaboration MCP configuration: " + diagnostic) from error


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host", choices=("claude", "codex", "install-codex", "install-claude"))
    parser.add_argument("--config-dir", type=Path, default=default_config_dir())
    parser.add_argument("--include-channel", action="store_true")
    parser.add_argument("--header-helper", type=Path,
                        default=Path(__file__).with_name("collaboration_auth_header.py"))
    parser.add_argument("--codex-config", type=Path,
                        default=Path.home() / ".codex" / "config.toml")
    parser.add_argument("--claude-bin", default="claude")
    parser.add_argument("--python-executable", default=sys.executable)
    parser.add_argument("--npx", default=shutil.which("npx"))
    parser.add_argument("--stdio-helper", type=Path,
                        default=Path(__file__).with_name("collaboration_claude_stdio.py"))
    args = parser.parse_args(argv)
    config = read_runtime_config(args.config_dir)
    if args.host == "claude":
        print(json.dumps(claude_mcp_config(config, args.include_channel), indent=2, sort_keys=True))
    elif args.host == "codex":
        print(codex_toml_fragment(config, args.header_helper, args.config_dir), end="")
    elif args.host == "install-codex":
        install_codex_config(config, args.header_helper, args.config_dir, args.codex_config)
        print("Codex collaboration MCP configuration installed (no token stored).")
    else:
        if not args.npx:
            raise ValueError("Claude stdio npx executable is unavailable")
        install_claude_config(
            args.stdio_helper, args.config_dir, args.claude_bin, args.python_executable, args.npx,
        )
        print("Claude collaboration MCP configuration installed (no token stored).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
