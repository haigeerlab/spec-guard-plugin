# Plan: verify-and-commit

依据 [`spec/verify-and-commit.md`](../../spec/verify-and-commit.md)（假设经用户 2026-10-09 确认）。分支
`claude/verify-and-commit`。以 `--interrupt` 插入：`self-observation-report` 与 `pre-push-ref-only-skip` 的剩余勾选
分别由观测会话的分支与 0.55.0 发版 PR 完成。本仓库评审节奏为合审：Spec 与本 Plan 一次批准。

## Task List

### Task 1：回归先行（先红）

新建 `scripts/test_verify_and_commit.py`：在临时仓库里放入脚本副本与各套件的桩，覆盖 Spec 需求 3 的全部情形。脚本
尚不存在，全部为红。

### Task 2：脚本实现

新建 `scripts/verify-and-commit.sh`；回归转绿并登记进 `validate.sh`。变异：去掉失败时的中止（失败用例变红）；
改成经管道判断成败（“先输出再失败”用例变红）；去掉未暂存改动检查（对应用例变红）。

### Task 3：文档

`docs/maintainer-workflow.md` “提交前”、`CLAUDE.md` “最小验证”。

### Checkpoint 1（report）：全部套件通过，ShellCheck 无告警；本模块自己的提交从这里起改用新脚本

### Checkpoint 2（gate）：模块评审

本 Plan 获批即授权推送本分支并开本模块 PR；合并由用户进行。

### Task 4：0.55.0 统一发版时补证据
