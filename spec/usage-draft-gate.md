# Spec: usage-draft-gate

<!-- spec-guard: review approved 211a00ef05d8 -->

## Objective

一个需求拆出多个模块、却没写用法草案时，由机器发现并提醒。规则（workflow-checkpoints「用法草案」）早就要求「同一次需求确认拆出
2 个及以上模块时……最晚在第一个模块的 Spec 之前审完」，但它只有文字：add-module 没有草案时什么都不说，阶段提示与 verify-artifacts
只处理已有的草案。结果 module-crew、delegate 各有一次批量插入两个模块，一路做到 Spec、Plan、实现，都没有草案，也没有任何提醒。

给谁用：用 add-module 逐个插入模块的 agent；审能力图与 Spec 的用户。

登记：ecosystem-lead #21942 报告（用户「两件都按建议办」），#21944 指正补写时的里程碑确认。2026-11-21 用户在本会话「验收通过；Q4 A」
（排在 takeover-narrow 之后、codex-approval 之前，并进 0.91.0）、「M1 A；说完了，确认插入」。账本 T1T36MR。

## Assumptions

1. **「一批」怎么认**：用 git 看能力图。沿 `spec/CAPABILITY-MAP.md` 的提交从新到旧（最多 100 个），某个提交里新出现的模块行算同一批；
   工作区里还没提交的新行也算一批（add-module 只写文件不提交）。一个模块只归它第一次出现的那一批。
2. **「缺草案」的判据**：一批里有 2 个及以上模块，其中还没完成的模块里至少有一个不在任何草案（`spec/usage/*.md`）的里程碑表里。
   已完成的模块不让一批被判缺（老的批量插入不会被翻旧账）。判据只在一处：新函数 `usage_draft.missing(project)`。
3. **读不到 git**（不是 git 仓库、git 出错）：报「未判定」并写原因，不当作没问题；阶段提示在这种情况下不变（避免每轮刷一条不可操作的提醒），
   由 verify-artifacts 报出来。
4. **verify-artifacts**：每个缺草案的批报一条 ⚠️，写明哪几个模块、哪个提交（工作区未提交的写「未提交」）；未判定报一条 ⚠️ 带原因。只警告，不判失败
   （已开工的项目要先补写，不能一升级就变红）。
5. **阶段提示**：当前模块在 NEEDS_SPEC、又属于一批缺草案的模块时，建议下一步换成「先写 `spec/usage/<需求>.md` 交用户审（含这批全部模块），
   再写 Spec」，节点规则附「能力图审阅」。草案写进里程碑后恢复原样。其他阶段不变（中途开工的批次靠 verify-artifacts 与补写规则）。
   中英两套措辞。
6. **add-module**：`--confirm` 写入后，如果工作区里这一批未提交的新模块已有 2 个及以上、又没有草案覆盖，结果末尾加一句提醒（写 Spec 前先出用法草案）。
   预览不加（还没写入）。
7. **补写规则**（写进 workflow-checkpoints「用法草案」）：已开工的项目照样补一份草案，覆盖这批全部模块（已完成的也列进里程碑，便于对齐）；
   随下一次交审给用户。这批里已完成的里程碑在交审时单独列出，请用户逐个三选一：照常停下跑一遍／凭已有证据直接判定通过（再用
   milestone-mark 记）／不记确认、保持停点。确认记录就是用户的判定，不自动记。
8. **不变的**：不拦写入、不自动生成草案内容；草案结构校验、里程碑停点规则不变；接口不变（不进 `/map`）。
9. **版本**：并进 0.91.0，版本号在 `codex-final-acceptance` 改。

## Contract

### C1 判据（`hooks/usage_draft.py`）

- `missing(project) -> {"status": "ok"|"missing"|"unverified", "batches": [{"commit": <sha|"uncommitted">, "modules": [...], "uncovered": [...]}], "reason"}`；
  只读 git（`log`、`show`）与文件，不写任何东西。完成与否沿用 `module_stage` 的模块状态。

### C2 verify-artifacts

- 新增一项「多模块批次的用法草案」：ok 时 ✅（没有批量插入时不输出）；missing 每批一条 ⚠️；unverified 一条 ⚠️ 带原因。

### C3 阶段提示（`hooks/module_stage.py`）

- 假设 5：NEEDS_SPEC 且当前模块在缺草案的批里 → 建议下一步换文字、`stop_node` 给 `map-review`；中英两套。

### C4 add-module（`hooks/module-insert.py`）

- 假设 6 的提醒；`commands/add-module.md`、`skills/spec-guard-ops/SKILL.md` 的 add-module 一节写明「同一需求插第 2 个模块后先出草案」。

### C5 规则

- `references/workflow-checkpoints.md`「用法草案」加补写一段（假设 7）与「机器会在哪里提醒」一句；`node-rules.md`「能力图审阅」不改。

## Acceptance criteria

- **AC1** `missing`（临时 git 仓库）：一个提交插入 2 个未完成模块且无草案 → missing 并列出模块与提交；有草案覆盖 → ok；一个提交只插 1 个 → ok；
  2 个都已完成 → ok；工作区未提交的 2 个新行 → missing、commit 为 uncommitted；不是 git 仓库 → unverified 带原因。
- **AC2** verify-artifacts：上面各情形分别出 ⚠️／✅／不输出；不判失败（`test-verify-artifacts.sh`）。
- **AC3** 阶段提示（`test-phase-guard.sh` 新段）：缺草案批里的模块在 NEEDS_SPEC 时建议下一步与节点规则按假设 5，中英各一例；补上草案后与改前逐字相同；
  没有批量插入的项目输出不变。
- **AC4** add-module：同一工作区连续插入两个模块、无草案 → 第二次 `--confirm` 的输出有提醒；有草案覆盖或只插一个 → 没有。
- **AC5** 规则：「用法草案」一节有补写段落、三选一与「不自动记确认」；`test_workflow_checkpoints.py` 断言并过字节上限；
  `validate.sh`、phase-guard、verify-artifacts 全绿。

## Boundaries

- **会做**：C1～C5 及回归。
- **先问再做**：把警告升级为失败或拦截写入；在 NEEDS_SPEC 以外的阶段加停点；改草案结构或里程碑停点规则。
- **不做**：替用户写草案内容；去其他仓库补草案（mc-coord、delegate-owner 自己补）；版本号与发版。

## 并行边界

- 独占：`spec/usage-draft-gate.md`、`tasks/usage-draft-gate/`、`plugins/spec-guard/hooks/usage_draft.py`、`plugins/spec-guard/hooks/module-insert.py`
- 公共：无

## 文档建议

改 `commands/add-module.md`、`skills/spec-guard-ops/SKILL.md`（add-module 与 verify-artifacts 两节）、`docs/commands.md`（verify-artifacts 表一行）。
CHANGELOG 与 README 在最后一个模块统一写。项目没有文档基线。
