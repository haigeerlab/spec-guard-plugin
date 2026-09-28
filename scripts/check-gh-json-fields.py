#!/usr/bin/env python3
"""校验仓库里写到的 `gh <sub> view|list --json <字段>` 都是真实存在的字段。

既查文档与 shell 里的命令行写法，也查 Python 里 `["gh", "issue", "list", ..., "--json", "<字段>"]`
这种参数列表写法 —— 插件里现存唯一的 `--json` 调用就是后者（proposal_tracker_read.py）。

为什么要有它：这个仓库已经两次把不存在的东西写进操作步骤 ——
`gh issue list --parent`（那个 flag 只在 create 上），以及
`gh issue view --json dependencies`（真实字段叫 `blockedBy`）。
两次都是**每次跑都会硬失败**的命令，两次都在文档里躺了很久。

它跟 check-bash32 / check-grep-pipe 不同：**判据不是冻结的清单，是问 gh 本人**。
`gh <sub> view --json <乱写>` 会打印合法字段表，而且这一步是 gh **本地**做的 ——
不需要仓库上下文、不需要网络、不需要登录（实测 GH_HOST 指向不存在的主机也照常打印）。

gh 不可用时**干净跳过**并说明「跳过不代表通过」——
本仓的规矩是探测失败就降级，不假阻塞。
"""
import re
import shutil
import subprocess
import sys

USE = re.compile(r"gh\s+(issue|pr|repo)\s+(view|list)\b[^\n]*?--json\s+([A-Za-z][A-Za-z,]*)")
ARGV = re.compile(r'"gh",\s*"(issue|pr|repo)",\s*"(view|list)"[^\]]*?"--json",\s*"([A-Za-z][A-Za-z,]*)"')


def valid_fields(sub: str, verb: str):
    """问 gh 要 `gh <sub> <verb>` 的合法字段表。拿不到就返回 None。"""
    # `gh issue view` 必须带一个编号才走到字段校验（不带的话先报
    # "accepts 1 arg(s), received 0"）。给个 1 即可 —— 字段校验在**取数据之前**，
    # 这个 issue 存不存在都不影响。`list` 给一个任意 --repo，同样在联网前校验字段。
    if verb == "view":
        target = ["1"] if sub in ("issue", "pr") else []
    else:
        target = ["--repo", "a/b"] if sub in ("issue", "pr") else []
    argv = ["gh", sub, verb] + target + ["--json", "__probe__"]
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=15)
    except Exception:
        return None
    out = r.stdout + r.stderr
    if "Available fields:" not in out:
        return None
    tail = out.split("Available fields:", 1)[1]
    fields = {ln.strip() for ln in tail.splitlines() if ln.strip() and " " not in ln.strip()}
    return fields or None


def main() -> int:
    if not sys.argv[1:]:
        print("  ❌ 没有传入任何文件 —— 这不是「没问题」，是「什么都没查」")
        return 1

    if shutil.which("gh") is None:
        print("  ⏭  gh 未安装，跳过 --json 字段校验（不代表通过）")
        return 0

    cache, ok, checked = {}, True, 0
    for path in sys.argv[1:]:
        try:
            text = open(path, encoding="utf-8").read()
        except (OSError, UnicodeDecodeError):
            continue
        for sub, verb, fieldlist in USE.findall(text) + ARGV.findall(text):
            if (sub, verb) not in cache:
                cache[(sub, verb)] = valid_fields(sub, verb)
            known = cache[(sub, verb)]
            if known is None:
                print(f"  ⏭  问不到 `gh {sub} {verb}` 的字段表，跳过（不代表通过）")
                continue
            for f in [x for x in fieldlist.split(",") if x]:
                checked += 1
                if f not in known:
                    print(f"  ❌ {path}: `gh {sub} {verb} --json {f}` —— 没有这个字段。"
                          f"合法值跑 `gh {sub} {verb} --json x` 看")
                    ok = False
    if ok:
        print(f"  ✅ gh --json 字段全部存在（校验了 {checked} 个）")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
