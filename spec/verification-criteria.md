# Spec: verification-criteria

<!-- spec-guard: review approved 3e925b054022 -->

## Objective

开发流程改版（S110）M3 的第二个模块，也是改版的最后一个模块。新流程要求合并前由**非作者**照回归文档逐条执行（⑦），结论分三档、只拦能证明的问题。
执行与把关归 autopilot；spec-guard 负责三件事：定义报告格式 `spec-guard.verification/v1`、只读判断一份报告是否成立、把成立的结论记下来并在 `/map --json` 给出。
现在这些都没有：新流程模块的最终验收要么等用户，要么（`merge=auto`）走 codex-final-acceptance 的「Codex 读代码」，和回归文档无关。

给谁用：autopilot（照回归执行、写报告、调校验器与记录命令、按结论合并）；module-crew（提示「还没有结论」）；合规监测（读 `/map --json` 的 `verification`）；
在新流程模块上实现的 agent（开工时记下作者会话）；用户（最终验收时看到结论）。

对外接口与用法草案一致吗：报告字段、三档结论、校验规则、记录位置与草案 C 节、D' 节一致（autopr-design #22347 补的字段都在）。草案没写、这里补上的：
JSON 字段名（假设 1）、作者会话怎么记（假设 3）、校验器的问题代码与退出码（假设 4）、`/map --json` 的 `verification` 多一个 `current`（假设 6）、
`merge=human` 时没有结论怎么办（Q1）、联调回归的结论（Q2）。

登记：用法草案 dev-flow-v2（用户 2026-11-24「确认插入，Q1–Q6 按推荐」），M3 里程碑；依赖 regression-doc-check（`regression_view` 的用例与 sha256）与 codex-final-acceptance（记录放在公共 git 目录的做法）。
需求确认沿用草案的确认，本 Spec 交审即确认范围；2026-11-25 用户回「批准；Q1 A；Q2 A」。

## Assumptions

1. **报告 `spec-guard.verification/v1`**（JSON，autopilot 写，存在它的证据目录 `~/.autopilot/evidence/<owner>__<repo>/<patchId>.verification.json`；校验器只按传入的路径读）：
   - 报告级：`schema`（固定 `spec-guard.verification/v1`）、`module`（模块 id）或 `usage`（需求名，Q2）、`regression: {document, sha256}`、`base`（merge-base）、`head`、`patchId`、
     `executor: {sessionId, host, vendor, sameVendorAsAuthor}`、`verdict`（`pass`／`pass-with-notes`／`fail`）、`cases`、`notes`。
   - 用例级：`{id, method, result, failCategory, baselineCommit, evidence}`；`result` 为 `pass`／`fail`／`baseline-fail`；`failCategory` 只在 `fail` 时写，取 `run-failure`（失败的运行）、
     `user-bug`（用户会遇到的 bug，附复现）、`check-failure`（跑不过的检查）、`wrong-doc`（改错的文档）；`evidence` 是 `[{type, path, sha256, source}]`，`type` 为 `log`／`screenshot`／`file`／`user-quote`，
     `source` 只在 `user-quote` 时必填（用户原话的出处，如会话 id 加时间）。
   - 意见：`[{title, detail, location, evidence}]`，`location` 是 `文件:行` 或用例编号；去重键由 autopilot 算（模块＋标题），spec-guard 不判。
   - 格式写进 `references/verification-report.md`（字段表与一份完整例子），校验器是唯一判据。
2. **patchId**：`git diff <base> <head> | git patch-id --stable` 的第一列。「当前补丁」= 默认分支（`origin/HEAD` 指向的分支，读不到时 `main`）与 HEAD 的 merge-base 到 HEAD 的 patchId；rebase 后补丁不变，结论照样有效。
   验证之后不改任何提交：最终 gate 的勾选与验收证据在合并后再补（同 codex-final-acceptance），记录在 git 目录里、不进提交。
3. **作者会话**：新流程模块开工后，写代码的会话用 `verification.py author --project <root> --module <id>` 记下自己：会话 id 取自环境变量（Claude Code 的 `CLAUDE_CODE_SESSION_ID`、Codex 的 `CODEX_THREAD_ID`），
   读不到时拒绝（`no-session-id`），不接受命令行传入；记在公共 git 目录 `spec-guard/authors/<id>.json`（列表，同一会话只记一次，带宿主与时间），不进提交。
   阶段提示在新流程模块构建中、还没有任何作者记录时多一行，给出这条命令。hook 不写文件，所以要 agent 自己运行。
4. **校验器 `verification.py check --project <root> (--module <id> | --usage <name>) --report <path>`**（只读）：报告成立要同时满足——
   - 格式对（`report-invalid`）；`regression.sha256` 等于当前回归文档的 sha256（`regression-changed`）；
   - 当前回归文档（`regression_view`）里每条用例都有结果（`case-missing`），报告里没有文档之外的用例（`case-unknown`）；用例的 `method` 与文档一致（`method-mismatch`）；
   - `manual` 用例至少有一条 `user-quote` 证据且写了 `source`（`manual-without-user`）；
   - `fail` 要有四类之一（`fail-category-missing`）并至少一条证据（`fail-evidence-missing`）；`baseline-fail` 要有 `baselineCommit`（`base` 或其祖先）和证据（`baseline-evidence-missing`）；
   - 证据文件读得到时 sha256 要对上（`evidence-sha-mismatch`）；读不到的只记为「未核验」，不判不成立（证据目录可能不在本机）；
   - 结论一致：有 `fail` 只能是 `fail`；没有 `fail`、有意见是 `pass-with-notes`；都没有是 `pass`（`verdict-inconsistent`）；
   - 执行者不是作者：`executor.sessionId` 不在作者记录里（`executor-is-author`）；
   - `patchId` 等于当前补丁（`patch-mismatch`）；`base`、`head` 在本仓库读得到时，`patchId` 要等于 `base..head` 的 patchId（`patch-id-wrong`），读不到只记为「未核验」（rebase 后旧的 head 可能已不在）。（2026-11-25 写 Plan 时修订：原文要求 `head` 是 HEAD 或其祖先，rebase 后不成立，与 AC5 冲突。）
   - 退出码：0 成立；1 不成立（列出全部问题代码）；2 用法错误、模块不在能力图上、不是新流程模块；3 判不了：没有作者记录（`author-unknown`）、git 读不了、回归文档还没写。
     `--json` 输出 `{schemaVersion, established, verdict, patchId, problems, unverified}`。
5. **记录命令 `verification.py record … --report <path> [--confirm]`**：先跑同一个校验，成立才写；不带 `--confirm` 只预览。记在公共 git 目录 `spec-guard/verification/<id>.json`（`--usage` 时为 `usage-<name>.json`）：
   `{schema, module|usage, verdict, patchId, base, head, regressionSha256, reportSha256, executor, notes: [title…], at}`，读回核对。同一模块再记会覆盖（以最新一次为准）。
   远端合并硬卡读不到本机目录，autopilot 另把「结论＋patchId＋报告 sha256」写进机器人证据评论，两边都要对上（autopilot 的事）。
6. **`/map --json` 的 `verification`**：老流程模块为 `null`；新流程模块没有记录为 `null`，有记录为 `{verdict, patchId, notes, reportSha256, current}`，
   `current` 表示记录的 patchId 等于当前补丁、`regressionSha256` 等于当前回归文档（不重跑整个校验）。只认 `current` 为真且 `verdict` 不是 `fail` 的记录算过。
7. **最终 gate**（新流程模块）：
   - 阶段提示在最终 gate 写明合并前验证的状态：没有结论 →「等合并前验证：由非作者照回归文档执行（autopilot）」；结论不是当前的 →「结论已过期（补丁或回归文档变了），要重新验证」；`fail` →「不通过，不要合并」；通过 → 给出结论与意见数。
   - `merge=auto`：有当前、通过的结论时最终 gate 算过（勾选在合并后补），同 codex-final-acceptance 的做法；没有就停下等用户（Q1 不影响这一条）。
   - `merge=human`：最终验收照旧交用户；验收消息里写明结论（或没有结论，Q1）。
8. **codex-final-acceptance 不再用于新流程模块**：`acceptance_step` 对新流程模块不给 Codex 验收的下一步；`review-mark --target acceptance` 对新流程模块拒绝（`acceptance-flow-v2`，退出 2）。老模块照旧。
9. **接口**：`interface.json` 1.23 → 1.24：加 `verification`（`author`、`check`、`record` 三条命令模板、退出码、问题代码、报告字段）与 `mapView` 的 `verification`；Q2 选 A 时加顶层 `usageVerification`。`check-interface.py` 同步。
10. **规则与文档**：新文件 `references/verification-report.md`；共享检查点规则与最终验收停点写明新流程模块的合并前验证；`docs/commands.md` 加 `verification.py`；CHANGELOG「未发布」加一条。
    版本仍是 0.96.0（未发布），不再升版本号。
11. **对外核对**：写定后把报告字段名、校验规则与命令发给 autopr-design（报告的写方）与 mc-coord；拟回告在验收时给出，发出要用户同意。
12. **不做**：执行回归用例、写报告、开意见 issue、合并、写机器人证据评论（autopilot）；非 spec-guard 模块的 PR；module-crew 的提示；判断用例内容写得好不好；
    改老流程模块的最终验收；删除 codex-final-acceptance。

## Contract

- **C1** 新文件 `hooks/verification.py`：`author`、`check`、`record` 三个子命令（假设 2～5，Q2 A 时含 `--usage`）；patchId 与作者记录的读取函数供 module_stage、map_view 复用。
- **C2** `hooks/module_stage.py`：作者记录提示行（假设 3）；新流程模块最终 gate 的验证状态与 `merge=auto` 算过（假设 7）；`acceptance_step` 跳过新流程模块（假设 8）；状态码带上验证状态。
- **C3** `hooks/map_view.py`：`verification`（假设 6），Q2 A 时顶层 `usageVerification`。
- **C4** `hooks/review_mark.py`：`--target acceptance` 拒绝新流程模块（假设 8）。
- **C5** `interface.json` 1.24、`scripts/check-interface.py`、`scripts/test-checkers.sh` 的接口夹具（假设 9）。
- **C6** `references/verification-report.md`、`references/workflow-checkpoints.md`、`references/node-rules.md`、`docs/commands.md`、CHANGELOG（假设 10）。

## Acceptance criteria

- **AC1** 一份合格的报告（含 `pass` 用例、`manual` 用户原话、`baseline-fail`、意见）校验成立，退出 0，`--json` 给出结论与 patchId。
- **AC2** 假设 4 的每个问题代码各有一份反例，退出 1 并列出代码；改回后成立。
- **AC3** 结论一致：有 `fail` 却写 `pass`，或有意见却写 `pass`，都判 `verdict-inconsistent`；风格类意见不影响 `pass-with-notes` 成立。
- **AC4** 执行者是作者时 `executor-is-author`；没有作者记录时退出 3 `author-unknown`；`author` 在读不到会话 id 时拒绝，同一会话记两次只留一条。
- **AC5** 补丁变了（多一个提交）判 `patch-mismatch`；把同样的改动 rebase 到新的 main 上，patchId 不变、照样成立；回归文档改一个字判 `regression-changed`。
- **AC6** `record` 只在成立时写，预览不写；写到公共 git 目录、不进提交；`/map --json` 的 `verification` 给出记录，补丁变了以后 `current` 为假；老模块为 `null`。
- **AC7** 新流程 `merge=auto` 模块：有当前、通过的记录时最终 gate 算过，`fail` 或过期时不算；阶段提示的四种验证状态各有一例；`merge=human` 的最终验收照旧停下交用户。
- **AC8** 新流程模块不再出 Codex 最终验收的下一步，`review-mark --target acceptance` 拒绝；老模块的 codex-final-acceptance 回归不变。
- **AC9** Q2 A 时：联调回归的报告用 `--usage` 校验与记录，`/map --json` 顶层 `usageVerification` 给出。
- **AC10** `interface.json` 1.24 与实际输出一致，`check-interface.py` 通过；老流程模块的阶段提示、`/map --json`、verify-artifacts 与 0.95.0 逐字相同；本机三条检查全绿；合并前头提交的 `CI required` 通过。

## Boundaries

- **会做**：C1～C6 及正反回归；拟回告（假设 11，发出要用户同意）。
- **先问再做**：超出假设 1～12 的改动；改用法草案的接口约定；并行边界外的文件；合并；发版。
- **不做**：假设 12 列出的事。

## 并行边界

- 独占：`spec/verification-criteria.md`、`tasks/verification-criteria/`、`plugins/spec-guard/hooks/verification.py`、`plugins/spec-guard/hooks/test_verification.py`、`scripts/validate.sh`、`plugins/spec-guard/hooks/module_stage.py`、`plugins/spec-guard/hooks/map_view.py`、`plugins/spec-guard/hooks/review_mark.py`、`plugins/spec-guard/hooks/test_flow_v2.py`、`plugins/spec-guard/hooks/test_map_view.py`、`plugins/spec-guard/hooks/test_review_marker.py`、`plugins/spec-guard/hooks/test-phase-guard.sh`、`plugins/spec-guard/interface.json`、`scripts/check-interface.py`、`scripts/test-checkers.sh`、`plugins/spec-guard/references/verification-report.md`、`plugins/spec-guard/references/workflow-checkpoints.md`、`plugins/spec-guard/references/node-rules.md`、`docs/commands.md`、`CHANGELOG.md`
- 公共：无

## Open questions

- **Q1 `merge=human` 的新流程模块，没有合并前验证结论时，用户的最终验收还能放行合并吗？**（2026-11-25 用户选 A）
  - A（推荐）：能。阶段提示与验收消息写明「没有合并前验证结论」，由用户决定；硬性要求只对 `merge=auto`（代替 codex-final-acceptance）。
    结果：没装 autopilot、或 autopilot 还没跑的项目照样能用新流程；结论是给用户看的事实，不是拦截。
  - B：不能。新流程模块一律要有当前、通过的结论才算过最终 gate。代价：没有 autopilot 的项目每个新流程模块都要有人手写一份报告，否则卡在最终 gate。
- **Q2 多模块需求的整体联调回归（`spec/usage/<需求>.regression.md`）的结论，本模块做不做？**（2026-11-25 用户选 A）
  - A（推荐）：做。`check`／`record` 加 `--usage <需求>`，报告的 `usage` 写需求名；作者是涉及的各模块的作者合集；`/map --json` 顶层加 `usageVerification: {<需求>: …}`，module-crew 据此提示「还没有结论」。
    结果：与 regression-doc-check 已采纳的布局配套，autopilot 跑联调回归时有地方记结论。代价：多一组用例与一个顶层字段，约多一个任务。
  - B：不做，只做模块级；联调回归的结论以后单开模块。代价：module-crew 的「联调回归还没有结论」提示一直没有数据可读。

## 文档建议

`references/verification-report.md` 是 autopilot 写报告时唯一要对照的说明，C6 里写全字段表与例子；`docs/commands.md` 加 `verification.py` 一节。项目没有文档基线。
