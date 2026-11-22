#!/usr/bin/env python3
"""Release Spec Guard from its merged commit and record host verification evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shlex
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


def run(args, check=False, timeout=120, stdin=None):
    """Run one command without a shell; preserve binary stdout for git archive."""
    try:
        result = subprocess.run(args, stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
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


def require_step(record, step):
    steps = record.get("steps")
    facts = steps.get(step) if isinstance(steps, dict) else None
    if not isinstance(facts, dict) or facts.get("status") != "ok":
        refuse(step + "-not-ok", "本机记录中没有成功的 %s，请先完成该步骤。" % step)
    return facts


def publish_release(args):
    record = read_record(args.version)
    prepared = require_step(record, "prepare")
    if not isinstance(prepared.get("asset"), str) or not prepared["asset"]:
        refuse("asset-changed", "本机记录中没有发布包路径，请重新 prepare。")
    asset = Path(prepared["asset"])
    if not asset.is_file() or hashlib.sha256(asset.read_bytes()).hexdigest() != prepared.get("sha256"):
        refuse("asset-changed", "发布包不存在或 sha256 已改变，请重新 prepare。")
    tag = "v" + args.version
    github = record["github"]
    directory = Path(tempfile.mkdtemp(prefix=TEMP_PREFIX))
    try:
        commands = [
            ["git", "-C", str(args.repo), "tag", "-a", tag, record["mergeCommit"], "-m", tag],
            ["git", "-C", str(args.repo), "push", args.remote, tag],
            ["gh", "release", "create", tag, "--repo", github, "--verify-tag", "--title", tag,
             "--notes-file", prepared["notes"], str(asset)],
            ["gh", "release", "download", tag, "--repo", github, "-p", asset.name, "-D", str(directory)],
            ["gh", "api", "repos/%s/releases/latest" % github],
        ]
        print("将按顺序执行以下发布命令，并核对回下载 sha256 与 latest 标签：")
        for command in commands:
            print(shlex.join(command))
        if not args.confirm:
            return {"status": "preview"}
        for command in commands[:4]:
            run(command, check=True)
        digest = hashlib.sha256((directory / asset.name).read_bytes()).hexdigest()
        if digest != prepared["sha256"]:
            raise ReleaseError("回下载 sha256 不一致：记录为 %s，下载为 %s。" % (prepared["sha256"], digest))
        latest = json.loads(run(commands[4], check=True)[1])
        if not isinstance(latest, dict):
            raise ReleaseError("GitHub latest Release 数据不是 JSON 对象。")
        if latest.get("tag_name") != tag:
            raise ReleaseError("latest Release 标签不符：期望 %s，实际 %s。" % (tag, latest.get("tag_name")))
        url = latest["html_url"]
        write_record(record, "publish", {"status": "ok", "tag": tag, "url": url,
                                         "downloadSha256": digest, "at": utc_now()})
        print("发布完成，回下载 sha256 与 latest 标签均已核对。")
        return {"status": "ok", "tag": tag, "url": url}
    finally:
        remove_temporary(directory)


def codex_ref_change(path, version):
    """Locate one exact ref line without decoding or normalizing any other bytes."""
    if not path.is_file():
        refuse("codex-config-ref", "Codex config.toml 不存在，无法定位 marketplace ref。")
    lines = path.read_bytes().splitlines(keepends=True)
    headers = [index for index, line in enumerate(lines)
               if line.rstrip(b"\r\n") == b"[marketplaces.spec-guard-marketplace]"]
    if len(headers) != 1:
        refuse("codex-config-ref", "Codex 配置必须恰好有一个 [marketplaces.spec-guard-marketplace] 节。")
    start = headers[0] + 1
    end = next((index for index in range(start, len(lines)) if lines[index].startswith(b"[")), len(lines))
    matches = [(index, re.fullmatch(rb'ref = "([^"\r\n]*)"', lines[index].rstrip(b"\r\n")))
               for index in range(start, end)]
    matches = [(index, match) for index, match in matches if match is not None]
    if len(matches) != 1:
        refuse("codex-config-ref", 'Codex marketplace 节内必须恰好有一行 ref = "..."。')
    index, match = matches[0]
    previous = match.group(1).decode("utf-8")
    target = "v" + version
    ending = lines[index][len(lines[index].rstrip(b"\r\n")):]
    lines[index] = ('ref = "%s"' % target).encode("utf-8") + ending
    backup = None
    if previous != target:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        backup = state_dir("release") / "backups" / ("config.toml.%s.%s" % (version, timestamp))
    return b"".join(lines), previous, target, backup


def update_codex_config(path, replacement, backup):
    if backup is None:
        return
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, backup)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".release-", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(replacement)
        shutil.copymode(path, temporary)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def compare_plugin(reference, installed, host, ignore_marker=False):
    """Compare relative file paths and bytes against the extracted release plugin."""
    if not installed.is_dir():
        raise ReleaseError("%s 安装目录不存在：%s。" % (host, installed))
    expected = {path.relative_to(reference): path for path in reference.rglob("*") if path.is_file()}
    actual = {path.relative_to(installed): path for path in installed.rglob("*")
              if path.is_file() and not (ignore_marker and path.relative_to(installed) == Path(".in_use"))}
    missing = expected.keys() - actual.keys()
    extra = actual.keys() - expected.keys()
    if missing or extra:
        raise ReleaseError("%s 安装文件集合不符：缺少 %s；多出 %s。" %
                           (host, ", ".join(str(path) for path in sorted(missing)) or "无",
                            ", ".join(str(path) for path in sorted(extra)) or "无"))
    for relative in sorted(expected):
        if expected[relative].read_bytes() != actual[relative].read_bytes():
            raise ReleaseError("%s 安装文件内容不符：%s。" % (host, relative))


def install_release(args):
    record = read_record(args.version)
    require_step(record, "publish")
    directory = Path(tempfile.mkdtemp(prefix=TEMP_PREFIX))
    try:
        with tarfile.open(record["steps"]["prepare"]["asset"], "r:gz") as archive:
            extract(archive, directory)
        reference = directory / ("spec-guard-v" + args.version) / "plugins/spec-guard"
        if not reference.is_dir():
            raise ReleaseError("发布包中没有参照插件目录：%s。" % reference)
        config = args.codex_home / "config.toml"
        replacement, ref_from, ref_to, backup = codex_ref_change(config, args.version)
        claude_commands = [["claude", "plugin", "marketplace", "update", "spec-guard-marketplace"],
                           ["claude", "plugin", "update", "spec-guard@spec-guard-marketplace"]]
        upgrade = ["codex", "plugin", "marketplace", "upgrade", "spec-guard-marketplace"]
        print("将更新并核对 Claude 与 Codex 插件：")
        for command in claude_commands:
            print(shlex.join(command))
        print("Codex 配置 %s：ref 从 %s 到 %s；备份：%s。" %
              (config, ref_from, ref_to, backup if backup is not None else "无需修改或备份"))
        print(shlex.join(upgrade))
        if not args.confirm:
            return {"status": "preview"}
        for command in claude_commands:
            run(command, check=True)
        data = json.loads((args.claude_home / "plugins/installed_plugins.json").read_bytes())
        plugins = data.get("plugins") if isinstance(data, dict) else None
        entries = plugins.get("spec-guard@spec-guard-marketplace") if isinstance(plugins, dict) else None
        claude = entries[0] if isinstance(entries, list) and entries else None
        if not isinstance(claude, dict):
            raise ReleaseError("Claude installed_plugins.json 没有 spec-guard 的安装记录。")
        for field, expected in (("version", args.version), ("gitCommitSha", record["mergeCommit"])):
            if claude.get(field) != expected:
                raise ReleaseError("Claude %s 不符：期望 %s，实际 %s。" % (field, expected, claude.get(field)))
        compare_plugin(reference, Path(claude["installPath"]), "Claude", ignore_marker=True)
        claude_facts = {"version": claude["version"], "commit": claude["gitCommitSha"],
                        "updatedAt": claude["lastUpdated"], "installPath": claude["installPath"]}
        update_codex_config(config, replacement, backup)
        run(upgrade, check=True)
        upgraded_at = utc_now()
        data = json.loads(run(["codex", "plugin", "list", "--json"], check=True)[1])
        entries = data.get("installed") if isinstance(data, dict) else None
        codex = next((entry for entry in entries if isinstance(entry, dict) and entry.get("name") == "spec-guard"),
                     None) if isinstance(entries, list) else None
        if codex is None:
            raise ReleaseError("Codex plugin list 中没有 spec-guard 的安装记录。")
        if codex.get("version") != args.version:
            raise ReleaseError("Codex version 不符：期望 %s，实际 %s。" % (args.version, codex.get("version")))
        if codex.get("enabled") is not True:
            raise ReleaseError("Codex enabled 不是 true。")
        source = codex["source"]["path"]
        compare_plugin(reference, Path(source), "Codex")
        codex_facts = {"version": codex["version"], "source": source, "upgradedAt": upgraded_at,
                       "backup": str(backup) if backup is not None else None, "refFrom": ref_from, "refTo": ref_to}
        write_record(record, "install", {"status": "ok", "claude": claude_facts, "codex": codex_facts, "at": utc_now()})
        print("两侧安装的版本与文件已核对，Claude 更新时间 %s；Codex 升级完成时间 %s。" %
              (claude_facts["updatedAt"], upgraded_at))
        return {"status": "ok", "claude": claude_facts, "codex": codex_facts}
    finally:
        remove_temporary(directory)


def chatgpt_restart(upgraded_at):
    """Compare the desktop main process's local start time with the recorded upgrade."""
    unknown = {"state": "unknown", "startedAt": None}
    try:
        code, output, _ = run(["ps", "-axo", "lstart=,command="])
        if code:
            return unknown
        for line in output.decode("utf-8", errors="replace").splitlines():
            match = re.fullmatch(r"\s*(\w+\s+\w+\s+\d+\s+\d{2}:\d{2}:\d{2}\s+\d{4})\s+"
                                 r"(.*/ChatGPT\.app/Contents/MacOS/ChatGPT)", line)
            if match:
                started = datetime.strptime(match[1], "%a %b %d %H:%M:%S %Y").astimezone(timezone.utc)
                upgraded = datetime.fromisoformat(upgraded_at.replace("Z", "+00:00"))
                if upgraded.tzinfo is None:
                    return unknown
                return {"state": "restarted" if started > upgraded else "not-restarted",
                        "startedAt": started.strftime("%Y-%m-%dT%H:%M:%SZ")}
    except (ReleaseError, ValueError, TypeError, AttributeError, OverflowError):
        return unknown
    return unknown


def smoke_release(args):
    record = read_record(args.version)
    installed = require_step(record, "install")
    source = args.expected_source if args.expected_source is not None else installed["codex"]["source"]
    command = ["/bin/bash", str(args.repo / "evals/codex-plugin-smoke.sh"), "--plugin-id",
               "spec-guard@spec-guard-marketplace", "--expected-source", str(source)]
    print("正在运行 Codex 插件 smoke，最长等待 600 秒。")
    try:
        code, stdout, stderr = run(command, timeout=600, stdin=subprocess.DEVNULL)
        output = "\n".join(part.decode("utf-8", errors="replace").rstrip("\n")
                           for part in (stdout, stderr) if part)
    except ReleaseError as error:
        code, output = None, str(error)
    if code == 0:
        status = "ok"
        print("Codex 插件 smoke 通过。")
    elif code == 2 and "未观察到宿主 hook 事件" in output:
        status = "waiting-on-user"
        print("Codex 升级后 hook 的批准失效了：请在新开的终端里启动命令行 `codex`，"
              "在 `/hooks` 里批准 spec-guard 的 hook，然后重跑本命令")
    else:
        status = "failed"
        print("Codex 插件 smoke 失败（退出码 %s），最后 5 行输出：\n%s" %
              (code, "\n".join(output.splitlines()[-5:])))
    cli = None
    try:
        cli_code, cli_output, _ = run(["codex", "--version"])
        lines = cli_output.decode("utf-8", errors="replace").splitlines()
        if cli_code == 0 and lines:
            cli = lines[0]
    except ReleaseError:
        pass
    chatgpt = chatgpt_restart(installed["codex"]["upgradedAt"])
    if chatgpt["state"] == "not-restarted":
        print("ChatGPT 尚未在安装后重开：请用 ⌘Q 退出 ChatGPT 再打开。")
    elif chatgpt["state"] == "restarted":
        print("ChatGPT 已在安装后重开，主进程启动时间为 %s。" % chatgpt["startedAt"])
    else:
        print("未能核实 ChatGPT 主进程的启动时间。")
    write_record(record, "smoke", {"status": status, "exitCode": code, "codexCli": cli,
                                   "chatgpt": chatgpt, "at": utc_now()})
    return {"status": status, "exitCode": code, "chatgpt": chatgpt}


def evidence_release(args):
    record = read_record(args.version)
    for step in ("check", "prepare", "publish", "install"):
        require_step(record, step)
    prepared = record["steps"]["prepare"]
    published = record["steps"]["publish"]
    installed = record["steps"]["install"]
    claude, codex = installed["claude"], installed["codex"]
    smoke = record["steps"].get("smoke")
    now = datetime.now(timezone.utc)
    observed_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    tag, sha = "v" + args.version, record["mergeCommit"]
    asset = Path(prepared["asset"]).name

    def verified(subject, status, kind, target, evidence):
        return {"subject": subject, "status": status, "target": {"kind": kind, "id": target},
                "observedAt": observed_at, "evidence": evidence}

    documents = {
        "source": verified("spec-guard-source", "source-verified", "source-checkout", "commit:" + sha, [
            "result:the %s annotated tag resolves to merge commit %s (pull request #%s); "
            "merged==true and main==merge sha were checked before tagging; "
            "the CI run on the tagged merge commit succeeded" % (tag, sha, record["pr"]),
            *["result:" + note for note in args.note]]),
        "package": verified("spec-guard-release-artifact", "package-verified", "package",
            "release:%s;asset:%s;sha256:%s" % (tag, asset, prepared["sha256"]), [
                "release:" + published["url"], "asset:%s;size:%s" % (asset, prepared["size"]),
                "source-tag:%s@%s" % (tag, sha),
                "command:git archive --prefix=spec-guard-%s/ %s .claude-plugin plugins/spec-guard" % (tag, tag),
                "command:python3 scripts/release-package.py validate <dir> " + args.version,
                "result:built from the merge commit the tag points to; no `._*` entries; validated before "
                "packing and again after extracting; the asset downloaded from the Release has the same "
                "SHA-256 (%s); the Release notes carry the %s CHANGELOG section; "
                "the Release is marked latest (releases/latest returns %s)" %
                (published["downloadSha256"], args.version, published["tag"])]),
        "claude": verified("spec-guard-claude", "host-verified", "host-session",
            "claude-code;plugin:spec-guard@spec-guard-marketplace;sha:" + sha, [
                "command:claude plugin marketplace update spec-guard-marketplace && "
                "claude plugin update spec-guard@spec-guard-marketplace",
                "result:installed_plugins.json records version %s, updated at %s and gitCommitSha %s "
                "(the tag); the installed plugin directory is identical to the release asset apart from "
                "Claude Code's own .in_use marker" % (claude["version"], claude["updatedAt"], claude["commit"])])}
    codex_target = {"kind": "host-session", "id": "codex-cli;test:%s-upgrade-%s" % (tag, now.strftime("%Y%m%d"))}
    install_result = ("the marketplace ref moved from %s to %s; codex plugin marketplace upgrade exited 0 "
                      "at %s; the snapshot is identical to the release asset; "
                      "codex plugin list --json shows spec-guard %s enabled" %
                      (codex["refFrom"], codex["refTo"], codex["upgradedAt"], codex["version"]))
    if isinstance(smoke, dict) and smoke.get("status") == "ok":
        source = Path(codex["source"])
        if source.is_relative_to(Path.home()):
            source = Path("~") / source.relative_to(Path.home())
        command = ["/bin/bash", "evals/codex-plugin-smoke.sh", "--plugin-id",
                   "spec-guard@spec-guard-marketplace", "--expected-source", str(source)]
        chatgpt = smoke["chatgpt"]
        if chatgpt["state"] == "unknown":
            desktop_result = "the ChatGPT desktop app restart and main process start time were not verified"
        else:
            desktop_result = ("the ChatGPT desktop app was %s after the install; its main process started %s "
                              "(checked with ps)" %
                              ("restarted" if chatgpt["state"] == "restarted" else "not restarted", chatgpt["startedAt"]))
        documents["codex"] = verified("spec-guard-codex", "host-verified", "host-session", codex_target["id"], [
            "command:" + shlex.join(command) + " </dev/null", "result:" + install_result,
            "result:%s; the smoke exited 0 on its first run" %
            (smoke["codexCli"] if smoke["codexCli"] is not None else "Codex CLI version was not verified"),
            "result:" + desktop_result])
    else:
        if not isinstance(smoke, dict):
            reason = "the smoke was not run"
        elif smoke.get("status") == "waiting-on-user":
            reason = "the hooks were not re-approved after the upgrade; the smoke is waiting on the user"
        else:
            reason = "the smoke did not succeed (status %s, exit code %s)" % (smoke.get("status"), smoke.get("exitCode"))
        documents["codex"] = {"subject": "spec-guard-codex", "status": "not-verified", "target": codex_target,
                              "reason": "installed: %s, but %s" % (install_result, reason)}
    directory = args.output_dir if args.output_dir is not None else args.repo / "docs/releases"
    directory.mkdir(parents=True, exist_ok=True)
    files = []
    for name, evidence in documents.items():
        path = directory / ("%s-%s.json" % (tag, name))
        data = {"schemaVersion": 1, "release": {"version": args.version}, "records": [evidence]}
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        files.append(str(path))
    for filename in files:
        code, stdout, stderr = run(["python3", "-B", str(args.repo / "scripts/release-evidence.py"), "validate", filename])
        if code:
            output = (stdout + stderr).decode("utf-8", errors="replace").strip()
            raise ReleaseError("证据校验失败：%s（退出码 %s）：%s" % (filename, code, output))
    write_record(record, "evidence", {"status": "ok", "files": files, "at": utc_now()})
    print("四份发版证据已写入 %s，逐份校验通过。" % directory)
    return {"status": "ok", "files": files}


class Parser(argparse.ArgumentParser):
    def error(self, message):
        refuse("invalid-arguments", "命令参数错误：%s" % message)


def parser():
    result = Parser(description="检查、准备、发布、安装与验证 Spec Guard 发版。")
    commands = result.add_subparsers(dest="step", required=True)
    result.add_argument("--repo", default=str(ROOT))
    result.add_argument("--remote", default="origin")
    result.add_argument("--github")
    for step, handler in (("check", check_release), ("prepare", prepare_release),
                          ("publish", publish_release), ("install", install_release),
                          ("smoke", smoke_release), ("evidence", evidence_release)):
        command = commands.add_parser(step)
        for option in ("--repo", "--remote", "--github"):
            command.add_argument(option, default=argparse.SUPPRESS)
        command.set_defaults(handler=handler)
        if step == "check":
            command.add_argument("--pr", type=int, required=True)
        else:
            command.add_argument("--version", required=True)
        if step in ("publish", "install"):
            command.add_argument("--confirm", action="store_true")
        if step == "install":
            command.add_argument("--claude-home", type=Path, default=Path.home() / ".claude")
            command.add_argument("--codex-home", type=Path, default=Path.home() / ".codex")
        if step == "smoke":
            command.add_argument("--expected-source", type=Path)
        if step == "evidence":
            command.add_argument("--note", action="append", default=[])
            command.add_argument("--output-dir", type=Path)
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
