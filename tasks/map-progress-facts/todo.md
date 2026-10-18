# Todo: map-progress-facts

- [x] Task 1：四项事实与表格的测试（先红） — `test_map_view.py` 新增 `ProgressFactsTest` 7 例（未提交勾选计数与表格那句、提交后表格回到原样、取消勾选为 0、未跟踪 todo、Spec 首次提交时间与 `head.committedAt`、没有提交为 null、`reviewCadence` 三种配置与 `summary()` 一致）；非 git 仓库断言补三项为 null；三处键集合加新字段；`ConcurrencyOff` 的快照比较去掉 `reviewCadence`（配置无效时它的来源本来就该不同，另由新用例断言）。旧代码上 13 例失败，都是缺新字段。
- [x] Task 2：实现 — `map_view.py` 加 `progress_facts()`（一次 `git diff HEAD -U0`、一次 `ls-files --others`、一次 `log --diff-filter=A`）、`_head()` 的 `committedAt`、顶层 `reviewCadence`（取 `project_config.summary()`）、进行中状态格的「N 项勾选未提交（最后一次提交 … 前）」。61 例全绿。两处变异各有断言变红：不把负数记为 0（1 例红）、未跟踪 todo 按 0 计（1 例红）。实现中发现 `_git` 会把 `\x1e` 分隔符当空白 strip 掉，Spec 首次提交改用 `@` 行首标记解析。本仓库实跑：改动前 0.34／0.34 秒，改动后 0.25／0.36 秒；126 个模块里 123 个有 `startedAt`，没有的 3 个是本轮新插、Spec 未提交的模块。
- [x] Checkpoint 1（report）：map 回归全绿 — 随本次提交跑 `verify-and-commit.sh` 全档。
- [x] Task 3：接口说明 — `interface.json` 升到 1.2：`mapView` 下加 `progressFacts`（四项字段的含义与 null 的情形、`reviewCadence` 两个取值、"只给事实，阈值与判断由读取方做"），concurrency 一节去掉"与 1.0 逐字相同"；`map_view.py` 加 `PROGRESS_FIELDS` 常量，`check-interface.py` 加 `_progress_facts()` 核对字段与 `project_config.CADENCES`。`test-checkers.sh` 加 3 例：先只改 `interface.json`、不改检查器时 3 例红（期望拦下、实际放行），改检查器后 136 例全绿。
- [x] Task 4：文档、实跑、CHANGELOG 与版本号 — `commands/map.md`、`spec-guard-ops` 的 map 一节、`docs/commands.md`、`docs/design.md` 写明新字段；CHANGELOG 新增 `[0.73.0] - 2026-10-19`；两份 `plugin.json` 改为 0.73.0，中英 README 的 `--ref` 改为 v0.73.0。实跑：临时 git 仓库（`mktemp -d` 固定前缀，用后按前缀删除）按 2026-10-16 提交 1/4，工作区再勾 2 项，`SPEC_GUARD_MAP_NOW=2026-10-19T09:00:00+08:00 map_view.py` 表格为「🔨 进行中 3/4，上次勾选 3 天前，2 项勾选未提交（最后一次提交 3 天前）」，JSON 的 `uncommittedTicks` 为 2、`startedAt` 与 `head.committedAt` 为 2026-10-16T09:00:00+08:00、`reviewCadence` 为 separate／default。本仓库实跑见 Task 2。
- [x] Checkpoint 2（gate）：最终验收；推送与开 PR 在此由用户确认，合并由用户进行 — 2026-10-19 在对话里按 AC1–AC6 逐条给出证据（测试名与结果、临时仓库实跑输出、本仓库耗时）、三处变异变红、与 Plan 的三处差异（`ConcurrencyOff` 快照去掉 `reviewCadence`、`@` 行首标记、`PROGRESS_FIELDS` 常量）、未验证项（安装版真实会话待发版后；未在那个前端项目实跑；未做独立代码审查）、实际改动的文件清单（取自版本库：18 个文件，新增 3、修改 15、删除 0，无超出 Plan 预计的文件）与文档建议（无）。用户批准：勾上 gate、推送、开 PR，并通知 module-crew 与 decision-inbox 核对字段。

## 外部审查意见

<!-- spec-guard: external-review declined -->
