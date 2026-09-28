# 设计理念与术语

## spec-guard 在做什么

[agent-skills](https://github.com/addyosmani/agent-skills) 给了 agent 一套从需求到交付的工作流：`/spec` 写规格，
`/plan` 拆任务，`/build` 逐项实现。它默认一个项目只有一份 `SPEC.md` 和一份 `tasks/plan.md`。项目一旦拆成多个模块，
就会出现三类问题：

- 多个模块的 plan 和 todo 写到同一个文件里，互相覆盖；
- agent 不知道现在该做哪个模块、处在哪一步，每轮都要重新摸索；
- 项目做到一半冒出新需求，没有地方登记，也没有人确认它该不该加、加在哪。

spec-guard 不替代 agent-skills，只在它外面补上三样东西：一个多模块的目录约定、每轮对话开头的阶段提示，以及把新需求
校验后插进能力图的方式——默认是快速插入，需要留痕时用 Proposal 流程。

## 设计原则

| 原则 | 具体表现 | 为什么 |
|---|---|---|
| 默认不生效 | 项目没有激活信号时，hook 完全静默 | 装了插件不应打扰与它无关的项目 |
| 只报告事实，不替你动手 | hook 不写文件；Proposal 流程不创建或修改 Issue、PR、分支和能力图 | agent 自动改远端状态最容易出错，也最难回退。决定和写入都留给人 |
| 探测失败就降级，不误报 | 缺 `python3` 或读不到远端时报「未验证」或 `unknown`，不说「流程断了」 | 把环境问题说成流程违规，会让人不再信任提示 |
| 共享事实只认远端默认分支 | Proposal 状态只从远端 main 的固定快照读，不看本地文件和其他 worktree | 多个 agent、多个 worktree 并行时，本地文件经常互相矛盾 |
| 一个项目一张能力图 | 新需求经快速插入或 Proposal，按锚点插进同一张图；模块按 Build order 逐个推进 | 两张图会给出两份互相冲突的「现在该做什么」；逐个推进让每一步都能验收 |
| 人工接受，记录不可改 | 接受 Proposal 要人来做，并留下写入后不能修改的验收记录 | 事后可以审计，谁接受了哪个版本一清二楚 |
| 可选能力显式启用 | 协作信箱、本地事项账本、文档治理都要单独开启 | 不用的人不背它们的依赖和风险 |

## 术语

| 术语 | 含义 |
|---|---|
| 能力图 | `spec/CAPABILITY-MAP.md`。列出项目的所有模块、各自职责、依赖关系和 Build order。每个项目同一时间只有一张 |
| 模块 | 能力图里的一行，一块可以单独验收的能力。id 用 kebab-case，定下后不改名 |
| Build order | 能力图里的一行 `Build order: a → b → c`，规定模块的推进顺序 |
| 模块 Spec | `spec/<模块>.md`，这个模块的需求与验收标准 |
| Plan / todo | `tasks/<模块>/plan.md` 与 `tasks/<模块>/todo.md`，每个模块各自一份，互不覆盖 |
| activeModule | `.agent/state.json` 里记录的当前模块，`/build` 只从它的 todo 取任务 |
| 阶段 | 每轮对话开头注入的状态，如 `NEEDS_PLAN`、`BUILDING`。完整列表见[使用流程](workflow.md#阶段提示) |
| 快速插入 | `/spec-guard:add-module`：在检查点校验、预览、经确认后把一个新模块插进能力图，是新增模块的默认方式 |
| Proposal | 需要留痕时，给已有能力图新增一个模块的提案，写在 `spec/proposals/<id>.md`，合进远端 main 才算发布 |
| Proposal Issue | GitHub 或 GitLab 上与 Proposal 一一对应的 Issue，用 `proposal-stage:*` 标签记录阶段 |
| revision | Proposal 内容的 SHA-256。内容一改，revision 就变，旧的评审结论随之失效 |
| 主链 | 由策略文件指定的一条评审分支，默认是 `integration/mainline`。只有在主链上才能给出「可接受」的候选结论 |
| 验收记录 | `spec/proposal-acceptances/<id>-<revision>.json`，人工接受时写入，之后不能修改 |
| 晋级 | 把已接受的 Proposal 按锚点插进能力图，并补上它的 Spec 和 Plan |
