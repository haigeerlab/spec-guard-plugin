# Plan: slow-test-speedup

依据 [`spec/slow-test-speedup.md`](../../spec/slow-test-speedup.md)（用户 2026-10-09 批准 Spec，做法 A）。分开审：本 Plan
单独批准。分支 `claude/slow-test-speedup`；提交一律走 `scripts/verify-and-commit.sh`。

## Task List

### Task 1：改前基线

记下当时的负载（`uptime`），三个测试各跑一次计时、记下用例数（149、59、52），`validate.sh` 整体计时一次，写进 todo。

### Task 2：并行运行器

回归先行：`scripts/test_run_tests_parallel.py` 用临时测试文件覆盖——全部通过退出 0；任一类失败退出非零并报出类名；
用例总数对不上算失败；`--jobs` 指定进程数。运行器不存在时全红。再写 `scripts/run_tests_parallel.py`（只用标准库，3.9 可用）。
变异：去掉总数核对；忽略失败进程。

### Task 3：`test_module_cost_report` 夹具

模板仓库复制、环境变量代替 `git config`、合并 `add` 与 `commit`；用例数仍 149，逐个核对没有删断言。改坏被测代码一个
判据（如任务窗口切分），用并行运行器跑必须变红，立即还原。

### Task 4：`test_local_ticket_portability` 夹具

模板仓库加 worktree 复制后 `git worktree repair`、环境变量代替 `git config`；用例数仍 52；同样做一次变异证明。

### Task 5：`test_proposal_promotion_proof` 夹具

类级准备按测出的热点精简（共用只读的远端快照等）；用例数仍 59；同样做一次变异证明。

### Task 6：接入 validate 并实测

`validate.sh` 改用并行运行器跑这三个测试；系统 Python 3.9（`/usr/bin/python3`）跑三个测试；改后在相近负载下各计时一次、
validate 整体计时一次，写进 todo；对照 40 秒目标，做不到的写明原因。

### Checkpoint 1（gate）：模块评审

全部回归通过、ShellCheck 无告警；本 Plan 获批即授权推送本分支并开本模块 PR；合并由用户进行。

### Task 7：下次发版时补证据
