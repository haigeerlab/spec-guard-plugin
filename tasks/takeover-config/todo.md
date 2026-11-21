# Todo: takeover-config

- [x] Task 0：提交 Plan 与 todo — 2026-11-21 用户批准 Spec（「批准；Q2 A」）与 Plan（「Plan 批准」）；能力图插入经用户「确认插入；Q1 B」。
- [x] Task 1：配置核心 — `project_config.py` 新增 `ITEMS`、`PRESETS`（none／plan／merge，merge 含 Spec＝codex，Q2 A）、`valid_takeover`／`expand`／`takeover_wider`、`module_takeover(s)`，`VALIDATORS` 加 `takeover`、`moduleTakeover`（逐条校验，任一条非法整键失效），`--value` 以 `{` 开头按 JSON 解析；预览打印四项、模块宽于项目时 note、发布为 auto-confirm／auto 时两行限制提示。`test_project_config.py` 新增 `Takeover` 10 例，实现前 7 失败 3 错误，实现后 61 例全过。
- [x] Task 2：autonomyTier、moduleAutonomy 退役 — 两个键移到 `RETIRED`：文件里有时 `load` 报 `retired-key`（同 `unknown-key` 不判失败，`check` 退出 0），`show` 逐个标「retired, not in effect」并指向 takeover，`summary` 不再列出；`set` 退出 2，`unset` 可用，其他写入原样保留它们；`module_tier(s)` 改读旧键（`_legacy`），`/map` 的 autonomy 字段输出不变。为保持阶段提示逐字不变，`module_stage.config_lines` 不为 `retired-key` 加行（Plan 写的是不改 module_stage，这里多了 3 行，最终验收列出）。verify-artifacts 的配置检查与能力图外 id 警告一并改到 moduleTakeover、已退役键只警告（原 Task 4 的这部分提前做，否则完整检查不过）；`test-verify-artifacts.sh` 100 例通过；`test_project_config.py` 旧档位用例换成 `RetiredAutonomy` 6 例，实现前 5 失败，实现后 53 例全过，`test_map_view.py` 不改也通过。
- [ ] Task 3：/map --json 的 takeover 字段与 interface 1.15
- [ ] Task 4：verify-artifacts 与阶段提示回归
- [ ] Task 5：说明文字
- [ ] Checkpoint 1（report）：完整检查、变异验证与临时项目实跑
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
