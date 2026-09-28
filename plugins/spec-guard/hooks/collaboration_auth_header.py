#!/usr/bin/env python3
"""Print the one private HTTP authorization header required by Codex MCP.

This helper is intended only for Codex's ``http_headers_helper`` setting. It
validates the runtime contract before reading the private token and writes the
header JSON to stdout; it never logs or persists the token.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import stat
import sys
from typing import Sequence

from collaboration_runtime import RuntimeContractError, default_config_dir, read_runtime_config


class TokenReadError(RuntimeContractError):
    """The private token changed or is unsafe while being read."""


def read_private_token(token_file: Path) -> str:
    """Read a token through a no-follow descriptor after validating its mode."""
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(token_file, flags)
    except OSError as error:
        raise TokenReadError("token file cannot be read safely") from error
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
            raise TokenReadError("token file changed while being read")
        with os.fdopen(descriptor, "r", encoding="utf-8", closefd=False) as handle:
            token = handle.read().strip()
    except (OSError, UnicodeDecodeError) as error:
        raise TokenReadError("token file cannot be read safely") from error
    finally:
        os.close(descriptor)
    if not token or any(character.isspace() or ord(character) < 0x20 for character in token):
        raise TokenReadError("token file contains an invalid bearer token")
    return token


def authorization_header(config_dir: Path) -> dict[str, str]:
    """Return the sole header Codex needs, without retaining token state."""
    config = read_runtime_config(config_dir)
    return {"Authorization": "Bearer " + read_private_token(config.token_file)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-dir", type=Path, default=default_config_dir())
    args = parser.parse_args(argv)
    try:
        print(json.dumps(authorization_header(args.config_dir), separators=(",", ":")))
    except RuntimeContractError as error:
        print("Spec Guard collaboration authentication is unavailable: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
