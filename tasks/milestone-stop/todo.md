# Todo: milestone-stop

- [x] Task 0：提交已批准的 Spec 与 Plan、todo — 2026-11-19 用户批准 Spec（「批准，加字段」，假设 7 定为加 `milestoneStop`）与 Plan（「Plan 批准」）。
- [x] Task 1：`usage_draft.py` 确认记录与停点判定，单元测试 — `parse` 读 Milestones 一节里的 `<!-- spec-guard: milestone M<n> confirmed … -->`（格式坏、同一里程碑两条判失败），新增 `confirmed()` 与 `stop(project, done, mapped)`（第一个全部完成且无有效确认的里程碑；草案读不了或模块不在能力图上返回 unverified 并给原因）；verify 对指向不存在里程碑的记录判失败、模块不一致只提醒；Build order 顺序只用本里程碑实际归属的模块，重复归属只报一条。新增 15 例，实现前 5 失败 9 报错，实现后 41 例通过。挂起与延期按完成与否由调用方给 `done`，在 Task 3 的阶段提示用例里覆盖。
- [ ] Task 2：`milestone_mark.py`、命令文档与 Codex 入口
- [ ] Task 3：阶段提示接停点，`node-rules.md` 加「里程碑停点」
- [ ] Task 4：`/map --json` 的 `milestoneStop`，interface 1.13
- [ ] Task 5：共享检查点规则补「里程碑停点」
- [ ] Task 6：文档与 README 功能段
- [ ] Task 7：版本号 0.88.0 与 CHANGELOG
- [ ] Checkpoint 1（report）：发布前完整检查、变异验证与临时项目实跑 U3
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
- [ ] 发版（合并后按 Checkpoint 2 授权）：核对合并、打 tag、发 Release、刷新并核对两个宿主、证据收尾 PR、回告 ecosystem-lead
- [ ] M2 停点（gate）：用安装副本在临时项目跑 U1–U3；经用户确认后用 milestone-mark 在本仓库草案补记 M1、记下 M2
