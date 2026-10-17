#!/usr/bin/env python3
"""Read the hosts' own plugin records to see whether a sibling plugin is installed and enabled.

Reads local files only: no subprocess, no network, writes nothing.  `claude_plugin_root` is shared with
`agent_relay_probe.py`, which reports read failures as `unknown`; `delegate_enabled` runs inside the phase
hint on every prompt (delegate-review-hint), so it answers False whenever it cannot tell.
"""
import json
import os
import re
import subprocess
from pathlib import Path

TIMEOUT_SECONDS = 10


class RecordError(Exception):
    """A plugin record exists but cannot be read."""


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        raise RecordError(f"cannot read {path}: {exc}") from exc


def main_checkout_local_settings(project):
    """Claude Code keeps a linked git worktree's local settings in its main checkout."""
    try:
        done = subprocess.run(["git", "-C", str(project), "rev-parse", "--path-format=absolute",
                               "--git-common-dir", "--git-dir"], stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ()
    lines = done.stdout.splitlines()
    if done.returncode != 0 or len(lines) != 2 or lines[0] == lines[1]:
        return ()
    return (Path(lines[0]).parent / ".claude" / "settings.local.json",)


def main_checkout_local_settings_from_files(project):
    """The same answer as `main_checkout_local_settings`, read from the worktree's `.git` file without git."""
    try:
        text = (project / ".git").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ()  # a main checkout (`.git` is a directory) or not a repository
    if not text.startswith("gitdir:"):
        return ()
    gitdir = (project / text[len("gitdir:"):].strip()).resolve()
    try:
        common = (gitdir / (gitdir / "commondir").read_text(encoding="utf-8").strip()).resolve()
    except (OSError, UnicodeError):
        return ()
    return (common.parent / ".claude" / "settings.local.json",) if common != gitdir else ()


def claude_plugin_root(project, plugin, local_settings=main_checkout_local_settings):
    """Plugin root of an enabled `plugin` for this project in Claude Code, or None; RecordError when unreadable."""
    home = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    record = read_json(home / "plugins" / "installed_plugins.json")
    if record is None:
        return None
    if not isinstance(record, dict) or not isinstance(record.get("plugins"), dict):
        raise RecordError("installed_plugins.json has no plugins table")
    enabled = {}
    for settings in (home / "settings.json", project / ".claude" / "settings.json",
                     *local_settings(project), project / ".claude" / "settings.local.json"):
        data = read_json(settings)
        if isinstance(data, dict) and isinstance(data.get("enabledPlugins"), dict):
            enabled.update(data["enabledPlugins"])
    for key, installs in record["plugins"].items():
        if key.split("@", 1)[0] != plugin or enabled.get(key) is not True:
            continue
        for install in installs if isinstance(installs, list) else []:
            if not isinstance(install, dict) or not install.get("installPath"):
                continue
            scoped = install.get("projectPath")
            if scoped and Path(scoped).resolve() != project.resolve():
                continue
            return Path(install["installPath"])
    return None


_TABLE = re.compile(r'^\s*\[\s*plugins\.\s*"([^"@]+)@([^"]+)"\s*\]\s*(?:#.*)?$')
_ENABLED_TRUE = re.compile(r"^\s*enabled\s*=\s*true\s*(?:#.*)?$")


def codex_plugin_cache(plugin):
    """Codex's cache directory for an enabled `plugin` (`plugins/cache/<market>/<plugin>`), or None; never raises."""
    home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    try:
        lines = (home / "config.toml").read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return None
    market = None
    for line in lines:
        if line.lstrip().startswith("["):
            match = _TABLE.match(line)
            market = match.group(2) if match and match.group(1) == plugin else None
        elif market and _ENABLED_TRUE.match(line):
            cache = home / "plugins" / "cache" / market / plugin
            return cache if cache.is_dir() else None
    return None


def codex_plugin_enabled(plugin):
    """True only when Codex's config enables `plugin` and its cached copy exists; never raises."""
    return codex_plugin_cache(plugin) is not None


def delegate_enabled(project, host):
    """Whether delegate is installed and enabled for this host; False when it cannot tell."""
    try:
        if host == "codex":
            return codex_plugin_enabled("delegate")
        # The phase hint runs every prompt, so the main checkout is found from files, not by running git.
        return claude_plugin_root(Path(project), "delegate", main_checkout_local_settings_from_files) is not None
    except Exception:  # noqa: BLE001 -- a hint is optional; any failure means no hint
        return False


# delegate-interface-check: delegate publishes interface.json in its plugin root; read it only when a hint is due.
DELEGATE_DEFAULTS = {"review": "/delegate:review", "doctor": "/delegate:doctor"}
_DELEGATE_COMMAND = re.compile(r"/delegate:[a-z][a-z-]*")
_INTERFACE = re.compile(r"(\d+)\.(\d+)")


def _delegate_root(project, host):
    """(enabled, plugin root or None).  Codex: the one version directory in the cache, else None."""
    if host == "codex":
        cache = codex_plugin_cache("delegate")
        if cache is None:
            return False, None
        versions = [path for path in cache.iterdir() if path.is_dir()]
        if not versions:
            return False, None
        return True, versions[0] if len(versions) == 1 else None
    root = claude_plugin_root(Path(project), "delegate", main_checkout_local_settings_from_files)
    return root is not None, root


def delegate_review_entry(project, host):
    """Commands for the external-review hint, or None when no hint is due.

    None: delegate not installed or enabled, or its interface major version is outside >=1.0,<2.0.  A missing or
    unreadable interface.json keeps the defaults: neither means delegate is not installed.  Only command names
    matching `/delegate:<lowercase-and-hyphens>` are taken from the file.
    """
    try:
        enabled, root = _delegate_root(project, host)
    except Exception:  # noqa: BLE001 -- a hint is optional; any failure means no hint
        return None
    if not enabled:
        return None
    default = dict(DELEGATE_DEFAULTS, source="default")
    try:
        declared = json.loads((root / "interface.json").read_text(encoding="utf-8")) if root else None
    except (OSError, ValueError, UnicodeError):
        return default
    version = _INTERFACE.fullmatch(str(declared.get("interface", ""))) if isinstance(declared, dict) else None
    if version is None:
        return default
    if int(version.group(1)) != 1:
        return None
    entry = dict(default, source="interface")
    for key in DELEGATE_DEFAULTS:
        section = declared.get(key)
        command = section.get("command") if isinstance(section, dict) else None
        if isinstance(command, str) and _DELEGATE_COMMAND.fullmatch(command):
            entry[key] = command
    return entry
