"""Generate explicit, no-secret Claude Code and Codex stdio MCP ledger adapters."""
import argparse
import json
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

from local_ledger_runtime import MCP_RELATIVE_PATH, default_runtime_dir, node_status, runtime_status


MCP_SERVER_NAME = "spec-guard-local-ledger"
CODEX_TABLE_NAME = MCP_SERVER_NAME.replace("-", "_")


def mcp_command(runtime_dir: Path, node_executable: str) -> list[str]:
    runtime = runtime_status(runtime_dir)
    if runtime["state"] != "ready":
        raise ValueError("local-ledger runtime is not ready")
    node_path = Path(node_executable)
    if not node_path.is_absolute():
        raise ValueError("local-ledger Node executable must be an absolute path")
    return [str(node_path), str(Path(runtime_dir) / MCP_RELATIVE_PATH)]


def codex_toml_fragment(runtime_dir: Path, node_executable: str) -> str:
    command = mcp_command(runtime_dir, node_executable)
    return "\n".join([
        f"[mcp_servers.{CODEX_TABLE_NAME}]",
        f"command = {json.dumps(command[0])}",
        "args = [" + ", ".join(json.dumps(argument) for argument in command[1:]) + "]",
        "",
    ])


def install_codex_config(codex_config: Path, runtime_dir: Path, node_executable: str) -> None:
    """Append the managed table without changing any unrelated Codex configuration."""
    codex_config = Path(codex_config)
    if codex_config.exists():
        metadata = codex_config.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise ValueError("Codex configuration must be a non-symlink regular file")
        existing = codex_config.read_text(encoding="utf-8")
        mode = stat.S_IMODE(metadata.st_mode)
    else:
        codex_config.parent.mkdir(parents=True, mode=0o700)
        existing, mode = "", 0o600
    table = re.compile(rf"^\s*\[mcp_servers\.{re.escape(CODEX_TABLE_NAME)}\]\s*$", re.MULTILINE)
    if table.search(existing):
        raise ValueError("Codex local-ledger MCP table already exists; refusing to overwrite it")
    content = existing.rstrip() + ("\n\n" if existing.strip() else "") + codex_toml_fragment(runtime_dir, node_executable)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix="config-", suffix=".tmp",
                                     dir=codex_config.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(content)
    temporary.chmod(mode)
    temporary.replace(codex_config)


def install_claude_config(claude_bin: str, runtime_dir: Path, node_executable: str) -> None:
    """Add an explicit user-scoped stdio server without touching project configuration."""
    command = mcp_command(runtime_dir, node_executable)
    existing = subprocess.run([claude_bin, "mcp", "get", MCP_SERVER_NAME], check=False,
                              capture_output=True, text=True)
    if existing.returncode == 0:
        raise ValueError("Claude local-ledger MCP server already exists; refusing to overwrite it")
    try:
        subprocess.run([claude_bin, "mcp", "add", "--scope", "user", MCP_SERVER_NAME, "--", *command],
                       check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as error:
        raise ValueError("unable to install Claude local-ledger MCP configuration") from error


def _node_path() -> str:
    node = node_status()
    if node["state"] != "ready":
        raise ValueError("local-ledger Node runtime is unavailable")
    return node["path"]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host", choices=("claude", "codex", "install-claude", "install-codex"))
    parser.add_argument("--runtime-dir", type=Path, default=default_runtime_dir())
    parser.add_argument("--codex-config", type=Path, default=Path.home() / ".codex" / "config.toml")
    parser.add_argument("--claude-bin", default="claude")
    parser.add_argument("--confirm-install", action="store_true",
                        help="allow the selected install command to write host configuration")
    args = parser.parse_args(argv)
    try:
        node_path = _node_path()
        if args.host == "codex":
            print(codex_toml_fragment(args.runtime_dir, node_path), end="")
        elif args.host == "claude":
            print(json.dumps({"command": node_path, "args": [str(args.runtime_dir / MCP_RELATIVE_PATH)]}, indent=2))
        elif not args.confirm_install:
            print("configuration-confirmation-required: rerun with --confirm-install to write host configuration")
            return 1
        elif args.host == "install-codex":
            install_codex_config(args.codex_config, args.runtime_dir, node_path)
            print("Codex local-ledger MCP configuration installed (no secret stored).")
        else:
            install_claude_config(args.claude_bin, args.runtime_dir, node_path)
            print("Claude local-ledger MCP configuration installed (no secret stored).")
    except ValueError as error:
        print("local-ledger adapter unavailable: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
