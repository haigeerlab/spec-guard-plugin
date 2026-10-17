# Todo: concurrency-rule-wording

- [x] Task 0：提交已批准的 Plan 与 todo — 2026-10-18 用户批准 Plan（含整份比对分两层的做法），review_mark 记录后与 todo 一起提交。
- [x] Task 1：共享规则新增一节与三句指引（先红后绿） — `test_workflow_checkpoints.py` 加 `CoordinatorApprovalTests` 5 例，先红 3 例（「三句原文逐字在」「模板不含开关名」本来就绿，作防线）；在「并行边界」之后新增「协调会话的批准与合并（moduleConcurrency 为 on 时）」一节，并在三处加指引后 41 例全绿，`check-no-parallel-surface.py` 通过。期间断言「一致」没命中，是规则原文没用 Spec 的说法，补成「与交审版本一致」，没有放宽断言。
- [x] Checkpoint 1（report）：整份比对、三套核心回归与改坏验证 — 一次性整份比对（临时脚本，不入库）：从当前规则文件去掉新一节与三句指引（各 1、2 处），结果与 `2cf8fb6` 的原文逐字节相同；`git diff 2cf8fb6 -- plugins/spec-guard/templates/` 为 0 行。改坏验证：把原文「先问清楚」改一个字时整份比对报 DIFFERENT；删「推送和远端合并」那句、删「不自动重试」时 `test_section_states_every_floor` 变红；均已复原。三套核心回归：`94319a1` 提交时全档通过（phase-guard 368、verify-artifacts 67）。此前两次提交被 phase-guard 第 9 段「标准输入不关闭时 3 秒内输出」拦下，原因是系统 Spotlight 索引把负载推到约 100，单独重跑 368 例全绿；等负载降到 20 以下后重提通过，未改任何代码。验收前自查发现两处指引少了标点（读成「唯一例外项目打开了……」），改为「本地集成分支有唯一例外：……」，整份比对（脚本同步改了要去掉的片段）仍为 identical，41 例全绿。
- [x] Task 2：CHANGELOG — 「未发布」小节加「变更」一条。
- [x] Checkpoint 2（gate）：模块验收 — 2026-10-18 在对话正文列出：实际改动 6 个文件（+310/-3，-3 为三行原文后续上指引，原文未删；无超出预计）、新一节全文与三句指引原文、一次性整份比对结果（与 `2cf8fb6` 逐字节相同，模板 0 行差异）、验证结果、期间因系统负载重提与标点修正（`d8130d8`）、未验证项（第 7 关实测）。用户验收通过；不推送、不开 PR，回到 map-startable 写 Plan。
