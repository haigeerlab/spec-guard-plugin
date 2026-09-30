# Plan: done-unmerged-hint

依据 [`spec/done-unmerged-hint.md`](../../spec/done-unmerged-hint.md)。一个 task、一条提交：先写能在当前代码上失败的测试
并记录失败输出，再修改到通过；夹具用临时 bare 远端与克隆，只用通用名。

## Task 1：DONE／MODULE_DONE 时提示未合并提交

- `module_stage.py`：`unmerged_commits()` 与 `describe()` 的调整。
- `test-phase-guard.sh`：Spec 测试策略中的正反场景。
- `references/workflow-checkpoints.md`（如描述阶段提示内容）与 `CHANGELOG.md` Unreleased。
- **验收：** 新测试在当前代码上失败、修改后通过；两种 Python 下三条最小验证与 `test_module_insert.py` 通过。

## Checkpoint：完成

- 在本仓库当前分支上（勾完后、推送前）阶段提示应出现未合并提示；逐条核对 Spec 成功标准；勾选随模块 PR 一起提交。
