#!/usr/bin/env python3
"""Expose the private collaboration runtime to Claude Code over stdio.

Claude launches this program from its user-scoped MCP configuration.  The
program obtains the bearer token only from Spec Guard's private runtime, then
execs a pinned open-source stdio-to-HTTP bridge.  Neither the Claude
configuration nor this process's argv contains the token.
"""
import argparse
import os
from pathlib import Path
import sys
from typing import Sequence

from collaboration_auth_header import read_private_token
from collaboration_runtime import RuntimeContractError, default_config_dir, read_runtime_config


MCP_REMOTE_PACKAGE = "mcp-remote"
MCP_REMOTE_VERSION = "0.1.38"
MCP_REMOTE_AUTH_ENV_VAR = "SPEC_GUARD_COLLABORATION_AUTH_HEADER"


def mcp_remote_command(config_dir: Path, npx_executable: str) -> tuple[list[str], dict[str, str]]:
    """Return a pinned bridge command and child environment without an argv secret."""
    config = read_runtime_config(config_dir)
    npx_path = Path(npx_executable)
    if not npx_path.is_absolute():
        raise RuntimeContractError("Claude stdio npx path must be absolute")
    if not npx_path.is_file():
        raise RuntimeContractError("Claude stdio npx executable is unavailable")
    token = read_private_token(config.token_file)
    environment = os.environ.copy()
    environment[MCP_REMOTE_AUTH_ENV_VAR] = "Bearer " + token
    return [
        str(npx_path), "--yes", "--package", f"{MCP_REMOTE_PACKAGE}@{MCP_REMOTE_VERSION}",
        "mcp-remote", f"http://{config.host}:{config.port}/mcp",
        "--transport", "http-only",
        "--header", f"Authorization:${{{MCP_REMOTE_AUTH_ENV_VAR}}}",
    ], environment


def serve(config_dir: Path, npx_executable: str) -> None:
    """Replace this process with the bridge after private configuration checks."""
    command, environment = mcp_remote_command(config_dir, npx_executable)
    os.execvpe(command[0], command, environment)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-dir", type=Path, default=default_config_dir())
    parser.add_argument("--npx", required=True)
    args = parser.parse_args(argv)
    try:
        serve(args.config_dir, args.npx)
    except RuntimeContractError as error:
        print("Spec Guard collaboration Claude stdio bridge is unavailable: " + str(error),
              file=sys.stderr)
        return 1
    raise AssertionError("stdio bridge exec unexpectedly returned")


if __name__ == "__main__":
    raise SystemExit(main())
