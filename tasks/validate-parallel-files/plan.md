# Plan: validate-parallel-files

依据 [`spec/validate-parallel-files.md`](../../spec/validate-parallel-files.md)（用户 2026-10-09 批准 Spec）。分开审：本 Plan
单独批准。分支 `claude/validate-parallel-files`；提交一律走 `scripts/verify-and-commit.sh`。改前基线已在 Spec 里测好
（完整 `validate.sh` 200.7 秒，负载 15–18）。

## Task List

### Task 1：并行步骤运行器

回归先行：`scripts/test_run_steps_parallel.py` 用临时 shell 命令覆盖以下情况，运行器不存在时全红：
- 全部通过退出 0；
- 一条失败退出非零，并报出那条命令；
- 输出按原顺序（后面的步骤先结束也一样）；
- 段落标题出现在该段输出之前；
- `SG_VALIDATE_JOBS=1` 串行；`SG_VALIDATE_JOBS` 不是正整数时为用法错误；
- 步骤数核对。

再写 `scripts/run_steps_parallel.py`（只用标准库，3.9 可用）。

变异：
- 忽略某一步的退出码；
- 按结束顺序打印；
- 去掉步骤数核对。

登记进 `validate.sh`。

### Task 2：接入 validate

`validate.sh` 回归段改为把步骤（连同段落标题）交给运行器。TMPDIR 那一步改成运行器里的一条：`mktemp` 与删除留在
`validate.sh`，删除仍用固定前缀的 case 守卫。其余段落与 `--quick` 不变。

核对：
- 改前、改后的步骤总数；
- 段落标题个数（29 个）；
- `test_validate_quick.py` 通过；
- `SG_VALIDATE_JOBS=1` 的全套通过。

在一份草稿副本上让某条测试失败，确认整体失败并报出那一步。

### Task 3：共享状态实测与计时

并行版连跑 5 遍。每遍跑前、跑后对比以下内容，结果写进 todo：
- 仓库的 `git status --porcelain --ignored`；
- `.git` 下的文件列表；
- `~/.spec-guard` 与 `~/.local/state/spec-guard` 的文件列表。

有变化或偶发失败时停下来问。用系统 Python 3.9 跑运行器的回归。改后在相近负载下计时完整 `validate.sh`，记下负载，
对照 100 秒目标。

### Checkpoint 1（gate）：模块评审

全部回归通过，ShellCheck 无告警。本 Plan 获批即授权推送本分支并开本模块 PR，合并由用户进行。PR 合并后记下 CI
改前、改后的用时。

### Task 4：下次发版时写进 CHANGELOG

插件发布包不变，不另补证据。下次发版时在 CHANGELOG 的"维护者工具"里写一条。
