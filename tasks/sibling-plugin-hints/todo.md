# Todo: sibling-plugin-hints

- [x] Task 0：提交已批准的产物 — 能力图新行、已批准的 Spec、Plan 与本 todo 一次提交。
- [ ] Task 1：约定块模板两行（先红） — 规则测试新增 1 例先红；两份模板与约定块文档各新增两行转绿；变异变红后复原；0.64.0→工作区 `--replace` 两边退出 0、不需 `--accept-removals`。
- [ ] Checkpoint 1（report）：三套核心回归、规则测试与 setup-teardown 回归全绿
- [ ] Task 2：CHANGELOG 与版本号 — CHANGELOG `[0.64.1]`；两份 `plugin.json` 与 README 中英 `--ref` 改为 0.64.1。
- [ ] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
- [ ] 发版后的验证 — 两边升级到 0.64.1，各跑一轮到 Spec 交审，看是否只提议一次 delegate 只读审查、未自行发起。
