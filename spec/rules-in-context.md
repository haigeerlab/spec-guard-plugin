# Spec: rules-in-context

<!-- spec-guard: review approved 3eb00d265758 -->

## Objective

0.63.3 在共享检查点规则里加了三条交审规则（最终验收附 Spec 差异一并复审；验收后接着写下一份 Spec；交审要点在正文、在会结束本轮的
确认框之前）。发版后的真实会话表明，这三条在 Claude Code 里没有生效：

1. `claude -p` 两次都没读规则文件（一次读取被拒，一次没去读），只照 CLAUDE.md 约定块办，仍要求单独复审 Spec。
2. 观测会话补充：一个真实的交互式桌面会话 6 小时做了 12 个模块，规则文件只在开头读过一次，压缩后没重读；约定块里 8 处“细则见
   共享检查点规则”一次都没触发重读。所以在约定块里加“指向”不能让新规则生效。
3. 更直接的一处：Spec 批准后被修订时，阶段提示在 BUILDING 写死了“先把修订后的 Spec 交用户复审，不要继续构建”
   （`module_stage.py` 的 `review_hint`），与 O2 矛盾，会把 agent 带回单独复审的老路。

本模块把这三条放进 agent 每轮都看得到的地方：约定块模板各写一行规则原文；阶段提示在最终验收这一刻改成与 O2 一致的建议。

登记：2026-10-16 经 `/spec-guard:add-module` 插入能力图。需求来自会话「Spec/Guard 插件使用观测」（`local_3b05d344-963e-4750-8edb-83b08ad9d0ca`）
的报告与补充证据，经用户审阅后转来；用户 2026-10-16 选定“模板写原文 + 阶段提示修正”。发版后按「需求来源与回告」回告该会话。

## Assumptions

用户已于 2026-10-16 在能力图预览时确认：

1. **模板写原文，不写指向。** 每条规则压成一行，写清要做什么，不以“细则见……”代替。
2. **模板只新增行，现有行一字不改。** 已有项目 `setup-convention --replace` 不需要 `--accept-removals`；代价是已装项目要跑一次
   `--replace` 才拿到新行。
3. **阶段提示只改一种情况**：当前模块的 Spec 是“批准后已修订”，并且已到最终验收——todo 里第一个未勾的 `gate` 之前没有未勾项，
   它之后也没有别的 `gate`（之后的非检查点项，如“发版后的验证”，不算）。此时建议改为在验收消息里原样附上 Spec 差异、一次批准
   同时算验收与复审、批准后先 `review-mark`。其他情况（构建途中被改）照旧要求先停下复审。
4. 版本 0.63.4，一个 PR。

## Contract

### 约定块模板（`claude-block-local.md`、`codex-block-local.md` 各新增，措辞两边一致，命令写法按宿主）

- 交审时要点写在本轮对话正文里，放在任何会结束本轮的确认框之前；只出现在确认框摘要里的不算交审。
- 最终验收时若 Spec 在构建中被补改过，验收消息原样附上 Spec 的改动差异并写明一次批准同时批准修订后的 Spec；批准后先记 Spec 的
  批准，再勾选与提交；没附差异就单独复审。
- 最终验收获批后，下一个模块已在能力图里且用户没说停时，直接写它的 Spec 并交审，不为“是否开始”另停；验收消息预告这一步并提示
  可先 `/compact`。

`docs/convention-block.md` 同步列出新增行。

### 阶段提示（`module_stage.py` 的 `review_hint`）

| 条件 | Review 行 | 建议 |
|---|---|---|
| Spec 批准后已修订，已到最终验收（见假设 3） | 不变：`Spec … was edited after it was approved.` | 改为：在最终验收消息里原样附上修订后 Spec 的差异，说明一次批准同时批准验收与修订后的 Spec；批准后先用 review-mark 记录，再勾选与提交 |
| Spec 批准后已修订，其他情况 | 不变 | 不变（先给用户复审，不继续构建） |

判定读 todo 失败或认不出检查点时按“其他情况”处理（降级为现行提示，不误报）。

## Commands

```bash
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
python3 plugins/spec-guard/hooks/test_workflow_checkpoints.py
/bin/bash plugins/spec-guard/hooks/test-setup-teardown.sh
/bin/bash scripts/validate.sh
```

## Testing strategy

- 阶段提示：先加失败用例——已修订 + 只剩最终 gate（含其后有“发版后的验证”非检查点项）→ 新建议；已修订 + 还有未勾 task → 现行建议；
  已修订 + 只剩一个 gate 但其后还有别的 gate → 现行建议；todo 读不了 → 现行建议。再改实现转绿；现有用例逐字不变；变异各有断言变红。
- 模板：`test_workflow_checkpoints.py` 断言两份模板与约定块文档含三行的关键词；`setup-convention --replace` 在 0.63.3 装好的项目上
  退出 0、不需 `--accept-removals`。
- 发版后：Claude Code 与 Codex 各在“Spec 已修订、只剩最终 gate”的临时项目跑一轮真实会话，看验收消息是否附差异并说明一次批准。

## Boundaries

- Always：规则原文以 `references/workflow-checkpoints.md` 为准，模板行与它一致；钩子只读；输出仍是合法 JSON。
- Ask first：改动或删除模板现有行；把阶段提示的改动扩到最终验收以外。
- Never：在仓库、提交或 PR 里写消费者项目的名称或路径。

## Success criteria

1. 两份模板与约定块文档各有三行规则原文，现有行不变，`--replace` 不需 `--accept-removals`。
2. Spec 已修订且到最终验收时，阶段提示给出附差异一并复审的建议；其他情况与现在逐字相同。
3. 三套核心回归、规则测试、setup-teardown 回归与 `validate.sh` 全绿；变异各有断言变红。
4. 发版后两边真实会话按 Testing strategy 观察并如实记录；回告观测会话。

## Open questions

- 无。
