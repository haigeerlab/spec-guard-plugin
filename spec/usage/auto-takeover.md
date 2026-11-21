# Usage draft: auto-takeover

自动接管（总账 S101，合并方案 r2 已获用户批准）：按项目或模块设的接管档位，让 Codex 代替人批准 Spec、Plan 与最终验收，出事时自动收窄。

## Entry points

| Entry | Does | Module |
|---|---|---|
| `/spec-guard:config` 设 `takeover`／`moduleTakeover` | 说话设置接管档位（不接管、只接管 Plan、接管到合并、自定义；自定义含 Spec、Plan、合并、发布四项），先预览，用户原话确认才写入；放宽一次一档 | takeover-config |
| `/spec-guard:map --json` 的 `takeover` 字段 | 每个模块报 Spec、Plan、合并各由谁批与来源，供 autopilot 与 module-crew 读 | takeover-config |
| `project_config.py narrow` | 只许收窄的写入口：autopilot、module-crew 出事时调用，往严里改一格，不要用户原话 | takeover-narrow |
| `/spec-guard:review-mark --state codex-approved`（Spec、Plan） | Codex 审过、无阻断时记 Codex 批准标记，与用户批准分开 | codex-approval |
| 阶段提示的批准行与停点 | 档位勾了该项时把 Codex 批准当已批准；阻断两轮未解决、Codex 不可用时停下交人 | codex-approval |
| 阶段提示的重要需求判定 | 新模块、跨模块、碰高风险路径时要求先做需求拷问，Spec 强制人批 | important-requirement |
| 越界检查（阶段提示与只读结果） | 接管模块的改动超出声明范围时停下，并给 autopilot 一个只读结果 | takeover-scope-check |
| `/spec-guard:review-mark` 记最终验收的 Codex 标记 | 合并勾了「自动」时，凭三样证据记 Codex 验收，与用户验收分开 | codex-final-acceptance |

## Typical usage

### U1: 给项目设接管档位

你说「这个项目只接管 Plan」。agent 跑 config 预览，写明三项各由谁批、与现在相比改了什么；你确认后写入 `.agent/config.json`。
`/map --json` 里每个模块的 `takeover` 显示 `plan: codex`，其余为 `human`。旧的 autonomyTier 还在文件里时，预览提示它已退役、不生效。

### U2: 只接管 Plan 时做一个普通需求

agent 总结需求、你说「说完了」；Spec 照常交你批。Plan 写好后，agent 用 delegate 请 Codex 审：没有阻断，就用 review-mark 记
`codex-approved`，阶段提示当作已批准、接着构建；有阻断就改完复审，两轮还没解决或 Codex 不可用，停下来交给你。

### U3: 出事自动降档

autopilot 发现一次自动合并被撤回，调 `narrow`：模块从「接管到合并」降到「只接管 Plan」，并记下原因。你想恢复时，用 config 说一句，
预览后确认，一次只升一档。

### U4: 接管到合并

模块勾了「合并：自动」。构建完成后，Codex 逐条对照 Spec 的验收标准审最终补丁、无阻断，另有非作者在同一提交上跑过检查；agent 记下
Codex 验收标记，autopilot 据此合并。缺任一样就停在最终验收，等你。

### U5: 重要需求

你提的需求要新开模块或跨模块，或碰到高风险路径：agent 先做需求拷问，再交你评审；这份 Spec 无论档位如何都由你批。

## Milestones

| Milestone | Usage | Modules |
|---|---|---|
| M1 | U1, U3 | takeover-config, takeover-narrow |
| M2 | U1, U2, U3, U5 | codex-approval, important-requirement, takeover-scope-check |
| M3 | U1, U2, U3, U4, U5 | codex-final-acceptance |
