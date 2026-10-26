# Spec: autonomy-tier

<!-- spec-guard: review pending -->

## Objective

S32 让多模块并行更顺：同一个项目可以选更放手的「自治档位」，少问用户一些机械的事。档位各级具体放开什么，由 module-crew 定义
（`strict` 等于今天；`standard` 让 Spec 与 Plan 一起交审、声明目录内的公共文件直接改；`relaxed` 再把同步、快检查、记账类通知
改为收尾汇总）。spec-guard 这一侧只做三件事：

1. 项目配置新增 `autonomyTier`，存、读、报告来源；
2. 把「任何档位都不能低于」的底线写进规则；
3. 发 1.11：本模块是 S32 在 spec-guard 的最后一个模块，版本号与发版在这里做（`pre-declared-scope` 已在 #414）。

登记：依据 `plugin-ecosystem/proposals/2026-10-24-S32-并行流畅与额度外包.md`（用户批准，总账 `612634c`）。2026-10-26 用户在本会话确认需求
「需求齐了，按两个模块、一次发版，三个问题按推荐」——其中「档位不联动 `reviewCadence`，只在 config 说明里写清关系」。账本 TKYJ8DH。

## Assumptions

1. **取值与默认**：`strict`（默认，未设置时也按它）、`standard`、`relaxed`。取值不合法时只这个键按默认处理、verify-artifacts 判失败，
   和现有 `reviewCadence` 等键同一套 config-per-key 规矩。
2. **spec-guard 自己的行为不随档位变。** 阶段注入、停点规则、交审节奏、verify-artifacts 都不读它。和 `moduleConcurrency` 一样，**取什么值
   都不注入阶段提示**：每轮多一行对 spec-guard 用户没有信息量，含义在 module-crew 那边。
3. **不联动 `reviewCadence`（用户已定）。** `standard` 档要「Spec 和 Plan 一起交审」时，由用户或 module-crew 另把 `reviewCadence` 设为 `combined`；
   config 说明写清这一点，`show` 不做任何推断。
4. **写入要用户原话。** `/spec-guard:config` 设置或取消这个键之前，要用户在对话里明确说要设成哪一档；`--confirm` 前在回复里引用原话。
   这是规则文字，脚本判断不了谁说的。module-crew 的「建议升档，用户一句话确认才切换」也走这条路。
5. **读法给 module-crew**：`project_config.py show --project <root> --format json` 里 `key` 为 `autonomyTier` 的那一项（`value`、`source`）。
   不新增命令。`interface.json` 新增 `autonomyTier` 条目写明这一点，同 `moduleConcurrency` 条目的形状。
6. **底线写在 `references/workflow-checkpoints.md`「批准节奏」之后一段「自治档位与底线」**，原文按 S32 第二节第 3 条：任何档位都不能低于
   「能力图、Spec（可以和 Plan 一起批）、最终验收要用户批；测试改不红、Spec 没覆盖的决策、高风险不可逆改动这三种情况必停」。不改节点规则
   （`node-rules.md`）：那里的停点清单已经包含这三种，档位不会让它们变少。
7. **旧版本兼容**：0.68.0 到 0.84.2 不认识这个键，只忽略它（`Project config: ignored (unknown-key)`、verify-artifacts 警告）；0.67.1 及更早会把
   整份配置判为无效。config 说明与 CHANGELOG 照 `moduleConcurrency` 的写法提醒「团队都升级后再设置」。
8. **版本号 0.85.0**：新增配置项与接口（interface 1.11），按次版本号升；两份清单、README 中英 `--ref`、CHANGELOG 版本段（把「未发布」段
   并入）一起改。`interface` 已在 `pre-declared-scope` 升到 1.11，本模块只往里追加条目。

## Contract

### C1 配置项（`hooks/project_config.py`）

- `TIERS = ("strict", "standard", "relaxed")`；`VALIDATORS` 加 `autonomyTier`，`DEFAULTS` 加 `"autonomyTier": "strict"`。
- `show`（文本与 JSON）列出它的生效值与来源；`set`／`unset` 照现有流程预览、`--confirm` 写入；不合法取值退出 2、不写。
- `config_lines`（阶段提示）对它不输出任何行。

### C2 说明文字

- `commands/config.md` 可配置项表加一行：取值、默认、作用（「自治档位，含义由 module-crew 定义；spec-guard 只存、读、报告来源，自己的行为不随它变」）、
  与 `reviewCadence` 的关系（「不自动改交审节奏；要 Spec 与 Plan 一起审，另设 `reviewCadence=combined`」）、写入要用户原话、旧版本兼容提醒；
  「设置了的项会在每轮阶段提示里各出现一行」那句的例外里加上它。
- `skills/spec-guard-ops/SKILL.md` 的 config 一节同步（Codex 侧）。

### C3 接口（`interface.json` 1.11）

- 新增 `autonomyTier` 条目：`config`、`key`、`default: "strict"`、`values`（三档；`strict` 写「今天的做法」，另两档写「由 module-crew 定义」）、
  `readFrom`（C 假设 5）、`notes`（不联动 `reviewCadence`；任何档位不低于底线）、`contract` 指向本 Spec。
- `scripts/check-interface.py` 核对 `autonomyTier.values` 与 `project_config.TIERS` 一致；`scripts/test-checkers.sh` 加缺条目、少一档两例。

### C4 底线规则（`references/workflow-checkpoints.md`）

- 「批准节奏」之后新增「自治档位与底线」一段：档位是什么、谁定义、不联动 `reviewCadence`、写入要用户原话；底线原文（假设 6）；
  「项目自己的规则更严时以项目为准」照旧。

### C5 发版准备

- 版本 0.85.0：`plugins/spec-guard/.claude-plugin/plugin.json`、`.codex-plugin/plugin.json`、`README.md`、`README.en.md` 的 `--ref`；
  CHANGELOG 把「未发布」段改为 `## [0.85.0]`，补本模块条目与「升级须知」（旧版本兼容、接口 1.11）。`interface.json` 不再改版本号。

## Acceptance criteria

- **AC1** `test_project_config.py`：三档各能 `set`；未设置时 `show` 为 `strict`、来源 `default`；`fast` 等不合法值 `set` 退出 2 不写，文件里有不合法值时
  只这个键回到默认、`check` 失败、其余键照常；`unset` 能去掉。
- **AC2** 阶段提示：设了任一档，`config_lines` 输出与未设置相同（`test-phase-guard.sh` 或单测断言）。
- **AC3** `interface.json` 含 `autonomyTier`，`check-interface.py` 通过；把 `TIERS` 改少一档，它变红；`test-checkers.sh` 两例。
- **AC4** `workflow-checkpoints.md` 有「自治档位与底线」一段，含底线三项批准与三种必停、「不联动」「用户原话」；`config.md` 与 SKILL.md 有对应说明；
  `test_workflow_checkpoints.py` 断言。
- **AC5** 版本：两份清单 0.85.0、README 中英 `--ref v0.85.0`（`check-readme-sync.py` 通过）、CHANGELOG 有 `## [0.85.0]` 且不再有顶部「未发布」段。
- **AC6** `scripts/validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 全绿；改到 `.sh` 时 CI 同版 ShellCheck 无告警。

## Boundaries

- **会做**：C1～C5 及回归；能力图不再改；todo 末尾记更新说明。
- **先问再做**：要让 spec-guard 自己的任何行为随档位变；要往阶段提示注入档位；版本号不是 0.85.0。
- **不做**：档位的具体含义、升降档证据与切换（module-crew）；联动 `reviewCadence`；打 tag 与发 Release（合并后按发布流程另做，发版前先告诉
  ecosystem-lead 影响面）；改 `pre-declared-scope` 已做的内容。

## 并行边界

- 独占：`spec/autonomy-tier.md`、`tasks/autonomy-tier/`、`plugins/spec-guard/hooks/project_config.py`、`plugins/spec-guard/hooks/test_project_config.py`、`plugins/spec-guard/commands/config.md`
- 公共：无

## 文档建议

改 `commands/config.md`、`skills/spec-guard-ops/SKILL.md`、`references/workflow-checkpoints.md` 与 CHANGELOG；README 只改 `--ref` 版本号——档位是给
module-crew 用的配置，README 的多模块并行一节目前只讲 `moduleConcurrency`，不加档位说明，用户从 config 说明里查。项目没有文档基线。

## 变更记录
