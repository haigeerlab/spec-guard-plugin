# Todo: gate-tick

- [x] Task 1：gate_tick.py 与测试（先红） — `test_gate_tick.py` 10 例，先红（脚本不存在，15 处失败）；写 `gate_tick.py`，判据只调 `module_stage.gate_checkpoints`／`at_final_gate`／`OPEN_ITEM`，以 `newline=""` 读入保留 CRLF，`_write_atomic` 写入；10 例全绿；登记进 `scripts/validate.sh`，快档通过。
- [x] Task 2：接口 1.7（先红） — `test-checkers.sh` 加两例（缺 gateTick 入口、脚本不存在），后一例先红；`interface.json` 升 1.7 加 `gateTick`，`check-interface.py` 的 ENTRIES 加上并核对脚本路径，145 例全过。注：前一例在接口加上之前因夹具 KeyError 而「通过」，接口加上后才真正生效。
- [x] Task 3：文档、CHANGELOG 与版本号 — `docs/design.md` 部件表加 `gate_tick.py`、接口一段加 1.7 说明、分层表「写」一栏补「最终验收的勾」；CHANGELOG 新开 0.83.0 段；两份 `plugin.json` 与中英 README 的 `--ref` 改为 0.83.0。
- [x] Checkpoint 1（report）：变异核对 — `git archive HEAD` 的完整仓库副本：未改时 10 例全过；判据换成「唯一未勾项」后 `test_items_after_the_final_gate_stay_and_are_counted` 与判据一致性用例变红；预览也写文件后 `test_preview_changes_nothing` 等 3 处变红。
- [x] Checkpoint 2（gate）：模块最终验收；推送与开 PR 在此由用户确认，合并由用户进行 — 2026-10-22 按交审小项呈现：做了什么、AC1～AC5 逐条证据、变异核对、文档改动表（3 个）、其他改动表（无超出 Plan 的文件）、「新增依赖、锁文件改动：无」、提交表（97017c6、da92902、8260510，勾选本 gate 为待提交）、Spec 未改、注意（未做独立评审；module-crew 发版后才接入）；用户回复「验收通过，推送并开 PR」。
