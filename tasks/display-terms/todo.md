# Todo: display-terms

- [x] Task 1：防回退断言（先红） — `test_workflow_checkpoints.py` 新增 `test_user_facing_text_uses_the_shared_terms`，扫描插件 `commands`／`skills`／`templates`／`references` 下全部 `.md`、`hooks/` 下非测试的 `.py`／`.sh`、中英 README、`AGENTS.md`、`docs/*.md`（不含子目录）；旧文字上失败，列出 182 处命中，作为待改清单。
- [x] Task 2：hook 输出 — `module_stage.py`（「- 评审:」行改「- 批准:」、批准节奏、批准状态未知、等用户批准、经过审查的决定记录、Plan 没有批准标记）、`map_view.py`（「待批准：」与 `REVIEW_WORDS`）、`verify-artifacts.sh`（批准标记各条、共享检查点规则「批准标记」）、`module-insert.py`（视为已批准、先批准再 --confirm、审查将报告 in-map）、`proposal_promotion_proof.py`（注释）；测试中文断言同步（`test_map_view.py` 5 处、`test-verify-artifacts.sh` 10 处、`test-phase-guard.sh` 2 处，`test-setup-teardown.sh` 与 `test_module_insert.py` 只改说明文字）。英文断言与 map 的 JSON 期望一条未改。map、module-insert、verify-artifacts 75 例、setup 73 例、phase-guard 410 例全绿。
- [x] Checkpoint 1（report）：hook 输出与回归全绿 — 见 Task 2。与 Plan 的差异：提交脚本检查整个工作区，防回退断言在 Task 4 之前一直是红的，所以 Task 1–4 合成一个提交（在全部改完、工作区全绿后提交），CHANGELOG 与版本号另一个提交。
- [x] Task 3：共享规则、references 与约定块 — `workflow-checkpoints.md` 两节标题改为「批准节奏」「批准标记」并同步全部引用，其余按对照表改（能力图审阅、待批准、交审时说明怎么批准、批准指纹、外部 API 审查等）；两份模板、`docs/convention-block.md`、`AGENTS.md` 同步；`test_workflow_checkpoints.py` 按新标题取节、短语同步。除防回退断言外规则测试全绿。
- [x] Task 4：命令、skill、README 与 docs — 按对照表改 commands（含 frontmatter description）、skills、`templates/CAPABILITY-MAP.md`（「审阅记录」「审阅人」）、README、`docs/*.md`；宿主 `/hooks` 界面的「审核并信任」改为「查看并信任」，Codex 提权的「审批」改为「批准」。防回退断言转绿，命中 0；完整 `validate.sh` 通过。
- [ ] Task 5：CHANGELOG 与版本号
- [ ] Checkpoint 2（gate）：最终验收；推送与开 PR 在此由用户确认，合并由用户进行

## 外部审查意见

<!-- spec-guard: external-review declined -->
