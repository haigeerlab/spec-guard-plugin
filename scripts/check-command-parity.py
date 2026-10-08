#!/usr/bin/env python3
"""校验 commands/*.md 引用的每个 hooks/<脚本> 都在至少一个 skill 里有对应路由。

背景（spec/audit-remediation.md R4）：Claude Code 走 `commands/*.md`（slash 命令），
Codex 走 `skills/*/SKILL.md`——两者是各自独立读取的合同，互不兜底。命令文件新增了一次
`hooks/<脚本>` 调用而没有把同样的路由写进任何 skill，Codex 侧就永远够不到它。
2026-09-28 审计就是这么发现 `spec-guard-ops` 缺 teardown 一节（`docs/workflow.md:136`
声称有，实际没有）；那次是靠人工通读发现的，本检查器把它自动化。

判据刻意保持字面：抓 `commands/*.md` 里出现的 `hooks/<name>.py` / `hooks/<name>.sh`
字面引用（与命令自身完全相同的路径形态），确认这个**字面串**在至少一个
`skills/*/SKILL.md` 全文中也出现过。

参数级（2026-10-08 审查 F8）：命令里调用某脚本的那一条命令行（反斜杠续行拼接后）上的每个
`--flag`，也必须出现在某个同样引用了该脚本的 skill 全文里；否则 Codex 拿不到正确的调用方式
（实测时缺了账本 `initialize` 的四个参数）。不检查子命令是否对称——那是内容审查。

刻意的不对称写进下面的 ALLOWLIST，每条一行理由。按 docs/lenses.md A5：零个命令文件
或零个 skill 文件是“没找到”，不是“没问题”，判失败。
"""
import pathlib
import re
import sys

HOOK_REF = re.compile(r"hooks/[A-Za-z0-9_.-]+\.(?:py|sh)")
FLAG = re.compile(r"(?<![\w-])--[a-z][a-z0-9-]+")


def invocations(text):
    """逐条命令行返回，反斜杠续行拼成一行。"""
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        while line.rstrip().endswith("\\") and index + 1 < len(lines):
            index += 1
            line = line.rstrip()[:-1] + " " + lines[index]
        yield line
        index += 1

# 刻意不对称的入口：<命令文件名> -> {字面引用: 理由}
# 目前为空——local-ticket-ledger.md 曾经唯一的不对称（hooks/local_ledger_adapters.py
# 的 install-codex 路由没写进 local-ticket-ledger-ops skill）已经在同一次改动里
# 补进 skill，不再需要豁免。
ALLOWLIST: dict[str, dict[str, str]] = {}


def main() -> int:
    # 可传入另一个仓库根（测试夹具用），默认检查本仓库。
    root = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parents[1]
    plugin = root / "plugins/spec-guard"
    commands_dir = plugin / "commands"
    skills_dir = plugin / "skills"

    command_files = sorted(commands_dir.glob("*.md")) if commands_dir.is_dir() else []
    skill_files = sorted(skills_dir.glob("*/SKILL.md")) if skills_dir.is_dir() else []

    # 「0 处不对称」和「0 个命令文件 / 0 个 skill 文件」在退出码上不能长得一样
    # （docs/lenses.md A5）——找不到输入就是没查过，不是查过没问题。
    if not command_files:
        print("  ❌ 0 个 plugins/spec-guard/commands/*.md —— 这是没找到，不是没问题", file=sys.stderr)
        return 1
    if not skill_files:
        print("  ❌ 0 个 plugins/spec-guard/skills/*/SKILL.md —— 这是没找到，不是没问题", file=sys.stderr)
        return 1

    skill_texts = [path.read_text(encoding="utf-8") for path in skill_files]
    skill_text = "\n".join(skill_texts)

    ok = True
    checked = 0
    for cmd_path in command_files:
        checked += 1
        text = cmd_path.read_text(encoding="utf-8")
        allow = ALLOWLIST.get(cmd_path.name, {})
        for ref in sorted(set(HOOK_REF.findall(text))):
            if ref in allow:
                continue
            if ref in skill_text:
                continue
            print(f"  ❌ {cmd_path.relative_to(root)} 引用了 {ref}，"
                  f"但没有任何 skill 提供这条路由（Codex 够不到这条命令）")
            ok = False
        for line in invocations(text):
            for ref in sorted(set(HOOK_REF.findall(line))):
                if ref in allow:
                    continue
                routes = "\n".join(body for body in skill_texts if ref in body)
                if not routes:
                    continue  # 上面已按“没有路由”报过
                for flag in sorted(set(FLAG.findall(line))):
                    if flag not in routes:
                        print(f"  ❌ {cmd_path.relative_to(root)} 给 {ref} 传了 {flag}，"
                              f"但引用该脚本的 skill 里都没有这个参数（Codex 拿不到正确调用）")
                        ok = False

    if ok:
        print(f"  ✅ {checked} 个命令文件，引用的 hooks/ 脚本在 skill 中都有路由")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
