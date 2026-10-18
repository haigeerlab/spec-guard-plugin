# Todo: map-progress-facts

- [x] Task 1：四项事实与表格的测试（先红） — `test_map_view.py` 新增 `ProgressFactsTest` 7 例（未提交勾选计数与表格那句、提交后表格回到原样、取消勾选为 0、未跟踪 todo、Spec 首次提交时间与 `head.committedAt`、没有提交为 null、`reviewCadence` 三种配置与 `summary()` 一致）；非 git 仓库断言补三项为 null；三处键集合加新字段；`ConcurrencyOff` 的快照比较去掉 `reviewCadence`（配置无效时它的来源本来就该不同，另由新用例断言）。旧代码上 13 例失败，都是缺新字段。
- [x] Task 2：实现 — `map_view.py` 加 `progress_facts()`（一次 `git diff HEAD -U0`、一次 `ls-files --others`、一次 `log --diff-filter=A`）、`_head()` 的 `committedAt`、顶层 `reviewCadence`（取 `project_config.summary()`）、进行中状态格的「N 项勾选未提交（最后一次提交 … 前）」。61 例全绿。两处变异各有断言变红：不把负数记为 0（1 例红）、未跟踪 todo 按 0 计（1 例红）。实现中发现 `_git` 会把 `\x1e` 分隔符当空白 strip 掉，Spec 首次提交改用 `@` 行首标记解析。本仓库实跑：改动前 0.34／0.34 秒，改动后 0.25／0.36 秒；126 个模块里 123 个有 `startedAt`，没有的 3 个是本轮新插、Spec 未提交的模块。
- [x] Checkpoint 1（report）：map 回归全绿 — 随本次提交跑 `verify-and-commit.sh` 全档。
- [x] Task 3：接口说明 — `interface.json` 升到 1.2：`mapView` 下加 `progressFacts`（四项字段的含义与 null 的情形、`reviewCadence` 两个取值、"只给事实，阈值与判断由读取方做"），concurrency 一节去掉"与 1.0 逐字相同"；`map_view.py` 加 `PROGRESS_FIELDS` 常量，`check-interface.py` 加 `_progress_facts()` 核对字段与 `project_config.CADENCES`。`test-checkers.sh` 加 3 例：先只改 `interface.json`、不改检查器时 3 例红（期望拦下、实际放行），改检查器后 136 例全绿。
- [ ] Task 4：文档、实跑、CHANGELOG 与版本号
- [ ] Checkpoint 2（gate）：最终验收；推送与开 PR 在此由用户确认，合并由用户进行

## 外部审查意见

<!-- spec-guard: external-review declined -->
