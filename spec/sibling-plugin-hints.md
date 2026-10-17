# Spec: sibling-plugin-hints

<!-- spec-guard: review approved 2eb23448d574 -->

## Objective

spec-guard 常与同一作者的两个插件一起用：delegate（把明确范围的只读审查或执行交给另一个 agent）和 agent-relay（本机
Claude Code／Codex 会话之间发消息）。两个插件各自带着由用户措辞触发的技能，用户说「派给 Codex」「告诉某某会话」时会被想起；
但 spec-guard 流程里需要它们的那几个时刻——交审、最终验收要第二个 agent 复核，回告需求来源、通知其他会话——用户不会说这些话，
agent 也就想不起来，只能自己硬做或提醒用户手工转告。

spec-guard 知道流程走到了哪一步，这是另外两个插件做不到的。本模块只在约定块模板里加两行带条件的提示，把这两个时刻和两个插件
接上；不介绍插件功能（那是插件自己的技能描述的事），不探测是否安装，不新增机制。

登记：2026-10-17 经 `/spec-guard:add-module` 插入能力图。需求来自用户本人（本会话），用户 2026-10-17 选定修正版范围：只改约定块
模板里的条件提示，不改钩子、不加探测。

## Assumptions

用户已于 2026-10-17 确认范围；以下细节随本 Spec 一并审：

1. **只写「若装了」，不探测。** 没装插件的 agent 看不到对应技能，自然跳过这一行；代码不判断安装与否。
2. **只提议，不自动调用。** delegate 一行写「可提议」，得到用户同意才发起；审查结论只是参考，批准仍由用户给。agent-relay 一行
   用于本来就要发的消息（回告、通知），不新增发消息的场合。
3. **频率由节点限定，不每轮提。** delegate 提示只在 Spec／Plan 交审与最终验收这两类节点、且这次值得第二个 agent 复核时提；同一
   模块里用户拒绝过就不再提。
4. **模板只新增两行，现有行一字不改。** 已装项目 `setup-convention --replace` 不需要 `--accept-removals`；代价是要跑一次
   `--replace` 才拿到新行（与 rules-in-context 相同）。
5. **入口按宿主写**：Claude 侧写 `/delegate:review` 与 agent-relay 的会话通信；Codex 侧 delegate 只有 `delegate-routing`
   技能，按 Codex 模板惯例写 `delegate:delegate-routing`，agent-relay 写 `agent-relay:session-routing`。
6. 共享检查点规则 `references/workflow-checkpoints.md` 不改：这两行是可选提示，不是检查点规则。
7. 版本 0.64.1（只改模板与文档文字），一个 PR。

## Contract

### 约定块模板（`claude-block-local.md`、`codex-block-local.md` 各新增两行，措辞两边一致，入口按宿主）

Claude 侧：

- 新增于「交审 Spec 或 Plan 时……」一行之后：
  > Spec、Plan 交审或最终验收值得另一个 agent 复核时，若装了 delegate 插件，可提议用 `/delegate:review` 做只读审查，用户同意
  > 后再发起；审查结论只作参考，不算用户批准；同一模块里用户拒绝过就不再提
- 新增于「别人提出的改动或模块……回告来源」一行之后：
  > 回告来源或通知其他会话（含跨 Claude Code／Codex）时，若装了 agent-relay 插件，用它给对方会话发消息

Codex 侧同样两行，`/delegate:review` 换成 `delegate:delegate-routing`，agent-relay 一行注明 `agent-relay:session-routing`。

`scripts/check-command-names.py` 的外部命令放行表登记 `/delegate:review`（与已登记的 `/agent-relay:collaboration` 同理）；
agent-relay 技能名一律带 `agent-relay:` 前缀，满足 `check-collaboration-boundary.py`。

`docs/convention-block.md` 同步列出新增的两行。CHANGELOG 记一条「新增」。

## Commands

```bash
python3 plugins/spec-guard/hooks/test_workflow_checkpoints.py
/bin/bash plugins/spec-guard/hooks/test-setup-teardown.sh
/bin/bash scripts/validate.sh
```

## Testing strategy

- 先加失败断言：`test_workflow_checkpoints.py` 断言两份模板与 `docs/convention-block.md` 含两行的关键词（`delegate`、`只读审查`、
  `不算用户批准`、`agent-relay`），Codex 模板含 `delegate:delegate-routing`、Claude 模板含 `/delegate:review`；再改模板转绿。
- 改坏一处（删掉 Codex 模板的 delegate 行）确认断言变红，再复原。
- `setup-convention --replace` 在 0.64.0 装好的临时项目上退出 0、不需 `--accept-removals`，写入后新行在约定块里。
- 发版后：Claude Code 与 Codex 各在装了两个插件的临时项目里，看到 Spec 交审时 agent 是否提议一次 delegate 审查且未自行发起。

## Boundaries

- Always：两行都以「若装了」开头；delegate 只提议、不自动发起；现有模板行不变。
- Ask first：在钩子注入、阶段提示或 `/spec-guard:map` 里加同类提示；增加对其他插件（tier-guard、decision-inbox）的提示。
- Never：把这两个插件写成 spec-guard 的依赖或在钩子里探测它们；在仓库、提交或 PR 里写消费者项目的名称或路径。

## Success criteria

1. 两份模板与约定块文档各多两行带条件的提示，入口按宿主写对，现有行不变，`--replace` 不需 `--accept-removals`。
2. 钩子、阶段提示、判据与指纹算法没有任何改动（diff 只涉及模板、文档、测试、版本与 CHANGELOG）。
3. 没装两个插件的项目，agent 行为与现在相同。

## 变更记录

- 2026-10-17：Codex 侧入口由 `$delegate-routing`、`$session-routing` 改为 `delegate:delegate-routing`、`agent-relay:session-routing`，并在命令名检查器登记 `/delegate:review`。原因：构建中全档校验报协作边界与命令名两项不通过（agent-relay 技能名须带前缀、外部插件命令须登记），且 Codex 模板现有行即用 `插件:技能` 写法。来源：本会话构建中的校验结果。
