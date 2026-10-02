# Plan: retired-module-separation

依据 [`spec/retired-module-separation.md`](../../spec/retired-module-separation.md) 和 Local Bug `SH62J51`。本模块只迁移仓库自身的能力登记与历史文件，不修改 Proposal 运行时代码、远端 Issue 或历史快照。

## Architecture decisions

- 当前图保持一个严格模块表和一个 Build order；不为退役模块增加解析器特例或第二张图。
- 四份旧 Spec/Plan 用 `git mv` 原样迁入 `docs/retirements/<id>/`。退役说明提供新路径；旧 Spec 的历史决定保持原文。
- 现行依赖直接改指仍活跃的提供者或删除已退役的依赖，不添加兼容适配层。
- 能力图与归档在同一提交中落地，避免出现图仍列模块而 Spec 已迁走的中间交付状态。

## Task list and checkpoints

任务清单在同目录的 `todo.md`，按以下顺序执行。

1. **记录红态和原始 blob。** 用当前严格解析器确认两个退役 id 仍在模块表与 Build order，运行一个只读断言并确认它失败；记录四份源文件的 Git blob id。
2. **原子迁移。** 用 `git mv` 归档四份文件；按 Spec R1 调整能力图两行、三处依赖、一个职责描述和 Build order；更新退役说明中的历史路径。
3. **验证和交付。** 比较归档文件与 Task 1 的 blob id，运行能力图严格解析、`verify-artifacts.sh`、阶段和产物回归、完整 `scripts/validate.sh`。核对现行入口没有新增退役调用；记录不能在本地证明的远端事实。

## Verification commands

```bash
python3 -B plugins/spec-guard/hooks/capability-map.py spec/CAPABILITY-MAP.md
CLAUDE_PROJECT_DIR="$PWD" /bin/bash plugins/spec-guard/hooks/verify-artifacts.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash scripts/validate.sh
git diff --check
```

## Risks and rollback

- **旧路径引用：** 保持历史文件原文；更新现行退役说明为新索引，并检查非历史入口是否仍指向旧路径。
- **Proposal 基线变化：** 变更只在合并后成为远端默认分支共享事实；可能使尚未晋级的 Proposal 失去新鲜度，交付前只读核对候选状态并如实报告。
- **回退：** 在未合并时撤销本分支的迁移提交即可恢复旧路径和能力图；不改已有快照或远端 Proposal 对象。

## Completion checkpoint

所有 task 勾选、四份归档逐字节相同、能力图只含现行模块、完整验证通过后，提交本地分支。推送及 PR 属于后续交付检查点；不自动合并或关闭本地 Bug。

## Verification record

- 迁移前只读断言退出 1：当前图仍含 `proposal-mainline-review`、`proposal-boundary-guidance`。
- 迁移后严格解析通过，现行模块 31 个；退役 id 在模块行、依赖和 Build order 中均不存在。
- 四份归档与迁移前 `HEAD` 的 Git blob 相同：`f3308cb73faf`、`1fa5a467c52f`、`85e71bf1e2b1`、`77e6240fc15a`。
- `verify-artifacts.sh` 退出 0；产物回归 18 例、阶段回归 78 例、完整 `scripts/validate.sh` 均通过。13 个历史模块缺 todo 的既有警告仍可观察，不计作本次迁移失败。
- 迁移已提交于本地分支，并将结果回填 Local Bug `SH62J51`；交付时复核远端分支与 PR 状态。
