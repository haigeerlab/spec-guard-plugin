#!/usr/bin/env python3
"""Generate non-secret MCP configuration fragments for collaboration hosts.

The output intentionally contains only a loopback endpoint, fixed package
version, helper path, and environment-variable *names*. Provisioning commands
are responsible for writing a private runtime and applying host configuration.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import sys
import tempfile
from typing import Any, Sequence

from collaboration_runtime import RuntimeConfig, default_config_dir, read_runtime_config
from host_config_removal import add_claude_server, remove_claude_server, remove_codex_table


MCP_SERVER_NAME = "spec-guard-collaboration"
TOKEN_ENV_VAR = "SPEC_GUARD_COLLABORATION_TOKEN"
CODEX_TABLE_NAME = MCP_SERVER_NAME.replace("-", "_")


def mcp_url(config: RuntimeConfig) -> str:
    return f"http://{config.host}:{config.port}/mcp"


def claude_mcp_config(config: RuntimeConfig) -> dict[str, Any]:
    """Return Claude Code's no-secret HTTP configuration.

    The caller must launch Claude with ``TOKEN_ENV_VAR`` set from the private
    token file.
    """
    return {"mcpServers": {
        MCP_SERVER_NAME: {
            "type": "http",
            "url": mcp_url(config),
            "headers": {"Authorization": f"Bearer ${{{TOKEN_ENV_VAR}}}"},
        }
    }}


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
        codex_config.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
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
    add_claude_server(claude_bin, [
        "add", "--scope", "user", MCP_SERVER_NAME, "--",
        python_executable, "-B", str(helper), "--config-dir", str(Path(runtime_dir)),
        "--npx", str(npx_path),
    ], MCP_SERVER_NAME)


def _uninstall(args: argparse.Namespace) -> int:
    """Remove only the entry this adapter installed; an edited entry is left for the user."""
    if not args.confirm_uninstall:
        print("uninstall-confirmation-required: rerun with --confirm-uninstall")
        return 1
    try:
        if args.host == "uninstall-claude":
            state = remove_claude_server(args.claude_bin, MCP_SERVER_NAME)
        else:
            # 用安装时的同一套参数重建片段；原片段若来自另一份源码，传入当时的 --header-helper。
            fragment = codex_toml_fragment(read_runtime_config(args.config_dir),
                                           args.header_helper, args.config_dir)
            state = remove_codex_table(args.codex_config, fragment, CODEX_TABLE_NAME)
    except ValueError as error:
        print("collaboration uninstall stopped: " + str(error), file=sys.stderr)
        return 1
    print("XATS collaboration MCP entry %s; restart the client to apply." % state)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host", choices=("claude", "codex", "install-codex", "install-claude",
                                         "uninstall-codex", "uninstall-claude"))
    parser.add_argument("--config-dir", type=Path, default=default_config_dir())
    parser.add_argument("--header-helper", type=Path,
                        default=Path(__file__).with_name("collaboration_auth_header.py"))
    parser.add_argument("--codex-config", type=Path,
                        default=Path.home() / ".codex" / "config.toml")
    parser.add_argument("--claude-bin", default="claude")
    parser.add_argument("--python-executable", default=sys.executable)
    parser.add_argument("--npx", default=shutil.which("npx"))
    parser.add_argument("--stdio-helper", type=Path,
                        default=Path(__file__).with_name("collaboration_claude_stdio.py"))
    parser.add_argument("--confirm-uninstall", action="store_true",
                        help="allow an uninstall command to remove host configuration")
    args = parser.parse_args(argv)
    if args.host.startswith("uninstall-"):
        return _uninstall(args)
    config = read_runtime_config(args.config_dir)
    if args.host == "claude":
        print(json.dumps(claude_mcp_config(config), indent=2, sort_keys=True))
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
