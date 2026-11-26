# Plan: takeover-config

<!-- spec-guard: review pending -->

Spec：[spec/takeover-config.md](../../spec/takeover-config.md)（2026-11-21 批准，Q2 A：「接管到合并」预设包含 Spec）。

## 架构决定

- **生效值只有一处判定**：`project_config.module_takeovers(root, ids)` 一次读文件返回项目生效值与每个模块的 `(items, source)`；
  `module_takeover(root, id)` 是它的单个版。`/map`、后续模块（codex-approval 等）、调用方都用它。预设展开表 `PRESETS` 与取值表 `ITEMS`
  只在 `project_config.py` 里定义一次。
- **值怎么从命令行传**：`set --value` 是预设名就按字符串存；以 `{` 开头按 JSON 解析成对象，解析失败或校验不过退出 2 不写。不另造
  `--spec/--plan` 之类的参数，免得同一个值有两种写法。
- **「宽于」逐项比较**：每项取值按 `ITEMS` 里从严到宽的顺序比，任一项比项目生效值宽就算宽（Spec 假设 5）。
- **退役不删解析**：`autonomyTier`、`moduleAutonomy` 从 `VALIDATORS` 移到 `RETIRED`；`load` 遇到它们报 `retired-key`（同 `unknown-key`
  一样不判失败），原样保留在文件里。原 `module_tier(s)` 改为直接读这两个旧键，只供 `/map` 的 deprecated `autonomy` 字段用，输出与改前相同。
- **阶段提示不碰**：`module_stage.py`、`phase-guard.sh` 不改；用 phase-guard 回归证明设与不设输出逐字相同。

## 任务

- **Task 0**：提交本 Plan 与 todo。验证：`validate.sh --quick`、verify-artifacts 0 失败。
- **Task 1**：配置核心（AC1、AC2）。`test_project_config.py` 先写预设、自定义、缺项、非法值、`--module`、宽于提醒、发布两行提示、
  生效值三种来源的例子并确认失败；再实现 `VALIDATORS`、`PRESETS`、`module_takeover(s)`、`set`／`unset` 与预览。验证：单测绿。
- **Task 2**：退役（AC3）。先写例子：旧键在文件里时 `show` 标已退役、`check` 退出 0 并提示、`set` 旧键退出 2、`unset` 可用、
  `module_tier` 读旧键结果不变；再实现。验证：单测绿；`test_map_view.py` 现有 `autonomy` 断言不改也通过。
- **Task 3**：`/map --json` 与接口（AC4、AC7）。`test_map_view.py` 先加 `takeover` 六个字段的例子；实现 `map_view.py`；`interface.json` 升 1.15
  （新增 `takeover`、`moduleTakeover`，旧两条标 retired，`mapView.autonomy` 标 deprecated，写明 `mapView.takeover`）；`check-interface.py`
  核对字段名，`test-checkers.sh` 加反例。验证：单测、`check-interface.py`、`test-checkers.sh` 绿。
- **Task 4**：verify-artifacts 与阶段提示回归（AC5、AC6）。`test-verify-artifacts.sh` 加：能力图上没有的 id 警告、已退役键警告、不合法值失败；
  `test-phase-guard.sh` 加一段：设 `takeover`／`moduleTakeover` 前后输出逐字相同。先确认新断言失败（verify-artifacts 部分），再实现。
  验证：两套回归绿。
- **Task 5**：说明文字。`commands/config.md`、`skills/spec-guard-ops/SKILL.md`、`docs/commands.md`（config 与 `/map`）、`docs/concepts.md`
  （自治档位一行改接管档位）、`references/workflow-checkpoints.md`「自治档位与底线」写明 autonomyTier 已退役、底线文字待 codex-approval 改。
  验证：`validate.sh --quick`（含规则回归与字节上限）；`test_workflow_checkpoints.py` 里提到 autonomyTier 的断言按新文字调整。

## 会改哪些文件

- 新增：`tasks/takeover-config/{plan,todo}.md`。
- 修改：`hooks/project_config.py`、`hooks/test_project_config.py`、`hooks/map_view.py`、`hooks/test_map_view.py`、`hooks/verify-artifacts.sh`、
  `hooks/test-verify-artifacts.sh`、`hooks/test-phase-guard.sh`、`hooks/test_workflow_checkpoints.py`、`interface.json`、`scripts/check-interface.py`、
  `scripts/test-checkers.sh`、`commands/config.md`、`skills/spec-guard-ops/SKILL.md`、`references/workflow-checkpoints.md`、`docs/commands.md`、
  `docs/concepts.md`。
- 不改：版本号、CHANGELOG、README（0.91.0 在 codex-final-acceptance 统一）。新增依赖、锁文件：无。

## 风险

- **超出 Spec 并行边界**：边界只写了 `project_config.py` 等 5 处；`map_view.py`、`interface.json`、`verify-artifacts.sh`、规则与文档也要改。
  本项目串行做，不与别的模块冲突；最终验收照规则单独列「超出并行边界」并说明原因。
- **调用方还在写旧键**：module-crew 的 `tier degrade` 现在可能直接 `set autonomyTier`，退役后会退出 2。合并方案定的是 module-crew 改调
  收窄入口（takeover-narrow），同一窗口切换；本模块合并前先问 mc-coord 现在怎么写，记进最终验收的拟回告。
- **check 语义变化**：旧键从「不合法即失败」变成「已退役只警告」，旧的失败用例要改；用正反例守住新键仍然判失败。
- **shell 改动**：`verify-artifacts.sh`、两个测试脚本是 `.sh`，提交前跑 ShellCheck（`-S warning`）。

## 检查点

- Checkpoint 1（report）：完整检查（validate、phase-guard、verify-artifacts、smoke 自检、ShellCheck）；变异验证两处（`module_takeover`
  忽略模块值、预设 `merge` 把 Spec 展开成 human）各让回归变红；临时项目命令行实跑：设 `merge` → 预览四项 → 确认 → `/map --json` 读回；
  旧 `autonomyTier` 留在文件里 → `show`、`check` 输出。记进 todo 后继续。
- Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行。本模块不发版。

## 未决问题

- 无。

## 返工：删除退役接口（2026-11-26，Spec 假设 11～13，Q1 A、Q2 A）

## 预先声明

- 公共路径：无
- 外部依赖：无
- 质量与工作区配置：无
- 补丁：无

## 返工架构决定

- **只删「拿退役键算档位」这一条线**：`map_view` 的 `autonomy` 字段、`AUTONOMY_FIELDS`、对 `module_tiers` 与 `wider` 的调用；`project_config` 的 `_project_tier`、`module_tier`、`module_tiers`、`wider`（全仓只有这一处用）。
- **识别与清理入口不动**（Q1 A）：`_RETIRED` 校验、`retired-key` 问题代码、`TIERS`（校验旧值要用）、`set` 拒绝、`unset` 可用、阶段提示过滤 `retired-key`、verify-artifacts 的警告，全部原样。
- **接口 1.25**（Q2 A）：`interface.json` 删 `autonomyTier`、`moduleAutonomy` 两个条目与 `mapView.autonomy`，版本 1.24 → 1.25。`check-interface.py` 删 `_autonomy` 与两条取值比对，改为检查这三处**不再出现**（防止有人照旧文档加回去）。
- **测试**：`test_map_view.py` 模块键集合去掉 `autonomy`，删 `AutonomyTest` 一类与快照里对 `autonomy` 的处理；加一例「模块对象没有 `autonomy` 键」。`test_project_config.py` 删 `module_tier` 那组断言，退役键的 show／check／set／unset 用例保留（AC10）。`test-checkers.sh` 删原来「缺 autonomyTier／autonomy 说明 → 报错」等反例，改为「接口里又出现 `autonomyTier`／`moduleAutonomy`／`mapView.autonomy` → 报错」三例。

## 返工任务

- **Task 6**：先改测试让它们红：`test_map_view.py`（没有 `autonomy` 键）、`test-checkers.sh`（三处又出现就报错）。再删代码与接口条目、升 1.25。验证：`test_map_view.py`、`test_project_config.py`、`check-interface.py`、`test-checkers.sh`。
- **Task 7**：文档。`commands/config.md`、`skills/spec-guard-ops/SKILL.md`、`docs/commands.md`、`docs/concepts.md`、`docs/design.md`、`references/workflow-checkpoints.md` 里说 `/map` 还按这两个键算、或 `autonomy` 字段「下一版删」的句子改成已删除；`test_workflow_checkpoints.py` 跟着改；CHANGELOG「未发布」加一条「移除」，写明三个接口条目与接口 1.25。验证：快档、`git grep` 只剩历史记录（AC11）。
- **Checkpoint 3（report）**：完整档三条全绿；变异（临时副本）：`map_view` 加回 `autonomy` 字段、`check-interface.py` 不查三处缺失，各自让用例变红；已安装的 0.96.2 与本分支比对：本仓库的阶段提示、verify-artifacts 逐字相同，`/map --json` 只差 `autonomy` 键与接口版本；临时项目里留着两个退役键时 `show`、`check`、`set`、`unset` 的输出逐字相同（AC10）。
- **Checkpoint 4（gate）**：推送、开 PR；最终验收与合并合成一问；发 0.97.0 另取授权（两件都合并后）。拟回告：给 ecosystem-lead「接口 1.25 移除了三个退役条目」，发版时再通知一次。

