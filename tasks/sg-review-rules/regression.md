# 回归测试文档: sg-review-rules

需求文档 `spec/sg-review-rules.md`，技术方案 `tasks/sg-review-rules/design.md`（均已批准）。新用例集中在 `plugins/spec-guard/hooks/test_sg_review_rules.py`（新文件，按 test-registration-check 登记进 validate），
规则文字的断言在 `test_workflow_checkpoints.py`。下面的命令都在仓库根目录跑。

## 用例清单

### R1: 需求文档没有审查记录时硬拦确认
- 步骤：临时项目里建新流程模块，生效档位依次为 `normal`、`important`、被风险路径抬升的 `small`；需求文档没有任何审查记录，跑 `review_mark.py --target spec --state approved --confirm`（以及 `--target both`）
- 预期：都退出 2，拒绝码 `requirement-unreviewed`，文件字节不变；补上三种记录中任一种后，同一命令照常写入批准
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_review_rules.py RequirementGate`
- 证据：运行输出

### R2: 不需要审的模块不拦
- 步骤：生效档位为 `bug`、`small`（没被抬升）的新流程模块，以及老流程模块，需求文档都没有审查记录，记确认
- 预期：照常写入；`/map --json` 的 `requirementReview` 依次为 `{required: false, status: not-required}`、同上、`null`
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_review_rules.py RequirementNotRequired`
- 证据：运行输出

### R3: 三种审查记录的写法、解析与只记一轮
- 步骤：分别用 `codex-reviewed --review <报告>`、`host-reviewed --blocking 2`、`no-reviewer --reason "<原因>"` 记一条；每种记完后再用三种写法各记一次；`no-reviewer` 不带 `--reason`、带空白、带 `--`、`>`、换行、超过 200 字
- 预期：第一条写入，记录行带审查时整份文件 sha256 前 12 位，`records` 的 `reviewer` 依次为 `codex`、`host`、`none`；之后任何一种都退出 2、拒绝码 `requirement-review-recorded`、不写文件；原因不合规退出 2、拒绝码 `requirement-review-reason`；手写的缺 `reason=` 的 `none` 行不算记录、verify-artifacts 判损坏；老流程模块的 `codex-reviewed` 照旧按轮次累加
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_review_rules.py RequirementRecords`
- 证据：运行输出

### R4: 确认停点的阶段提示
- 步骤：需求待确认的新流程 `normal` 模块：没有记录；有记录且审查后没改；有记录、审查后改过并提交；有记录但审查时的版本不在 git 里；改动差异超过 60 行
- 预期：没有记录时下一步是「先审一轮」，列出 delegate、宿主全新子会话、写明没有审查者三条路；有记录后才要求复述确认，并要求附上审查提了什么、改了哪些、哪些没采纳；依次给出「审查后没有改动」、差异正文、取不到的原因、前 60 行加「还有 N 行」；其他阶段不跑 git
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_review_rules.py RequirementHint`
- 证据：运行输出

### R5: review-mark 确认预览给出审查以来的全文差异
- 步骤：同 R4 的后三种情形，跑 `review_mark.py --target spec --state approved`（不带 `--confirm`）
- 预期：预览打印审查时到现在的全文差异，或写明取不到的原因；不写文件
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_review_rules.py RequirementDiffPreview`
- 证据：运行输出

### R6: 技术方案送审只看三种高风险
- 步骤：新流程 `normal` 模块的技术方案：影响面命中风险清单；「接口和数据改动」有实际内容；该节只写「不涉及」「无」「没有」`None`、`N/A`、`Not applicable`、`No changes`（含大小写、句末标点、列表符号变体）；影响面列了 `package.json`、`requirements-dev.txt`、`go.sum` 等；影响面只列已有文件但都不命中；影响面没写路径；`designReview: on` 且都不命中
- 预期：`designApproval.reason` 依次为 `risk-path`、`irreversible`、`null`（各空值变体都是 `null`）、`new-dependency`、`null`、`null`、`configured`；多种命中时 `reason` 是第一个、`reasons` 全列；`old-files`、`impact-unknown` 不再出现
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_review_rules.py DesignRequirement`
- 证据：运行输出

### R7: 没有风险清单时写明未检查
- 步骤：项目没有 `.github/autopr/risk-paths.json`，新流程模块刚写完技术方案（`NEEDS_REGRESSION`）；再放一份可读清单
- 预期：前者技术方案阶段提示有「T4 路径：没有可读的风险路径清单，`risk-path` 未检查」，`designApproval.riskList` 为 `no-list`，`risk-path` 不在 `reasons` 里；后者 `riskList` 为 `ok`、没有这句提示
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_review_rules.py RiskListHint`
- 证据：运行输出

### R8: design=reviewer 时重要需求也由第二审查者放行
- 步骤：生效档位 `important`、`design=reviewer` 的新流程模块：送审方案一轮无阻断；第一轮有阻断、第二轮无阻断；两轮都有阻断；不送审的方案；再把 `design` 换成 `human` 重跑
- 预期：`reviewer` 时依次为 `approved`（`approvedBy: reviewer`）、`approved`、`pending-user`、`not-required`；`takeover.designForcedBy` 为 `null`；`human` 时与改动前相同（每份交用户批，送审的先审）
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_review_rules.py DesignApprover`
- 证据：运行输出

### R9: 技术方案的宿主子会话与没有审查者
- 步骤：`review_mark.py --target design --state host-reviewed --blocking 0`、`--blocking 3`、`--state no-reviewer`；手写 `vendor=openai report=none` 的行
- 预期：写入 `design-review … vendor=host … report=none` 行，`--blocking 0` 同时写 `reviewer-approved` 标记；`no-reviewer` 写 `vendor=none … report=none`，状态 `unreviewed`；`rounds` 里这些轮次的 `reportSha256` 为 `null`；`vendor=openai report=none` 判损坏
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_review_rules.py DesignHostRound`
- 证据：运行输出

### R10: 被抬升的短流程模块能记技术方案
- 步骤：档位写 `small`、影响面命中风险清单被抬升成 `important` 的新流程模块，跑 `review_mark.py --target design --state reviewer-reviewed --review <报告>`；没被抬升的 `small` 再跑一次
- 预期：前者写入轮次；后者照旧拒绝（没有技术方案）
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_review_rules.py ElevatedTier`
- 证据：运行输出

### R11: 新流程重要需求判定只看风险路径
- 步骤：新流程模块分别满足「用法草案一次拆出多个模块」「并行边界公共文件」「与未完成模块重叠」「影响面命中风险清单」；同样的四种情形换成老流程模块
- 预期：新流程只有第四种给出 `important.reasons: ["risk-path"]`，前三种不判为重要需求；老流程四种的 `reasons` 与改动前逐字相同
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_review_rules.py ImportantV2`
- 证据：运行输出

### R12: 接口 1.27 与 /map 新字段
- 步骤：读 `interface.json` 与 `/map --json`
- 预期：接口版本 `1.27`；`requirementReview`、`designApproval.reason`、`reasons`、`riskList`、`rounds[*].reportSha256` 都在 `/map` 里且有说明；`reviewMark` 列出新 state、参数与三个拒绝码；`old-files`、`impact-unknown` 标注从 1.27 起新流程不再出现；`check-interface.py` 通过
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_review_rules.py InterfaceFields && python3 -B plugins/spec-guard/hooks/test_map_view.py`
- 证据：运行输出

### R13: 规则文字写的是新规则
- 步骤：读 `workflow-checkpoints.md` 的「需求确认」「技术方案审查」、`node-rules.md` 的「Spec 交审」「技术方案交审」、`doc-skeletons.md` 档位表
- 预期：有「先审一轮」三条路、只审一轮、交用户时附审查提了什么、改了哪些、哪些没采纳；送审只看三种高风险；`design=reviewer` 时重要需求由第二审查者放行；「重要需求技术方案一律交用户」「跨模块必为重要需求」「技术方案由用户批」不再出现；node-rules 每节不超过 3200 字节
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py`
- 证据：运行输出

### R14: 报告位置回告 ecosystem-lead
- 步骤：技术方案批准后把第 5 节（审查报告位置与格式）和两条下游改动需求经 agent-relay 发给 ecosystem-lead
- 预期：消息已投递（线程 `autopilot-m5-7`，2026-11-27 消息 #23440），lead 回复已转给 hub 与 module-crew（#23443）
- 执行方式：manual
- 证据：agent-relay 消息编号

## 成功标准对照

| 成功标准 | 用例 |
|---|---|
| S1 | R1, R2 |
| S2 | R4 |
| S3 | R6 |
| S4 | R8 |
| S5 | R11 |
| S6 | R7 |
| S7 | R12, R15 |
| S8 | R14 |
| S9 | R3, R4, R5, R9 |
| S10 | R1, R10 |
| S11 | R13 |

## 受影响的老功能

### R15: 全部现有回归不变
- 步骤：跑仓库的三条最小验证
- 预期：全部通过；老流程模块的阶段提示、`/map --json` 除新增字段外逐字不变；钉旧规则的断言改成钉新规则，没有删断言
- 执行方式：script
- 命令：`/bin/bash scripts/validate.sh && /bin/bash plugins/spec-guard/hooks/test-phase-guard.sh && /bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh`
- 证据：运行输出

### R16: design=human 与老流程的审批路线不变
- 步骤：`none` 预设与默认配置下的新流程 `normal`、`important` 模块，以及老流程重要需求模块，读阶段提示与 `/map --json`
- 预期：新流程 `design=human` 时技术方案照旧由用户批；老流程的 Codex 路由（`codexRoute`）、`important.reasons` 与改动前相同
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_important_requirement.py && python3 -B plugins/spec-guard/hooks/test_flow_v2.py && python3 -B plugins/spec-guard/hooks/test_review_marker.py`
- 证据：运行输出
