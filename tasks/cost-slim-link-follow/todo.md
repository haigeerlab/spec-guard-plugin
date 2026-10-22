# Todo: cost-slim-link-follow

- [x] Task 0：提交已批准的 Spec 标记、Plan 与 todo — Spec（C84，修订后标记 61b845f）与 Plan（C87／C97）由模块协调带批准标记提交到集成分支 30d5510；按开工通知 `module-crew sync`（HEAD 82d51fe，已含该提交）；validate、phase-guard（438 例）、verify-artifacts（74 例）全过。
- [x] Task 1：成本报告瘦身（C1） — 测试先改：返工信号四个用例与 Codex apply_patch 用例换成「报错调用不计入 `subagents`（正文含收回原因或其他文字都一样）」「成功调用的正文含收回文字也照常计入」「task 与 Codex task 不再有 `dispatches`／`redispatches`／`reclaims`／`edits_after_handback`」，多模块对照用例改为断言 JSON 无 `comparison`，表格断言含「子代理记录」、不含派活／重派／收回／交回后改／对照／返工，无法统计的部分提到 `spec-guard-link.json`；在原代码上 7 失败 27 错误。实现：删 `EDIT_TOOLS`、`HOOK_DENIAL`、`RECLAIM_MARK`、`PATCH_FILE`、`_text` 与 `comparison()`，`_claude_events` 只取错误标记与提问时间，Codex 不再收集补丁路径；表格列与金额列对齐。默认 python3 与 `/usr/bin/python3` 3.9.6 各跑 138 例全过；全仓旧字段只剩 `evals/dispatch-cost/results/` 历史结果与报告。
- [ ] Task 2：派活规则退役（C2）
- [ ] Task 3：跟随解析（C3）
- [ ] Checkpoint 1（report）：变异核对
- [ ] Task 4：Claude 命令入口（C4，不含 `config.md`、`review-mark.md`）
- [ ] Task 5：等 `sibling-rules-out` 合入后同步
- [ ] Task 6：重叠文件与 Codex 入口（C4 `config.md`、`review-mark.md`、C5）
- [ ] Task 7：阶段注入措辞（C6）
- [ ] Task 8：文档（C7）
- [ ] Task 9：公共文件实查（C8）
- [ ] Task 10：端到端跟随核对
- [ ] Task 11：合入集成分支并跑完整检查
- [ ] Checkpoint 2（gate）：模块最终验收；不含推送与开 PR，合并由模块协调按用户原话做

## 拟写的更新说明（由模块协调整批写入 CHANGELOG）

> **变更**：`cost-report` 只看 token 与主会话轮次：去掉派活、重派、收回、交回后改与「派过／没派过」对照（决定 D17）；`--json` 删
> `dispatches`、`redispatches`、`reclaims`、`edits_after_handback`，`dispatches_unrecorded` 改名 `subagents_unrecorded`，新增 `subagents`。
> 派活规则退役：`setup-convention --dispatch`／`--no-dispatch` 被拒，`--replace` 会移除旧块里的派活规则段。
> 有项目指向时，除 `link-project` 外的所有命令自动跟随到被指向的项目，并输出「本次操作的是被指向的项目 `<路径>`」；指向失效时命令停下并说明（决定 D18）。
