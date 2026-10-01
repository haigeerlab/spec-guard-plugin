"""Generate explicit, no-secret Claude Code and Codex stdio MCP ledger adapters."""
import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

from host_config_removal import add_claude_server
from local_ledger_runtime import MCP_RELATIVE_PATH, default_runtime_dir, node_status, runtime_status


MCP_SERVER_NAME = "spec-guard-local-ledger"
CODEX_TABLE_NAME = MCP_SERVER_NAME.replace("-", "_")
# epiq@1.11.0 的完整 MCP 工具面；升级 Epiq 时必须重新核对这两组清单。
LEDGER_TOOLS = (
    "epiq_actor_assume", "epiq_board_create", "epiq_board_list", "epiq_board_title_edit",
    "epiq_contributor_email_link", "epiq_contributor_email_list", "epiq_contributor_email_suggest",
    "epiq_contributor_email_unlink", "epiq_contributor_list", "epiq_contributor_remove",
    "epiq_contributor_restore", "epiq_issue_assignee_add", "epiq_issue_assignee_remove",
    "epiq_issue_attachment_add", "epiq_issue_close", "epiq_issue_comment_add",
    "epiq_issue_comment_delete", "epiq_issue_comment_edit", "epiq_issue_create",
    "epiq_issue_description_edit", "epiq_issue_get", "epiq_issue_list", "epiq_issue_move",
    "epiq_issue_reopen", "epiq_issue_stats", "epiq_issue_tag_add", "epiq_issue_tag_remove",
    "epiq_issue_title_edit", "epiq_project_init", "epiq_skill_install", "epiq_state_get",
    "epiq_swimlane_create", "epiq_swimlane_delete", "epiq_swimlane_list", "epiq_swimlane_move",
    "epiq_swimlane_title_edit", "epiq_sync", "epiq_tag_remove", "epiq_tag_restore",
)
# 推送远端、改写仓库文件、删除项目级记录或处理邮箱：Claude 逐次询问，Codex 不暴露。
GATED_TOOLS = (
    "epiq_sync", "epiq_project_init", "epiq_skill_install",
    "epiq_issue_comment_delete", "epiq_swimlane_delete", "epiq_tag_remove", "epiq_contributor_remove",
    "epiq_contributor_email_link", "epiq_contributor_email_suggest", "epiq_contributor_email_unlink",
)
DAILY_TOOLS = tuple(tool for tool in LEDGER_TOOLS if tool not in GATED_TOOLS)


def mcp_command(runtime_dir: Path, node_executable: str) -> list[str]:
    runtime = runtime_status(runtime_dir)
    if runtime["state"] != "ready":
        raise ValueError("local-ledger runtime is not ready")
    node_path = Path(node_executable)
    if not node_path.is_absolute():
        raise ValueError("local-ledger Node executable must be an absolute path")
    return ["/bin/sh", "-c", 'umask 077; exec "$1" "$2"',
            MCP_SERVER_NAME, str(node_path), str(Path(runtime_dir) / MCP_RELATIVE_PATH)]


def codex_toml_fragment(runtime_dir: Path, node_executable: str) -> str:
    command = mcp_command(runtime_dir, node_executable)
    return "\n".join([
        f"[mcp_servers.{CODEX_TABLE_NAME}]",
        f"command = {json.dumps(command[0])}",
        "args = [" + ", ".join(json.dumps(argument) for argument in command[1:]) + "]",
        "enabled_tools = [" + ", ".join(json.dumps(tool) for tool in DAILY_TOOLS) + "]",
        "",
    ])


def claude_ask_rules() -> list[str]:
    return [f"mcp__{MCP_SERVER_NAME}__{tool}" for tool in GATED_TOOLS]


def install_claude_guard(settings: Path) -> None:
    """Merge ask rules for gated ledger tools, preserving every other Claude setting."""
    settings = Path(settings)
    if settings.exists() or settings.is_symlink():
        metadata = settings.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise ValueError("Claude settings must be a non-symlink regular file")
        current = settings.read_text(encoding="utf-8")
        mode = stat.S_IMODE(metadata.st_mode)
    else:
        settings.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        current, mode = "", 0o600
    try:
        value = json.loads(current) if current.strip() else {}
    except json.JSONDecodeError as error:
        raise ValueError("Claude settings must be valid JSON") from error
    if not isinstance(value, dict):
        raise ValueError("Claude settings must be a JSON object")
    permissions = value.setdefault("permissions", {})
    if not isinstance(permissions, dict):
        raise ValueError("Claude permissions must be a JSON object")
    ask = permissions.setdefault("ask", [])
    if not isinstance(ask, list) or not all(isinstance(rule, str) for rule in ask):
        raise ValueError("Claude ask rules must be a string list")
    ask.extend(rule for rule in claude_ask_rules() if rule not in ask)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix="settings-", suffix=".tmp",
                                     dir=settings.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    try:
        os.chmod(temporary, mode)
        temporary.replace(settings)
    finally:
        temporary.unlink(missing_ok=True)


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
        codex_config.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
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


def install_claude_config(claude_bin: str, runtime_dir: Path, node_executable: str,
                          settings: Path) -> None:
    """Install ask rules, then add an explicit user-scoped stdio server; never touch project files."""
    command = mcp_command(runtime_dir, node_executable)
    install_claude_guard(settings)
    add_claude_server(claude_bin, ["add", "--scope", "user", MCP_SERVER_NAME, "--", *command],
                      MCP_SERVER_NAME)


def _node_path() -> str:
    node = node_status()
    if node["state"] != "ready":
        raise ValueError("local-ledger Node runtime is unavailable")
    return node["path"]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host", choices=("claude", "codex", "install-claude", "install-codex",
                                         "install-claude-guard"))
    parser.add_argument("--runtime-dir", type=Path, default=default_runtime_dir())
    parser.add_argument("--codex-config", type=Path, default=Path.home() / ".codex" / "config.toml")
    parser.add_argument("--claude-bin", default="claude")
    parser.add_argument("--claude-settings", type=Path, default=Path.home() / ".claude" / "settings.json")
    parser.add_argument("--confirm-install", action="store_true",
                        help="allow the selected install command to write host configuration")
    args = parser.parse_args(argv)
    try:
        node_path = "" if args.host == "install-claude-guard" else _node_path()
        if args.host == "codex":
            print(codex_toml_fragment(args.runtime_dir, node_path), end="")
        elif args.host == "claude":
            command = mcp_command(args.runtime_dir, node_path)
            print(json.dumps({"command": command[0], "args": command[1:],
                              "permissions": {"ask": claude_ask_rules()}}, indent=2))
        elif not args.confirm_install:
            print("configuration-confirmation-required: rerun with --confirm-install to write host configuration")
            return 1
        elif args.host == "install-claude-guard":
            install_claude_guard(args.claude_settings)
            print("Claude local-ledger ask rules installed for gated tools.")
        elif args.host == "install-codex":
            install_codex_config(args.codex_config, args.runtime_dir, node_path)
            print("Codex local-ledger MCP configuration installed (no secret stored).")
        else:
            install_claude_config(args.claude_bin, args.runtime_dir, node_path, args.claude_settings)
            print("Claude local-ledger ask rules and MCP configuration installed (no secret stored).")
    except (OSError, ValueError) as error:
        print("local-ledger adapter unavailable: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
