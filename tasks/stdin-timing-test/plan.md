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

## 返工：高负载下仍误报，改为失败时重测、按最小值判断（2026-10-19）

2026-10-19 这条用例在 `verify-and-commit.sh` 全档检查中失败一次：`extra wait 2.01 s (open 2.77 s, base 0.75 s)`，当时 ShellCheck 在并行跑，
重跑后通过。本机在 10 个忙循环加 ShellCheck 循环的负载下量 20 轮，单轮「多出的等待」在 −0.67 到 1.75 秒之间：负载会随机拖慢基础那次或
被测那次，单次相减的差值噪声有 ±1.5 秒，2 秒的阈值挡不住。负载只会让一次运行变慢、不会变快，所以多次取最小值能去掉这部分噪声。

契约细化（Spec 的「断言 `open - base < 2`」改为下面的判法；Spec 的成功标准「只在多出的等待超过 2 秒或 hook 挂住时失败」不变，阈值不放宽）：

- 每轮照旧先以 `stdin=DEVNULL` 跑一次得 `base`，再以不关闭的 `stdin=PIPE` 跑一次得 `open`，两次输出都要是 `BUILDING`；
- 判断量是「到目前为止各轮 `open` 的最小值 − 各轮 `base` 的最小值」，小于 2 秒即通过并停止；
- 不通过就再测一轮，最多 3 轮；3 轮后仍不小于 2 秒才失败，失败信息写出每一轮的两个耗时；
- 任何一轮被 15 秒计时器杀掉，立即以「挂住」失败，不重测。

为什么拦得住真的超时：hook 多等 4 秒时每轮 `open` 都不少于 4 秒，而 `base` 的最小值接近空载值（约 0.4 秒），差值不少于约 3.6 秒，重测几轮
都一样失败；不设超时时第一轮就被计时器判为挂住。正常情况第一轮就通过，耗时与现在相同。

### Task 3：改写判法并在高负载下验证

- 验收：
  - 当前代码上通过，phase-guard 回归用例总数不变；
  - 高负载（10 个忙循环 + ShellCheck 循环）下单独连续跑这条用例 30 次，0 次失败；全档 `verify-and-commit.sh` 跑 3 次不误报；
  - 反向验证（`git archive` 出的草稿副本，跑完即删）：`INPUT_WAIT = 4` 时失败，信息写出 3 轮耗时；`select` 不设超时时 15 秒后以「挂住」失败，
    整套不卡死。高负载下也各做一次。
- 验证：`verify-and-commit.sh` 全档。
- 文件：`hooks/test-phase-guard.sh`、`CHANGELOG.md`（「未发布」下的维护者工具一条）。

### Checkpoint 3（gate）：返工验收

展示用例差异、负载下的统计、反向验证结果与未验证项；推送与开 PR 在此由用户确认，合并由用户进行。不单独发版。
