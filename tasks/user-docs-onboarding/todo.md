# Todo: user-docs-onboarding

- [x] Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿 — 2026-10-28 用户批准 Spec（「Spec 批准；Q1 A；Q2 A；Q3 A；Q5 A」）与 Plan（「Plan 批准」），能力图新行经 add-module 预览确认后写入；verify-artifacts 0 失败。
- [x] Task 1：实跑例子项目并存下输出（AC2、AC4 的证据） — scratchpad 里 `mktemp -d note-app.XXXX`、`git init`，用 `hooks/setup-convention.sh local` 装约定、`project_config.py set artifactLanguage zh-CN --confirm`，
  每步提交后用 `CLAUDE_PROJECT_DIR=<例子> bash hooks/phase-guard.sh </dev/null` 取 `additionalContext` 存成 `onboarding-out/01～10-*.txt`；能力图写完与结束时各跑一次 `verify-artifacts.sh`（4 通过／5 通过，均 0 警告 0 失败）；`map_view.py` 存 `09-map.txt`。
  阶段依次为 MAP_ONLY（装好即是，模板里有示例模块）→ NEEDS_PLAN（Spec 待批准）→ NEEDS_PLAN → BUILDING（Plan 待批准）→ BUILDING（下一个 gate）→ BUILDING（最终验收）→ MODULE_DONE → NEEDS_SPEC。
- [x] Task 2：写 `docs/getting-started.md`（AC1 文档部分、AC2～AC6） — 用脚本把实跑输出嵌入模板，避免手抄；Spec、Plan、todo 取自例子项目「待批准」那次提交（`git show`）。
  偏离 Plan 决定 2：除路径换成 `<项目目录>` 外，另删「外部审查（delegate）」一行（只在装了 delegate 时出现）、停点规则原文用一句代替，页首写明这三处处理。
  一行摘要的写法用 `module_stage.brief_line` 对例子项目实际生成后贴入（我起初手拼的少了反引号和「未勾选」）。/spec 与能力图关系核对 `docs/upstream-analysis.md` 3.3 节与 `templates/CAPABILITY-MAP.md`；链接检查 0 处问题。
  发现（先问，未改）：user-docs-align 写进 `docs/troubleshooting.md`「只看到一行 spec-guard 提示」的例子格式不对，同样少了反引号和「未勾选」。
- [x] Task 3：`docs/concepts.md` 术语（AC7） — 术语表末尾加 11 条，已有条目未改。核对：workflow-checkpoints「Plan 检查点分级」（61-63 行）、「并行边界」（353 行起）、331 行逗号组与 `templates/CAPABILITY-MAP.md` 的串行展开注释；
  激活信号对 `docs/workflow.md`；零足迹对 `commands/teardown-convention.md` 52-56 行；停点规则对 `references/node-rules.md` 五节；预先声明对 workflow-checkpoints 77-81 行；Epiq 对 `references/local-ticket-ledger-runtime.md` 4、19 行。
- [x] Task 4：`docs/commands.md` 的 Codex 话术（AC8） — 命令对照的 Codex 一列改为可直接说的话，表头改为「Codex（直接对 agent 说）」；每句点出 skill 名，动词对应 `spec-guard-ops/SKILL.md` 的小节
  （setup、teardown、phase and verify、tracker default、config、module-suspend、link-project、review-mark、checkout-role、add-module、documentation、proposal、history、map、cost report），
  本地事项对 `ticket`、`local-ticket-ledger-ops`、`local-ticket-portability` 的 description，会话协作对 agent-relay 的 collab skill。「skill 的 … 一节」写法 0 处；`check-command-table.py` 25 条命令都在。
- [x] Task 5：README 中英（AC1、AC9） — 「快速开始」末尾加上手文档入口；导航使用者一组首行加上手文档；原「常用命令」（6 条）改为「功能一览」，按 6 组列全 25 条命令
  （与其另起一节重复列出常用的 6 条，不如合成一处；偏离 AC9「新增」的字面，最终验收说明）；多模块并行一节加「spec-guard 不依赖 module-crew，没装时开关只打开规划层规则」，不写安装（module-crew 无公开仓库）。
  英文版同结构；`check-readme-sync.py` 通过；没有别处引用旧锚点 `#常用命令`；链接检查 0 处问题。
- [x] Checkpoint 1（report）：整体检查（validate、两套回归、链接、插件包无改动） — `validate.sh` 通过；`test-phase-guard.sh` 507 例、`test-verify-artifacts.sh` 78 例通过；
  链接检查（README 中英、getting-started、concepts、commands）0 处问题；`git diff --stat origin/main -- plugins/spec-guard` 为空。每个 task 提交前也各跑了一次完整 validate，均通过。
- [x] Task 6：新手测试复跑（AC10） — 派 sonnet 只读子代理，只给 README 路径、禁读源码与维护者文档。它照文档为「个人书签管理」写的能力图（`bookmark-store` → `bookmark-search` → `bookmark-cli`）
  放进新临时项目跑 `verify-artifacts.sh`：3 通过 · 0 警告 · 0 失败（第一次 `cp` 被交互确认拦下没覆盖，改用 `/bin/cp -f` 并 `cmp` 确认后重跑）。
  三样东西都找到：端到端例子在 getting-started「例子：记事工具 note-app」第 1～9 步；谁做什么在「你做什么，agent 自动做什么」（12 行，它评「够用」）；选用指引在「可选能力：什么时候开」。
  Codex 用户「知道」该说什么，举了命令对照里的「用 spec-guard-ops 查看阶段」。
  新发现（只列出，不在本模块处理）：
  1. README 前置条件没给 agent-skills 的安装命令，也没说 `/spec`、`/plan`、`/build` 来自它；
  2. workflow.md 新项目第 4 步「把 activeModule 改成下一个模块」主语不明，和 getting-started「agent 按阶段提示改」对不上；
  3. 没装协作插件时哪些话算批准没有明确列表（「批准」算、「继续」不算）；
  4. 「推送与不可逆操作须标 gate」时，新手不知道自己的检查点算不算不可逆；
  5. 阶段名是英文、提示正文是中文，没有解释；
  6. `/map` 输出的图例（🟢、○、折叠的「1 个未就绪」）没解释；
  7. 未启用账本时 `ticket` 会怎样没说；
  8. getting-started 叙述用 `/spec`、`/plan`、`/build`，Codex 里怎么对应没提；
  9. 停点规则原文被省略，看不到交审消息的实际样子；没演示驳回或批准后修订；Proposal、文档治理的「该开」判断偏抽象。
- [x] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行 — 2026-10-28 呈现做了什么（含与 Plan 的三处差异）、AC1～AC11 逐条证据、文档与其他改动表、6 个提交、Spec 未改、新手测试的 9 条新发现；用户回复「user-docs-onboarding 验收通过」。
