# Plan: module-suspend

依据 [`spec/module-suspend.md`](../../spec/module-suspend.md)（假设经用户 2026-10-08 确认）。本仓库 `reviewCadence` 为
`combined`：Spec 与本 Plan 一起评审、一次批准。分支 `claude/module-suspend`，从 `acdffd3`（`project-config` 合并）开出。
本模块不单独发版，todo 在本模块 PR 内勾完。

## 依赖与顺序

判定只在 `module_stage.py` 一处，命令、插入和校验都依赖它，所以先做判定；命令脚本依赖判定的结果显示"挂起后的当前模块"。

## Task List

### Task 1：挂起判定与阶段提示（先红）

`test-phase-guard.sh` 加 Spec「Testing strategy」列出的 5 类用例并确认失败；再在 `module_stage.py` 加 `suspended`、
调整 `project_stage`、`paused_modules`、计数行、Suspended 行和 DONE 文案。
变异：标记改为"包含即可"、跳过逻辑不排除挂起模块、`paused_modules` 包含挂起模块。

- 验收：phase-guard 回归全绿，无标记的既有用例逐字节不变，三处变异被抓到。
- 文件：`hooks/module_stage.py`、`hooks/test-phase-guard.sh`。

### Task 2：`add-module` 不被挂起的模块挡住（先红）

`test_module_insert.py` 加用例：唯一未完成的模块挂起时允许插入、不需要 `--interrupt`、插入后当前模块是新模块。
预计 Task 1 已使其转绿；若没有，在 `module-insert.py` 补上。

- 验收：module-insert 单测全绿。
- 文件：`hooks/test_module_insert.py`（必要时 `hooks/module-insert.py`）。

### Task 3：`module_suspend.py` 与单测（先红）

新增 `hooks/test_module_suspend.py` 与 `hooks/module_suspend.py`：`suspend`／`resume`，预览、`--confirm` 原子写入并读回，
全部拒绝情况，恢复时做到一半的提示。复用 `module_stage` 的判定与 `tracker_default` 的原子写入。

- 验收：单测全绿。
- 文件：上述两个文件。

### Task 4：`verify-artifacts` 校验（先红）

`test-verify-artifacts.sh` 加重复标记失败、过期标记警告、正常标记通过；再改 `verify-artifacts.sh`。

- 验收：verify-artifacts 回归全绿。
- 文件：`hooks/verify-artifacts.sh`、`hooks/test-verify-artifacts.sh`。

### Checkpoint 1（report）：核心回归全绿，ShellCheck 无警告

### Task 5：命令、Codex 路由与文档

新增 `commands/module-suspend.md`（规范引导段，含提醒的那段说明）；`spec-guard-ops` 新增 `module-suspend` 一节；
`docs/workflow.md` 命令对照表登记；`docs/design.md` 的 Local boundary 补一句挂起；CHANGELOG `## [未发布]` 新增条目。
command-parity、command-names、command-table、bash 3.2 检查器兜底。

- 验收：`scripts/test-checkers.sh` 与 `validate.sh` 通过；在临时项目里实跑一次挂起与恢复（预览与确认）。
- 文件：`commands/module-suspend.md`、`skills/spec-guard-ops/SKILL.md`、`docs/workflow.md`、`docs/design.md`、`CHANGELOG.md`。

### Checkpoint 2（gate）：模块评审

推送前在同一条 `&&` 链里跑 `validate.sh`、两套 hook 断言、新单测和 ShellCheck；pre-push 钩子兜底。
批准本 Plan 即授权推送本分支并开本模块的 PR；合并由用户进行。

## 风险

| 风险 | 应对 |
|---|---|
| 改动 `project_stage` 影响既有阶段判定 | 无标记用例逐字节不变；module-insert、cost-report 等依赖 `module_stage` 的单测全部重跑 |
| 挂起与插队组合出意外的当前模块 | Task 1 与 Task 3 覆盖"做到一半时恢复"的组合 |
| 标记写法被误改导致静默失效 | verify-artifacts 只认完全相等的一行，重复即失败；变异覆盖"包含即可" |
