# Todo: docs-refresh

- [x] Task 0：提交已批准的产物 — 能力图新行、已批准的 Spec、Plan 与本 todo 一次提交。
- [x] Task 1：去掉命令总数（R1） — `README.md`、`README.en.md`、`docs/commands.md` 各一处改为不带数字的说法；三个文件里 `grep -nE '[0-9]+ ?(条|commands)'` 无命中。24 条命令在 `docs/commands.md` 都有说明：21 条有独立小节或表格行，`documentation-baseline／impact／verification` 三条在「文档治理与历史」表各一行，命令对照表以 `documentation-*` 合并一行，不需要补。
- [x] Task 2：术语表补 7 个概念（R2） — `docs/concepts.md` 新增 10 行（7 个概念中评审标记与批准指纹、进度表与关键卡点、变更记录与回告各拆两行）。依据：评审标记、批准指纹、评审节奏取自 `references/workflow-checkpoints.md`「评审节奏」「评审状态标记」；插队与暂停取自 `docs/workflow.md`「插队」与 `hooks/module_stage.py` 的 `paused_modules`（除当前模块外做到一半的都算暂停，不只插队）；挂起取自 `hooks/module_stage.py` 的 `SUSPEND_MARKER` 与 `docs/commands.md`；进度表、关键卡点取自 `commands/map.md`；变更记录、回告取自「需求来源与回告」；项目指向取自 `docs/commands.md` 的 link-project。已有条目未发现与现行行为矛盾。顺带发现（不在本任务文件范围）：`docs/design.md:115` 写“插件不记录原因或日期”，与 map-view 的挂起原因、stall-signals 的挂起时间不符。
- [x] Task 3：重新核对上游（R3） — 2026-10-16 浅克隆上游 HEAD `aeac41d`（0.6.13，2026-10-13，216 个文件）逐条跑「逐条怎么验」八条：全部与上次相同，五个缺口仍成立，命令 9 个、skill 24 个与 `check-command-names.py` 快照逐一相同；唯一变化是 Phase 0 起点由 :38 前移到 :34。`upstream-analysis.md` 更新头部日期与 commit、文件数注释、3.3 行号，新增本次结果表，原 09-30 表降为“上一次”，08-26 表移除（git 历史可查）。最低上游版本不变，README 未引用它，不需改。本机安装副本是 `1401c8b`（2026-10-03），比上游落后，已在文档注明。临时克隆已删除。不需要另开模块。
- [x] Task 4：审查报告索引与收口状态（R4） — `docs/reports/README.md` 补两份 2026-10-04 报告，现在列出目录下全部 7 份报告。架构审查报告末尾追加「收口状态」表：20 条全部收口。依据：CHANGELOG 0.52.1–0.54.0 各条写明的 F 编号（`CHANGELOG.md:445-532`），以及 `git log --merges origin/main` 里对应模块分支的合并 PR #241、#243、#245、#247–#250、#258；没有“未查到”的项。
- [ ] Task 5：SECURITY.md（R5）
- [ ] Task 6：数据与隐私一节（R6）
- [ ] Checkpoint 1（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
