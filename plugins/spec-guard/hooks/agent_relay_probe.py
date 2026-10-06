#!/usr/bin/env python3
"""Report whether the agent-relay plugin can serve Spec Guard's collaboration steps.

This is Spec Guard's only code-level entry into collaboration (docs/collaboration-interface.md
section 11). It reads the host's own plugin record and agent-relay's `interface.json`, takes no message
content, writes nothing, never touches the network, and always exits 0 with one JSON object:

    {"state": "ready" | "not-installed" | "incompatible" | "runtime-not-ready" | "unknown",
     "interface": "<x.y>" | null, "required": ">=1.0,<2.0", "message": "<user-facing text>"}

A probe that cannot read its sources reports `unknown`, never `not-installed`: a failed check is not
evidence about the plugin. Phase injection never calls this script.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

PLUGIN = "agent-relay"
REQUIRED = ">=1.0,<2.0"
MIN_VERSION, MAX_VERSION = (1, 0), (2, 0)
TIMEOUT_SECONDS = 10
NOT_INSTALLED = (
    "协作能力已移到独立插件 agent-relay，当前未安装。工作流不受影响。安装与旧状态迁移见\n"
    "`docs/migrations/2026-10-07-collaboration-split.md`。"
)


class ProbeFailure(Exception):
    """The probe could not read a source it needs; the plugin state is unknown."""


def result(state, interface=None, message=""):
    return {"state": state, "interface": interface, "required": REQUIRED, "message": message}


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        raise ProbeFailure(f"cannot read {path}: {exc}") from exc


def claude_root(project):
    """Plugin root of an enabled agent-relay for this project in Claude Code, or None."""
    home = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    record = read_json(home / "plugins" / "installed_plugins.json")
    if record is None:
        return None
    if not isinstance(record, dict) or not isinstance(record.get("plugins"), dict):
        raise ProbeFailure("installed_plugins.json has no plugins table")
    enabled = {}
    for settings in (home / "settings.json", project / ".claude" / "settings.json",
                     project / ".claude" / "settings.local.json"):
        data = read_json(settings)
        if isinstance(data, dict) and isinstance(data.get("enabledPlugins"), dict):
            enabled.update(data["enabledPlugins"])
    for key, installs in record["plugins"].items():
        if key.split("@", 1)[0] != PLUGIN or enabled.get(key) is not True:
            continue
        for install in installs if isinstance(installs, list) else []:
            if not isinstance(install, dict) or not install.get("installPath"):
                continue
            scoped = install.get("projectPath")
            if scoped and Path(scoped).resolve() != project.resolve():
                continue
            return Path(install["installPath"])
    return None


def codex_root():
    """Plugin root of an installed and enabled agent-relay in Codex, or None."""
    try:
        done = subprocess.run(["codex", "plugin", "list", "--json"], stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProbeFailure(f"codex plugin list failed: {exc}") from exc
    if done.returncode != 0:
        raise ProbeFailure(f"codex plugin list exited {done.returncode}")
    try:
        plugins = json.loads(done.stdout).get("installed")
    except (ValueError, AttributeError) as exc:
        raise ProbeFailure("codex plugin list printed no JSON object") from exc
    if not isinstance(plugins, list):
        raise ProbeFailure("codex plugin list has no installed list")
    for plugin in plugins:
        if (isinstance(plugin, dict) and plugin.get("name") == PLUGIN
                and plugin.get("installed") is True and plugin.get("enabled") is True):
            source = plugin.get("source")
            path = source.get("path") if isinstance(source, dict) else None
            if not isinstance(path, str) or not path:
                raise ProbeFailure("codex lists agent-relay without a source path")
            return Path(path)
    return None


def parse_version(text):
    try:
        major, minor = (int(part) for part in text.split("."))
        return major, minor
    except (AttributeError, ValueError):
        return None


def runtime_status(root, command):
    """Run agent-relay's declared status command; return (ready, setup)."""
    if not (isinstance(command, list) and command and all(isinstance(arg, str) for arg in command)):
        raise ProbeFailure("interface.json status is not an argument list")
    try:
        done = subprocess.run(command, cwd=root, stdin=subprocess.DEVNULL, capture_output=True,
                              text=True, timeout=TIMEOUT_SECONDS, check=False)
        report = json.loads(done.stdout)
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        raise ProbeFailure(f"agent-relay status failed: {exc}") from exc
    if not isinstance(report, dict) or not isinstance(report.get("ready"), bool):
        raise ProbeFailure("agent-relay status printed no ready flag")
    setup = report.get("setup") if isinstance(report.get("setup"), str) else ""
    return report["ready"], setup


def probe(host, project):
    try:
        root = claude_root(project) if host == "claude" else codex_root()
        if root is None:
            return result("not-installed", message=NOT_INSTALLED)
        declared = read_json(root / "interface.json")
        found = declared.get("interface") if isinstance(declared, dict) else None
        version = parse_version(found)
        if version is None or not MIN_VERSION <= version < MAX_VERSION:
            shown = found if isinstance(found, str) else "缺失"
            return result("incompatible", found if isinstance(found, str) else None,
                          f"已安装的 agent-relay 接口版本为 {shown}，Spec Guard 需要 {REQUIRED}。"
                          "工作流不受影响；协作步骤会跳过，更新 agent-relay 后可用。")
        if "status" in declared:
            ready, setup = runtime_status(root, declared["status"])
            if not ready:
                hint = f"：{setup}" if setup else ""
                return result("runtime-not-ready", found,
                              f"agent-relay 已安装，但信箱运行时尚未就绪。请用 agent-relay 自己的初始化命令{hint}。"
                              "Spec Guard 不会代为安装。")
        return result("ready", found, f"agent-relay 已就绪（接口 {found}）。")
    except ProbeFailure as exc:
        return result("unknown", message=f"无法检查 agent-relay 的状态（{exc}）。这不代表它未安装。")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", required=True, choices=("claude", "codex"))
    parser.add_argument("--project", default=os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    args = parser.parse_args(argv)
    print(json.dumps(probe(args.host, Path(args.project)), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
