# Spec: doc-suggestion-template-line

<!-- spec-guard: review approved 5a2f96d3144f -->

## Objective

0.60.2 在共享检查点规则里加了「文档建议」一节：能力图评审、每个模块的 Spec 交审、能力图全部完成时各提一次。发版后的
真实会话里，Spec 交审两边都照做了，能力图全部完成那一处两边都没做全（Codex 只对 README 表了态，Claude Code 没提）。

差别在于 agent 读不读得到：Spec 交审时 agent 会读 `review-mark` 的命令说明与技能，那两处都写了“文档建议”；全部完成时
agent 只会读到约定块，而约定块里没有一行提到它。0.60.1 的“最终验收列出实际改动的文件”在约定块里有一行，两边都照做了。

本模块在两份约定块模板里各新增一行，指向「文档建议」。

登记：2026-10-14 经 `/spec-guard:add-module` 插入能力图。

## Assumptions

用户已于 2026-10-14 确认：

1. 两份约定块模板各新增一行，已有的行逐字不变；升级的项目 `setup-convention --replace` 只新增这一行，不需要 `--accept-removals`。
2. 这一行只点出三个位置和“没有就写无”，细则指向共享检查点规则，不在模板里重复写法。
3. 本模块不带版本号；与下一个模块 `ui-verify-by-change` 一起发 0.60.3，版本号在那个模块的 PR 里改。
4. 判断“读不到所以没照做”只基于一次观察；本模块的效果由 0.60.3 发版后的真实会话再看一次。
5. 不加命令、钩子或阶段提示的文字。

## Contract

两份模板（`templates/claude-block-local.md`、`templates/codex-block-local.md`）在“模块最终验收时在对话里列出实际改动的文件”
那一行之后各新增一行：

```text
- 能力图评审、每个模块的 Spec 交审、能力图全部完成时各提一次文档建议（README 默认在候选里），没有就写“无”；
  细则见 `spec-guard:spec-guard-ops` 的共享检查点规则
```

`docs/convention-block.md` 同步；本仓库 `AGENTS.md` 的约定块用工作区源码更新（先预览，只应新增这一行）。
`CHANGELOG.md` 在 `[未发布]` 下记一条。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
/bin/bash plugins/spec-guard/hooks/test-setup-teardown.sh
/bin/bash scripts/validate.sh
```

## Testing strategy

- 先加断言并确认失败：`test_workflow_checkpoints.py` 的文档建议用例补一项，两份模板都含“文档建议”“能力图全部完成”。
- `test-setup-teardown.sh` 全部通过。
- 发版后（0.60.3）两边宿主各跑一次能力图全部完成的最终验收，看是否给出收尾文档建议并对 README 表态。

## Boundaries

- Always：模板只新增行。
- Ask first：在模板里写文档建议的细则；为它加钩子提示。
- Never：在 Spec、代码、测试、提交信息或 PR 中写入消费者项目的名称、模块或编号。

## Success criteria

- 两份模板各多一行，已有行逐字不变；本仓库约定块只多一行。
- 全套检查通过。
- 发版后的真实会话按 Testing strategy 观察，结果如实记录。

## Open questions

- 无。
