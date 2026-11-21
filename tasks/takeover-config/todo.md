# Todo: takeover-config

- [x] Task 0：提交 Plan 与 todo — 2026-11-21 用户批准 Spec（「批准；Q2 A」）与 Plan（「Plan 批准」）；能力图插入经用户「确认插入；Q1 B」。
- [x] Task 1：配置核心 — `project_config.py` 新增 `ITEMS`、`PRESETS`（none／plan／merge，merge 含 Spec＝codex，Q2 A）、`valid_takeover`／`expand`／`takeover_wider`、`module_takeover(s)`，`VALIDATORS` 加 `takeover`、`moduleTakeover`（逐条校验，任一条非法整键失效），`--value` 以 `{` 开头按 JSON 解析；预览打印四项、模块宽于项目时 note、发布为 auto-confirm／auto 时两行限制提示。`test_project_config.py` 新增 `Takeover` 10 例，实现前 7 失败 3 错误，实现后 61 例全过。
- [ ] Task 2：autonomyTier、moduleAutonomy 退役
- [ ] Task 3：/map --json 的 takeover 字段与 interface 1.15
- [ ] Task 4：verify-artifacts 与阶段提示回归
- [ ] Task 5：说明文字
- [ ] Checkpoint 1（report）：完整检查、变异验证与临时项目实跑
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
