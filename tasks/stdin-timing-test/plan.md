# Plan: stdin-timing-test

<!-- spec-guard: review approved -->

依据 [`spec/stdin-timing-test.md`](../../spec/stdin-timing-test.md)（已批准）。本仓库评审节奏为分开审：Spec 已批准，本 Plan 单独交审。
分支 `claude/stdin-timing-test`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `811341d`（0.70.2 发版收尾）开出。
本模块一个 PR，**不改版本号**：随下一个有功能变化的版本一起发，CHANGELOG 先写在「未发布」下。

所需工具：无 UI 改动；反向验证在临时草稿副本里做，不提交。

## Overview

只改 `hooks/test-phase-guard.sh` 第 9 段「标准输入一直不关闭」那一条用例：先量关闭标准输入的基础耗时，再断言不关闭时多出的等待小于 2 秒；
不关闭的那次加 15 秒计时器，挂住就杀进程判失败。hook 代码不动。

## Architecture Decisions

- **同一次运行里对比。** 基础耗时与被测耗时用同一个夹具、同一组环境变量，前后紧挨着跑，机器快慢对两者的影响相同。
- **用计时器而不是阻塞读。** 不关闭标准输入的那次用 `threading.Timer` 到时杀进程，读输出不会永远卡住。
- **用例名与成功行可读。** 失败信息写出两个耗时，或写明「挂住」，一眼能看出是哪种失败。

## Task List

### Task 0：提交已批准的 Plan 与 todo

- 验收：`verify-and-commit.sh` 快档通过并提交。
- 文件：`tasks/stdin-timing-test/plan.md`、`tasks/stdin-timing-test/todo.md`。

### Task 1：改写这条用例并做反向验证

改写用例；在当前代码上确认通过（本机 base 约 0.2 秒、open 约 1.2 秒）。再在临时草稿副本（`git archive` 出的 hooks 目录）里做两次反向验证：
- 把 `read_hook_input` 的等待改成 4 秒：新用例失败，信息写明多出的等待超限；
- 改成一直等：新用例约 15 秒后失败，信息写明挂住，测试整体不卡死。
两次的结果记进 todo，草稿副本不进仓库。

- 验收：phase-guard 回归全绿，用例总数不变；两次反向验证都按预期失败。
- 文件：`hooks/test-phase-guard.sh`。

### Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无告警

### Task 2：CHANGELOG

CHANGELOG 顶部新增「未发布」一节，记一条维护者工具：这条计时用例改为对比基础耗时、挂住时判失败。版本号不改。

- 验收：`validate.sh` 通过。
- 文件：`CHANGELOG.md`。

### Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行

列出实际改动、验证结果与未验证项；拟回告：无（本模块由用户本人提出）。合并后看 main 上的 CI 是否通过这条用例，结果记进 todo 末项。

### 合并后的 CI 核对

PR 合并后看 main 的 CI：这条用例通过，记下耗时；不单独发版，所以没有宿主同步与发版证据。
