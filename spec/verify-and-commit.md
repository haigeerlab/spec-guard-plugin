# Spec: verify-and-commit

## Objective

“校验没过却照样提交”在本仓库出现了 4 次，每次写法不同：用 `;` 连接、日志路径写错、`validate.sh | tail -1 && git commit`
被管道吞掉退出码。记忆里的规则防不住新的写法，需要一个脚本来把关：只有检查全部通过才提交。来源：「spec-guard 插件根目录
解析检查」会话观测到的候选，用户 2026-10-09 选定做法 A（封装脚本）。

读者：本仓库维护者（人或 agent）。

## Assumptions

用户于 2026-10-09 确认：

1. 用法 `scripts/verify-and-commit.sh [--suite NAME]... -- <git commit 参数>`。只提交已暂存的内容，脚本不做 `git add`；
   已跟踪文件里有未暂存改动、或没有任何已暂存改动时拒绝。
2. 每次都跑 validate、phase-guard、verify-artifacts；按已暂存路径自动加跑：setup/teardown/managed-block 相关 →
   setup/teardown 回归；钩子安装脚本或其测试 → pre-push 回归；任何 `.sh` → CI 用的 ShellCheck。`--suite` 可手动加。
   ShellCheck 无法运行时判失败，不跳过。
3. 每套检查的完整输出写进临时日志，屏幕每套一行结果；失败时列出失败行与日志路径、退出非零、不提交。脚本用
   `set -euo pipefail`，成败只看各检查自己的退出码，不经过管道。
4. 不负责推送；推送仍由 pre-push 钩子把关。
5. 回归 `scripts/test_verify_and_commit.py` 在临时仓库里用桩脚本代替真实检查，登记进 `validate.sh`。
6. `docs/maintainer-workflow.md` “提交前”一节写用法，`CLAUDE.md` “最小验证”加一句提交走它。
7. 不改插件发布包与版本号，随统一发版 0.55.0。

## Requirements

1. 新建 `scripts/verify-and-commit.sh`，只依赖 `bash`、`git`、`python3`（ShellCheck 另需 `npx`）。拒绝与失败时
   不创建提交、不改暂存区；成功时把 `--` 之后的参数原样交给 `git commit`。
2. 套件名固定：`validate`、`phase-guard`、`verify-artifacts`、`setup-teardown`、`pre-push`、`shellcheck`；未知名称是
   用法错误（退出 2）。
3. 回归覆盖：全部通过时生成提交且提交内容等于暂存内容；任一套件失败时不提交、报出套件名与日志路径；桩先输出再失败时
   照样不提交；有未暂存改动、没有暂存内容、缺少 `--` 时拒绝；按暂存路径自动加跑对应套件，`--suite` 手动加跑；
   未知套件退出 2。新断言先红，再手动改坏实现确认会变红。
4. 文档两处。

## Commands

```bash
/bin/bash scripts/validate.sh
python3 -B scripts/test_verify_and_commit.py
```

## Boundaries

- Always：测试只用临时目录里的仓库；检查失败绝不提交。
- Ask first：推送、PR。
- Never：脚本执行 `git add`、推送或改暂存区；改插件发布包或版本号。

## Success criteria

1. 任何一套检查失败时都不会产生提交，无论输出多少、怎么失败。
2. 维护者只需一条命令完成“检查通过才提交”。

## Open questions

无。
