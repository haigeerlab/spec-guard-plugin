# Plan: milestone-stop

<!-- spec-guard: review approved -->

Spec：[spec/milestone-stop.md](../../spec/milestone-stop.md)（2026-11-19 批准，假设 7 定为加 `milestoneStop`）。

## 架构决定

- **判据只有一处**：确认记录的解析与停点判定都在 `hooks/usage_draft.py`，新增 `confirmations(draft)` 与
  `stop(project, states)`；`states` 由调用方传入（`module_stage.module_state` 的结果），`usage_draft.py` 不反向 import
  `module_stage.py`，避免循环依赖。阶段提示、`milestone_mark.py`、`map_view.py` 都调 `stop()`。
- **确认记录**是 HTML 注释行，`_visible_lines` 不剥注释，所以 `parse()` 在 `## Milestones` 一节里读
  `<!-- spec-guard: milestone M<n> confirmed a, b -->`；同节里其他形如 `<!-- spec-guard: milestone` 的行算格式坏。
- **阶段提示**：`_describe_body` 在算出 `stage`、`current` 后调 `stop()`；有停点时不改 `stage`，只在计数后加停点行、
  换掉「建议下一步」、附 `node-rules.md` 新节「里程碑停点」（`NODE_TITLES` 加 `milestone-stop`）。停点优先于当前模块的其他节点
  规则（当前模块此时通常是下一个里程碑的 NEEDS_SPEC）。停点事实进 `state_key`，状态变了才重新注入完整内容。
  DONE（整个能力图完成）时同样判定：最后一个里程碑没确认也停。
- **`/map --json`**：顶层加 `milestoneStop`（`null` 或 `{file, milestone, modules, usages}`），放在 `nextGate` 之后；
  文字版在有停点时多一行。interface 1.12 → 1.13，`mapView` 里写明新增字段与出现条件；其余字段不变。
- **milestone-mark** 仿 `review_mark.py`／`module_suspend.py`：默认预览，`--confirm` 才写；写入用读-改-写整个文件，
  保留原换行风格；确认行放在 Milestones 表之后的第一个空行处，替换同一里程碑的旧行。

## 任务

- **Task 0**：提交已批准的 Spec 与本 Plan、todo。验证：`validate.sh --quick`、本仓库 verify-artifacts 0 失败。
- **Task 1**：`usage_draft.py` 的确认记录与停点判定。先在 `test_usage_draft.py` 写测试并确认在 0.87.0 上失败：停点判定 7 例
  （全完成未确认→停；确认后不停；确认后加模块且做完→再停；挂起不算完成；只剩延期项算完成；多个停点报第一个；草案坏→不判并给原因），
  确认记录 3 例（坏格式判失败、指向不存在的里程碑判失败、模块不一致只提醒），重复归属只报一条（AC7）。验证：单元测试绿。
- **Task 2**：`milestone_mark.py`、`commands/milestone-mark.md`、`skills/spec-guard-ops/SKILL.md` 一句。测试 `test_milestone_mark.py`：
  预览只读（sha 不变）；四种拒绝（里程碑不存在、模块未完成、前面有未确认、已确认退出 0 不写）；`--confirm` 写一行；替换失效记录；
  只改那份草案。`validate.sh` 登记新测试。验证：单元测试绿，命令文档通过插件清单与命令表一致性检查。
- **Task 3**：阶段提示。`module_stage.py` 接 `stop()`；`node-rules.md` 加「里程碑停点」一节（字节数在上限内）；
  `test-phase-guard.sh` 加例：有停点时出停点行、建议下一步与停点规则；确认后回到原样；没有草案逐字不变；草案坏时写原因不失败；
  DONE 时最后一个里程碑未确认也停。验证：phase-guard 全部用例绿。
- **Task 4**：`/map`。`map_view.py` 加 `milestoneStop` 与文字行；`interface.json` 1.13；`spec/map-view.md` 契约；
  `test_map_view.py` 正反例与接口契约回归。验证：map_view 与 interface 相关回归绿。
- **Task 5**：共享检查点规则。`workflow-checkpoints.md` 的「用法草案」一节补「里程碑停点」；`test_workflow_checkpoints.py`
  加共用短语与用例。验证：规则回归绿、各节字节数在上限内。
- **Task 6**：文档。`docs/commands.md`（milestone-mark、verify-artifacts 一行、map JSON 字段）、`docs/concepts.md`、`docs/workflow.md`、
  README 中英命令表一行，README 功能介绍加「多模块需求：用法草案与里程碑停点」一段，从 `spec/usage/usage-milestones.md` 展开。
  验证：`validate.sh --quick`、`check-readme-sync.py`。
- **Task 7**：版本 0.88.0 与 CHANGELOG（新增、接口 1.13、文档）。验证：`check-manifests.py`。

## 会改哪些文件

- 新增：`hooks/milestone_mark.py`、`hooks/test_milestone_mark.py`、`commands/milestone-mark.md`、`tasks/milestone-stop/{plan,todo}.md`。
- 修改：`hooks/usage_draft.py`、`hooks/test_usage_draft.py`、`hooks/module_stage.py`、`hooks/test-phase-guard.sh`、`hooks/map_view.py`、
  `hooks/test_map_view.py`、`interface.json`、`spec/map-view.md`、`references/node-rules.md`、`references/workflow-checkpoints.md`、
  `hooks/test_workflow_checkpoints.py`、`skills/spec-guard-ops/SKILL.md`、`scripts/validate.sh`、两份 `plugin.json`、`CHANGELOG.md`、
  `README.md`、`README.en.md`、`docs/commands.md`、`docs/concepts.md`、`docs/workflow.md`。
- 可能连带：`hooks/verify-artifacts.sh`（失效记录提醒的文字）、`hooks/test-verify-artifacts.sh`、`hooks/test_stop_rules.py`
  （节点种类清单）、`hooks/phase-guard.sh`（若状态码要带停点事实）。
- 新增依赖、锁文件：无。公共文件：版本号、CHANGELOG、README（串行做，无并行冲突）。

## 风险

- **阶段提示回归面大**（`module_stage.py` 1184 行、phase-guard 512 例）：停点分支只在 `stop()` 返回非空时生效，没有草案的项目走原路径；
  用「没有草案逐字不变」的用例守住。
- **本仓库自己会立刻停**：安装 0.88.0 后，本仓库草案的 M1（usage-draft）已完成未记录，阶段提示会报停点。用户已于 2026-11-19 判定
  M1 通过，发版后经用户确认用 milestone-mark 补记（见 M2 停点）。
- **interface 1.13 的读取方**：module-crew、decision-inbox 读 `/map --json`；只新增字段，旧读取方忽略即可。发版回告写明。
- **字节上限**：node-rules 各节有 2600 字节上限，「里程碑停点」一节写短。

## 检查点

- Checkpoint 1（report）：发布前完整检查（validate、phase-guard、verify-artifacts、smoke 自检、ShellCheck）、变异验证三处、
  临时项目命令行实跑 U3（停点出现 → milestone-mark 预览 → 确认 → 提示转下一个模块；加模块后再停），记进 todo 后继续。
- Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行。
- 发版（合并后按 Checkpoint 2 授权）。
- M2 停点（gate）：用安装副本在临时项目跑 U1–U3；经用户确认后，用 milestone-mark 在本仓库草案里补记 M1、记下 M2。

## 未决问题

- 无。
