#!/usr/bin/env python3
"""Read and validate the private, loopback-only collaboration runtime contract.

The mutating commands run only when an operator invokes them. They never place a
token in an argv, project file, or diagnostic output.
"""
import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import plistlib
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from typing import Any, Sequence
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen
from urllib.request import Request
from uuid import UUID


PACKAGE_NAME = "cross-agent-teams-mcp"
PACKAGE_VERSION = "0.8.6"
# XATS 0.8.6 reports this separate server protocol value from /health.
HEALTH_PROTOCOL_VERSION = "0.1.0"
# XATS requires a team string for its storage/query model. Spec Guard keeps one
# fixed local namespace so project paths never become a routing boundary.
LOCAL_NAMESPACE = "spec-guard-local"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9100
CONFIG_FILENAME = "runtime.json"
TOKEN_FILENAME = "token"
DATABASE_FILENAME = "messages.sqlite"
PID_FILENAME = "daemon.pid"
LAUNCH_AGENT_LABEL = "com.specguard.collaboration"
LAUNCH_AGENT_FILENAME = LAUNCH_AGENT_LABEL + ".plist"
DAEMON_STDOUT_FILENAME = "daemon.stdout.log"
DAEMON_STDERR_FILENAME = "daemon.stderr.log"
_TOKEN_FILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class RuntimeContractError(ValueError):
    """A private runtime configuration is missing or unsafe."""


@dataclass(frozen=True)
class RuntimeConfig:
    host: str
    port: int
    package: str
    package_version: str
    token_file: Path


def runtime_contract() -> dict[str, Any]:
    """Return only non-secret facts required to provision the audited runtime."""
    return {
        "package": PACKAGE_NAME,
        "packageVersion": PACKAGE_VERSION,
        "host": DEFAULT_HOST,
        "defaultPort": DEFAULT_PORT,
        "localNamespace": LOCAL_NAMESPACE,
        "tokenFileMode": "0600",
    }


def default_config_dir() -> Path:
    return Path.home() / ".spec-guard" / "collaboration"


def launch_agent_plist(
    config_dir: Path, runtime_script: Path, python_executable: str, npx_executable: str,
    tmux_executable: str | None = None,
) -> dict[str, Any]:
    """Build the non-secret, per-user launchd contract for the runtime."""
    config_dir = Path(config_dir)
    path_entries = [str(Path(npx_executable).parent)]
    if tmux_executable is not None:
        if not Path(tmux_executable).is_absolute() or any(
            character == ":" or ord(character) < 32 for character in tmux_executable
        ):
            raise RuntimeContractError("tmux path must be absolute and contain no PATH separators")
        path_entries.append(str(Path(tmux_executable).parent))
    path_entries.extend(("/usr/bin", "/bin", "/usr/sbin", "/sbin"))
    return {
        "Label": LAUNCH_AGENT_LABEL,
        "ProgramArguments": [
            python_executable, str(Path(runtime_script)), "serve", "--config-dir", str(config_dir),
            "--npx", npx_executable,
        ],
        "RunAtLoad": True,
        "KeepAlive": True,
        "EnvironmentVariables": {
            "PATH": ":".join(dict.fromkeys(path_entries)),
        },
        "StandardOutPath": str(config_dir / DAEMON_STDOUT_FILENAME),
        "StandardErrorPath": str(config_dir / DAEMON_STDERR_FILENAME),
    }


def _write_private_json(path: Path, value: dict[str, Any]) -> None:
    """Atomically write a non-secret JSON file in an already-private directory."""
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", prefix="runtime-", suffix=".tmp",
        dir=path.parent, delete=False,
    ) as handle:
        temporary = Path(handle.name)
        handle.write(json.dumps(value, sort_keys=True) + "\n")
    temporary.chmod(0o600)
    temporary.replace(path)


def initialize_runtime(config_dir: Path, port: int = DEFAULT_PORT) -> RuntimeConfig:
    """Create a fresh private runtime directory; never overwrite an existing one."""
    config_dir = Path(config_dir)
    if config_dir.exists() or config_dir.is_symlink():
        raise RuntimeContractError("runtime configuration already exists")
    if not isinstance(port, int) or isinstance(port, bool) or not 1024 <= port <= 65535:
        raise RuntimeContractError("runtime port must be an unprivileged TCP port")
    try:
        config_dir.mkdir(parents=True, mode=0o700)
        config_dir.chmod(0o700)
        token_path = config_dir / TOKEN_FILENAME
        descriptor = os.open(token_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(descriptor, (secrets.token_urlsafe(32) + "\n").encode("ascii"))
            os.fchmod(descriptor, 0o600)
        finally:
            os.close(descriptor)
        _write_private_json(config_dir / CONFIG_FILENAME, {
            "host": DEFAULT_HOST,
            "port": port,
            "package": PACKAGE_NAME,
            "packageVersion": PACKAGE_VERSION,
            "tokenFile": TOKEN_FILENAME,
        })
    except OSError as error:
        raise RuntimeContractError("unable to initialize private runtime configuration") from error
    return read_runtime_config(config_dir)


def daemon_command(config_dir: Path, config: RuntimeConfig) -> list[str]:
    """Return the pinned daemon command without any authentication material."""
    return [
        "npx", "--yes", "--package", f"{config.package}@{config.package_version}",
        "cross-agent-teams-mcp", "daemon",
        "--host", config.host,
        "--port", str(config.port),
        "--db", str(Path(config_dir) / DATABASE_FILENAME),
        "--pid-file", str(Path(config_dir) / PID_FILENAME),
    ]


def health(config: RuntimeConfig, timeout_seconds: float = 1.0) -> bool:
    """Check XATS's unauthenticated loopback health endpoint without reading a token."""
    url = f"http://{config.host}:{config.port}/health"
    try:
        with urlopen(url, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, URLError):
        return False
    return (isinstance(payload, dict) and payload.get("ok") is True
            and payload.get("version") == HEALTH_PROTOCOL_VERSION)


def clear_stale_daemon_pid(config_dir: Path) -> None:
    """Remove only a well-formed pid file whose recorded process no longer exists."""
    pid_path = Path(config_dir) / PID_FILENAME
    if not pid_path.exists() and not pid_path.is_symlink():
        return
    _regular_file(pid_path, "daemon pid file")
    try:
        value = json.loads(pid_path.read_text(encoding="utf-8"))
        pid = value["pid"]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise RuntimeContractError("daemon pid file is invalid") from error
    if not isinstance(pid, int) or isinstance(pid, bool) or pid < 1:
        raise RuntimeContractError("daemon pid file is invalid")
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        pid_path.unlink()
    except PermissionError:
        return


def _private_database(config_dir: Path) -> None:
    """Keep the mailbox and its SQLite sidecars owner-only; XATS creates them with the caller's umask."""
    for suffix in ("", "-wal", "-shm"):
        path = Path(config_dir) / (DATABASE_FILENAME + suffix)
        if path.exists() or path.is_symlink():
            _regular_file(path, "collaboration database")
            path.chmod(0o600)


def start_daemon(config_dir: Path, health_attempts: int = 20) -> dict[str, Any]:
    """Start the pinned daemon with a child-only token, then await its health check."""
    config = read_runtime_config(config_dir)
    _private_database(config_dir)
    if health(config):
        return {"state": "running", "host": config.host, "port": config.port}
    clear_stale_daemon_pid(config_dir)
    from collaboration_auth_header import read_private_token
    environment = os.environ.copy()
    environment["CROSS_AGENT_TEAMS_MCP_TOKEN"] = read_private_token(config.token_file)
    try:
        process = subprocess.Popen(
            daemon_command(config_dir, config), env=environment, start_new_session=True, umask=0o077,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except OSError as error:
        raise RuntimeContractError("unable to start collaboration daemon") from error
    for _ in range(health_attempts):
        if health(config, timeout_seconds=0.25):
            return {"state": "started", "pid": process.pid, "host": config.host, "port": config.port}
        if process.poll() is not None:
            break
        time.sleep(0.1)
    if process.poll() is None:
        return {"state": "starting", "pid": process.pid, "host": config.host, "port": config.port}
    return {"state": "unhealthy", "host": config.host, "port": config.port}


def _regular_file(path: Path, label: str) -> os.stat_result:
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise RuntimeContractError(f"{label} is absent") from error
    if not stat.S_ISREG(metadata.st_mode):
        raise RuntimeContractError(f"{label} must be a regular file")
    return metadata


def _load_json(path: Path) -> dict[str, Any]:
    _regular_file(path, "runtime configuration")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeContractError("runtime configuration must be valid JSON") from error
    if not isinstance(value, dict):
        raise RuntimeContractError("runtime configuration must be a JSON object")
    return value


def _private_directory(path: Path) -> None:
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise RuntimeContractError("runtime configuration is absent") from error
    if stat.S_ISLNK(metadata.st_mode):
        raise RuntimeContractError("runtime configuration directory must not be a symbolic link")
    if not stat.S_ISDIR(metadata.st_mode):
        raise RuntimeContractError("runtime configuration directory must be a directory")
    if stat.S_IMODE(metadata.st_mode) & 0o077:
        raise RuntimeContractError("runtime configuration directory must be private")


def _token_path(config_dir: Path, value: Any) -> Path:
    if not isinstance(value, str) or not _TOKEN_FILE_RE.fullmatch(value):
        raise RuntimeContractError("tokenFile must be a simple private filename")
    path = config_dir / value
    metadata = _regular_file(path, "token file")
    if stat.S_IMODE(metadata.st_mode) != 0o600:
        raise RuntimeContractError("token file mode must be 0600")
    if metadata.st_size == 0:
        raise RuntimeContractError("token file must not be empty")
    return path


def read_runtime_config(config_dir: Path) -> RuntimeConfig:
    """Validate and return private configuration without loading the token value."""
    config_dir = Path(config_dir)
    _private_directory(config_dir)
    config = _load_json(config_dir / CONFIG_FILENAME)
    expected = {"host", "port", "package", "packageVersion", "tokenFile"}
    if set(config) != expected:
        raise RuntimeContractError("runtime configuration fields are invalid")
    if config["host"] != DEFAULT_HOST:
        raise RuntimeContractError("runtime host must be loopback 127.0.0.1")
    if not isinstance(config["port"], int) or isinstance(config["port"], bool) or not 1024 <= config["port"] <= 65535:
        raise RuntimeContractError("runtime port must be an unprivileged TCP port")
    if config["package"] != PACKAGE_NAME:
        raise RuntimeContractError("runtime package must match the audited package")
    if config["packageVersion"] != PACKAGE_VERSION:
        raise RuntimeContractError("runtime packageVersion must match the audited version")
    return RuntimeConfig(
        host=config["host"],
        port=config["port"],
        package=config["package"],
        package_version=config["packageVersion"],
        token_file=_token_path(config_dir, config["tokenFile"]),
    )


def _ensure_private_log(path: Path) -> None:
    if path.exists() or path.is_symlink():
        _regular_file(path, "daemon log")
    else:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(descriptor)
    path.chmod(0o600)


def _managed_launch_agent(value: Any, config_dir: Path) -> bool:
    if not isinstance(value, dict):
        return False
    arguments = value.get("ProgramArguments")
    return (
        value.get("Label") == LAUNCH_AGENT_LABEL
        and isinstance(arguments, list)
        and len(arguments) == 7
        and arguments[2:5] == ["serve", "--config-dir", str(config_dir)]
        and arguments[5] == "--npx"
        and isinstance(arguments[6], str)
        and Path(arguments[6]).is_absolute()
    )


def _write_launch_agent_plist(path: Path, value: dict[str, Any]) -> None:
    with tempfile.NamedTemporaryFile(mode="wb", prefix="spec-guard-", suffix=".plist.tmp",
                                     dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        plistlib.dump(value, handle, sort_keys=True)
    temporary.chmod(0o644)
    temporary.replace(path)


def enable_background_service(
    config_dir: Path, launch_agents_dir: Path, runtime_script: Path, python_executable: str,
    npx_executable: str,
) -> Path:
    """Install the opt-in user LaunchAgent without copying the private token."""
    read_runtime_config(config_dir)
    config_dir = Path(config_dir)
    launch_agents_dir = Path(launch_agents_dir)
    plist_contract = launch_agent_plist(
        config_dir, runtime_script, python_executable, npx_executable, shutil.which("tmux"),
    )
    launch_agents_dir.mkdir(parents=True, exist_ok=True)
    plist_path = launch_agents_dir / LAUNCH_AGENT_FILENAME
    if plist_path.exists() or plist_path.is_symlink():
        try:
            _regular_file(plist_path, "LaunchAgent plist")
            with plist_path.open("rb") as handle:
                existing = plistlib.load(handle)
        except (OSError, plistlib.InvalidFileException) as error:
            raise RuntimeContractError("refusing to overwrite an unknown LaunchAgent plist") from error
        if not _managed_launch_agent(existing, config_dir):
            raise RuntimeContractError("refusing to overwrite an unknown LaunchAgent plist")
        subprocess.run(
            ["launchctl", "bootout", f"gui/{os.getuid()}", str(plist_path)],
            check=False, capture_output=True, text=True,
        )
    _ensure_private_log(config_dir / DAEMON_STDOUT_FILENAME)
    _ensure_private_log(config_dir / DAEMON_STDERR_FILENAME)
    _write_launch_agent_plist(plist_path, plist_contract)
    subprocess.run(
        ["launchctl", "bootstrap", f"gui/{os.getuid()}", str(plist_path)],
        check=True, capture_output=True, text=True,
    )
    return plist_path


def serve_daemon(config_dir: Path, npx_executable: str) -> None:
    """Exec the pinned daemon for launchd with token material in memory only."""
    config = read_runtime_config(config_dir)
    if not health(config):
        clear_stale_daemon_pid(config_dir)
    npx_path = Path(npx_executable)
    if not npx_path.is_absolute():
        raise RuntimeContractError("launchd npx path must be absolute")
    from collaboration_auth_header import read_private_token
    environment = os.environ.copy()
    environment["CROSS_AGENT_TEAMS_MCP_TOKEN"] = read_private_token(config.token_file)
    command = daemon_command(config_dir, config)
    command[0] = str(npx_path)
    _private_database(config_dir)
    os.umask(0o077)
    os.execvpe(str(npx_path), command, environment)


def background_service_status(config_dir: Path, launch_agents_dir: Path) -> dict[str, Any]:
    """Report only non-secret facts about the opt-in per-user LaunchAgent."""
    read_runtime_config(config_dir)
    plist_path = Path(launch_agents_dir) / LAUNCH_AGENT_FILENAME
    if not plist_path.exists() and not plist_path.is_symlink():
        return {"state": "service-absent"}
    try:
        _regular_file(plist_path, "LaunchAgent plist")
        with plist_path.open("rb") as handle:
            value = plistlib.load(handle)
    except (OSError, plistlib.InvalidFileException):
        return {"state": "service-invalid", "plist": str(plist_path)}
    if not _managed_launch_agent(value, Path(config_dir)):
        return {"state": "service-invalid", "plist": str(plist_path)}
    runtime_path = Path(value["ProgramArguments"][1])
    if not runtime_path.is_file():
        return {"state": "service-stale", "plist": str(plist_path)}
    loaded = subprocess.run(
        ["launchctl", "print", f"gui/{os.getuid()}/{LAUNCH_AGENT_LABEL}"],
        check=False, capture_output=True, text=True,
    ).returncode == 0
    config = read_runtime_config(config_dir)
    return {
        "state": "service-running" if loaded and health(config) else "service-offline",
        "plist": str(plist_path), "loaded": loaded,
    }


def remove_registry_agent(config_dir: Path, agent_id: str) -> dict[str, Any]:
    """Explicitly remove one XATS registry row without touching message data."""
    try:
        parsed_agent_id = UUID(agent_id)
    except (TypeError, ValueError, AttributeError) as error:
        raise RuntimeContractError("agent id must be a UUID") from error
    config = read_runtime_config(config_dir)
    from collaboration_auth_header import read_private_token
    request = Request(
        f"http://{config.host}:{config.port}/api/agents/{quote(str(parsed_agent_id))}",
        headers={"Authorization": "Bearer " + read_private_token(config.token_file)}, method="DELETE",
    )
    try:
        with urlopen(request, timeout=5.0) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, URLError) as error:
        raise RuntimeContractError("unable to remove collaboration registry agent") from error
    if (not isinstance(payload, dict) or payload.get("deleted") is not True
            or payload.get("agent_id") != str(parsed_agent_id)):
        raise RuntimeContractError("collaboration registry did not confirm deletion")
    return {
        "state": "agent-removed",
        "agentId": str(parsed_agent_id),
        "name": payload.get("name"),
        "team": payload.get("team"),
    }


def disable_background_service(config_dir: Path, launch_agents_dir: Path) -> None:
    """Explicitly remove only the validated LaunchAgent owned by Spec Guard."""
    read_runtime_config(config_dir)
    plist_path = Path(launch_agents_dir) / LAUNCH_AGENT_FILENAME
    try:
        _regular_file(plist_path, "LaunchAgent plist")
        with plist_path.open("rb") as handle:
            value = plistlib.load(handle)
    except (OSError, plistlib.InvalidFileException) as error:
        raise RuntimeContractError("LaunchAgent plist is not a managed service") from error
    if not _managed_launch_agent(value, Path(config_dir)):
        raise RuntimeContractError("LaunchAgent plist is not a managed service")
    subprocess.run(
        ["launchctl", "bootout", f"gui/{os.getuid()}", str(plist_path)],
        check=False, capture_output=True, text=True,
    )
    plist_path.unlink()


def status(config_dir: Path) -> tuple[int, dict[str, Any]]:
    """Provide a sanitized, read-only runtime state for commands and diagnostics."""
    try:
        config = read_runtime_config(config_dir)
    except RuntimeContractError as error:
        state = "absent" if str(error) == "runtime configuration is absent" else "invalid"
        return (0 if state == "absent" else 1, {"state": state, "diagnostic": str(error)})
    return 0, {
        "state": "valid",
        "host": config.host,
        "port": config.port,
        "package": config.package,
        "packageVersion": config.package_version,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=(
        "init", "status", "health", "start", "serve", "service-enable", "service-status", "service-disable",
        "remove-agent",
    ))
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--config-dir", type=Path, default=default_config_dir())
    parser.add_argument("--launch-agents-dir", type=Path, default=None)
    parser.add_argument("--runtime-script", type=Path, default=Path(__file__).resolve())
    parser.add_argument("--python-executable", default=sys.executable)
    parser.add_argument("--npx", default=None)
    parser.add_argument("--agent-id", default=None)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    args = parser.parse_args(argv)
    if args.command == "init":
        try:
            config = initialize_runtime(args.config_dir, args.port)
        except RuntimeContractError as error:
            code, payload = 1, {"state": "invalid", "diagnostic": str(error)}
        else:
            code, payload = 0, {"state": "initialized", "host": config.host, "port": config.port,
                                "package": config.package, "packageVersion": config.package_version}
    elif args.command == "health":
        code, payload = status(args.config_dir)
        if code == 0 and payload["state"] == "valid":
            config = read_runtime_config(args.config_dir)
            payload["daemon"] = "running" if health(config) else "offline"
            code = 0 if payload["daemon"] == "running" else 1
    elif args.command == "start":
        try:
            payload = start_daemon(args.config_dir)
            code = 0 if payload["state"] in {"running", "started", "starting"} else 1
        except RuntimeContractError as error:
            code, payload = 1, {"state": "invalid", "diagnostic": str(error)}
    elif args.command == "serve":
        if not args.npx:
            code, payload = 1, {"state": "invalid", "diagnostic": "launchd npx path is required"}
        else:
            try:
                serve_daemon(args.config_dir, args.npx)
            except RuntimeContractError as error:
                code, payload = 1, {"state": "invalid", "diagnostic": str(error)}
            else:
                raise AssertionError("daemon exec unexpectedly returned")
    elif args.command == "service-enable":
        npx_executable = args.npx or shutil.which("npx")
        if not npx_executable:
            code, payload = 1, {"state": "invalid", "diagnostic": "npx executable is unavailable"}
        else:
            try:
                plist_path = enable_background_service(
                    args.config_dir,
                    args.launch_agents_dir or Path.home() / "Library" / "LaunchAgents",
                    args.runtime_script, args.python_executable, npx_executable,
                )
            except (RuntimeContractError, subprocess.CalledProcessError) as error:
                code, payload = 1, {"state": "invalid", "diagnostic": str(error)}
            else:
                code, payload = 0, {"state": "service-enabled", "plist": str(plist_path)}
    elif args.command == "service-status":
        try:
            payload = background_service_status(
                args.config_dir, args.launch_agents_dir or Path.home() / "Library" / "LaunchAgents",
            )
            code = 0 if payload["state"] in {"service-absent", "service-running"} else 1
        except RuntimeContractError as error:
            code, payload = 1, {"state": "invalid", "diagnostic": str(error)}
    elif args.command == "service-disable":
        try:
            disable_background_service(
                args.config_dir, args.launch_agents_dir or Path.home() / "Library" / "LaunchAgents",
            )
        except RuntimeContractError as error:
            code, payload = 1, {"state": "invalid", "diagnostic": str(error)}
        else:
            code, payload = 0, {"state": "service-disabled"}
    elif args.command == "remove-agent":
        if not args.agent_id:
            code, payload = 1, {"state": "invalid", "diagnostic": "agent id is required"}
        else:
            try:
                payload = remove_registry_agent(args.config_dir, args.agent_id)
            except RuntimeContractError as error:
                code, payload = 1, {"state": "invalid", "diagnostic": str(error)}
            else:
                code = 0
    else:
        code, payload = status(args.config_dir)
    if args.format == "json":
        print(json.dumps(payload, sort_keys=True))
    elif payload["state"] in {"valid", "initialized", "running", "started", "starting"}:
        print("协作运行时配置有效：%s:%s（%s@%s）" % (
            payload["host"], payload["port"], payload.get("package", PACKAGE_NAME),
            payload.get("packageVersion", PACKAGE_VERSION)))
    elif payload["state"] == "service-enabled":
        print("协作后台服务已启用：" + payload["plist"])
    elif payload["state"] in {"service-absent", "service-running", "service-offline", "service-stale", "service-invalid", "service-disabled"}:
        print("协作后台服务状态：" + payload["state"])
    elif payload["state"] == "agent-removed":
        print("协作临时身份已删除：" + payload["agentId"])
    else:
        print("协作运行时配置%s：%s" % (
            "尚未创建" if payload["state"] == "absent" else "无效", payload["diagnostic"]))
    return code


if __name__ == "__main__":
    sys.exit(main())
