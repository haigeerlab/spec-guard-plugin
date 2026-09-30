# Spec: ledger-worktree-owner

## Objective

Epiq 1.11.0 把本地账本的状态 worktree 固定放在 `<EPIQ_GLOBAL_DIR 或 ~/.epiq-global>/worktrees/<projectId>`，路径里
只有 `projectId`，不区分仓库。同一台 Mac 上两个仓库共用一个 `projectId`（复制或迁移出的仓库副本、同一仓库的两份
克隆）时，先建 worktree 的那个仓库占用该路径，另一个仓库的每次账本调用都以
`Failed to create state branch worktree … already exists` 失败，看不出原因。

2026-09-30 本仓库自己就撞上了：迁移前的旧副本占用了该路径，本仓库的账本全部失败；排查需要读压缩后的 Epiq 源码。
本模块让只读的 `local_ledger_runtime.py status` 直接报告"状态 worktree 被另一个仓库占用"、占用者路径与处理办法。

登记：2026-09-30 经 `/spec-guard:add-module` 插入能力图。

## Assumptions

用户已于 2026-09-30 确认（按推荐方案）：

1. 只做诊断与文档，不自动修复：插件不移动、删除或改写任何 worktree、分支或 `~/.epiq-global` 内容；不改 Epiq。
2. 检查放在已有的只读 `status` 里：项目已初始化时，计算状态 worktree 路径（尊重 `EPIQ_GLOBAL_DIR`），读取该目录的
   `.git` 文件所指 gitdir，与本仓库的公共 git 目录（`git rev-parse --git-common-dir`，只读）比较。

本 Spec 提出、用户于 2026-09-30 确认的细节：

3. 结果写在 `project.stateWorktree`：`absent`（目录不存在，Epiq 下次会创建）、`owned`（属于本仓库）、`foreign`
   （属于另一个仓库，附 `owner` 为占用仓库路径）、`unknown`（读不到或无法判断，附短码诊断，不当作故障）。
4. `foreign` 时顶层 `state` 为新值 `conflict`，退出码 1，`diagnostic` 为 `ledger-state-worktree-foreign`；其余情况顶层
   状态与退出码保持现状（`absent`／`owned`／`unknown` 不改变原来的 `initialized` 结果）。

2026-10-01 安全补充：受管路径不存在时，还须只读检查本仓状态分支是否已在其他 worktree
检出；若是，`project.stateWorktree=unknown`、`diagnostic=ledger-state-worktree-away`，
附 `checkedOutAt`。如果状态分支也不存在，报告 `ledger-state-branch-missing` 而不创建空账本。
两种情况顶层仍为 `initialized`。路径为符号链接或配置中的 project ID 不是
安全的单一路径分量时，不得把它当作可创建的空状态。日常入口遇到 `unknown` 不写入。
5. 文档给出处理办法：先备份占用的 worktree；若占用仓库已停用，在**占用仓库**执行 `git worktree move <路径> <别处>`
   （保留其中未同步的事件）；若两个仓库都要用账本，则为其中一个的账本进程设置不同的 `EPIQ_GLOBAL_DIR`，并说明账本 MCP
   是用户级配置、改全局目录会影响所有项目。不推荐换 `projectId`（需删除本地与远端状态分支，不可逆）。
6. 一个 task：代码、测试、参考文档与命令说明、CHANGELOG；在 `docs/migrations/2026-09-27-repository-copy.md` 补一段
   账本说明（本仓库自己的迁移记录，不涉及消费者项目）。

## Contract

- `local_ledger_runtime.py`：新增 `state_worktree_status(project_dir, project_id)`（只读检查文件、
  Git worktree、状态分支与 common dir），`status()` 在项目 `initialized` 时调用并按第 3、4 条合并结果。
- 路径比较使用 realpath；`.git` 为目录（非 worktree）、内容无法解析、gitdir 指向不存在的位置时为 `unknown`。
- 不改 `contract`、`preflight`、`install`、`initialize` 的行为与输出。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_local_ledger_runtime.py
python3 -B plugins/spec-guard/hooks/test_local_ledger_adapters.py
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 scripts/check-command-parity.py
```

## Testing strategy

- 先写测试并确认它在当前代码上失败；夹具用临时目录中的两个 git 仓库与临时 `EPIQ_GLOBAL_DIR`，不碰真实 `~/.epiq-global`，
  不需要安装 Epiq 或 Node。
- 状态 worktree 属于另一个仓库 → `conflict`、`ledger-state-worktree-foreign`、`owner` 为另一个仓库、退出码 1；
- 属于本仓库（由本仓库 `git worktree add` 建立）→ `owned`，顶层状态与原来相同；
- 目录不存在 → `absent`，顶层状态与原来相同；
- `.git` 内容无法解析 → `unknown`，不当作冲突；
- 调用前后夹具文件与两个仓库的 `git worktree list` 不变（只读）；已有测试全部保持通过。
- 两种 Python 下三条最小验证与上述测试都通过。

## Boundaries

- Always：先红后绿；status 只读；尊重 `EPIQ_GLOBAL_DIR`；诊断只输出短码与路径，不输出原始异常。
- Ask first：任何自动修复；修改 Epiq 或其锁定版本；改变其他子命令的行为。
- Never：在 Spec、代码、测试、提交信息或 PR 中写入消费者项目的名称、模块或编号。

## Success criteria

- 两个仓库共用 `projectId` 且另一个占用状态 worktree 时，`status` 直接给出 `conflict`、占用者与文档里的处理办法。
- 其余情况的输出与退出码不变；status 保持只读。
- 两种 Python 下全部检查通过。

## Open questions

- 无（第 3、4 条已于 2026-09-30 经用户确认）。
