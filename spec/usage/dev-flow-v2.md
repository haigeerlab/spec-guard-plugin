# Usage draft: dev-flow-v2

开发流程改版（总账 S110，需求见 plugin-ecosystem `research/2026-11-24-开发流程改版/需求.md`，用户 11-24 在本会话确认 spec-guard 部分的复述「说完了，照这样做」）：
流程固定为 需求文档 → 技术方案 → 回归测试文档 → 拆任务 → 实现 → 按回归验收。人确认需求；第二审查者对照代码审技术方案；Plan 不审、自动批准；
合并前由非作者照回归文档执行，结论分三档，只拦能证明的问题。spec-guard 是通用插件，不和前端耦合。

本草案只管 spec-guard 一侧。⑦ 的执行与把关、接管档位的放行归 autopilot；审查标准与第二审查者的选择归 delegate；多模块写法归 module-crew。
老模块（本版之前建的 Spec、Plan）照旧规则，不改、不补。

## Entry points

| Entry | Does | Module |
|---|---|---|
| 新模块的文档骨架 | 需求文档 `spec/<id>.md`、技术方案 `tasks/<id>/design.md`、回归测试文档 `tasks/<id>/regression.md`、Plan `tasks/<id>/plan.md`（只留任务）；需求文档头部写档位（bug／小改动／普通／重要），小改动三份合成一份 | flow-doc-skeletons |
| 阶段提示与 `/map` | 认新文档：缺需求、需求待确认、缺技术方案、技术方案待审或待批、缺回归、构建中、待合并前验证、完成；老模块照旧显示 | flow-doc-skeletons |
| `.agent/config.json` 的 `projectSections` | 项目声明追加章节（如前端「浏览器兼容」、后端「数据迁移」），骨架与检查按它补章节标题 | project-sections |
| 需求确认停点 | 每个需求都由用户在对话里确认，没有接管选项；复述里有写不出来的项（谁用、为什么、怎样算做成、不做什么）、有 agent 自己补的假设、或是重要需求时，自动转入拷问（interview-me） | requirement-confirm-gate |
| 技术方案审查 | 配置 `designReview`（`on`／`off`）决定普通需求审不审；碰老逻辑或跨模块时不论开关都强制审；第二审查者审一轮、改一轮，第二轮只核对上一轮；重要需求的技术方案由用户批 | design-review |
| Plan | 写完即自动批准，不交人、不交 AI；越界、不可逆操作、碰 T4 路径照拦 | plan-auto-approve |
| `takeover` 新取值 | 预设 `none`／`design`／`merge`，自定义 `{"design","merge","release"}`；旧值按兼容表读 | takeover-redefine |
| 回归文档检查 | 每条用例有执行方式（`command`／`script`／`ai-operate`／`manual`）与证据形式；每条成功标准都有用例；受影响的老功能列入回归 | regression-doc-check |
| 合并前验证（⑦）的通过标准 | 定义报告格式与三档结论；只读校验器判报告是否成立；`/map --json` 给出结论 | verification-criteria |

## Typical usage

### U1: 普通需求，用户只确认一次

你提需求，agent 复述（含档位「普通」）。复述里谁用、为什么、怎样算做成、不做什么有一项写不出来，或有 agent 自己补的假设，就先自动转入拷问，问清再复述；
你说「说完了」。agent 写技术方案和回归文档；项目 `designReview` 为 `on`，或技术方案碰到老逻辑、跨模块（不论开关），就交第二审查者审一轮、改一轮，
无需你批；两者都不是时不审；Plan 写完自动批准，开始实现。实现完，autopilot 让非作者照回归文档逐条执行，结论为「通过」或「通过但附意见」且绑定当前补丁时，
按档位合并或交你合并；附的意见自动开成后续 issue。

### U2: 重要需求

需求是新模块、跨模块或碰高风险路径：agent 先自动拷问，再复述交你确认；技术方案和回归文档写好后交你批（第二审查者的意见一并附上）；Plan 照样自动批准。

### U3: bug 与小改动

bug：需求文档写复现步骤和预期，修完补一条回归用例，不写技术方案。小改动：一份文档里写需求、做法和回归用例三节，按普通需求走。

### U4: 项目追加章节

前端项目在配置里声明「浏览器兼容」「视觉回归」两个追加章节：新模块的技术方案和回归文档骨架带上这两节，回归文档检查要求它们有内容或写明「不涉及」。

### U5: 合并前验证不通过

非作者执行回归时有一条命令用例失败：结论「不通过」，附失败的运行输出；autopilot 不合并。只有风格、命名类意见时结论为「通过但附意见」，不拦。

## 对外接口草案（给 autopilot、delegate、module-crew 对齐用）

### A. 接管档位（存储键仍是 spec-guard 的 `takeover`／`moduleTakeover`）

| 项 | 取值 | 说明 |
|---|---|---|
| 需求 | 不可配置 | 永远由用户确认 |
| `design` | `human`／`reviewer` | 技术方案由人批，或第二审查者审过即可（重要需求永远人批；第二审查者可能是同厂商独立会话，厂商写在审查记录里）。`reviewer` 时是否审仍按 `designReview`，但碰老逻辑、跨模块时不论开关都审；不审的普通需求技术方案直接放行 |
| Plan | 不可配置 | 永远自动批准 |
| `merge` | `human`／`auto` | 用户在对话里说『合并』后会话执行（GitHub `--auto`），或 ⑦ 通过后自动合 |
| `release` | `human`／`prepare`／`auto-confirm`／`auto` | 不变 |

预设：`none`（全人）／`design`（`design=reviewer`）／`merge`（`design=reviewer`、`merge=auto`）。

`/map --json` 每个模块直接给出**生效档位**：已把「重要需求的技术方案永远人批」算进去，autopilot 不再自己判。

旧值兼容（新版读到时）：预设 `plan` 读作 `none`（Plan 本来就自动批准了，技术方案仍要人批）；旧预设 `merge` 读作新 `merge`；自定义里的 `spec`、`plan` 两项忽略，
`show` 标为「已不生效」。四个仓库 11-23 开的 `takeover=plan` 因此在切换后等于 `none`：每份技术方案都要用户亲自批，比现在打扰得更多（现在 Plan 由 Codex 批）。
切换时怎么处理见待定问题 Q6。

### B. 回归测试文档的用例格式

每条用例一个小节：`### R<n>: <标题>`，下面四行 `- 步骤：`、`- 预期：`、`- 执行方式：command｜script｜ai-operate｜manual`、`- 证据：<形式>`，
另有「成功标准 → 用例」对照表与「受影响的老功能」一节。执行方式为 `command`／`script` 时写出命令。

Markdown 只在 spec-guard 一处解析：只读入口 `regression_view --json` 输出每条用例的编号、步骤、预期、执行方式、要跑的命令、证据形式、覆盖的成功标准编号、是否「受影响的老功能」。

### C. 合并前验证报告与「怎样算通过」

autopilot 照回归文档执行后写一份报告（`spec-guard.verification/v1`，JSON），存在 `~/.autopilot/evidence/<owner>__<repo>/<patchId>.verification.json`：

- 报告级：模块 id；回归文档的 sha256（结论绑定当时那一版文档，文档一改即作废）；`base`（merge-base）、`head`；`patchId`（merge-base..head 的 `git patch-id --stable`）；
  执行者（会话 id、厂商、是否与作者同厂商）；结论 `pass`／`pass-with-notes`／`fail`。
- 用例级：编号、执行方式、结果 `pass`／`fail`／`baseline-fail`、证据 `{type: log|screenshot|file|user-quote, path, sha256}`；`manual` 用例要有用户原话与出处；`baseline-fail` 写明基线提交。
- 意见（供自动开 issue）：每条 `{title, detail, location（文件:行 或用例编号）, evidence}`；去重键由 autopilot 算（模块＋标题）。

作者会话 id 由 spec-guard 在实现阶段记下（不靠报告自填），校验器据此判「执行者不是作者」。

spec-guard 只读校验（新脚本，退出码区分）报告是否成立，成立才算结论：

- 回归文档里的每条用例都有结果；`manual` 用例的结果来自用户确认；
- `fail` 必须属于四类之一并附证据：失败的运行、用户会遇到的 bug（附复现）、跑不过的检查、改错的文档；风格、命名、要未来改动才成立的风险只能记为意见；
- `baseline-fail` 要附改动前同一用例的失败证据，不算阻断；
- 结论与用例结果一致：有 `fail` 就只能是 `fail`；有意见、无 `fail` 为 `pass-with-notes`；
- 执行者不是 spec-guard 记下的作者会话；`patchId` 与当前补丁一致（rebase 后补丁不变，结论照样有效）；回归文档 sha256 与当前文档一致。

autopilot 调校验器，通过后调 spec-guard 的记录命令写结论，记在公共 git 目录（同现在的验收记录）；远端合并硬卡读不到本机目录，autopilot 另把「结论＋patchId＋报告 sha256」写进机器人证据评论，两边都要对上。
不是 spec-guard 模块的 PR，⑦ 由 autopilot 按同一套判据自己执行。校验通过的结论`/map --json` 每个模块给出 `verification: {verdict, patchId, notes}`；最终 gate 据此算过。原「Codex 读代码的最终验收」（codex-final-acceptance）在新模块上不再使用。

### D'. 合规监测要读的字段（`/map --json` 每个模块）

- `tier`：`bug`／`small`／`normal`／`important`；
- `requirementConfirm`：`{status, by（只能是 user）, at, sha256（需求文档）}`；
- `designApproval`：`{status, approvedBy（user 或 reviewer）, reviewerVendor, sameVendor, reportSha256, rounds}`；
- `verification`（见 C）；`takeover` 给生效档位（见 A）。

### D. 技术方案审查的记录

沿用现有轮次行与 `reviewRounds`（0.93.0）：技术方案的每轮审查记一行，最多两轮且第二轮只核对上一轮；审查者同厂商时报告里注明，spec-guard 照记、不判定。审查标准归 delegate。

delegate 侧已定（delegate-owner #22369，用户在 delegate 会话确认）：调用 `/delegate:review --profile design --backend auto --author-host <claude-code|codex> --paths tasks/<id>/design.md --spec spec/<id>.md [--spec <影响面里列的已有文件>…]`，
第二轮加 `--previous-report <上一轮报告>`；判据 `design-v1`；`--author-host` 由阶段提示按当前宿主填。报告顶层 `reviewer: {vendor, backend, same_vendor, selection}`，
`reviewerVendor`／`sameVendor` 取 `reviewer.vendor`／`reviewer.same_vendor`；`selection="none"`（`execution_status=conditions_missing`、诊断 `no_reviewer_available`）记为「未审」、不当失败。
阻断 = `recheck.items` 中 `unresolved` 的条目 + `findings` 中非 `suggestion` 的条目；拿不出代码证据的阻断 delegate 已降为 `suggestion`。`backend` 不再限 codex。delegate 计划 0.12.0、接口 1.7。
细化（delegate-owner #22372，delegate 两份 Spec 用户已批）：`--backend auto --author-host …` 时 `reviewer.same_vendor` 一定是 true／false（显式 backend 不带 author-host 时为 null）；
报告顶层 `criteria` 为 `severity-v1` 或 `design-v1`，复审前后必须相同；`--backend auto` 不能与 `--model`、`--effort`、`--max-turns`、`--max-budget-usd` 同用（退出 64），阶段提示给的命令不带这些参数；
开工前检测可用审查者用 `/delegate:doctor --reviewers --json`（`delegate.reviewers/v1`，只检查、不阻止、退出 0）。

## 待定问题

用户 2026-11-24「确认插入，Q1–Q6 按推荐」：Q1～Q6 均按推荐定；Q4 autopr-design 已同意（#22347），并补了报告字段与证据评论双重核对，已并入 C。接口按 #22347 的意见修订为 v1（`design` 取值改为 `reviewer`、生效档位、报告与用例字段、作者会话记录、`regression_view`、合规监测字段）。

- **Q1 文件布局**：技术方案与回归放 `tasks/<id>/`（推荐：与 Plan、todo 同目录，现有检查不受影响），还是 `spec/` 下。
- **Q2 档位谁定**：bug／小改动／普通由 agent 在复述里提出、你确认时一并确认（推荐），还是全由规则判定。
- **Q3 `designReview` 默认值**：`off`（推荐：与现状一致，项目自己开）还是 `on`。
- **Q4 报告存放与写入方**：报告由 autopilot 存在它的证据目录、spec-guard 校验后记结论（推荐，同现在的检查证据），还是由 spec-guard 命令写入。待 autopr-design 意见。

- **Q5「碰老逻辑」怎么判定**：技术方案的影响面列出了已有文件（不是本模块新增的文件）就算（推荐：可机械判定，宁可多审）；或只在改动已有文件里的函数、接口时才算。
  「跨模块」沿用现有的 cross-module 判定（并行边界列了公共文件或与其他未完成模块重叠）。
- **Q6 四个仓库切换时的档位**：切换时把 `takeover=plan` 映射为 `design`（推荐：Plan 原本交给 Codex，改版后对应的是技术方案交给第二审查者，打扰最少；
  放宽档位需要你在对话里的原话，切换时逐个仓库请你说一句）；或保持读作 `none`，每份技术方案都由你批。

## 后续模块已收到的输入（写对应 Spec 时处理，交用户批）

- regression-doc-check：module-crew 的多模块布局提案（mc-coord #22381；需求一级各节写进用法草案，整体联调回归 `spec/usage/<需求>.regression.md`，结论复用 `spec-guard.verification/v1`），
  需要让 `usage_draft.draft_files` 排除 `*.regression.md`；bug／small 的回归用例按同一格式解析、阶段提示提醒补上（ecosystem-lead #22380）；`regression_view --ref` 与用例内容 sha256（#22354）。
  另：M2 实跑（2026-11-25，用户「M2 通过」）发现草案字面与实现的三处差异，写 M3 的 Spec 时一并处理：U1「不审时无需你批」只在 `takeover=design` 下成立（默认 `design=human` 要人批，takeover-redefine Q2 A）；U2 实为技术方案先批、再写回归文档；U3 小改动不走技术方案审查。
  另：项目追加章节（projectSections）不能只有标题，要有内容或写明「不涉及」——0.94.0 只查标题（project-sections 假设 8），M1 验收时用户同意记到这里（2026-11-24「M1 通过」）。
- design-review：delegate 的调用方式与报告字段（见 D 节，#22369、#22372）。

## Milestones

| Milestone | Usage | Modules |
|---|---|---|
| M1 | U3, U4 | flow-doc-skeletons, project-sections |
| M2 | U1, U2, U3, U4 | requirement-confirm-gate, design-review, plan-auto-approve, takeover-redefine |
| M3 | U1, U2, U3, U4, U5 | regression-doc-check, verification-criteria |

<!-- spec-guard: milestone M1 confirmed flow-doc-skeletons, project-sections -->
<!-- spec-guard: milestone M2 confirmed requirement-confirm-gate, design-review, plan-auto-approve, takeover-redefine -->
