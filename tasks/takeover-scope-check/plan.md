# Plan: takeover-scope-check

<!-- spec-guard: review approved -->

Spec：[spec/takeover-scope-check.md](../../spec/takeover-scope-check.md)（2026-11-22 批准；Q10 A、Q11 A）。

## 架构决定

- **谁要查只有一处**：`module_scope.scope_applies(root, module)`（开关 on，或 `project_config.module_takeover` 里任一项不是 human）；`_check`、`validate`
  的开关判断换成它（`validate` 对接管模块的 Spec 也查并行边界格式）。
- **基线**：`module_scope.default_base(root, module)` 用 `git log --diff-filter=A --format=%H -- spec/<id>.md` 取最早加入的提交，返回它的父提交（Q10 A）；
  Spec 还没提交或是根提交时返回 None。
- **预先声明放行**：复用 `plan_approval`／`declaredScope` 的判定——Plan 已批准且批准后未改时，预先声明的公共路径记为 `declared`；否则不放行。
- **阶段提示**：`module_stage.scope_overreach(root, module)` 只在 BUILDING 且模块是接管模块时调用 `module_scope` 的判定（延迟导入，避免循环），
  返回越界列表／`no-boundary`／`unverified`／None；`no-boundary` 按 Q11 A 同样停下。越界与未判定写进状态码事实。
- **没开关、非接管的项目逐字不变**：用 phase-guard 回归守住。

## 任务

- **Task 0**：提交本 Plan 与 todo。验证：`validate.sh --quick`、verify-artifacts 0 失败。
- **Task 1**：`module_scope` 的 `scope_applies`、`default_base`、`declared` 放行与 JSON 新字段（AC1、AC3 的结果部分）；`test_module_scope.py` 先写例子确认失败。
- **Task 2**：阶段提示（AC2）：`scope_overreach` 与越界行、停下交用户的建议（中英）；`test-phase-guard.sh` 新增第 30 段（PARTS=30），先写确认失败。
- **Task 3**：接口与规则（AC3 接口部分、AC4）：`interface.json` 的 `scopeCheck`、`check-interface.py` 与 `test-checkers.sh` 反例；`workflow-checkpoints.md`「并行边界」
  与「自治档位与底线」；`test_workflow_checkpoints.py`；`docs/commands.md`、`skills/spec-guard-ops/SKILL.md`。

## 会改哪些文件

- 新增：`tasks/takeover-scope-check/{plan,todo}.md`。
- 修改：`hooks/module_scope.py`、`hooks/test_module_scope.py`、`hooks/module_stage.py`、`hooks/test-phase-guard.sh`、`interface.json`、`scripts/check-interface.py`、
  `scripts/test-checkers.sh`、`references/workflow-checkpoints.md`、`hooks/test_workflow_checkpoints.py`、`docs/commands.md`、`skills/spec-guard-ops/SKILL.md`。
- 不改：版本号、CHANGELOG、README。新增依赖、锁文件：无。

## 风险

- **每轮多一次 git diff**：只在接管模块 BUILDING 时算；`git diff --name-status` 与 `ls-files --others` 两次调用，本仓库实测耗时记进 Checkpoint 1。
- **本仓库自己**：本仓库没设接管档位，开关 on，原有行为不变。
- **叠加分支**：基于 #464 的分支，前面合并后 rebase 再开 PR。
- **shell 改动**：提交前跑 ShellCheck。

## 检查点

- Checkpoint 1（report）：完整检查（validate、phase-guard、verify-artifacts、smoke 自检、ShellCheck）；变异验证两处（接管模块不查、预先声明不看批准）
  各让回归变红；临时项目实跑：档位 plan、写边界、开工后改一个边界外文件 → 阶段提示停下；补进预先声明并批准 Plan → 恢复；`check --json` 读回。记进 todo 后继续。
- Checkpoint 2（gate）：最终验收；通过后推送，前面合并后 rebase 开本模块 PR，合并由用户进行。本模块不发版。之后 M2 里程碑停点照 M1 的办法交用户判定。

## 未决问题

- 无。
