# Todo: module-autonomy

- [x] Task 0：提交已批准的 Spec 与 Plan、todo — 2026-11-19 用户批准 Spec（「批准」）与 Plan（「Plan 批准」）；能力图插入经用户「确认插入」。
- [x] Task 1：`project_config.py` 校验、`module_tier` 与 `--module` 写入，单元测试 — `VALIDATORS` 加 `moduleAutonomy`（对象，id 合 `MODULE_ID`、值在 `TIERS`，任一条目坏整个键失效），`DEFAULTS` 为 `{}`；新增 `module_tier()`（条目优先，否则随 `autonomyTier`；`moduleAutonomy` 不合法时来源为 `default (config invalid)`）与 `wider()`；`set`／`unset` 加 `--module`（只对 `moduleAutonomy`，写它必须带；最后一个条目去掉时整个键删除；宽于项目档位时预览多一行 note）。`test_project_config.py` 新增 10 例并把汇总项清单加上新键，实现前 8 失败 2 报错，实现后 51 例通过。
- [ ] Task 2：`/map --json` 每个模块的 `autonomy`
- [ ] Task 3：阶段提示逐字不变的回归与 verify-artifacts 未知 id 警告
- [ ] Task 4：接口 1.14 与检查器
- [ ] Task 5：说明文字（config、ops 技能、commands、concepts）
- [ ] Task 6：版本号 0.89.0 与 CHANGELOG
- [ ] Checkpoint 1（report）：发布前完整检查、变异验证与临时项目实跑
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
- [ ] 发版（合并后按 Checkpoint 2 授权）：打 tag、发 Release、刷新两个宿主、证据收尾 PR，回告 autopr-design 与 ecosystem-lead
