# Plan: self-report-tmpdir-independence

依据 [`spec/self-report-tmpdir-independence.md`](../../spec/self-report-tmpdir-independence.md)（假设经用户 2026-10-09
确认）。分支 `claude/self-report-tmpdir-test`。本仓库评审节奏为合审：Spec 与本 Plan 一次批准。

## Task List

### Task 1：回归先行（先红）

`validate.sh` 增加外部 `TMPDIR` 那一遍（目录建在 `git rev-parse --git-path` 下、用完即删）；在现有测试上这一遍为红。

### Task 2：修正用例

该用例改用固定的临时前缀路径；两种 `TMPDIR` 下 `test_self_report.py` 全部通过。变异：改回 `self.root` 推导，外部
`TMPDIR` 那一遍重新变红。

### Checkpoint 1（report）：validate 全部通过；用 `scripts/verify-and-commit.sh` 提交

### Checkpoint 2（gate）：模块评审

本 Plan 获批即授权推送本分支并开本模块 PR；合并由用户进行。

### Task 3：下次发版时补证据
