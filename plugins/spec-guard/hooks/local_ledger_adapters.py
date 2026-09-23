"""Generate explicit, no-secret Claude Code and Codex stdio MCP ledger adapters."""
import json
from pathlib import Path
import re
import stat
import subprocess
import tempfile

from local_ledger_runtime import MCP_RELATIVE_PATH, runtime_status


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
