# 回归测试文档: sg-gate-flow

需求文档 `spec/sg-gate-flow.md`，技术方案 `tasks/sg-gate-flow/design.md`（均已批准）。新用例集中在 `plugins/spec-guard/hooks/test_sg_gate_flow.py`（新文件，按 test-registration-check 登记进 validate），
规则文字的断言在 `test_workflow_checkpoints.py`。下面的命令都在仓库根目录跑。

## 用例清单

### R1: 档位允许时需求确认要问发版，不允许时不问
- 步骤：临时项目里建一个新流程模块，需求未确认；分别把档位设成 `autopilot`、`{"preset":"autopilot","release":"human"}`、`none`，各跑一次阶段提示
- 预期：`autopilot` 时需求确认提示里有「做完自动发版吗？」与写 `release-preauth yes` 的说明；另两种没有，且提示文字与改动前逐字相同
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_gate_flow.py ReleaseQuestion`
- 证据：运行输出

### R2: releasePreauth 三种取值与批准失效
- 步骤：`autopilot` 档的新流程模块：有 `yes` 行且需求已确认；确认后改动需求文档；没有这一行；`release` 覆盖成 `human`；老流程模块；`release-preauth maybe` 写坏的行。逐个读 `/map --json`
- 预期：依次为 `true`、`false`、`false`、`null`、`null`、`false`（写坏的行 verify-artifacts 判失败）
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_gate_flow.py ReleasePreauth`
- 证据：运行输出

### R3: 总体技术方案关卡拦住、放行与失效
- 步骤：需求已确认、带 `overall-design spec/overall/x.md` 行的模块：文件缺失；文件 `pending`；用户批准；批准后改文件；标记是 Codex 的；路径指到 `spec/overall/` 以外。逐个看阶段提示、`/map --json` 的 `flow.overallDesign` 与 verify-artifacts
- 预期：只有「用户批准且指纹有效」时放行（`status` 为 `approved`），其余都停在这一关、`status` 依次为 `missing`、`pending`、`revised`、`pending`、`invalid`；verify-artifacts 对缺失、失效（已过需求确认）、路径不合规判失败；不带这一行的模块不出这一关、`overallDesign` 为 `null`
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_gate_flow.py OverallDesign`
- 证据：运行输出

### R4: review-mark 记总体技术方案只认用户
- 步骤：`review_mark.py --target overall` 分别带 `--state approved`、`pending`、`codex-approved`、`reviewer-approved`；模块没有 `overall-design` 行时也跑一次
- 预期：前两个写入那份文件的标记；Codex 与审查者状态拒绝、退出 2、拒绝码 `overall-user-only`；没有这一行时拒绝并说明，什么都不写
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_gate_flow.py OverallReviewMark`
- 证据：运行输出

### R5: 同一用法草案里的模块指向不同总体技术方案时提醒
- 步骤：用法草案里两个模块的 `overall-design` 行分别指向 `a.md`、`b.md`；再改成都指向 `a.md`
- 预期：前者 verify-artifacts 出提醒（不判失败），后者没有
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_gate_flow.py OverallConsistency`
- 证据：运行输出

### R6: 里程碑在 autopilot 下不阻塞
- 步骤：一个里程碑的模块全做完、未确认：模块全是 `autopilot`；其中一个是 `merge`；全是带 `preset` 的覆盖对象；全是不带 `preset` 的对象。各看阶段提示与 `/map --json`
- 预期：全 `autopilot`（含带 `preset` 的对象）时事实行带「不阻塞」、下一步不要求停、`blocking: false`；其余情况阶段提示与改动前逐字相同、`blocking: true`；出错对象不带 `blocking`
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_gate_flow.py MilestoneBlocking`
- 证据：运行输出

### R7: 六处合并写法逐字一致，旧句子不再出现
- 步骤：读 `references/workflow-checkpoints.md`，与附录 A 的改后原文（O1 那一句换成用户批过的收窄措辞）逐处比对
- 预期：六处一致；「合并永远由用户在对话里决定」不出现；钉原文的断言全部通过，没有删断言
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py`
- 证据：运行输出

### R8: 出事处理一节在、范围写清、有指向
- 步骤：读规则文件
- 预期：有「出事处理」一节，正文与用户批过的附录 B 一致，写明只管开 PR 以后；第 154 行那一句后面有指向它的说明；③-2 里「按『出事处理』」能找到这一节
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py IncidentSection`
- 证据：运行输出

### R9: 预设 autopilot 与单项覆盖的读写
- 步骤：`project_config.py set takeover autopilot`（预览与 `--confirm`）；`set takeover '{"preset":"autopilot","release":"human"}'`；`set takeover '{"preset":"plan"}'`；模块级 `moduleTakeover` 同样各一次；没有配置的项目读一次
- 预期：前两个预览与写入正确，`/map --json` 的 `takeover.preset` 为 `autopilot`、三项取值正确（覆盖后 `release` 为 `human`）；`preset` 取旧值被拒；没有配置时为 `none`、`preset` 为 `none`
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_gate_flow.py PresetConfig`
- 证据：运行输出

### R10: 收窄 autopilot 与三关不受预设影响
- 步骤：收窄入口对 `autopilot`、带 `preset` 的对象各收一格；`autopilot` 档下的需求确认、总体技术方案
- 预期：`autopilot` 收成 `merge`；带 `preset` 的对象收回最外层的非 human 项、结果不带 `preset`；需求确认与总体技术方案仍只认用户
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_gate_flow.py NarrowAndGates`
- 证据：运行输出

### R11: 连着做之前先说一句
- 步骤：新流程模块在 `NEEDS_REGRESSION`（技术方案已批）、`NEEDS_PLAN`、`BUILDING` 时看阶段提示；需求未确认、技术方案待批时再看；老流程模块看一次
- 预期：前三种下一步末尾有「先用一句话告诉用户接下来做什么」；有关卡在等时与老流程模块没有这句
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_gate_flow.py SayFirst`
- 证据：运行输出

### R12: 接口升 1.26，只加字段
- 步骤：读 `interface.json`
- 预期：`interface` 为 `1.26`；`takeover.releasePreauth`、`takeover.preset`、`milestoneStop.blocking`、`flow.overallDesign`、`reviewMark` 的 `overall` 都有说明与出现条件；`takeover.spec`／`takeover.plan` 仍在
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_gate_flow.py InterfaceFields`
- 证据：运行输出

## 成功标准对照

| 成功标准 | 用例 |
|---|---|
| S1 | R1 |
| S2 | R2 |
| S3 | R3, R4, R5 |
| S4 | R6 |
| S5 | R7 |
| S6 | R8 |
| S7 | R9 |
| S8 | R10 |
| S9 | R11 |
| S10 | R12, R13, R14 |

## 受影响的老功能

### R13: 全部现有回归不变
- 步骤：跑仓库的三条最小验证
- 预期：全部通过；老流程模块的阶段提示、`/map --json` 除新增字段外逐字不变
- 执行方式：script
- 命令：`/bin/bash scripts/validate.sh && /bin/bash plugins/spec-guard/hooks/test-phase-guard.sh && /bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh`
- 证据：运行输出

### R14: 旧值与无效配置照旧
- 步骤：配置写 `takeover: "plan"`、`{"plan":"codex"}`、`merge`、无效值；不带 `preset` 的自定义对象
- 预期：读取、收窄、老流程那一对（spec、plan）与改动前相同；`preset` 为对应预设名或 `null`
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_project_config.py`
- 证据：运行输出
