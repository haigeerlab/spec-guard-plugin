# Plan: pre-declared-scope

<!-- spec-guard: review pending -->

依据 [`spec/pre-declared-scope.md`](../../spec/pre-declared-scope.md)（2026-10-26 用户在本会话批准：「批准；并行评估 B」）。评审节奏为分开审，
本 Plan 单独交审。分支 `claude/s32-interface-1.11`，worktree `distracted-morse-46ef70`，从 `origin/main`（`a390e68`）切出；串行，在本会话做。
版本号与发版归下一个模块 `autonomy-tier`，本模块只在 CHANGELOG 未发布段记一条。

## Overview

先做解析与错误码，再做批准判断与命令，然后接口说明、verify-artifacts、规则文字，各自先红后绿、单独提交（`scripts/verify-and-commit.sh`）。
代码 task 在草稿副本里把修复改坏一处，确认新用例变红（手工变异，不入库）。

## Architecture Decisions

1. **解析器放在 `module_scope.py`，新增 `DeclaredScope` NamedTuple 与 `parse_declared(text)`**。复用 `_visible`（围栏）、`FIELD`、`SEPARATORS`、
   `TICKED`、`_path`；标题、行名、`无` 各自一组常量。四行各最多一次，重复 → `unknown-line`；没有这一节返回 `None`。错误用现有 `ScopeError`
   （只带固定码），新增码 `bad-dependency` 与 `unreadable` 放进常量 `DECLARED_ERRORS`，供 `check-interface.py` 核对。
2. **依赖项解析**：去反引号后从**最后一个**不在开头的 `@` 切开，左边是名称、右边是范围（这样 `@scope/pkg@^1` 正确）；任一边为空、含空白，
   或范围以 `workspace:` 开头 → `bad-dependency`。名称本身不做包管理器格式校验。
3. **批准判断 `plan_approval(root, module_id) -> (bool, str | None)`**，只用只读 git：
   - 工作区 `tasks/<id>/plan.md` 的 `review_state(...,"plan")` 不是 `approved` → `(False, None)`；
   - `git log --format=%H -- tasks/<id>/plan.md`（新到旧）逐个取 blob（`git show <c>:<path>`），找到最近一个「这一版 approved、它之前那一版
     不是 approved 或不存在」的提交 C；
   - 工作区文件字节与 C 版本相同 → `(True, C)`，否则 `(False, None)`。git 不可用、不是仓库、找不到 C → `(False, None)`。
   `review_state` 来自 `module_stage`，判据不复制。
4. **命令 `module_scope.py declared --project --module`**：模块 id 用 `MODULE_ID` 校验、必须在能力图里（读图失败也退 2）；读 Plan 失败 → 4 + `unreadable`；
   格式错 → 4 + 码；其余 0。JSON 键顺序固定，`ensure_ascii=False`。
5. **verify-artifacts 用新子命令 `module_scope.py validate-declared --project`**，输出与 `validate` 同一种行协议（`ok <n>`、`bad <code> <id>`、
   `unverified map|<id>`），不看 `moduleConcurrency`；verify-artifacts.sh 新增一段解析这些行，只要有能力图就跑。
6. **接口 1.11**：`interface.json` 的 `interface` 改为 `"1.11"`，新增 `declaredScope` 条目；`check-interface.py` 的 `ENTRIES` 加它，
   `_concurrency` 里核对 command 脚本存在、`values.error` 与 `DECLARED_ERRORS` 相同；`scripts/test-checkers.sh` 加缺条目与错误码不符两例。
   `docs/design.md` 接口一段补一句 1.11。`autonomy-tier` 之后再往 1.11 里加它自己的条目，同一次发版。

## Task List

### Task 0：提交已批准的 Spec、能力图两行与 Plan 草稿

- 验证：verify-artifacts 0 失败；快档提交。

### Task 1：「预先声明」解析与错误码（C1，AC1、AC2，先红后绿）

- 文件：`hooks/module_scope.py`、`hooks/test_module_scope.py`。
- 用例：中英标题与行名；齐全、缺行、全 `无`；目录与文件；`@scope/pkg@^1`；围栏里的示例节；每个错误码（通配符、`..`、绝对路径、配置或补丁写目录、
  依赖缺范围／空名／含空白／`workspace:`、未知行名、重复行、两个标题）；断言错误输出不含文件文字。
- 变异：草稿副本里去掉「配置／补丁不许目录」的判断，对应用例变红。

### Task 2：批准判断与 `declared` 命令（C2，AC3、AC4，先红后绿）

- 文件：`hooks/module_scope.py`、`hooks/test_module_scope.py`。
- 真 git 夹具（`tempfile` 下 `git init`，固定 `user.*`、`commit.gpgsign=false`）：Spec AC3 的六种情况逐一断言 `planApproved`／`approvedCommit`；
  命令以子进程跑，断言退出码 0／2／4 与 JSON 形状、没有 `plan.md` 与没有这一节时 `declared: false`。
- 变异：草稿副本里去掉「工作区与 C 版本逐字节比较」，「改一个字未提交」用例变红。

### Task 3：接口 1.11 与说明（C2 末段，AC5）

- 文件：`interface.json`、`scripts/check-interface.py`、`scripts/test-checkers.sh`、`docs/design.md`。
- `test-checkers.sh` 新增：缺 `declaredScope` → 报错；`values.error` 少一个码 → 报错。先红后绿。

### Task 4：verify-artifacts 校验这一节（C3，AC6，先红后绿）

- 文件：`hooks/module_scope.py`（`validate-declared`）、`hooks/verify-artifacts.sh`、`hooks/test-verify-artifacts.sh`。
- 用例：未完成模块格式错 → 失败并给出 id 与码；格式对 → 「预先声明格式正确：1 个模块」；没有这一节、已完成模块 → 不出现；开关 off 时同样生效。
- `.sh` 改动跑 CI 同版 ShellCheck。

### Task 5：规则文字（C4，AC7）

- 文件：`references/node-rules.md`、`references/workflow-checkpoints.md`、`hooks/test_workflow_checkpoints.py`、`hooks/test_stop_rules.py`。
- 断言：Plan 交审一条（逐条列出、写 `无` 的行也列、「批准本 Plan 即授权以下公共改动」）；workflow-checkpoints 一段（何时写、不能预先声明的三类、
  不得自加更严条款、没有这一节时不用写）。先红后绿；跑 `test-phase-guard.sh` 确认节点注入照常。

### Checkpoint 1（report）：三套核心回归

- `validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 全绿，CI 同版 ShellCheck 无告警；结果记入 todo。

### Task 6：CHANGELOG 未发布段与更新说明

- CHANGELOG 新开「未发布」段（若已有则追加）一条；todo 末尾写给 `autonomy-tier` 发版用的更新说明。版本号不动。

### Checkpoint 2（gate）：最终验收

- 呈现做了什么、AC 逐条证据、改动文件与提交表、Spec 中途改动（如有）。通过后推送本分支并开本模块 PR（批准本 Plan 即授权推送与开 PR），
  合并由用户进行；随后开始 `autonomy-tier` 的 Spec。

## Files likely touched

- 代码：`plugins/spec-guard/hooks/module_scope.py`、`plugins/spec-guard/hooks/verify-artifacts.sh`、`scripts/check-interface.py`
- 测试：`plugins/spec-guard/hooks/test_module_scope.py`、`plugins/spec-guard/hooks/test-verify-artifacts.sh`、`plugins/spec-guard/hooks/test_workflow_checkpoints.py`、
  `plugins/spec-guard/hooks/test_stop_rules.py`、`scripts/test-checkers.sh`
- 说明：`plugins/spec-guard/interface.json`、`plugins/spec-guard/references/node-rules.md`、`plugins/spec-guard/references/workflow-checkpoints.md`、`docs/design.md`、`CHANGELOG.md`
- 新增依赖、锁文件改动：无。

## 风险

- **已有项目恰好有一节叫「预先声明」做别的用途**：升级后 verify-artifacts 可能判失败。概率低；失败信息只给模块 id 与错误码，用户改标题或改写即可。
  交审与 CHANGELOG 写明。
- **`git log` 遍历在 Plan 历史很长时变慢**：只取 `plan.md` 这一个文件的提交，通常几十个以内；找到 C 即停。
- **浅克隆找不到批准提交**：按假设 6 返回 false，module-crew 照今天的做法问用户，不会误放行。
- **`interface.json` 是两模块共用文件**：串行做，本模块先改到 1.11，`autonomy-tier` 再追加，不会冲突。
