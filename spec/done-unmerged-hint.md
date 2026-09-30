# Spec: done-unmerged-hint

## Objective

阶段提示（`phase-guard` → `module_stage.describe()`）只看本地的能力图与 `todo.md`。按约定，模块的 Checkpoint 勾选随模块
PR 一起提交，所以勾完最后一项、分支还没推送或合并时，提示已经是 `DONE`，建议是"插入新模块"——推送、开 PR、合并这一步
在提示里看不到，只能靠对话里提醒。2026-09-30 用户问"为什么没有下一步提示了"，正是这种情况。

本模块在 `DONE` 与 `MODULE_DONE` 时补一行事实：当前分支还有几个提交不在本地已知的远端默认分支里，并把建议改为先推送、
合并。

登记：2026-09-30 经 `/spec-guard:add-module` 插入能力图。

## Assumptions

用户已于 2026-09-30 确认（按推荐方案）：

1. 只读、不联网：只比较本地的远端跟踪引用，不执行 `git fetch`（fetch 会写引用，且会拖慢每轮提示）。提示中说明比较的是
   "本地已知的" 远端默认分支，可能过时。
2. 只在 `DONE` 与 `MODULE_DONE` 时检查；`NEEDS_SPEC`／`NEEDS_PLAN`／`BUILDING` 等阶段不变。
3. 看不到 PR 状态、不提示发版；探测失败（非 git 仓库、没有远端默认分支引用、分离 HEAD 等）时不输出任何提示，阶段结果
   不受影响。

本 Spec 提出、用户于 2026-09-30 确认的细节：

4. 远端默认分支取 `refs/remotes/origin/HEAD` 指向的引用；没有时依次尝试 `origin/main`、`origin/master`；都没有则不提示。
   远端名固定为 `origin`。
5. 计数用 `git rev-list --count <默认分支引用>..HEAD`；为 0 不提示。大于 0 时：
   - 追加一行：`- This branch has N commit(s) not yet in \`origin/main\` (as last fetched).`
   - `DONE` 时建议改为：先推送当前分支并合并这些提交，之后再按原建议插入新模块；`MODULE_DONE` 时在原建议前加同样的一句。
6. 阶段名、模块计数与其余行逐字不变；没有未合并提交时整段输出与现在逐字相同。

## Contract

- `module_stage.py`：新增 `unmerged_commits(root)` → `(count, ref_name)` 或 `None`；只调用 `git`（`symbolic-ref`／
  `rev-parse --verify`／`rev-list --count`），每个调用设短超时，任何失败返回 `None`。`describe()` 在 `DONE`／`MODULE_DONE`
  时调用并按第 5 条调整输出。
- 不改 `module_state`、`project_stage`、`paused_modules`（`verify-artifacts` 与 `module-insert` 仍用它们，判据不变）。
- `phase-guard.sh` 不改：它已经原样注入 `describe()` 的输出。

## Commands

```text
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
/bin/bash scripts/validate.sh
python3 -B plugins/spec-guard/hooks/test_module_insert.py
```

## Testing strategy

- 先写测试并确认它在当前代码上失败，再修改；在 `test-phase-guard.sh` 里用临时的 bare 远端与克隆：
  - `DONE` 且本地领先 `origin/main` 2 个提交 → 输出含未合并提示与"先推送合并"的建议；
  - 推送后（跟踪引用追上）→ 与现在逐字相同；
  - `MODULE_DONE` 且领先 → 原建议前多一句；
  - 没有远端 → 无提示，输出与现在相同；`BUILDING` 且领先 → 无提示；
  - 只读：运行前后 `git for-each-ref` 与工作区状态不变。
- 已有的 phase-guard、verify-artifacts、module-insert 测试全部通过。
- 两种 Python 下三条最小验证都通过。

## Boundaries

- Always：先红后绿；hook 只读、只依赖 bash／git／python3、输出宿主 JSON；探测失败时降级为不提示。
- Ask first：执行 `git fetch` 或任何联网操作；读取 PR 状态；改变阶段判定。
- Never：在 Spec、代码、测试、提交信息或 PR 中写入消费者项目的名称、模块或编号。

## Success criteria

- 模块在本地全部勾完、分支尚未合并时，阶段提示明确给出"先推送、合并"的下一步。
- 其余情况输出逐字不变；阶段判定与 `verify-artifacts` 不受影响。
- 两种 Python 下全部检查通过。

## Open questions

- 无（第 4–6 条已于 2026-09-30 经用户确认）。
