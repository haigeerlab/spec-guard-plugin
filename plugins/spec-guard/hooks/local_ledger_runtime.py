"""Read-only contract and diagnostics for the optional local Epiq ticket ledger."""
from __future__ import annotations
import argparse
import json
import re
import shutil
import stat
import subprocess
import tempfile
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


def validate_lock_files(lock_dir: Path) -> list[str]:
    """Read-only drift check of the shipped package.json/package-lock.json; returns problems."""
    problems: list[str] = []
    documents: dict[str, Any] = {}
    for name in ("package.json", "package-lock.json"):
        try:
            documents[name] = json.loads((Path(lock_dir) / name).read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            problems.append(f"{name}: unreadable ({error.__class__.__name__})")
    expected = {PACKAGE_NAME: PACKAGE_VERSION}
    package = documents.get("package.json")
    if package is not None and package.get("dependencies") != expected:
        problems.append(f"package.json: dependencies must be exactly {expected}")
    lock = documents.get("package-lock.json")
    if lock is not None:
        entries = lock.get("packages")
        if lock.get("lockfileVersion") != 3:
            problems.append("package-lock.json: lockfileVersion must be 3")
        if not isinstance(entries, dict):
            problems.append("package-lock.json: packages missing")
            return problems
        if (entries.get("") or {}).get("dependencies") != expected:
            problems.append(f"package-lock.json: root dependencies must be exactly {expected}")
        if (entries.get(f"node_modules/{PACKAGE_NAME}") or {}).get("version") != PACKAGE_VERSION:
            problems.append(f"package-lock.json: {PACKAGE_NAME} must be locked at {PACKAGE_VERSION}")
        for key, entry in entries.items():
            if not key:
                continue
            if not (isinstance(entry, dict) and entry.get("resolved")):
                problems.append(f"package-lock.json: {key} lacks resolved")
            integrity = entry.get("integrity") if isinstance(entry, dict) else None
            if not (isinstance(integrity, str) and re.match(r"^(sha512|sha1)-.+", integrity)):
                problems.append(f"package-lock.json: {key} lacks integrity")
    return problems


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


SHIPPED_LOCK_DIR = Path(__file__).resolve().parent.parent / "locks" / "local-ticket-ledger"
LOCK_FILE_NAMES = ("package.json", "package-lock.json")


def install_command(npm_executable: str) -> list[str]:
    """Build the fixed npm command; it runs in a directory holding the shipped lock files."""
    return [npm_executable, "ci", "--ignore-scripts", "--no-audit", "--no-fund"]


def install_runtime(
    runtime_dir: Path, npm_executable: str | None = None, lock_dir: Path | None = None,
) -> dict[str, str]:
    """Install the locked runtime only when explicitly invoked by the caller."""
    runtime_dir = Path(runtime_dir)
    lock_dir = Path(lock_dir) if lock_dir is not None else SHIPPED_LOCK_DIR
    existing = runtime_status(runtime_dir)
    if existing["state"] == "ready":
        raise RuntimeContractError("local-ledger runtime is already installed")
    if existing["state"] == "invalid":
        # 旧版本安装失败会留下空目录；空目录没有任何数据，可以接管，其余无效运行时一律不碰。
        if (runtime_dir.is_symlink() or not runtime_dir.is_dir() or
                any(runtime_dir.iterdir())):
            raise RuntimeContractError("refusing to overwrite an invalid local-ledger runtime")
    problems = validate_lock_files(lock_dir)
    if problems:
        raise RuntimeContractError("shipped lock files are unusable: " + "; ".join(problems))
    npm_path = npm_executable or shutil.which("npm")
    if not npm_path:
        raise RuntimeContractError("npm executable is unavailable")
    runtime_dir.parent.mkdir(parents=True, exist_ok=True)
    # 装进同级临时目录，校验通过后才原子改名；失败时只删自己建的临时目录，正式目录不会出现。
    staging = Path(tempfile.mkdtemp(prefix=runtime_dir.name + ".installing-", dir=runtime_dir.parent))
    try:
        try:
            for name in LOCK_FILE_NAMES:
                shutil.copyfile(lock_dir / name, staging / name)
            completed = subprocess.run(
                install_command(npm_path), cwd=staging, check=False, capture_output=True, text=True,
            )
        except OSError as error:
            raise RuntimeContractError("unable to run npm ci") from error
        if completed.returncode != 0:
            lines = [line.strip() for line in (completed.stderr or "").splitlines() if line.strip()]
            detail = (": " + lines[-1][:200]) if lines else ""
            raise RuntimeContractError("npm ci failed" + detail)
        installed = runtime_status(staging)
        if installed["state"] != "ready":
            raise RuntimeContractError(
                "installed local-ledger runtime does not match the audited contract")
        try:
            if runtime_dir.exists() or runtime_dir.is_symlink():
                runtime_dir.rmdir()
            staging.rename(runtime_dir)
        except OSError as error:
            raise RuntimeContractError("unable to move the verified runtime into place") from error
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return dict(installed, directory=str(runtime_dir))


def project_init_arguments(
    project_dir: Path, user_name: str, preferred_editor: str, auto_sync: bool,
) -> dict[str, Any]:
    """Build the documented Epiq setup input without using an agent identity."""
    if not isinstance(user_name, str) or not user_name.strip():
        raise RuntimeContractError("Epiq user name is required")
    if not isinstance(preferred_editor, str) or not preferred_editor.strip():
        raise RuntimeContractError("Epiq preferred editor is required")
    if not isinstance(auto_sync, bool):
        raise RuntimeContractError("Epiq auto sync must be a boolean")
    return {
        "repoRoot": str(Path(project_dir)),
        "userName": user_name.strip(),
        "preferredEditor": preferred_editor.strip(),
        "autoSync": auto_sync,
    }


def _read_mcp_response(stream: Any, request_id: int) -> dict[str, Any]:
    while True:
        line = stream.readline()
        if not line:
            raise RuntimeContractError("MCP server closed before responding")
        try:
            response = json.loads(line)
        except json.JSONDecodeError as error:
            raise RuntimeContractError("MCP server returned invalid JSON") from error
        if response.get("id") == request_id:
            if not isinstance(response.get("result"), dict) or "error" in response:
                raise RuntimeContractError("MCP server rejected the request")
            return response["result"]


def read_mcp_tool_result(stream: Any, request_id: int) -> dict[str, Any]:
    """Read Epiq's JSON text result without exposing unstructured server diagnostics."""
    result = _read_mcp_response(stream, request_id)
    content = result.get("content")
    if not isinstance(content, list) or not content:
        raise RuntimeContractError("MCP tool response is invalid")
    first = content[0]
    if not isinstance(first, dict) or first.get("type") != "text" or not isinstance(first.get("text"), str):
        raise RuntimeContractError("MCP tool response is invalid")
    try:
        payload = json.loads(first["text"])
    except json.JSONDecodeError as error:
        raise RuntimeContractError("MCP tool response is invalid") from error
    if not isinstance(payload, dict) or payload.get("status") != "success":
        raise RuntimeContractError("MCP tool response is unsuccessful")
    return payload


def mcp_tool_call(command: list[str], tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Call one stdio MCP tool and terminate the private child process afterwards."""
    try:
        process = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True,
        )
    except OSError as error:
        raise RuntimeContractError("unable to start the local-ledger MCP server") from error
    if process.stdin is None or process.stdout is None:
        process.terminate()
        raise RuntimeContractError("unable to open local-ledger MCP streams")
    try:
        process.stdin.write(json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": "2025-03-26", "capabilities": {},
                "clientInfo": {"name": "spec-guard", "version": "local-ledger"},
            },
        }) + "\n")
        process.stdin.flush()
        _read_mcp_response(process.stdout, 1)
        process.stdin.write(json.dumps({
            "jsonrpc": "2.0", "method": "notifications/initialized", "params": {},
        }) + "\n")
        process.stdin.write(json.dumps({
            "jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
                "name": tool_name, "arguments": arguments,
            },
        }) + "\n")
        process.stdin.flush()
        return read_mcp_tool_result(process.stdout, 2)
    finally:
        process.stdin.close()
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)


def initialize_project(
    runtime_dir: Path, project_dir: Path, user_name: str, preferred_editor: str, auto_sync: bool,
    allow_epiq_push: bool = False,
) -> dict[str, Any]:
    """Explicitly initialize Epiq only after clean-tree and push-consent preflight."""
    code, preflight = initialization_preflight(project_dir, allow_epiq_push)
    if code != 0:
        raise RuntimeContractError("initialization preflight: " + preflight["state"])
    node = node_status()
    runtime = runtime_status(runtime_dir)
    if node["state"] != "ready" or runtime["state"] != "ready":
        raise RuntimeContractError("local-ledger runtime is not ready")
    result = mcp_tool_call(
        [node["path"], str(Path(runtime_dir) / MCP_RELATIVE_PATH)],
        "epiq_project_init",
        project_init_arguments(Path(preflight["projectDir"]), user_name, preferred_editor, auto_sync),
    )
    value = result.get("value")
    if not isinstance(value, dict) or not isinstance(value.get("projectId"), str):
        raise RuntimeContractError("Epiq initialization returned an invalid project identity")
    if value.get("stateBranch") != STATE_BRANCH:
        raise RuntimeContractError("Epiq initialization returned an unexpected state branch")
    return {
        "state": "initialized",
        "projectId": value["projectId"],
        "stateBranch": value["stateBranch"],
        "upstreamPush": preflight["upstreamPush"],
        "warnings": bool(value.get("warnings")),
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
    parser.add_argument("command", choices=("contract", "status", "preflight", "install", "initialize"))
    parser.add_argument("--runtime-dir", type=Path, default=default_runtime_dir())
    parser.add_argument("--project-dir", type=Path, default=Path.cwd())
    parser.add_argument("--allow-epiq-push", action="store_true")
    parser.add_argument("--confirm-install", action="store_true")
    parser.add_argument("--confirm-initialize", action="store_true")
    parser.add_argument("--user-name", default=None)
    parser.add_argument("--preferred-editor", default=None)
    parser.add_argument("--auto-sync", choices=("true", "false"), default=None)
    parser.add_argument("--npm", default=None)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    args = parser.parse_args(argv)
    if args.command == "contract":
        code, payload = 0, runtime_contract()
    elif args.command == "status":
        code, payload = status(args.runtime_dir, args.project_dir)
    elif args.command == "preflight":
        code, payload = initialization_preflight(args.project_dir, args.allow_epiq_push)
    elif args.command == "install" and not args.confirm_install:
        code, payload = 1, {
            "state": "install-confirmation-required",
            "diagnostic": "rerun with --confirm-install to install the fixed local-ledger runtime",
        }
    elif args.command == "install":
        try:
            payload = install_runtime(args.runtime_dir, args.npm)
        except RuntimeContractError as error:
            code, payload = 1, {"state": "invalid", "diagnostic": str(error)}
        else:
            code, payload = 0, {"state": "installed", **payload}
    elif not args.confirm_initialize:
        code, payload = 1, {
            "state": "initialization-confirmation-required",
            "diagnostic": "rerun with --confirm-initialize after reviewing the Git effects",
        }
    elif not args.user_name or not args.preferred_editor or args.auto_sync is None:
        code, payload = 1, {
            "state": "user-setup-required",
            "diagnostic": "user name, preferred editor, and auto sync choice are required",
        }
    else:
        try:
            payload = initialize_project(
                args.runtime_dir, args.project_dir, args.user_name, args.preferred_editor,
                args.auto_sync == "true", args.allow_epiq_push,
            )
        except RuntimeContractError as error:
            code, payload = 1, {"state": "invalid", "diagnostic": str(error)}
        else:
            code = 0
    if args.format == "json":
        print(json.dumps(payload, sort_keys=True))
    elif args.command == "contract":
        print("本地事项账本固定运行时：%s@%s" % (PACKAGE_NAME, PACKAGE_VERSION))
    elif args.command == "preflight":
        print("本地事项账本初始化预检：" + payload["state"])
    elif args.command == "install" and payload["state"] == "installed":
        print("本地事项账本运行时已安装：%s@%s" % (PACKAGE_NAME, PACKAGE_VERSION))
    elif args.command == "initialize" and payload["state"] == "initialized":
        print("本地事项账本项目已初始化：" + payload["projectId"])
    else:
        print("本地事项账本状态：" + payload["state"])
    return code


if __name__ == "__main__":
    raise SystemExit(main())
