"""Read-only contract and diagnostics for the optional local Epiq ticket ledger."""
import argparse
import json
import re
import shutil
import stat
import subprocess
from pathlib import Path
from typing import Any, Sequence


PACKAGE_NAME = "epiq"
PACKAGE_VERSION = "1.11.0"
MINIMUM_NODE_MAJOR = 18
MCP_RELATIVE_PATH = Path("node_modules") / PACKAGE_NAME / "dist" / "mcp.js"
PROJECT_RELATIVE_PATH = Path(".epiq") / "project.json"
STATE_BRANCH = "__epiq_state__"
_NODE_VERSION = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


class RuntimeContractError(ValueError):
    """The optional local-ledger runtime is absent or does not match its contract."""


def default_runtime_dir() -> Path:
    return Path.home() / ".spec-guard" / "local-ticket-ledger" / "runtime"


def runtime_contract() -> dict[str, Any]:
    """Return stable public facts without inspecting or creating the runtime."""
    return {
        "package": PACKAGE_NAME,
        "packageVersion": PACKAGE_VERSION,
        "minimumNodeMajor": MINIMUM_NODE_MAJOR,
        "entrypoint": str(MCP_RELATIVE_PATH),
        "projectConfig": str(PROJECT_RELATIVE_PATH),
        "stateBranch": STATE_BRANCH,
    }


def node_status(node_executable: str | None = None) -> dict[str, str]:
    """Report whether a compatible Node executable is available without modifying it."""
    executable = node_executable or shutil.which("node")
    if not executable:
        return {"state": "missing", "diagnostic": "node executable is unavailable"}
    try:
        completed = subprocess.run(
            [executable, "--version"], check=False, capture_output=True, text=True,
        )
    except OSError:
        return {"state": "invalid", "diagnostic": "node executable cannot be run"}
    if completed.returncode != 0:
        return {"state": "invalid", "diagnostic": "node executable returned an error"}
    version = completed.stdout.strip()
    match = _NODE_VERSION.fullmatch(version)
    if not match:
        return {"state": "invalid", "diagnostic": "node version is invalid"}
    if int(match.group(1)) < MINIMUM_NODE_MAJOR:
        return {"state": "unsupported", "path": executable, "version": version}
    return {"state": "ready", "path": executable, "version": version}


def _regular_file(path: Path, label: str) -> None:
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise RuntimeContractError(label + " is absent") from error
    if not stat.S_ISREG(metadata.st_mode):
        raise RuntimeContractError(label + " must be a regular file")


def _directory(path: Path, label: str) -> None:
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise RuntimeContractError(label + " is absent") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise RuntimeContractError(label + " must be a directory, not a symbolic link")


def _json_object(path: Path, label: str) -> dict[str, Any]:
    _regular_file(path, label)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeContractError(label + " must be valid JSON") from error
    if not isinstance(value, dict):
        raise RuntimeContractError(label + " must be a JSON object")
    return value


def runtime_status(runtime_dir: Path) -> dict[str, str]:
    """Validate the already-installed package without executing it."""
    runtime_dir = Path(runtime_dir)
    if not runtime_dir.exists() and not runtime_dir.is_symlink():
        return {"state": "absent"}
    try:
        _directory(runtime_dir, "runtime directory")
        package_dir = runtime_dir / "node_modules" / PACKAGE_NAME
        _directory(package_dir, "Epiq package directory")
        package = _json_object(package_dir / "package.json", "Epiq package metadata")
        if package.get("name") != PACKAGE_NAME:
            raise RuntimeContractError("Epiq package name does not match the audited package")
        if package.get("version") != PACKAGE_VERSION:
            raise RuntimeContractError("Epiq package version does not match the audited version")
        _regular_file(runtime_dir / MCP_RELATIVE_PATH, "Epiq MCP entrypoint")
    except RuntimeContractError as error:
        return {"state": "invalid", "diagnostic": str(error)}
    return {
        "state": "ready",
        "directory": str(runtime_dir),
        "package": PACKAGE_NAME,
        "packageVersion": PACKAGE_VERSION,
    }


def project_status(project_dir: Path) -> dict[str, str]:
    """Read the committed project identity only; do not invoke Git or Epiq."""
    project_dir = Path(project_dir)
    config_path = project_dir / PROJECT_RELATIVE_PATH
    if not config_path.exists() and not config_path.is_symlink():
        return {"state": "uninitialized"}
    try:
        config = _json_object(config_path, "Epiq project configuration")
        expected = {"projectId", "stateBranch", "createdAt"}
        if set(config) != expected:
            raise RuntimeContractError("Epiq project configuration fields are invalid")
        if not all(isinstance(config[key], str) and config[key] for key in expected):
            raise RuntimeContractError("Epiq project configuration values are invalid")
        if config["stateBranch"] != STATE_BRANCH:
            raise RuntimeContractError("Epiq state branch does not match the audited contract")
    except RuntimeContractError as error:
        return {"state": "invalid", "diagnostic": str(error)}
    return {
        "state": "initialized",
        "projectId": config["projectId"],
        "stateBranch": config["stateBranch"],
    }


def _git(project_dir: Path, *arguments: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["git", "-C", str(project_dir), *arguments],
            check=False, capture_output=True, text=True,
        )
    except OSError:
        return None


def initialization_preflight(
    project_dir: Path, allow_epiq_push: bool = False,
) -> tuple[int, dict[str, Any]]:
    """Read Git facts that must be safe before explicit Epiq initialization."""
    project_dir = Path(project_dir)
    top_level = _git(project_dir, "rev-parse", "--show-toplevel")
    if top_level is None or top_level.returncode != 0:
        return 1, {"state": "not-git", "diagnostic": "project directory is not a Git worktree"}
    repository = Path(top_level.stdout.strip())
    worktree = _git(repository, "status", "--porcelain", "--untracked-files=all")
    if worktree is None or worktree.returncode != 0:
        return 1, {"state": "invalid", "diagnostic": "unable to inspect Git worktree"}
    if worktree.stdout:
        return 1, {"state": "dirty", "projectDir": str(repository)}
    origin = _git(repository, "remote", "get-url", "origin")
    if origin is None:
        return 1, {"state": "invalid", "diagnostic": "unable to inspect Git origin"}
    if origin.returncode == 0:
        origin_url = origin.stdout.strip()
        if not allow_epiq_push:
            return 1, {
                "state": "push-confirmation-required",
                "projectDir": str(repository),
                "origin": origin_url,
                "upstreamPush": "requires-explicit-confirmation",
            }
        return 0, {
            "state": "ready",
            "projectDir": str(repository),
            "origin": origin_url,
            "upstreamPush": "permitted",
        }
    return 0, {
        "state": "ready",
        "projectDir": str(repository),
        "origin": None,
        "upstreamPush": "will-fail-as-warning",
    }


def status(runtime_dir: Path, project_dir: Path) -> tuple[int, dict[str, Any]]:
    """Return side-effect-free status for the optional local ledger."""
    node = node_status()
    runtime = runtime_status(runtime_dir)
    project = project_status(project_dir)
    payload: dict[str, Any] = {"node": node, "runtime": runtime, "project": project}
    if runtime["state"] == "invalid" or project["state"] == "invalid":
        payload["state"] = "invalid"
        return 1, payload
    if runtime["state"] == "absent":
        payload["state"] = "absent"
        return 0, payload
    if node["state"] != "ready":
        payload["state"] = "invalid"
        return 1, payload
    if project["state"] == "uninitialized":
        payload["state"] = "ready"
        return 0, payload
    payload["state"] = "initialized"
    return 0, payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("contract", "status", "preflight"))
    parser.add_argument("--runtime-dir", type=Path, default=default_runtime_dir())
    parser.add_argument("--project-dir", type=Path, default=Path.cwd())
    parser.add_argument("--allow-epiq-push", action="store_true")
    parser.add_argument("--format", choices=("json", "text"), default="text")
    args = parser.parse_args(argv)
    if args.command == "contract":
        code, payload = 0, runtime_contract()
    elif args.command == "status":
        code, payload = status(args.runtime_dir, args.project_dir)
    else:
        code, payload = initialization_preflight(args.project_dir, args.allow_epiq_push)
    if args.format == "json":
        print(json.dumps(payload, sort_keys=True))
    elif args.command == "contract":
        print("本地事项账本固定运行时：%s@%s" % (PACKAGE_NAME, PACKAGE_VERSION))
    elif args.command == "preflight":
        print("本地事项账本初始化预检：" + payload["state"])
    else:
        print("本地事项账本状态：" + payload["state"])
    return code


if __name__ == "__main__":
    raise SystemExit(main())
