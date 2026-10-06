# Spec: checkpoint-tiers

## Objective

开发链路常在不需要人的地方停下：Plan 里"展示给用户"的检查点被当成停点，连续几个模块又各自卡在 Spec、Plan 评审上，
开发者不在电脑前时整条链路就停了。用户曾设想"倒计时自动跳过"；2026-10-06 评审后改为更直接的做法：把检查点分级、
把人审前置、让 AI 先做能自己做的 UI 验证。

本模块只改写给 agent 的规则文本（共享检查点规则与约定块）及其静态回归，不改任何 hook 判定。

登记：2026-10-06 经 `/spec-guard:add-module` 插入能力图。

## Assumptions

用户已于 2026-10-06 确认：

1. 规则写进共享检查点规则 `references/workflow-checkpoints.md`（新增三节），约定块模板各加一行指向它。宿主是否遵守只能靠
   真实会话行为验证；静态测试只证明规则可被找到，不得表述为行为验收。
2. **检查点分级。** Plan 中每个检查点标为 `gate` 或 `report`：
   - `gate`：停下，展示结果并等明确确认；
   - `report`：把结果（验证命令、结果、未验证项）记入 todo 的该项后直接继续，不停、不倒计时；
   - 未标注的检查点按 `gate` 处理（保守默认）；
   - 异常停点（测试改不红、Spec 未覆盖的决策、高风险不可逆、权限被拒、结果未知）任何级别下都停。
3. **推送与开 PR 的授权。** 只有当 Plan 的 `gate` 检查点逐项写明授权（例如"本 Plan 获批即授权推送并开模块 PR 与发版 PR"）
   时才免问；没写就照旧在交付前询问。合并永远由用户进行。插件不把任何远端写入设为默认授权。
4. **按需求批量前置审。** 一个需求拆成多个模块时，用户可以一次审完它们的 Spec 与 Plan。每个获批模块的 plan.md 在其 `gate`
   检查点写明"本 Plan 已于 <日期> 随同一需求批量批准"。模块完成后，若 Build order 中下一个模块带有这句，就切换
   `activeModule` 并继续构建；没有这句就停在该模块的 Spec 或 Plan 评审。不新增文件或状态字段。
5. **连续构建遇到模块边界提醒**（context-hint-thresholds 的 50% 档）：用户在场照常提示；按第 4 条连续构建时在当前会话继续，
   到 80% 安全阀时停下并给出 `/spec-guard:handoff` 交接文本。agent 不自行开新会话。
6. **UI 自验。** 模块涉及 UI 或宿主可见显示时：
   - Plan 的测试检查点必须含一步由 AI 执行的验证——网页用浏览器工具，原生界面用电脑操作（经用户授权）；
   - Plan 开头先列出所需工具并确认可用，缺失时在该检查点之前提醒用户安装或授权，不默默跳过；
   - AI 验证后，人做最后兜底审查（`gate`）；
   - 例外：电脑操作永远不能用于 Claude 桌面应用自身，这类显示只能由人看。
7. 约定块模板改动只对重新运行 `setup-convention --replace` 的项目生效；本仓库在交付时运行一次。

## Contract

- `references/workflow-checkpoints.md` 新增三节：`## Plan 检查点分级`、`## 按需求批量前置审`、`## UI 自验`，内容按第 2–6 条；
  `## 阶段交接` 的"交付前"一条补一句：Plan 的 `gate` 检查点写明的授权视为已获授权。
- `templates/claude-block-local.md`、`templates/codex-block-local.md` 各加一行：Plan 检查点标 `gate`／`report`，批量前置审与
  UI 自验按共享检查点规则。
- `docs/workflow.md` 一段说明；CHANGELOG `[未发布]`。
- 不改 hook、`module_stage`、`verify-artifacts` 的判定。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash scripts/validate.sh
```

## Testing strategy

- 先写测试并确认在当前文本上失败，再改文本。
- `test_workflow_checkpoints.py`：
  - 合同含三节标题与关键规则词（`gate`、`report`、"未标注…按 `gate`"、"合并永远由用户"、"批量批准"、"80%"、
    "浏览器"、"电脑操作"、"Claude 桌面应用"）；
  - 两份约定块模板都含 `gate`／`report` 与指向共享检查点规则的说明；
  - 反向：合同中不出现把推送设为默认授权的表述（不含"默认授权推送"之类短语）。
- 已有 phase-guard、verify-artifacts、setup-convention 回归全部通过。
- Checkpoint（宿主行为）：本模块自己的 Plan 按新规则标注 `gate`／`report`，在本会话实际执行；交付后在本仓库运行
  `setup-convention --replace`，确认约定块更新、阶段注入不变。

## Boundaries

- Always：先红后绿；规则写清停点；不把静态检查说成行为验收。
- Ask first：把任何远端写入设为默认授权；让 agent 自行开新会话；新增状态文件或 hook 判定。
- Never：倒计时自动通过 `gate`；在 Spec、代码、测试、提交信息或 PR 中写入消费者项目的名称、模块或编号。

## Success criteria

- 共享检查点规则清楚区分 `gate`／`report`，未标注按 `gate`，异常停点永远停。
- 远端写入只在 Plan 写明时免问，合并始终由用户。
- 批量前置审与连续构建的条件、遇到边界提醒时的处理可以从规则直接读出。
- UI 自验与 Claude 桌面应用例外写入规则。
- 两份约定块模板指向这些规则；本仓库更新约定块后阶段注入不变。

## Open questions

- 无。
