# Todo: autonomy-tier

- [x] Task 0：提交已批准的 Spec 与 Plan 草稿 — 2026-10-26 用户批准 Plan（「批准 autonomy-tier 的 Plan」）；Spec 与 Plan 草稿在 `269be3ba` 提交，Plan 批准标记随本次提交。
- [x] Task 1：配置项 `autonomyTier`（C1，先红后绿） — `test_project_config.py` 新增 `AutonomyTier` 4 例（三档 set／读回／来源／unset、未设置为 strict／default、`fast` 写不进且文件里的坏值只让这个键回默认并 `check` 失败、`config_lines` 设与不设三档相同）；改前 4 例红（未知键）。`project_config.py` 加 `TIERS`、校验器与默认值；原「汇总列出全部配置项」用例加上新键。配置与阶段注入相关 59 例全绿；变异（TIERS 删掉 relaxed）→ 2 例红。
- [ ] Task 2：接口条目（C3，先红后绿）
- [ ] Task 3：底线规则与说明（C2、C4）
- [ ] Checkpoint 1（report）：三套核心回归
- [ ] Task 4：版本号 0.85.0 与 CHANGELOG
- [ ] Checkpoint 2（gate）：最终验收；通过后同步 main、推送并开本模块 PR，合并由用户进行
