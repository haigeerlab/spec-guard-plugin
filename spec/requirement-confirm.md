# Spec: requirement-confirm

<!-- spec-guard: review approved 3b593ba81b58 -->

## Objective

用户反馈：在 spec-guard 管理的项目里提出一个想法后，agent 很快就插入模块、写 Spec，没有总结需求，也没问用户是否已经说完，
让人不放心（2026-10-21，用户本人，事项 JHMZ4K4）。

原因已查明，共三处：
1. 上游 agent-skills 0.6.12 的 `interview-me` 本身要求先总结、拿到用户明确的「是」、确认后停下；但它只在缺「给谁／为什么／怎样算成功／限制」
   时才自动触发。「做个 X」这类说法通常触发不了；什么时候算聊完，也由 agent 自己判断。
2. spec-guard 每轮注入的「建议下一步」都是产物：DONE 是「要做新工作，用 add-module 插入一个模块」，MAP_ONLY 是「写第一份模块 Spec」，
   IDLE 是「建能力图」。共享规则里也没有写 Spec 之前确认需求这一步。
3. 用户自己的全局配置也把「新功能」直接指向 `spec-driven-development`。这个文件不归插件管，本模块不碰。

本模块在 spec-guard 管理的项目里降低这道门槛：新需求进入能力图之前，先总结需求，并问用户「需求说完了吗」。上游不改。

## Assumptions

1. **触发时机只有一个：新需求进入能力图之前**，也就是用 `add-module` 插入模块，或在没有能力图／只有能力图时写第一份 Spec 之前。
   下面这些不触发：改 bug、构建中已批准范围内的修正与增补、已在能力图里的下一个模块（「验收后接着写下一份 Spec」照旧）、
   单纯提问、Proposal 流程。
2. **最低要求**：在对话正文里给一段需求总结，包括目标、给谁用、怎样算成功、限制、明确不做什么、还没定的。然后问
   「需求说完了吗？还有要补充的吗？」。
   - 只认明确确认。「好的」「继续」「你看着办」不算，要再问一次还有没有要补充的。用户主动说「已确定」、但还没看过总结时，
     先给总结再确认。
   - 用户确认后，这一轮停下。下一轮把能力图新行和 Spec 一起交审（一次批准），不为能力图新行单独停一次。
   - 总结里有明显空缺（上面几项答不出来）时，改用上游 `interview-me` 一次问一个问题，问完再回到总结。
3. **可以跳过**：
   - 用户明说「不用拷问，直接写」之类的话，按意思认，不按字面匹配；
   - 别的会话转来的需求，已附完整需求、而且用户已在别处批过（例如经总协调或收件枢纽转来用户原话）的，不再问，免得同一件事用户答两遍（用户 2026-10-21 确认）。
4. **只改文字，不加拦截**：
   - 共享检查点规则新增一节「需求确认」；
   - 两份约定块模板各加一行，指向这一节；
   - `commands/add-module.md` 在「提出四项」之前加一步；
   - DONE、MAP_ONLY、IDLE 三处「建议下一步」的措辞改成先确认需求，中英两版都改。
   NEEDS_SPEC 的提示不改：那时模块已经在能力图里，需求应已确认。
5. 不改 hook 判定、阶段名、interface.json、verify-artifacts 和上游 agent-skills。要不要给上游提 issue，另外再定。
6. 冻结期间只开发、不发版：版本号与 CHANGELOG 只写未发布段，阶段丙-2 结束后再定发版。

## Contract

### `references/workflow-checkpoints.md`

在「阶段交接」之前新增一节「需求确认」，写明第 1～3 条：触发时机、总结的各项、那句提问、只认明确确认、确认后停、
转 `interview-me` 的条件、两种跳过。

### 约定块模板（`claude-block-local.md`、`codex-block-local.md`）

各加一行：新需求插入能力图或写第一份 Spec 之前，先总结需求并问用户是否说完，细则见共享检查点规则「需求确认」。

### `commands/add-module.md`

「先读能力图，提出四项」之前加一步：这个需求是从用户对话里新提出的，且还没确认过时，先按「需求确认」总结并提问，等用户确认后再提出四项。

### 建议下一步（`hooks/module_stage.py` 的 DONE、`hooks/phase-guard.sh` 的 MAP_ONLY 与 IDLE）

- DONE：「要做新工作，先总结需求并问用户是否说完，确认后再用 add-module 插入一个模块」；英文同义。
- MAP_ONLY：「先跟用户确认第一个模块的需求已说完，再在 `spec/` 下写第一份模块 Spec 并交审」；英文同义。
- IDLE：「先跟用户确认需求已说完，再建能力图并交审」；英文同义。
- 其余阶段的提示一字不改。

### 不变

- 阶段判定；NEEDS_SPEC 及之后各阶段的提示；「验收后接着写下一份 Spec」；Proposal 流程；批准标记与交审规则。

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
```

## Testing strategy

- `test_workflow_checkpoints.py`：「需求确认」一节含触发时机、那句提问、只认明确确认、确认后停、转 `interview-me`、两种跳过的关键句；
  两份约定块模板都有指向这一节的一行；`add-module.md` 有这一步。先写断言，确认先红。
- `test-phase-guard.sh`：DONE、MAP_ONLY、IDLE 的建议语含「先确认需求」的说法（中英两版）；NEEDS_SPEC 的建议语照旧。
  依赖旧措辞的原有期望按新措辞改，逐条列出。
- 反向：删掉规则那一节或提示里那一句，对应断言变红（在副本上手工改坏，结果记入 todo）。

## Boundaries

- **会做**：规则一节、两份模板各一行、add-module 说明、三处提示措辞、回归、CHANGELOG 未发布段。
- **先问**：扩大触发范围（例如 NEEDS_SPEC 也问）；做成拦截或检测；改上游；发版。
- **不做**：用户的全局配置；给上游提 issue（另定）；冻结期间发版或升级本机。

## Success criteria

- AC1：共享规则有「需求确认」一节，写明触发时机、总结各项、「需求说完了吗？还有要补充的吗？」、只认明确确认、确认后停、转 `interview-me` 的条件和两种跳过。
- AC2：两份约定块模板各有一行指向这一节；`add-module.md` 在提出四项之前有这一步。
- AC3：DONE、MAP_ONLY、IDLE 的建议下一步（中英）都先提确认需求；NEEDS_SPEC 与其他阶段的提示不变。
- AC4：`validate.sh`、两边回归、`test_workflow_checkpoints.py` 通过；依赖旧措辞而改动的原有期望逐条列出。
- AC5：版本号不变，CHANGELOG 只写未发布段。

## Open questions

- 无。

## 变更记录

- 2026-10-21：第 2 条补两句：用户说「已确定」但还没看过总结时先给总结；确认后的下一轮把能力图新行和 Spec 一起交审。原因：最终验收后向用户讲解工作流时发现没写明，#395 未合并，补在同一 PR。来源：本会话（当前插件所有者）提出，用户回复「继续」。
