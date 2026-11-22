#!/usr/bin/env python3
"""Check and prepare a Spec Guard release from its merged commit."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "plugins/spec-guard/hooks"))
from state_paths import state_dir


SCHEMA = "spec-guard.release/v1"
RECORD_SCHEMA = "spec-guard.release-record/v1"
TEMP_PREFIX = "spec-guard-release-"
REQUIRED = (
    ".claude-plugin/marketplace.json",
    "plugins/spec-guard/.claude-plugin/plugin.json",
    "plugins/spec-guard/.codex-plugin/plugin.json",
)
EXIT_CODES = {"ok": 0, "preview": 0, "refused": 2, "waiting-on-user": 3, "failed": 1}


class ReleaseError(Exception):
    def __init__(self, message, status="failed", reason=None):
        super().__init__(message)
        self.status = status
        self.reason = reason


def refuse(reason, message):
    raise ReleaseError(message, "refused", reason)


def run(args, check=False, timeout=120):
    """Run one command without a shell; preserve binary stdout for git archive."""
    try:
        result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ReleaseError("无法执行命令 %s：%s" % (args[0], error)) from error
    if check and result.returncode:
        detail = (result.stderr or result.stdout).decode("utf-8", errors="replace").strip()
        raise ReleaseError("命令失败（%s，退出码 %s）：%s" % (args[0], result.returncode, detail))
    return result.returncode, result.stdout, result.stderr


def git(repo, *args):
    return run(["git", "-C", str(repo), *args], check=True)[1].decode("utf-8")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def valid_version(version):
    return isinstance(version, str) and re.fullmatch(r"[0-9][A-Za-z0-9.+-]*", version) is not None


def record_path(version):
    if not valid_version(version):
        refuse("invalid-version", "版本号无效，不能用于本机记录文件名。")
    return state_dir("release") / (version + ".json")


def read_record(version):
    path = record_path(version)
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        record = json.load(handle)
    if not isinstance(record, dict):
        raise ReleaseError("本机发版记录不是 JSON 对象。")
    return record


def write_record(record, step, facts):
    """Replace just this step, preserving all other recorded steps and facts."""
    path = record_path(record["version"])
    record.setdefault("steps", {})[step] = facts
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".release-", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def github_repo(args):
    if args.github:
        github = args.github
    else:
        url = git(args.repo, "remote", "get-url", args.remote).strip()
        match = re.fullmatch(r"(?:git@github\.com:|https://github\.com/)([^/]+/[^/]+?)(?:\.git)?", url)
        if not match:
            refuse("github-not-resolved", "无法从远端 URL 解析 GitHub 仓库，请指定 --github owner/repo。")
        github = match.group(1)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", github):
        refuse("invalid-github", "--github 必须是 owner/repo。")
    return github


def check_release(args):
    github = github_repo(args)
    pull = json.loads(run(["gh", "api", "repos/%s/pulls/%s" % (github, args.pr)], check=True)[1])
    if not isinstance(pull, dict):
        raise ReleaseError("GitHub 返回的 PR 数据不是 JSON 对象。")
    if pull.get("merged") is not True:
        refuse("not-merged", "检查未通过：PR 尚未合并。")
    sha = pull.get("merge_commit_sha")
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-fA-F]{40,64}", sha):
        raise ReleaseError("PR 未提供有效的合并提交。")
    print("PR 已合并，正在核对 main 与合并提交。")
    git(args.repo, "fetch", args.remote)
    if git(args.repo, "rev-parse", args.remote + "/main").strip() != sha:
        refuse("main-moved", "检查未通过：远端 main 已不等于 PR 的合并提交。")
    runs = json.loads(run(["gh", "run", "list", "--repo", github, "--commit", sha,
                           "--json", "conclusion,status,workflowName"], check=True)[1])
    if (not isinstance(runs, list) or not runs or
            any(not isinstance(item, dict) or item.get("status") != "completed" or
                item.get("conclusion") != "success" for item in runs)):
        refuse("ci-not-green", "检查未通过：CI 为空、尚未完成或存在非成功结论。")
    print("main 与 CI 检查通过，正在核对合并提交上的版本。")
    try:
        versions = [json.loads(git(args.repo, "show", sha + ":" + path))["version"]
                    for path in REQUIRED[1:]]
        version = versions[0]
        if not valid_version(version) or versions[1] != version:
            refuse("version-mismatch", "检查未通过：两份插件清单的版本不一致或无效。")
        args.version = version
        reference = re.compile(r"--ref[ \t]+v" + re.escape(version) + r"(?![A-Za-z0-9_.+-])")
        for readme in ("README.md", "README.en.md"):
            if not reference.search(git(args.repo, "show", sha + ":" + readme)):
                refuse("version-mismatch", "检查未通过：%s 没有对应版本的 --ref。" % readme)
    except (ReleaseError, ValueError, KeyError, TypeError) as error:
        refuse("version-mismatch", "合并提交的版本检查未通过：%s" % error)
    tag = "v" + version
    if (git(args.repo, "tag", "-l", tag).strip() or
            git(args.repo, "ls-remote", "--tags", args.remote, tag).strip()):
        refuse("tag-exists", "检查未通过：本地或远端已存在标签 %s。" % tag)
    record = read_record(version)
    record.update({"schema": RECORD_SCHEMA, "version": version, "pr": args.pr,
                   "mergeCommit": sha, "github": github})
    write_record(record, "check", {"status": "ok", "at": utc_now()})
    print("全部检查通过，已保存本机发版记录。")
    return {"status": "ok", "mergeCommit": sha}


def remove_temporary(path):
    if not path.name.startswith(TEMP_PREFIX):
        raise ReleaseError("临时目录前缀不符，拒绝删除：%s" % path)
    shutil.rmtree(path)


def extract(archive, destination):
    """Keep archive members and links within their temporary extraction root."""
    root = destination.resolve()
    for member in archive.getmembers():
        targets = [destination / member.name]
        if member.issym():
            targets.append(destination / Path(member.name).parent / member.linkname)
        if member.islnk():
            targets.append(destination / member.linkname)
        if member.isdev() or any(not target.resolve().is_relative_to(root) for target in targets):
            raise ReleaseError("归档包含不安全的成员：%s" % member.name)
        archive.extract(member, destination)


def release_notes(changelog, version):
    heading = re.search(r"^## \[" + re.escape(version) + r"\][^\r\n]*(?:\r?\n|$)", changelog, re.M)
    if heading is None:
        raise ReleaseError("CHANGELOG.md 中找不到版本 %s 的章节。" % version)
    body = changelog[heading.end():]
    following = re.search(r"^## \[", body, re.M)
    return body[:following.start()] if following else body


def prepare_release(args):
    record = read_record(args.version)
    steps = record.get("steps")
    checked = steps.get("check") if isinstance(steps, dict) else None
    if not isinstance(checked, dict) or checked.get("status") != "ok":
        refuse("check-not-ok", "无法备包：本机记录中没有成功的 check，请先执行 check。")
    directory = Path(tempfile.mkdtemp(prefix=TEMP_PREFIX))
    verification = None
    keep = False
    try:
        name = "spec-guard-v" + args.version
        source = directory / name
        print("正在从已核对的合并提交导出插件文件。")
        data = run(["git", "-C", str(args.repo), "archive", "--format=tar", "--prefix=" + name + "/",
                    record["mergeCommit"], ".claude-plugin", "plugins/spec-guard"], check=True)[1]
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
            extract(archive, directory)
        manifest = {"schemaVersion": 1, "artifactKind": "spec-guard-plugin",
                    "version": args.version, "files": list(REQUIRED)}
        (source / "ARTIFACT-MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        validator = ["python3", "-B", str(args.repo / "scripts/release-package.py"), "validate"]
        run(validator + [str(source), args.version], check=True)
        asset = directory / (name + ".tar.gz")
        print("打包前校验通过，正在生成并解包复验 tar.gz。")
        with tarfile.open(asset, "w:gz") as archive:
            for path in [source] + sorted(source.rglob("*")):
                archive.add(path, arcname=path.relative_to(directory).as_posix(), recursive=False)
        verification = Path(tempfile.mkdtemp(prefix=TEMP_PREFIX))
        with tarfile.open(asset, "r:gz") as archive:
            if any(Path(member.name).name.startswith("._") for member in archive.getmembers()):
                raise ReleaseError("发布包中存在 ._* 元数据成员，备包失败。")
            extract(archive, verification)
        run(validator + [str(verification / name), args.version], check=True)
        notes = directory / "notes.md"
        notes.write_text(release_notes(git(args.repo, "show", record["mergeCommit"] + ":CHANGELOG.md"),
                                       args.version), encoding="utf-8")
        digest = hashlib.sha256(asset.read_bytes()).hexdigest()
        size = asset.stat().st_size
        write_record(record, "prepare", {"status": "ok", "dir": str(directory), "asset": str(asset),
                                         "sha256": digest, "size": size, "notes": str(notes), "at": utc_now()})
        keep = True
        print("备包完成，两次包校验通过；产物与说明保存在 %s。" % directory)
        return {"status": "ok", "asset": str(asset), "sha256": digest, "size": size}
    finally:
        if verification is not None:
            remove_temporary(verification)
        if not keep:
            remove_temporary(directory)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        refuse("invalid-arguments", "命令参数错误：%s" % message)


def parser():
    result = Parser(description="检查与准备 Spec Guard 发版。")
    commands = result.add_subparsers(dest="step", required=True)
    result.add_argument("--repo", default=str(ROOT))
    result.add_argument("--remote", default="origin")
    result.add_argument("--github")
    for step, handler in (("check", check_release), ("prepare", prepare_release)):
        command = commands.add_parser(step)
        for option in ("--repo", "--remote", "--github"):
            command.add_argument(option, default=argparse.SUPPRESS)
        command.set_defaults(handler=handler)
        if step == "check":
            command.add_argument("--pr", type=int, required=True)
        else:
            command.add_argument("--version", required=True)
    return result


def main(argv):
    args = argparse.Namespace(step=None, version=None)
    try:
        parser().parse_args(argv, namespace=args)
        args.repo = Path(args.repo).resolve()
        facts = args.handler(args)
    except ReleaseError as error:
        print(str(error))
        facts = {"status": error.status}
        if error.reason:
            facts["reason"] = error.reason
    except (OSError, ValueError, KeyError, TypeError, tarfile.TarError) as error:
        print("发版步骤失败：%s" % error)
        facts = {"status": "failed"}
    payload = {"schema": SCHEMA, "step": args.step, "version": args.version, **facts}
    print(json.dumps(payload, ensure_ascii=False))
    return EXIT_CODES[payload["status"]]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
