# Plan: phase-guard-test-parallel

依据 [`spec/phase-guard-test-parallel.md`](../../spec/phase-guard-test-parallel.md)（用户 2026-10-09 批准 Spec）。分开审：本 Plan
单独批准。分支 `claude/phase-guard-test-parallel`；提交一律走 `scripts/verify-and-commit.sh`。

## Task List

### Task 1：改前基线

在未改的文件上跑一次，存下全部 `✅` 行（按顺序）与用例数，记下墙钟、CPU 与负载。之后每一步都拿它逐行比对。

### Task 2：挪纯函数、定切点

- 把跨段用到的纯函数定义挪到公共部分，只移动不改内容；跑一遍，`✅` 行与基线逐行相同。
- 用脚本按用例数选 4–6 个切点（落在已有段落注释处），列出每段跨段用到的夹具。

### Task 3：分段与调度

- 各段包进 `part_N()`；跨段夹具在用到它的段里按原建法再建一份（只复制建夹具的行）；每段 `WORK=$WORK/part-N`。
- 末尾调度：后台子 shell 同时跑各段，输出按段序打印，汇总通过数；任一段失败打印它的输出、末尾报出第几段、退出 1。
  `SG_VALIDATE_JOBS=1` 时逐段串行。
- 用脚本核对每段只用到公共部分与本段定义的名字。

验证：
- 并行与串行两种方式的 `✅` 行都与基线逐行相同，最后一行 `phase-guard regression passed (190 cases)`；
- 变异：第一段、最后一段各改坏一条断言；删掉一个挪上来的函数。三次都整体退出 1 并报出对应段，改完还原；
- `/bin/bash` 3.2 通过，CI 同版本 ShellCheck 无告警。

### Task 4：稳定性与计时

连跑 5 遍全绿，每遍前后对比仓库 `git status --porcelain --ignored`。相近负载下计时改后，对照 20 秒目标；经
verify-and-commit 全档提交，记下 phase-guard 与 validate 各自的耗时。

### Checkpoint 1（gate）：模块评审

全部回归通过，ShellCheck 无告警。本 Plan 获批即授权推送本分支并开本模块 PR，合并由用户进行。PR 合并后记下 CI 改前、
改后 phase-guard 步骤的用时。

### Task 5：下次发版

包里的 `test-phase-guard.sh` 随下次发版发出：发版证据里在安装副本上跑一遍；CHANGELOG 的"维护者工具"写一条。
