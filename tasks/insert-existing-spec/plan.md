# Plan: insert-existing-spec

依据 [`spec/insert-existing-spec.md`](../../spec/insert-existing-spec.md)。一个 task、一条提交：先写能在当前代码上失败的
测试并记录失败输出，再修改到通过；只用通用夹具名。

## Task 1：已存在的 Spec 允许插入并提示

- `module-insert.py`：去掉拒绝，预览结果带 `existing_spec`，预览与写入输出在该情况下追加提示；`--proposal` 同样适用。
- `test_module_insert.py`：Spec 测试策略中的场景；改写原"已存在即拒绝"的断言并在提交说明中列出。
- `commands/add-module.md`（及 Codex `spec-guard-ops` 的相同表述）、`CHANGELOG.md` Unreleased `### 变更`。
- **验收：** 新测试在当前代码上失败、修改后通过；两种 Python 下三条最小验证、`test_module_insert.py`、
  `check-command-parity.py` 通过。

## Checkpoint：完成

- 逐条核对 Spec 成功标准；勾选随模块 PR 一起提交；阶段回到 DONE。
