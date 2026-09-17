#!/usr/bin/env python3
"""Launch Claude Code with an ephemeral, token-free collaboration MCP config."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Sequence

from collaboration_adapters import CHANNEL_SERVER_NAME, TOKEN_ENV_VAR, claude_mcp_config
from collaboration_auth_header import read_private_token
from collaboration_runtime import RuntimeContractError, default_config_dir, read_runtime_config


def write_ephemeral_mcp_config(config_dir: Path, include_channel: bool) -> Path:
    """Create a private config containing only endpoint and env-variable names."""
    config = read_runtime_config(config_dir)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", prefix="claude-mcp-", suffix=".json",
        dir=config_dir, delete=False,
    ) as handle:
        json.dump(claude_mcp_config(config, include_channel), handle, separators=(",", ":"))
        handle.write("\n")
        path = Path(handle.name)
    path.chmod(0o600)
    return path


def build_claude_command(
    claude_bin: str, config_path: Path, include_channel: bool, extra_args: Sequence[str]
) -> list[str]:
    """Build a command that cannot be overridden with another MCP configuration."""
    forbidden = {"--mcp-config", "--dangerously-load-development-channels"}
    if any(argument in forbidden for argument in extra_args):
        raise ValueError("pass MCP options to the Spec Guard wrapper, not directly to Claude")
    command = [claude_bin, "--mcp-config", str(config_path)]
    if include_channel:
        command.extend([
            "--dangerously-load-development-channels", f"server:{CHANNEL_SERVER_NAME}",
        ])
    return command + list(extra_args)


def launch_claude(
    config_dir: Path, claude_bin: str, include_channel: bool, extra_args: Sequence[str]
) -> int:
    """Run Claude with a child-only token and remove the temporary config afterward."""
    config = read_runtime_config(config_dir)
    token = read_private_token(config.token_file)
    temporary_config = write_ephemeral_mcp_config(config_dir, include_channel)
    environment = os.environ.copy()
    environment[TOKEN_ENV_VAR] = token
    try:
        command = build_claude_command(claude_bin, temporary_config, include_channel, extra_args)
        return subprocess.run(command, env=environment, check=False).returncode
    finally:
        try:
            temporary_config.unlink()
        except FileNotFoundError:
            pass


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-dir", type=Path, default=default_config_dir())
    parser.add_argument("--claude-bin", default="claude")
    parser.add_argument("--enable-channel-wake", action="store_true",
                        help="explicitly enable Claude Code's preview channel loader")
    parser.add_argument("claude_args", nargs=argparse.REMAINDER,
                        help="arguments forwarded to Claude; place them after --")
    args = parser.parse_args(argv)
    forwarded = args.claude_args[1:] if args.claude_args[:1] == ["--"] else args.claude_args
    try:
        return launch_claude(args.config_dir, args.claude_bin, args.enable_channel_wake, forwarded)
    except (RuntimeContractError, ValueError) as error:
        print("Spec Guard collaboration Claude launcher is unavailable: " + str(error), file=os.sys.stderr)
        return 1
    except FileNotFoundError:
        print("Spec Guard collaboration Claude launcher is unavailable: claude executable not found",
              file=os.sys.stderr)
        return 127


if __name__ == "__main__":
    raise SystemExit(main())
