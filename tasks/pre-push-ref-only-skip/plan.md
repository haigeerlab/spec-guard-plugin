# Plan: pre-push-ref-only-skip

依据 [`spec/pre-push-ref-only-skip.md`](../../spec/pre-push-ref-only-skip.md)（假设经用户 2026-10-09 确认）。
分支 `claude/pre-push-ref-only-skip`。本仓库评审节奏为合审：Spec 与本 Plan 一次批准。

## Task List

### Task 1：回归先行（先红）

在 `test_pre_push_environment.py` 加用例：只删远端分支时三套检查调用 0 次且远端分支已删；只推 tag 时调用 0 次且 tag
到达远端；分支与 tag 一起推时调用 3 次。在现有钩子上前两例为红。

### Task 2：钩子实现

`install-git-hooks.sh` 生成的钩子读取 stdin，全部为删除或 tag 时打印跳过原因并退出 0；否则照旧。测试转绿，原有用例
不变。变异：把 tag 判定放宽到任意 ref（混推用例变红）；去掉删除判定（删除用例变红）；跳过时不读完 stdin 照常全跑。

### Task 3：文档

`docs/maintainer-workflow.md` “提交前”一节写明跳过规则。

### Checkpoint 1（report）：validate 与 pre-push 回归通过，ShellCheck 无告警

### Checkpoint 2（gate）：模块评审

本 Plan 获批即授权推送本分支并开本模块 PR；合并由用户进行。

### Task 4：重新安装本机钩子

合并后在主线上运行 `scripts/install-git-hooks.sh`，确认 `.git/hooks/pre-push` 与新生成文本一致，并用一次真实的删分支
推送确认跳过。

### Task 5：0.55.0 统一发版时补证据
