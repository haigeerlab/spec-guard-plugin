# 回归测试文档: sg-design-outline

需求文档 `spec/sg-design-outline.md`，技术方案 `tasks/sg-design-outline/design.md`（均已批准）。新用例集中在 `plugins/spec-guard/hooks/test_sg_design_outline.py`（新文件，按 test-registration-check 登记进 validate），
规则文字的断言在 `test_workflow_checkpoints.py`。下面的命令都在仓库根目录跑。

## 用例清单

### R1: 三种情况的判定
- 步骤：新流程 `normal` 模块分别：需求文档恰好一行合规的 `overall-design`；两行；路径不合规；以 `<!-- spec-guard: overall-design` 开头但缺路径；没有这一行。生效档位 `important`（含规则抬升）与 `normal`。与另一个模块同批插入能力图、单独插入、不在 git 里
- 预期：`design_outline_case` 的 `new` 只在恰好一行合规时为真；`important` 按生效档位；`cross` 只在同批 2 个及以上时为真，git 读不了时为假、不报错；bug、small、老流程模块返回 `None`；缺路径的那种行由 `overall_problems` 报 invalid
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_design_outline.py OutlineCase`
- 证据：运行输出

### R2: 全新的技术方案缺四节判失败
- 步骤：`new` 为真的模块（在途、已完成各一），技术方案只有六节；补上四节中文标题；换成英文标题；四节都写「不涉及」
- 预期：只有六节时 verify-artifacts 判失败并列出缺的四节；补齐后（中文或英文、内容只是「不涉及」）通过
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_design_outline.py NewDesignSections`
- 证据：运行输出

### R3: 改已有功能照旧六节
- 步骤：`new` 为假的模块，技术方案只有六节
- 预期：verify-artifacts 与阶段提示的输出与改动前逐字相同
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_design_outline.py Unchanged`
- 证据：运行输出

### R4: 重要需求的方案取舍少于两种做法时提醒
- 步骤：生效档位 `important` 的模块，「方案取舍」分别为：0 条、1 条、写成段落、`1)` `2)` 编号、`- <!-- x -->` 注释项、缩进续行、代码块里的列表、2 条、`1.` `2.` 编号；非重要需求只写 1 条
- 预期：少于 2 条（含段落、`1)` 编号、注释项、续行、代码块）时 verify-artifacts 出警告且不判失败；2 条及以上不提醒；非重要需求不提醒
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_design_outline.py Alternatives`
- 证据：运行输出

### R5: 跨模块缺「模块接口」时提醒
- 步骤：同批插入两个模块，其中一个的技术方案：没有「模块接口」一节；这一节为空；只有 `- <!-- TODO -->`；写了「无直接接口，因为…」；有接口描述；英文标题 `Module interfaces`。单独插入的模块没有这一节
- 预期：前三种出警告、不判失败；后三种不提醒；单模块不提醒
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_design_outline.py ModuleInterfaces`
- 证据：运行输出

### R6: 阶段提示只在 NEEDS_REGRESSION 出、各占一行、跟着条数变
- 步骤：同时命中 R4、R5 的模块，依次在 `NEEDS_DESIGN`（还没有技术方案）、`NEEDS_REGRESSION`、`NEEDS_PLAN`、`BUILDING` 看阶段提示；在 `NEEDS_REGRESSION` 把「方案取舍」从 0 条改成 1 条
- 预期：只有 `NEEDS_REGRESSION` 出「- 技术方案大纲：」两行；0 条改 1 条后状态码变化、文字里的条数变；其他阶段没有这两行
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_design_outline.py OutlineHint`
- 证据：运行输出

### R7: 批次结果在一次运行里复用、变了就重算
- 步骤：同一进程里对同一项目连续判两次跨模块；之间改能力图（加一个模块）或新提交一次
- 预期：不改时第二次不再调用 git 取批次；能力图或 HEAD 变了就重新算，结果跟着变
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_design_outline.py BatchCache`
- 证据：运行输出

### R8: 骨架与规则文字
- 步骤：读 `doc-skeletons.md`、`workflow-checkpoints.md`「技术方案审查」、`node-rules.md`「技术方案交审」
- 预期：骨架有四节与「模块接口」的中英文标题（`SkeletonTest` 通过）；三处都写明三种情况，「全新」写成恰好一行、格式正确、路径有效；node-rules 写出全新四节放进「实现方案」、重要需求写几种做法、跨模块写接口要点；每节不超过 `NodeRulesTests` 的字节上限
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py && python3 -B plugins/spec-guard/hooks/test_flow_v2.py SkeletonTest`
- 证据：运行输出

### R9: 版本与 CHANGELOG
- 步骤：读两份 `plugin.json`、两份 README 的 `--ref`、`CHANGELOG.md`、`interface.json`
- 预期：版本 0.100.0，CHANGELOG 有 `[0.100.0]` 一节并写明「有 `overall-design` 行的模块要补四节」；接口版本仍是 1.27
- 执行方式：command
- 命令：`python3 -B plugins/spec-guard/hooks/test_sg_design_outline.py Release && python3 -B scripts/check-interface.py`
- 证据：运行输出

### R10: 下游结论交付前再核一次
- 步骤：在本机 autopilot-hub、module-crew 的 `origin/main` 上 `git grep` 技术方案章节名与 verify-artifacts 的调用
- 预期：hub 不读这些章节、不跑 verify-artifacts 脚本；module-crew 只按 `_DESIGN_POINTS` 核对交审小项；结果与提交号记进 todo
- 执行方式：manual
- 证据：命令输出与提交号

## 成功标准对照

| 成功标准 | 用例 |
|---|---|
| S1 | R1, R2 |
| S2 | R3 |
| S3 | R4, R6 |
| S4 | R1, R5, R6, R7 |
| S5 | R3, R11 |
| S6 | R8 |
| S7 | R9, R11 |

## 受影响的老功能

### R11: 全部现有回归不变
- 步骤：跑仓库的三条最小验证
- 预期：全部通过；bug、small、老流程模块与三种情况都不成立的模块输出逐字不变；钉旧文字的断言改钉新文字，不删断言
- 执行方式：script
- 命令：`/bin/bash scripts/validate.sh && /bin/bash plugins/spec-guard/hooks/test-phase-guard.sh && /bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh`
- 证据：运行输出
