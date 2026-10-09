# Plan: local-check-dedup

依据 [`spec/local-check-dedup.md`](../../spec/local-check-dedup.md)（用户 2026-10-09“按推荐，批准 Spec”）。分支
`claude/local-check-dedup`。以 `--interrupt` 插入：`self-report-tmpdir-independence` 剩余两项等发版。本模块起按分开审。

## Task List

### Task 0：本机准备（不入库）

把 `.agent/state.json` 加进共用的 `.git/info/exclude`。它是本机的当前模块书签；不忽略的话按假设 7，本仓库每次提交都
不会写记录。只改本机 git 配置，不改仓库文件。

### Task 1：`validate.sh --quick`

回归先行：在 `scripts/test-checkers.sh` 或新用例里断言 `--quick` 跑完假设 5 的各节、不跑任何回归套件、能拦下一个结构
错误（如坏掉的 JSON）、不带参数时行为不变。实现后实测 `--quick` 耗时写进 todo。

### Task 2：`verify-and-commit.sh` 分档、并行与记录

回归先行（`test_verify_and_commit.py`）：快档与全套的路径分界（含拿不准的路径走全套）；快档不调用 validate 全量；全套
三套并行、任一失败不提交并逐项报出；提交成功后记录 tree 与档位，失败时不记录，有未跟踪文件时不记录并说明；不再自动加跑
setup-teardown 与 pre-push。实现后变异：快档放进一个 `scripts/` 路径；失败时仍写记录；有未跟踪文件仍写记录。

### Task 3：pre-push 按记录跳过

回归先行（`test_pre_push_environment.py`，真实本地推送）：全套记录过的提交推送时跳过；快档提交在父提交已记录时跳过；
照常全跑的情况——记录里没有该 tree、快档提交改了快档外路径、父提交未记录、已跟踪文件有未提交改动、合并提交只有快档记录、
记录文件缺失；照常全跑时任一检查失败仍拦截。实现后变异：去掉父提交检查；去掉工作区检查；合并提交接受快档记录。
安装提示耗时改为实测值。

### Task 4：本仓库改回分开审与文档

删 `.agent/config.json` 的 `reviewCadence`；`docs/maintainer-workflow.md`“提交前”、`CLAUDE.md`“最小验证”写明档位、
记录与跳过规则。

### Checkpoint 1（report）：全部回归通过，ShellCheck 无告警；本模块的提交用改进后的脚本

### Task 5：实测验收

在本分支上用改进后的脚本与重新安装的钩子：一个纯文档提交、一个脚本改动提交各走一遍“提交 → 推送”，前后计时写进
todo。目标：纯文档提交加推送 30 秒以内；脚本改动提交 4 分钟以内，推送跳过全套。

### Checkpoint 2（gate）：模块评审

本 Plan 获批即授权推送本分支、开本模块 PR，以及合并后重新安装本机 pre-push 钩子；合并由用户进行。

### Task 6：下次发版时补证据
