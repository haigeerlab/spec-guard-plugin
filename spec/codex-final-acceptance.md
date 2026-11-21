# Spec: codex-final-acceptance

<!-- spec-guard: review approved b26d1fd47c5a -->

## Objective

勾了「合并：自动」的模块，最终验收可以不等用户，由 Codex 凭三样证据完成：① Codex 逐条对照 Spec 的验收标准审最终补丁，没有阻断；② 非作者在最终提交上
跑过检查（命令与输出，autopilot 的硬卡证据）；③ 两者绑定到同一个提交（也就是当前 HEAD）。三样齐了记一个和用户验收分开的 Codex 验收记录（不进提交），
autopilot 据此合并；缺任一样就停在最终验收等用户。本模块也是 S101 的最后一个：改版本号 0.91.0、写 CHANGELOG 与 README 的「自动接管」一段。

给谁用：接管到合并的模块；据此合并的 autopilot；用户。

对外接口与用法草案一致吗：一致。对应 `spec/usage/auto-takeover.md` 入口「`/spec-guard:review-mark` 记最终验收的 Codex 标记」，典型用法 U4。

登记：S101 合并方案 r2 Q2（用户「按推荐批准」，总账 `bfce091`）；能力图插入经用户「确认插入；Q1 B」。账本 T1T36MR。

## Assumptions

1. **只对「合并：自动」的模块**：模块生效的接管档位里 `merge` 是 `auto` 时才可用；其余模块的最终验收照旧由用户做，输出不变。
2. **证据①（Codex 审最终补丁）**：`/delegate:review`（后端 codex）以本模块开工前的提交（takeover-scope-check 的默认基线）到 HEAD 为范围、`--spec` 带上
   `spec/<id>.md`；报告须完成、有结论、无阻断（缺 severity 按阻断），`scope.baseline` 为 commits 模式且 `to` 等于 HEAD，`scope.files` 里的 Spec 内容
   sha256 等于工作区 Spec。报告存到仓库外。
3. **证据②（检查证据）**：读本机文件 `~/.autopilot/evidence/<owner>__<repo>/<HEAD 完整 sha>.json`（autopr-design #21981；不进仓库，否则 HEAD 就变了），
   schema `autopilot.check-evidence/v1`：`repo`、`head_sha`、`runner`、`non_author`、`clone`、`ran_at`、`checks[{cmd, exit, output_sha256, tail}]`。只认
   `runner` 为 `autopilot-orchestrator`、`non_author` 为 `true`、`head_sha` 等于 HEAD、每条 `exit` 为 0；owner/repo 取 `origin` 的地址。文件不存在就是没有证据。
   spec-guard 不自己判谁是作者。
4. **证据③（同一提交）**：报告的 `to`、检查证据的提交、HEAD 三者相同；工作区不得有未提交改动。
5. **记录不进提交**（autopr-design #21981 指出：写进仓库文件再提交，HEAD 就变了，三样绑不到同一提交）：`review-mark --target acceptance --state codex-approved
   --review <报告>` 把 `{"marker": "codex-approved", "sha": <HEAD>, "module", "report_sha256", "report": <报告路径>, "at"}` 写到 git 目录里的
   `spec-guard/acceptance/<id>.json`（`git rev-parse --git-path` 求路径，不被跟踪、不进提交）；证据②按 HEAD 自己去找，不需要参数。`/map --json` 每个模块加
   `acceptance`（`null` 或 `{marker, sha}`），供 autopilot 读。三样缺一或越界检查不为 0（复用 takeover-scope-check）都拒绝并写明原因。
   todo 里的最终 gate 不在验收时勾：阶段提示把「记录的 sha 是 HEAD 或 HEAD 的祖先」视为最终 gate 已通过；合并后由 agent 在下一个提交里补勾并写一句来源。
6. **阶段提示**：「合并：自动」的模块到最终 gate 时，建议下一步换成「交 Codex 审最终补丁、等检查证据，齐了用 review-mark 记下；缺任一样停下等用户」（中英），
   节点仍附最终验收规则。勾掉后与用户验收一样转到下一个模块。
7. **底线**：「自治档位与底线」里「最终验收照旧由用户做」改为「勾了合并：自动的模块按本规则由 Codex 验收，其余照旧」。拟回告、文档核验等最终验收的其他要求照旧由 agent 写进
   todo 记录，回告文字在 Codex 验收时不发，留给用户（见 Q13）。
8. **发版准备**：两份 `plugin.json` 与 README `--ref` 改 0.91.0；CHANGELOG 写 0.91.0（S101 六个模块、S102，接口 1.15）；README 中英加「自动接管」一段（从用法草案展开）；
   能力图全部完成时的收尾文档建议在本模块最终验收里给出。

## Contract

- **C1** `hooks/codex_review.py`：`inspect_final(report, root, module)` 校验假设 2；`inspect_check(root)` 按 HEAD 找证据文件并校验假设 3。
- **C2** `hooks/review_mark.py`：`--target acceptance --state codex-approved --review`，记录写在 git 目录（假设 4、5）。
- **C3** `hooks/module_stage.py`：最终 gate 的建议下一步（假设 6）；读到验收记录（sha 是 HEAD 或其祖先）的模块按已验收处理。
- **C4** 规则、接口（`reviewMark` 新目标、`mapView` 加 `acceptance`）、说明；版本与 CHANGELOG、README（假设 7、8）。

## Acceptance criteria

- **AC1** 证据①：报告不是 codex、未完成、有阻断、`to` 不等于 HEAD、Spec 不在 `scope.files` 或 sha256 不符 → 各自拒绝。
- **AC2** 证据②③：检查证据缺失、`runner` 或 `non_author` 不对、任一 `exit` 非 0、`head_sha` 与 HEAD 不同、工作区有未提交改动、越界不为 0 → 各自拒绝；
  三样齐全 → 在 git 目录写验收记录（不改任何被跟踪的文件），`/map --json` 报出 `acceptance`，阶段提示视最终 gate 为已通过。
- **AC3** 档位：`merge` 不是 `auto` 的模块，`--target acceptance` 拒绝；阶段提示输出与改前逐字相同。
- **AC4** 阶段提示：`merge: auto` 的模块到最终 gate 时建议下一步按假设 6（中英）；`test-phase-guard.sh` 新段。
- **AC5** 规则、接口、0.91.0（`check-manifests.py`、`check-readme-sync.py`）、CHANGELOG、README；`validate.sh`、phase-guard、verify-artifacts 全绿。

## Boundaries

- **会做**：C1～C4 及回归、发版准备。
- **先问再做**：让 Codex 验收在 `merge` 不是 `auto` 时生效；替 autopilot 判断「非作者」；自动发出拟回告。
- **不做**：合并本身（autopilot）；打 tag 与发 Release（合并后按发布流程做）。

## 未决问题

- **Q12 检查证据的格式与位置**：autopr-design #21981 已答复，写进假设 3；它同时指出验收记录不能进提交，假设 5 与 AC2 随之修订（开工前修订，随 Plan 一起批）。
- **Q13 Codex 验收时拟回告怎么办**（2026-11-22 用户选 A）：
  - **A（推荐）**：Codex 验收只勾 gate、写标记，回告文字写进 todo 记录，不自动发出，等你下次在场时确认再发（回告是对外发送，照规则要你同意）。
  - **B**：照验收时写好的原文自动发出。

## 并行边界

- 独占：`spec/codex-final-acceptance.md`、`tasks/codex-final-acceptance/`、`plugins/spec-guard/hooks/codex_review.py`、`plugins/spec-guard/hooks/test_codex_review.py`
- 公共：无

## 文档建议

README 中英加「自动接管」一段（从用法草案展开：怎么设档位、试点先用「只接管 Plan」、Codex 审什么、出事自动降档）；`docs/workflow.md`、`docs/commands.md`、
`commands/review-mark.md`、`SKILL.md` 同步；CHANGELOG 写 0.91.0。项目没有文档基线。

## 变更记录

- 2026-11-22（开工前）：按 autopr-design #21981 写定检查证据（本机 `~/.autopilot/evidence/…`、`autopilot.check-evidence/v1`）；验收记录改为写在 git 目录、不进提交，最终 gate 合并后补勾，`/map --json` 报 `acceptance`。
- 2026-11-22（M3 返工，用户「批准；Q14 A」）：假设 5 加一条——除 HEAD 外，本模块开工前的提交（takeover-scope-check 的默认基线）里的配置也必须是「合并：自动」，否则拒绝；原因是 `.agent/config.json` 改为不算越界后，PR 不能借改配置给自己开自动合并。
- 2026-11-22（M3 返工，用户「Q15 A」，autopr-design 沙盒演练 2 发现）：基线仍按 Q10 A；接管模块的 `flow` 再加 `.agent/state.json`（`activeModule` 在模块交接时就会改）。约定块所在的 `CLAUDE.md`／`AGENTS.md` 与 `.github/autopr/risk-paths.json` 照旧算越界，应在 Spec 之前单独提交。
