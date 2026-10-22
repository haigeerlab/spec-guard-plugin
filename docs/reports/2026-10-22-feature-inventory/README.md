# spec-guard 功能点清单（2026-10-22，基线 `85a1f560`）

五个子代理按功能区精读源码、命令、技能、模板、参考文档与能力图，共摘出约 716 个功能点；每个功能点写明行为、触发、默认开关、文件:行、来自能力图哪个模块，以及一句需求疑点。主会话抽查了 5 条关键说法，全部属实。

| 区 | 文件 | 功能点 | 内容 |
|---|---|---|---|
| A | [A-core.md](A-core.md) | 150 | 激活判定、会话事实、关联项目、阶段判定、阶段注入的每一种提示行、配置、setup/teardown、校验 |
| B | [B-module.md](B-module.md) | 126 | 中途插入、批准标记、挂起、进度表、gateTick、并行开关与角色、姐妹插件探测与 interface.json |
| C | [C-rules.md](C-rules.md) | 160 | 约定块每一条、检查点规则每一条子规则、派活规则 |
| D | [D-tickets.md](D-tickets.md) | 109 | 本地账本、受理事项、默认后端、GitHub/GitLab 托管、迁移归档恢复交接 |
| E | [E-proposal-docs.md](E-proposal-docs.md) | 171 | Proposal 生命周期、文档治理、能力历史、成本报告、维护者工具 |

## 大功能一览

| 大功能 | 功能点 | 近 30 天使用者项目使用 | 默认 |
|---|---|---|---|
| 多模块目录约定 + setup/teardown + verify | 约 40 | verify 344 次 | 需 setup |
| 每轮阶段注入（7 个阶段、21 种附注行、上下文、批准、外审提示） | 约 60 | 每轮（Claude 7,947 / Codex 1,154） | 启用即开，不能单独关 |
| 关联项目 link-project | 14 | 10 次 | 关 |
| 中途插入模块 add-module | 24 | 32 + 脚本 65 | 手动 |
| 批准标记 review-mark | 18 | 343 次 | 手动 |
| 挂起 module-suspend | 10 | 2 + 脚本 15 | 手动 |
| 进度表 map | 30 | 27 次 | 手动 |
| gateTick（给 module-crew 的接口） | 7 | — | 接口 |
| 并行开关、角色、并行边界 | 13 + 规则 | checkout-role 2 次 | 关 |
| 姐妹插件探测与 interface.json | 22 | 每轮（delegate 提示） | 装了就开 |
| 写给 agent 的规则：约定块 + 检查点规则 | 153（默认）+ 7（派活） | 每个会话常驻 | setup 即全部写入 |
| 本地账本（包装 epiq） | 32 | 约 100 次 | 需显式启用 |
| 受理事项 ticket | 20 | 4 次 | 手动 |
| 默认后端 tracker-default | 8 | 0 | 手动 |
| GitHub/GitLab 托管事项 | 22 | 0 | 手动 |
| 迁移、归档、恢复、交接 | 27 | 1 次 | 手动 |
| Proposal 五命令 | 77 | 0（窗口外 1 个项目） | 手动 |
| 文档基线、影响、核验 | 19 | 117 / 76（集中在 1 个项目） | 手动 |
| 能力历史 | 14 | 1 次 | 手动 |
| 成本报告 | 22 | 0 | 手动 |
| 维护者工具（scripts、evals、CI） | 39 | 仅本仓库 | — |

## 抽查确认的事实不一致（不需要需求判断，直接修）

- 能力图目标段说 GitHub/GitLab「只读、不创建或修改 Issue」，还写着「本机协作邮箱」；实际托管事项与交接会写远端 Issue，协作邮箱已拆到 agent-relay（`spec/CAPABILITY-MAP.md:7-10`）。
- `phase-guard.sh` 在激活判定之前就启动 python 解析根目录，与同文件注释「在启动任何 python3 之前就退出」不符（`hooks/phase-guard.sh:29-32` 对照 `:61-64`）。
- 能力图仍有 `dependency-check` 一行，代码已在 `a42a7f1b` 删除。
- 能力图 `module-insert` 一行写「with a spec skeleton」，实现明确不建骨架（`hooks/module-insert.py:6-8`）。
- README 对上游的描述过时（上游已有每模块 Spec）。

## 需求拷打议程（按影响从大到小，一次一个问题）

1. 定位：spec-guard 首先给谁用
2. 写给 agent 的 153 条默认规则：哪些是产品，哪些是个人习惯
3. 每轮阶段注入：要报告什么、多久报告一次、谁来报告上下文用量
4. 批准标记是否该改写下一步建议（hook 只报告事实的不变量）
5. 并行层与 gateTick：规划层还是运行层（module-crew）
6. 与决策收件箱、session-protocol 的耦合
7. 事项与账本：是否属于这个插件
8. Proposal：真实用户与 add-module、OpenSpec 的区别
9. 文档治理三件套
10. 能力历史
11. 成本报告与派活规则
12. link-project
13. 默认授权模型（批 Plan 即授权装包、并行时本地合并）
