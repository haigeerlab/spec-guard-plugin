# Plan: ledger-worktree-owner

依据 [`spec/ledger-worktree-owner.md`](../../spec/ledger-worktree-owner.md)。一个 task、一条提交：先写能在当前代码上失败的
测试并记录失败输出，再修改到通过；夹具用临时仓库与临时 `EPIQ_GLOBAL_DIR`，只用通用名。

## Task 1：状态 worktree 占用诊断

- `local_ledger_runtime.py`：`state_worktree_status()` 与 `status()` 合并（`conflict`／`ledger-state-worktree-foreign`）。
- `test_local_ledger_runtime.py`：Spec 测试策略中的场景。
- `references/local-ticket-ledger-runtime.md`、`commands/local-ticket-ledger.md`（及 Codex `local-ticket-ledger-ops`
  的相同表述）：`conflict` 的含义与处理办法；`docs/migrations/2026-09-27-repository-copy.md` 补账本一段；
  `CHANGELOG.md` Unreleased。
- **验收：** 新测试在当前代码上失败、修改后通过；两种 Python 下三条最小验证、账本测试与 `check-command-parity.py` 通过。

## Checkpoint：完成

- 在本仓库（已修复、状态 worktree 属于本仓库）上运行 status 应为 `owned`、顶层状态不变；逐条核对 Spec 成功标准；
  勾选随模块 PR 一起提交；阶段回到 DONE。
