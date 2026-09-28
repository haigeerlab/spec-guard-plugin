#!/usr/bin/env python3
"""Launch Claude Code with an ephemeral, token-free collaboration MCP config."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Sequence
from uuid import uuid4

from collaboration_adapters import TOKEN_ENV_VAR, claude_mcp_config
from collaboration_auth_header import read_private_token
from collaboration_runtime import RuntimeContractError, default_config_dir, read_runtime_config


def write_ephemeral_mcp_config(config_dir: Path) -> Path:
    """Create a private config containing only endpoint and env-variable names."""
    config = read_runtime_config(config_dir)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", prefix="claude-mcp-", suffix=".json",
        dir=config_dir, delete=False,
    ) as handle:
        json.dump(claude_mcp_config(config), handle, separators=(",", ":"))
        handle.write("\n")
        path = Path(handle.name)
    path.chmod(0o600)
    return path


def build_claude_command(
    claude_bin: str, config_path: Path, extra_args: Sequence[str]
) -> list[str]:
    """Build a command that cannot be overridden with another MCP configuration.

    Development channels stay refused: Spec Guard does not load a downloaded Channel.
    """
    forbidden = {"--mcp-config", "--dangerously-load-development-channels"}
    if any(argument in forbidden or any(argument.startswith(option + "=") for option in forbidden)
           for argument in extra_args):
        raise ValueError("pass MCP options to the Spec Guard wrapper, not directly to Claude")
    return [claude_bin, "--mcp-config", str(config_path), *extra_args]


def launch_claude(config_dir: Path, claude_bin: str, extra_args: Sequence[str]) -> int:
    """Run Claude with a child-only token and remove the temporary config afterward."""
    config = read_runtime_config(config_dir)
    token = read_private_token(config.token_file)
    temporary_config = write_ephemeral_mcp_config(config_dir)
    environment = os.environ.copy()
    environment[TOKEN_ENV_VAR] = token
    try:
        command = build_claude_command(claude_bin, temporary_config, extra_args)
        return subprocess.run(command, env=environment, check=False).returncode
    finally:
        try:
            temporary_config.unlink()
        except FileNotFoundError:
            pass


def build_tmux_command(
    config_dir: Path, claude_bin: str, extra_args: Sequence[str], session_name: str
) -> list[str]:
    """Use tmux's direct argv form (https://man.openbsd.org/tmux#new-session)."""
    return [
        "tmux", "new-session", "-s", session_name, "-c", str(Path.cwd()),
        sys.executable, "-B", str(Path(__file__).resolve()),
        "--config-dir", str(config_dir), "--claude-bin", claude_bin,
        "--tmux-wake", "--", *extra_args,
    ]


def launch_tmux_claude(config_dir: Path, claude_bin: str, extra_args: Sequence[str]) -> int:
    """Enter one tmux pane, then launch Claude through the existing private MCP path."""
    if os.environ.get("TMUX_PANE"):
        return launch_claude(config_dir, claude_bin, extra_args)
    if shutil.which("tmux") is None:
        raise ValueError("tmux executable not found")
    if not sys.stdin.isatty():
        raise ValueError("tmux wake requires an interactive terminal")
    command = build_tmux_command(config_dir, claude_bin, extra_args, "spec-guard-" + uuid4().hex[:12])
    return subprocess.run(command, check=False).returncode


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-dir", type=Path, default=default_config_dir())
    parser.add_argument("--claude-bin", default="claude")
    parser.add_argument("--tmux-wake", action="store_true",
                        help="explicitly launch Claude Code CLI inside a tmux pane for XATS inbox hints")
    parser.add_argument("claude_args", nargs=argparse.REMAINDER,
                        help="arguments forwarded to Claude; place them after --")
    args = parser.parse_args(argv)
    forwarded = args.claude_args[1:] if args.claude_args[:1] == ["--"] else args.claude_args
    try:
        if args.tmux_wake:
            return launch_tmux_claude(args.config_dir, args.claude_bin, forwarded)
        return launch_claude(args.config_dir, args.claude_bin, forwarded)
    except (RuntimeContractError, ValueError) as error:
        print("Spec Guard collaboration Claude launcher is unavailable: " + str(error), file=os.sys.stderr)
        return 1
    except FileNotFoundError:
        print("Spec Guard collaboration Claude launcher is unavailable: claude executable not found",
              file=os.sys.stderr)
        return 127


if __name__ == "__main__":
    raise SystemExit(main())
