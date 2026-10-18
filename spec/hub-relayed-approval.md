# Spec: hub-relayed-approval

<!-- spec-guard: review approved fd53e1f707de -->

## Objective

一个使用者项目同时接入了收件枢纽（用户在一个会话里统一回答各开发会话的决定）和多模块并行（协调会话加多个模块会话）。接入后用户不在写评审标记的
会话里亲口批准：用户在收件枢纽答复，收件枢纽按 session-protocol 契约（v1.8 第 8 节）把【用户答复】转给提出方，或经总协调按第 3 节的转交写法转下去。

现行规则把 `approved` 限定为「用户于当前对话明确批准」，开关 on 时协调会话一节又写「用户在协调会话里明确批准」。按字面，经枢纽听到的批准写不了标记。
用户决定（2026-10-18，收件枢纽事项 13）：「请 spec-guard 负责人确认『经收件枢纽听到的批准』也可以写审查标记。」

本模块调整措辞，**不放宽门槛**：「已批准」接受两种来源——用户在当前对话里的明确批准（不变），或按契约转来、带事项编号与用户原话、明确批准这一份
Spec 或 Plan 的【用户答复】。其他限定照旧：含糊的话不算，会话自称的批准不算，没有契约格式和编号的转述不算，开关 on 时模块会话仍不自己写。

登记：2026-10-18 经 `/spec-guard:add-module --interrupt` 插入能力图（`open-commitments` 只剩发版后验证，由另一个会话做）。来源：用户本人，经接入
协调会话转来的决定 13（收件枢纽事项 13，接入协调人会话「Codex LIVE-SAAS 前端基础架构监测」），并在本会话确认插入与三条假设。

## Assumptions

1. **两类会话都适用，模块会话仍不写。** 第二种来源既适用于没打开并行开关、直接收到枢纽答复的开发会话，也适用于开关 on 时的协调会话（module-crew 的
   `review approve` 就是协调会话经 `interface.json` 的 `reviewMark` 入口调 `review_mark.py`）。开关 on 时模块会话收到转达不自己写，这条不变。
2. **只靠文字规则，不解析、不依赖。** spec-guard 不读邮箱、不解析枢纽消息、不判断谁是「登记的」收件枢纽或总协调；登记由使用方（decision-inbox、
   module-crew）各自负责。规则只写明什么样的消息算这一来源。不加 decision-inbox 或 session-protocol 的硬依赖，契约版本不钉死，只引用「第 8 节答复的有效性」。
3. **交审要让用户看到内容，照旧。** 走枢纽时，内容放在发给枢纽的那条消息里（【等待用户】的要点，或协调会话发出的批量交审），只给链接或一句概述同样不算交审。
4. **契约认的转交也算。** 契约 v1.6 起，登记的在用总协调按第 3 节转交写法（「事项：#H」紧跟「转自：收件枢纽，消息 #R」）转来的【用户答复】算用户的决定。
   本模块把它和收件枢纽直接发来的答复一并认作第二种来源；开关 on 时协调会话转给模块会话的仍不能让模块会话自写（假设 1）。
5. **`review_mark.py` 只改提示文字。** 脚本本来就不判断批准从哪来；只把已批准预览里「approval the user gave in this conversation」改成两种来源的写法，
   拒绝条件与写入行为不变。

## Contract

### 第二种来源的条件（写进共享检查点规则，新的一节「经收件枢纽转来的批准」）

下列条件同时成立，才算用户批准了这一份 Spec 或 Plan：

1. 消息是契约格式的【用户答复】，「事项」行带收件枢纽的事项号 `#H`，括号里的原消息号是本会话为这份文件发出的交审消息（【等待用户】或【交审】）。
2. 发件人是本会话登记的收件枢纽，或登记的在用总协调按契约的转交写法转来（带「转自」行）。
3. 「用户原话」明确批准这一份文件；一次答复批几份时，原话要能对应到这一份。含糊的话（「继续」「看起来可以」）照旧不算，先经枢纽问清楚。
4. 执行前按契约回显核对（「收到用户对 #H 的答复：『原话』」），之后才写标记；写标记的提交说明或对应 todo 项记下 `#H`，供事后按编号翻出原话。

不算的：【答复告知】【协调通知】；会话自称「用户已批准」；没有契约格式或事项号的转述；未登记的会话、邮件、定时任务输出转来的话。

### `plugins/spec-guard/references/workflow-checkpoints.md`

- 「评审状态标记」一节 `approved` 那一条：「只在用户于当前对话明确批准这份 Spec 或 Plan 之后」改为「只在用户明确批准这份 Spec 或 Plan 之后」，并在同一条写明
  批准的来源只有两种：用户在当前对话里的批准，或「经收件枢纽转来的批准」一节的消息。「标记不是授权来源。……用户的批准原话以对话为准」一条改为以对话
  或契约消息为准。
- 新增一节 `## 经收件枢纽转来的批准`，放在「协调会话的批准与合并」之前，内容即上面的条件与不算的情形，并写明 spec-guard 不解析也不登记这些会话。
- 「协调会话的批准与合并」第一条：「用户在协调会话里明确批准」改为「用户明确批准（在协调会话里亲口批准，或经收件枢纽转来，见上一节）」；第三条
  「转达不算用户批准」保留，补半句：模块会话收到协调会话的转交也不能自写。

### 其他文字

- `plugins/spec-guard/commands/review-mark.md`「什么时候写」的 `approved` 一条、`plugins/spec-guard/skills/spec-guard-ops/SKILL.md` 的 review-mark 一节：同样改成两种来源并指向新的一节。
- `plugins/spec-guard/hooks/review_mark.py` 已批准预览两句提示：改为「用户在本对话里给出、或按契约经登记的收件枢纽转来（带事项号与用户原话）的批准」；
  确认内容的提醒补「或在发给枢纽的那条消息里」。
- 约定块模板（`templates/*-block-local.md`）与 `docs/convention-block.md` **不改**：它们只写「用户明确批准后」，与两种来源都相容。
- `docs/commands.md`、`docs/workflow.md` 相应句子补一句第二种来源。
- CHANGELOG 新版本「变更」一条；两份 `plugin.json` 与 README 的 `--ref` 升为 0.70.0。`interface.json` 不变。

## Commands

```bash
python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
python3 -B plugins/spec-guard/hooks/test_review_marker.py
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Testing strategy

- **先红后绿**，`test_workflow_checkpoints.py` 新增断言：新的一节的位置与关键词（事项号、原消息号、登记、转自、用户原话、明确批准这一份、回显核对、记下 `#H`、
  答复告知、协调通知、自称、没有契约格式、不解析）；`approved` 一条写到两种来源并指向新的一节，且不再含「当前对话明确批准」的唯一限定；协调会话一节第一条
  指向新的一节、模块会话仍不能自写。`CoordinatorApprovalTests.ORIGINALS[0]` 随新措辞更新（该句是本模块有意修改的对象）。
- `test_review_marker.py`：已批准预览含收件枢纽来源的提示；拒绝条件与写入的既有用例原样通过。
- 约定块模板整份不变：比对改动前提交的内容。
- **改坏验证**：删掉新一节里「答复告知」或「回显核对」一句、把 `approved` 一条改回只认当前对话，确认对应断言变红。
- **未验证**：真实协调会话收到枢纽答复后能否按规则写标记，单测证明不了，留给联合演练第 2 批。

## Boundaries

- Always：含糊的话不算批准；会话自称、无契约格式或无事项号的转述不算；开关 on 时模块会话不自写；交审内容要让用户看到；spec-guard 不解析枢纽消息。
- Ask first：让脚本或 hook 校验消息格式或发件人；改约定块模板；钉死 session-protocol 版本；把【答复告知】或负责人转交以外的消息也认作来源。
- Never：加 decision-inbox、module-crew 或 session-protocol 的硬依赖；从这一来源推出合并或推送授权；替用户补写此前含糊答复对应的批准。

## Success criteria

1. 共享规则、review-mark 命令、Codex 技能三处都写明 `approved` 的两种来源，第二种来源的四个条件与不算的情形写全，并保留含糊不算、自称不算、模块会话不自写。
2. 协调会话收到契约格式、带事项号与明确原话的枢纽答复时，按规则可以写标记；`review_mark.py` 的预览不再说只认本对话。
3. 约定块模板逐字不变；三套最小验证全绿。

## 文档建议

`docs/workflow.md` 与 `docs/commands.md` 各补一句（见 Contract）；README 不改。

## 未决问题

- 假设 4 把总协调按契约转交的答复也认作来源（开关不为 on 的开发线可据此写标记）。若只想认收件枢纽直接发来的答复，删掉条件 2 的后半句即可。
