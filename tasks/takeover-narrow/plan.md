# Plan: takeover-narrow

<!-- spec-guard: review approved -->

Spec：[spec/takeover-narrow.md](../../spec/takeover-narrow.md)（2026-11-21 批准，Q3 A：收窄记录与档位同存 `.agent/config.json`）。

## 架构决定

- **「一格」只有一处判定**：`project_config.narrow_step(value)` 返回收回一格后的值，`widen_steps(from_value, to_value)` 返回放宽了几格；
  两者都基于 `PRESETS`、`ITEMS` 与同一条顺序表（预设 `none < plan < merge`；自定义按 Spec、Plan、合并、发布由内到外，发布整项算一格），
  `narrow` 子命令与 `set` 的恢复检查都调它们。
- **记录与档位同一次写入**：`narrow` 与 `set` 都走现有 `_change` 的预览、原子写、读回核对；`takeoverNarrowed` 跟 `takeover`／`moduleTakeover`
  一起算出新文档再写，不会出现档位改了、记录没改的中间状态。
- **自定义与预设之间怎么比宽窄**：都先展开成四项，按项比较；「宽几格」= 从严往宽数，`to` 比 `from` 多放开的格数（预设之间按预设顺序数，
  自定义按项数，发布不论取值都算一格）。
- **`reason` 的安全**：只接受单行可打印字符、≤200 字；`show` 原样列出（已限长），阶段提示与 `/map --json` 不出现它。
- **阶段提示不碰**：用 phase-guard 回归证明有无收窄记录输出逐字相同。

## 任务

- **Task 0**：提交本 Plan 与 todo。验证：`validate.sh --quick`、verify-artifacts 0 失败。
- **Task 1**：`narrow_step` 与 `narrow` 子命令、`takeoverNarrowed` 校验（AC1、AC2、AC3）。`test_project_config.py` 先写顺序、范围、记录、
  参数不合格的例子并确认失败，再实现。验证：单测绿。
- **Task 2**：恢复一次一格（AC4）。先写：有记录时放宽两格退出 2、一格成功、回到 from 删记录、无记录不限、往严不限；再在 `_change` 里实现。验证：单测绿。
- **Task 3**：`/map --json` 的 `narrowed` 与接口（AC5、AC6）。`test_map_view.py` 先写；实现；`interface.json` 加 `takeoverNarrow` 条目与
  `mapView.takeover.fields.narrowed`；`check-interface.py` 核对 `narrow` 子命令存在、`--source` 词表一致；`test-checkers.sh` 加反例；
  `test-phase-guard.sh` 第 25 段加一种带收窄记录的配置。验证：单测、接口检查、两套回归绿。
- **Task 4**：说明文字：`commands/config.md`、`skills/spec-guard-ops/SKILL.md`、`docs/commands.md`。验证：`validate.sh --quick`。

## 会改哪些文件

- 新增：`tasks/takeover-narrow/{plan,todo}.md`。
- 修改：`hooks/project_config.py`、`hooks/test_project_config.py`、`hooks/map_view.py`、`hooks/test_map_view.py`、`hooks/test-phase-guard.sh`、
  `interface.json`、`scripts/check-interface.py`、`scripts/test-checkers.sh`、`commands/config.md`、`skills/spec-guard-ops/SKILL.md`、`docs/commands.md`。
- 不改：版本号、CHANGELOG、README、阶段提示代码。新增依赖、锁文件：无。

## 风险

- **叠加分支**：本分支基于 #460（takeover-config）的分支。#460 合并前不开 PR；合并后 rebase 到 main 再开。#460 若按评审改动，这里跟着 rebase。
- **超出并行边界**：`test-phase-guard.sh`、`test-checkers.sh`、`skills/…/SKILL.md`、`docs/commands.md` 不在 Spec 的独占列表里；串行做无冲突，最终验收单独列出。
- **未提交改动**：调用方收窄后 `.agent/config.json` 会有未提交改动（Q3 A 的已知代价）；文档写明由谁提交、autopilot 在降级 issue 里提醒。
- **shell 改动**：提交前跑 ShellCheck。

## 检查点

- Checkpoint 1（report）：完整检查（validate、phase-guard、verify-artifacts、smoke 自检、ShellCheck）；变异验证两处（`narrow_step` 先收 Spec
  而不是发布、恢复检查放过两格）各让回归变红；临时项目命令行实跑：`merge` 连续 narrow 到最严、模块 narrow、带记录时恢复两格被拒、一格成功、
  回到 from 记录消失、`/map --json` 读回。记进 todo 后继续。
- Checkpoint 2（gate）：最终验收；通过后推送，#460 合并后 rebase 到 main 开本模块 PR，合并由用户进行。本模块不发版。

## 未决问题

- 无。
