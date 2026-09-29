# Plan: plan-without-todo

依据 [`spec/plan-without-todo.md`](../../spec/plan-without-todo.md)。三个 task 串行，每个 task 一条提交；先写能在当前
代码上失败的测试并记录失败输出，再修改到通过。全部在临时项目上测试，不访问网络。

每个 task 完成时都运行三条最小验证，并用 `/usr/bin/python3` 再跑一次：

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

T1 与 T2 共用"plan 存在、todo 不存在"这一判据：T1 在 `module_state` 中加 `todo` 字段，T2 复用同一判据；按仓库不变量，
两边各有正反回归。

## Task 1：阶段提示（T1）

- `module_stage.py`：`module_state` 加 `todo` 字段（`stage` 计算不变）；`activeModule` 指向图中模块、其 `stage` 为 `DONE`
  且无 `todo.md` 时，在计数行后、`Paused` 行前加提醒行，适用于 `MODULE_DONE` 与 `DONE`。
- `test-phase-guard.sh`：MODULE_DONE 与 DONE 两个正例；有 todo 且全勾、无 activeModule、activeModule 不在图中三个反例；
  已有 48 个用例保留。
- **验收：** 新断言在当前代码上失败、修改后通过；`test_module_insert.py` 全部通过。
- **文件：** `module_stage.py`、`test-phase-guard.sh`。

## Task 2：verify-artifacts 汇总警告（T2）

- `verify-artifacts.sh`：能力图通过严格解析后，按 Build order 统计"有 plan 无 todo"的模块；大于 0 时一条 `warn`，
  最多列 10 个，超过时以"等 N 个"结尾；不产生 `bad`，退出码不变。判据取自 `module_stage`（可经 `module_state` 或
  同一 Python 调用），不在 shell 里另写一份完成判据。
- `test-verify-artifacts.sh`：0 个、1 个、超过 10 个三种情况的输出、警告计数与退出码。
- **验收：** 新断言在当前代码上失败、修改后通过；三条最小验证通过。
- **文件：** `verify-artifacts.sh`、`test-verify-artifacts.sh`。

## Task 3：文档（T3）

- `commands/phase.md`、`docs/workflow.md`：缺 `todo.md` 按已完成计、提醒何时出现、如何处理。
- `commands/verify-artifacts.md`：新警告的含义。
- `CHANGELOG.md` Unreleased。
- **验收：** `validate.sh` 与 `check-command-parity.py` 通过。
- **文件：** 四份文档。

## Checkpoint：完成

- 三条最小验证在默认 `python3` 与 `/usr/bin/python3` 下都通过；在本仓库与抽查的消费者项目只读副本上核对
  "无触发条件时阶段输出不变、verify-artifacts 只多一条汇总警告"，并复现"activeModule 指向只有 Plan 的新模块"的场景看到提醒；检查点勾选随
  模块 PR 一起提交，由分支保护的两项必需 CI 把关合并；阶段变为 DONE。

## Task 4：已退役 tracker 模式的项目不提醒（修订）

- `module_stage.py`：读取 `.agent/state.json` 的 `tracker`（与 `active_module` 同一次读取或同一辅助函数）；为 `github` 或
  `gitlab` 时不加 T1 提醒行。
- `verify-artifacts.sh`：同一条件下不发缺 todo 汇总；判据复用 `module_stage` 的函数，不在 shell 里重复解析 tracker。
- 测试：两个脚本各加 tracker=github、tracker=gitlab 的反例（有 activeModule 指向只有 Plan 的模块、有多个只有 Plan 的模块），
  以及 tracker=none 的正例（行为不变）。
- **验收：** 新断言在当前代码上失败、修改后通过；已有断言全部保留。
- **文件：** `module_stage.py`、`verify-artifacts.sh`、两个回归脚本、`phase.md`、`verify-artifacts.md`、`CHANGELOG.md`。

## Checkpoint 2

- 两种 Python 下三条最小验证；在本仓库与抽查的消费者项目只读副本上核对：tracker 项目不再出现提醒与汇总，本地模式项目行为不变。
