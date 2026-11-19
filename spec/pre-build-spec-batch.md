# Spec: pre-build-spec-batch

<!-- spec-guard: review approved e3a3c1d18130 -->

## Objective

开工前的 Spec 修订不再一改就复审。现在 Spec 批准后、Plan 批准前只要改一个字，阶段提示就让 agent 停下、先不写 Plan、把 Spec 再交
用户审一次；用户嫌这样反复批准太频繁。本模块把开工前这一段改成「攒着批」：修订记进 Spec 的变更记录，Plan 照常写，交审 Plan 时
附上 Spec 自上次批准以来的累计差异，一次批准同时记下 Spec 与 Plan；攒的期间只有 E1–E4 才当场停。构建中与最终验收的规则不变。

给谁用：按阶段提示推进的 agent；批准 Spec 与 Plan 的用户。

登记：autopr 需求 1b 第一步，由 autopr-design 会话提出（bridge #21580），用户对 1b 的安排「1a 之后做」经 #21582 转述，2026-11-20 用户在
本会话核对后「现在开工」，确认需求「说完了，第 4 条选甲」，确认插入能力图「确认插入」。第二步（AI 代替人批准）用户未授权，不做。账本 T1T36MR。

## Assumptions

1. **「开工前」**：Spec 有带指纹的批准标记、读作「批准后已修订」（`revised`），且 Plan 还没批准——阶段是 NEEDS_PLAN，或阶段是 BUILDING
   而 Plan 标记是 `pending`。Plan 已批准（或 Plan 没有标记的旧项目）之后按现有的构建中规则，不变。
2. **基线**：Spec 批准时的原文。从 git 历史里取：沿 `spec/<id>.md` 的提交从新到旧，找第一个「去掉标记行后的指纹等于当前批准标记里的
   指纹」的版本（指纹算法仍只在 `spec-digest.py`）。最多看最近 50 个提交。找到即「有基线」；找不到（批准后没提交就改了、指纹对不上）或
   git 读不了即「无基线」，按现在的做法当场复审，不凭记忆写差异。读不了时如实写「基线未判定」，不说成「没有基线」。
3. **有基线时的阶段提示**：批准一行照常报「批准后又改过」并写明基线提交；建议下一步换成：修订记进 Spec 末尾的变更记录，照常写 Plan；
   交审 Plan 时附上 Spec 相对基线的累计差异，用户批准后用 `review-mark --target both` 同时记下；出现 E1–E4 当场停下复审。节点规则按
   Plan 交审给（NEEDS_PLAN 时原来给的是 Spec 交审）。无基线时提示与现在逐字相同，只多半句原因。
4. **当场停的四种情况**（规则文字，hook 判断不了）：
   - E1 削弱已批准的意图：以修改前的验收标准逐条核对；判断不了按「已削弱」处理；新加的标准也要检查是否与旧标准冲突；
   - E2 Spec 没覆盖的新决定；
   - E3 碰到项目在 Spec Boundaries「先问」里列的项：由项目自己定，不做全局清单（例如装一个包只在项目写了「加依赖先问」时才停）；
   - E4 高风险或不可逆的操作。
5. **批准后先提交再改**：规则写明 Spec 获批后先提交（让基线可取），再继续改；取不到原文时退回当场复审。
6. **`review-mark`（用户选甲）**：`--target both --state approved` 且 Spec 读作 `revised` 时，预览先打印 Spec 相对基线的累计差异（写明基线
   提交）；无基线时打印一行说明要把改过的 Spec 全文给用户看。`--target plan` 在 Spec 为 `revised` 时照旧拒绝，提示改用 `--target both`
   并先给用户看累计差异。不新增命令。
7. **不变的**：第一次批准、最终验收由人做；构建中「范围内修正不停」的规则与最终验收一并复审；verify-artifacts 对「批准后已修订」照旧只警告；
   interface 不升。版本 0.90.0（阶段提示行为改变，次版本号）。

## Contract

### C1 基线（`hooks/module_stage.py`）

- 新函数 `spec_baseline(root, module) -> dict`：`{"status": "found", "commit": <sha>, "text": <原文>}`、`{"status": "absent"}` 或
  `{"status": "unverified", "reason": ...}`。只读 git（`log`、`show`），不写任何文件；最多 50 个提交。

### C2 阶段提示

- 开工前（假设 1）且有基线：批准行 `- 批准: Spec \`spec/<id>.md\` 批准后又改过（基线 <短 sha>）。`／英文同义；建议下一步按假设 3；
  节点规则种类为 `plan-review`。状态码包含「有基线」这一事实，状态变了才重发完整内容。
- 开工前且无基线或未判定：与现在相同的提示，加原因（「取不到批准时的原文」／「基线未判定：<原因>」）。
- 其他阶段、没有修订的项目：输出逐字不变。中英两套措辞都改。

### C3 `review-mark`（`hooks/review_mark.py`）

- 按假设 6；累计差异用 `difflib.unified_diff`，比较的是去掉标记行后的正文；`fromfile` 写 `spec/<id>.md (approved <短 sha>)`。

### C4 规则

- `references/workflow-checkpoints.md`「批准标记」一节「构建中范围内的修正不停」那条：把「还没开工时 Spec 被改，照旧交用户复审」改为开工前
  攒批规则（假设 1、3、4、5）。
- `references/node-rules.md`「Plan 交审」加一条：Spec 批准后又改过时，交审正文附 Spec 相对基线的累计差异（原样），写明批准本 Plan 也就批准
  修订后的 Spec，批准后用 `review-mark --target both` 记下；E1–E4 已当场停过的不再重复。各节字节数在上限内。

### C5 文档与版本

- `commands/review-mark.md`、`skills/spec-guard-ops/SKILL.md` 的 review-mark 一节、`docs/workflow.md`（批准一段）写明攒批与 `--target both` 的差异预览。
- 0.90.0：两份 `plugin.json`、README 中英 `--ref`、CHANGELOG `## [0.90.0]`。

## Acceptance criteria

- **AC1** `spec_baseline`：批准后提交、再改 → `found` 且 `text` 是批准时的原文；批准后未提交就改 → `absent`；不是 git 仓库或 git 失败 →
  `unverified` 带原因；超过 50 个提交以外的版本不找。
- **AC2** 阶段提示（`test-phase-guard.sh`）：NEEDS_PLAN 有基线时出攒批建议、基线短 sha 与 Plan 交审规则；无基线时与改前逐字相同外加原因；
  BUILDING 且 Plan `pending` 同样攒批；Plan 已批准的 BUILDING 输出不变；没有修订的项目输出不变。
- **AC3** `review-mark`（`test_review_marker.py`）：`--target both` 且 Spec 修订过时预览含累计差异与基线 sha、`--confirm` 后两份都为已批准；
  无基线时有全文提示；`--target plan` 仍拒绝并提示 `--target both`。
- **AC4** 规则：`workflow-checkpoints.md` 有攒批规则、E1–E4、「先提交再改」与「取不到原文退回当场复审」；`node-rules.md`「Plan 交审」有累计差异一条；
  `test_workflow_checkpoints.py`、`test_stop_rules.py` 断言并通过字节上限。
- **AC5** 版本 0.90.0（`check-manifests.py`、`check-readme-sync.py`）；`validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 全绿。

## Boundaries

- **会做**：C1～C5 及回归。
- **先问再做**：改构建中或最终验收的规则；让 hook 自己判定 E1–E4；新增命令；改 interface。
- **不做**：第二步（`ai-approved`、不可变人工基线、AI 做最终验收、凭证）；1c 自动合并；打 tag 与发 Release（合并后按发布流程做）。

## 并行边界

- 独占：`spec/pre-build-spec-batch.md`、`tasks/pre-build-spec-batch/`、`plugins/spec-guard/hooks/module_stage.py`、`plugins/spec-guard/hooks/review_mark.py`、`plugins/spec-guard/hooks/test_review_marker.py`、`plugins/spec-guard/references/node-rules.md`
- 公共：无

## 文档建议

改 `commands/review-mark.md`、`skills/spec-guard-ops/SKILL.md`、`docs/workflow.md` 与 CHANGELOG；README 只改 `--ref`（攒批是交审节奏的细节，
README 不讲批准标记）。项目没有文档基线。
