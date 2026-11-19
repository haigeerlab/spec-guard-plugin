# Plan: usage-draft

<!-- spec-guard: review approved -->

依据 [`spec/usage-draft.md`](../../spec/usage-draft.md)（2026-11-19 用户在本会话批准：「批准」，能力图新行 `usage-draft`、`milestone-stop`
与用法草案 [`spec/usage/usage-milestones.md`](../../spec/usage/usage-milestones.md) 同时确认写入）。写 Plan 时 Spec 假设 9 与 AC5 有一处
修订（见下文「Spec 修订」），随本 Plan 一并复审。
分支 `claude/usage-draft`（从 `origin/main` `a06d43f0` 开出），worktree `distracted-morse-46ef70`。串行，在本会话做。本模块改版本号到 0.87.0。

## Overview

先写 `test_usage_draft.py`（合格草案与每个失败项的反例），确认在 0.86.7 上失败（模块不存在），再写 `hooks/usage_draft.py`；接着接入
`verify-artifacts.sh` 与 `module-insert.py` 的预览，补规则文本、模板与文档，改版本号，交最终验收。M1 停点在发版后手动做一次。

## Spec 修订

能力图审阅的交审小项与 `interface.json` 的 `reviewKinds.capability-map.sections` 一一对应（契约 1.x 只增不改）。Spec 原写「加第四项
『用法草案』」会让规则与契约不一致，或者要改 `interface.json`（Spec 边界里属于先问）。改为：草案写在「拆成哪些模块」这一小项里，
不新增小项、不改 `interface.json`。差异只在假设 9 与 AC5 两句。

## Architecture Decisions

1. **判据只在 `usage_draft.py`**：`parse(path)` 读一份草案（去围栏视图，复用 `capability_map` 的可见行与表格切分，不另写表格解析）；
   `validate(project)` 读 `spec/usage/*.md`，用 `capability_map.parse_map` 的严格结果取模块与 Build order 分组，输出
   `{"status": "pass|fail|absent", "files": [...], "failures": [...], "warnings": [...]}`；`milestones(project)` 给 add-module 用，
   返回 `{模块: (草案文件, 里程碑)}`。CLI：`usage_draft.py validate --project <dir>`，`fail` 时退出 1，参数或环境错误退出 2。
2. **顺序判据**：Build order 分组序号；对每份草案，第 k 个里程碑所有模块的最大序号必须小于第 k+1 个里程碑所有模块的最小序号
   （同一逗号组算同一序号，所以跨里程碑同组判失败）。里程碑按表中行序，不按编号排序；编号只要求 `M<n>` 形式且不重复。
3. **verify-artifacts**：照「预先声明」「延期写法」那几项的写法加一段：没有 `spec/usage/` 时不输出；`pass` 输出一行通过（有提醒附在后面），
   `fail` 逐条报失败并让整体失败；脚本跑不起来报「未验证」不判违规。
4. **module-insert**：`format_report` 在「新的 Build order」那段之后、diff 之前加一段「用法草案」：草案文件列表；锚点（`after:<id>`）属于
   某个里程碑时写明「锚点 `<id>` 属于 `<文件>` 的 `M<n>`」；提醒一句。`milestones()` 抛错时写「未读取到用法草案：<原因>」，预览不失败。
   没有 `spec/usage/` 时整段不出现，输出逐字不变。`--confirm` 路径不变。
5. **规则文本**：`node-rules.md` 与 `workflow-checkpoints.md` 的能力图审阅「拆成哪些模块」写明多模块需求附用法草案与拆分核对；Spec 交审
   对属于草案的模块加一致性一句；「文档建议」的能力图全部完成那条写明 README 从草案展开。约定块模板只链接 node-rules，不改。
6. **模板** `templates/USAGE.md`：Spec 假设 5 的格式，正文留占位说明。`check-command-names.py` 会扫 `templates/*.md`，模板里只写已有命令。
7. **发版**照 0.86.7：合并后核对、打 tag（遇 500 改在你的终端推）、打包、Release、两个宿主核对（Codex 在新开 CLI 的提示里批 hook）、
   证据收尾 PR（REST 开 PR）、回告 ecosystem-lead（回复 #21414）。发版后做 M1 停点：在临时项目跑 U1、U2，证据摆给你判定。

## Task List

### Task 0：提交能力图两行、已批准的 Spec、用法草案与 Plan 草稿

- 验证：verify-artifacts 0 失败；快档提交。

### Task 1：`usage_draft.py` 与单元测试（假设 5、6，AC1–AC3 的判据部分）

- 文件：`hooks/usage_draft.py`、`hooks/test_usage_draft.py`、`scripts/validate.sh`（登记新测试）。
- 用例：合格草案 `pass`；假设 6 的每个失败项各一个反例并断言点名文件与项；没有入口的模块只进 `warnings`；没有 `spec/usage/` 为 `absent`；
  两份草案同一模块判失败；逗号组跨里程碑判失败；表格写坏为 `fail` 不抛堆栈；CLI 退出码。
- 验证：新测试在 0.86.7 上失败，实现后全部通过；`test_python_compat.py` 通过。

### Task 2：接入 verify-artifacts（AC1、AC2）

- 文件：`hooks/verify-artifacts.sh`、`hooks/test-verify-artifacts.sh`。
- 用例：合格草案多一行通过；坏草案整体失败且点名；没有草案时输出与 0.86.7 相同。
- 验证：`test-verify-artifacts.sh` 全部通过；暂存 `.sh` 时 ShellCheck 通过。

### Task 3：接入 add-module 预览（AC4）

- 文件：`hooks/module-insert.py`、`hooks/test_module_insert.py`、`commands/add-module.md`（说明多出的这一段）。
- 用例：有草案且锚点在里程碑里时预览含文件、里程碑名与提醒；锚点不在任何里程碑时只有文件与提醒；没有草案时预览逐字不变；
  `--confirm` 不改草案；草案读不出来时预览照常并写明未读取到。
- 验证：`test_module_insert.py` 全部通过。

### Task 4：规则文本与模板（AC5）

- 文件：`references/node-rules.md`、`references/workflow-checkpoints.md`、`hooks/test_workflow_checkpoints.py`、`templates/USAGE.md`。
- 验证：新规则回归先红后绿；`validate.sh --quick` 通过。

### Task 5：文档（AC7 的文档部分）

- 文件：`docs/concepts.md`（术语表：用法草案、里程碑）、`docs/commands.md`（verify-artifacts、add-module）、`docs/workflow.md`（能力图审阅一步）、
  README 中英命令与功能列表各一句。
- 验证：`validate.sh --quick` 通过。

### Task 6：版本号 0.87.0 与 CHANGELOG（PR 最后一个内容提交）

- 文件：两份 `plugin.json`、README 中英 `--ref`、`CHANGELOG.md`（0.87.0：新增、文档）。
- 验证：`check-readme-sync.py`、`check-manifests.py` 通过。

### Checkpoint 1（report）：发布前完整检查

- macOS 系统 `/bin/bash` 跑 `validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 并记录主机；`evals/codex-plugin-smoke.sh --selftest`；
  ShellCheck。
- 变异（草稿副本）：去掉 Build order 顺序检查、去掉「最后里程碑覆盖全部用法」、去掉 add-module 提醒，三处都要让测试变红。
- 临时项目命令行实跑 U1、U2（为 M1 停点备证据）。
- 本仓库自己的 `verify-artifacts` 对 `spec/usage/usage-milestones.md` 通过。

### Checkpoint 2（gate）：最终验收

- 呈现做了什么、AC 证据、改动表、提交表、Spec 中途改动（如有）、拟回告原文。通过即同时授权：推送、开 PR；你合并后由我核对合并并按发版
  步骤一次做完，随后做 M1 停点。

### 发版（合并后，按 Checkpoint 2 的授权）

- 核对合并、打 `v0.87.0`、打包、Release、比对 SHA-256；刷新并核对 Claude 与 Codex 安装副本；收尾扫描、证据收尾 PR；回告 ecosystem-lead。
  任一步失败就停下说明。

### M1 停点（发版后，gate）

- 用安装副本在临时项目跑 U1、U2，摆出命令与输出，由你判定通过与否。通过后才写 `milestone-stop` 的 Spec。

## Files likely touched

- 插件包：新增 `hooks/usage_draft.py`、`hooks/test_usage_draft.py`、`templates/USAGE.md`；修改 `hooks/verify-artifacts.sh`、
  `hooks/test-verify-artifacts.sh`、`hooks/module-insert.py`、`hooks/test_module_insert.py`、`hooks/test_workflow_checkpoints.py`、
  `references/node-rules.md`、`references/workflow-checkpoints.md`、`commands/add-module.md`、两份 `plugin.json`
- 仓库：`scripts/validate.sh`（登记测试）、`docs/concepts.md`、`docs/commands.md`、`docs/workflow.md`、`README.md`、`README.en.md`、`CHANGELOG.md`；
  收尾 PR：`docs/releases/v0.87.0-*.json`
- 记录：`spec/CAPABILITY-MAP.md`（已写入两行）、`spec/usage-draft.md`、`spec/usage/usage-milestones.md`、本 Plan、`tasks/usage-draft/todo.md`
- 新增依赖、锁文件改动：无。不碰 `capability_map.py`（只调用）、`spec-digest.py`、`proposal_contract.py`、`phase-guard.sh`、`module_stage.py`、
  `interface.json`、约定块模板。

## 风险

- **phase-guard 与 verify-artifacts 判据一致**：本模块的判据只有 verify-artifacts 和 add-module 用，phase-guard 不读草案（那是 milestone-stop），
  所以不产生「两边判据不一致」；milestone-stop 时再把 phase-guard 接到同一个 `usage_draft.py`。
- **本仓库自用**：本仓库也会有 `spec/usage/`，phase-guard 用的是安装版，不受影响；verify-artifacts 自检会读到它，Task 0 提交时它还是旧逻辑，
  不报。
- **表格解析复用**：复用 `capability_map` 的私有函数（`_visible_lines`、`_table_cells`）有耦合风险；若它们不适合导出，就在 `usage_draft.py`
  里写最小的表格读取并在测试里覆盖，不改 `capability_map.py`。
- **Python 版本**：`test_python_compat.py` 要求的最低版本照旧，不用新语法。
