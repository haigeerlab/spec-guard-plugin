# 回归测试文档: sg-skill-map

需求文档 `spec/sg-skill-map.md`，技术方案 `tasks/sg-skill-map/design.md`（均已批准）。新用例集中在 `plugins/spec-guard/hooks/test_sg_skill_map.py`（新文件，按 test-registration-check 登记进 validate），
规则文字的断言在 `test_workflow_checkpoints.py`。下面的命令都在仓库根目录跑。

## 用例清单

### R1: 位置判定互不重叠
- 步骤：新流程模块依次处于：需求等确认且没有审查记录；需求等确认且有记录；总体技术方案等批；`NEEDS_DESIGN`；`NEEDS_REGRESSION` 且技术方案等审；`NEEDS_REGRESSION` 且技术方案已批；`BUILDING` 未到最终 gate；`BUILDING` 到最终 gate。老流程模块
- 预期：`skill_position` 依次为 `review-first`、`confirm`、`overall`、`design`、`design`、`None`、`build`、`final`；老流程为 `None`
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_skill_map.py Position`
- 证据：运行输出

### R2: 点名那一行
- 步骤：R1 的每个位置看阶段提示（中英文）
- 预期：有位置时恰好一行「- Skill：」，列出该位置的 skill 与括号里的条件；写 todo 之前的位置写「写 todo 时补进」，构建与最终验收写「记进 todo」，构建一行带情境触发；没有位置时、老流程模块没有这一行
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_skill_map.py SkillLine`
- 证据：运行输出

### R3: 模块角色视角
- 步骤：多模块并行、标了模块角色的 checkout；需求从「先审一轮」切到「确认停点」
- 预期：角色视角同样出点名行；状态码随位置变化
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_skill_map.py RoleView`
- 证据：运行输出

### R4: 记录解析
- 步骤：todo 的「Skill 使用记录」写：`- 实现：incremental-implementation、test-driven-development`；`- 审查：delegate:review`；`- 画图：没有现成的 skill，按常规做法来。`；`- Diagram: No existing skill, done the usual way`；`- 混合：a，b,c；d;e、a`；`- 没有冒号`；`- ：x`；`- 空：`；代码块里的一行；英文标题 `## Skill log`；没有这一节；老流程模块
- 预期：分别得到正确的 `{place, skills, none}`：`delegate:review` 不被切断、两种「没有现成」写法 `none` 为真、五种分隔符拆开并去重；写坏的行与代码块里的行跳过；没有这一节为 `[]`；老流程为 `null`；`/map --json` 每个模块带 `skillLog`
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_skill_map.py SkillLog`
- 证据：运行输出

### R5: 记录不影响勾选进度
- 步骤：todo 加了「Skill 使用记录」一节，前后对比模块进度与阶段
- 预期：未勾选数、阶段、下一个 gate 不变
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_skill_map.py TodoProgress`
- 证据：运行输出

### R6: 最终验收提醒
- 步骤：新流程模块到最终 gate，记录为空与非空；模块 `DONE`（含合并是自动、最终 gate 未勾的完成态）而记录为空；未完成且不在最终 gate
- 预期：最终 gate 且为空时阶段提示多一行提醒、verify-artifacts 警告不判失败，空与非空切换时状态码变化；有记录时不提醒；`DONE` 且为空时 verify-artifacts 警告；其他情况不警告
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_skill_map.py Reminder`
- 证据：运行输出

### R7: 规则文字
- 步骤：读 `workflow-checkpoints.md`「skill 对照」一节与「出事处理」、发版段落；`node-rules.md`「能力图审阅」「最终验收」；`doc-skeletons.md` 的 Plan 一节
- 预期：「skill 对照」写全五处对不上阶段的关卡、情境触发、不进主流程的两个与记录写法；「出事处理」与发版段落各有一句指向；能力图审阅提到 planning-and-task-breakdown；「最终验收」一节**没有**静态的补记录提醒；骨架说明记录写法；每节不超过 `NodeRulesTests` 的字节上限
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py`
- 证据：运行输出

### R8: 接口 1.28 与版本
- 步骤：读 `interface.json`、两份 `plugin.json`、两份 README、CHANGELOG
- 预期：接口 `1.28`，`mapView.flow.fields.skillLog` 写明含义、解析规则与 `null`／`[]`；`takeover.notes` 是 #530 改过的写法；版本 0.101.0，CHANGELOG 有 `[0.101.0]` 并写到 #530 的修正；`check-interface.py` 通过
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_skill_map.py Release && python3 -B scripts/check-interface.py`
- 证据：运行输出

### R9: 回告 lead
- 步骤：经 agent-relay 给 ecosystem-lead（线程 `autopilot-m5-7`）发 `skillLog` 的位置、字段与 todo 写法
- 预期：投递成功，消息编号记进 todo 的证据；失败时这一项不勾
- 执行方式：manual
- 证据：agent-relay 消息编号

### R10: 下游再核一次
- 步骤：在本机 autopilot-hub、module-crew 的 `origin/main` 上对全部受版本控制的文件 `git grep` `skillLog`、`Skill 使用记录`
- 预期：没有命中（不读、不枚举）；提交号记进 todo
- 执行方式：manual
- 证据：命令输出与提交号

## 成功标准对照

| 成功标准 | 用例 |
|---|---|
| S1 | R1, R2, R3 |
| S2 | R7 |
| S3 | R4 |
| S4 | R4, R5 |
| S5 | R6 |
| S6 | R8, R10, R11 |
| S7 | R9 |

## 受影响的老功能

### R11: 全部现有回归不变
- 步骤：跑仓库的三条最小验证
- 预期：全部通过；老流程模块输出除 `skillLog: null` 外不变；三处钉接口版本的断言按技术方案改，不删断言
- 执行方式：script
- 命令：`/bin/bash scripts/validate.sh && /bin/bash plugins/spec-guard/hooks/test-phase-guard.sh && /bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh`
- 证据：运行输出
