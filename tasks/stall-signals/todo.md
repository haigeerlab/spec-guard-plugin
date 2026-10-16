# Todo: stall-signals

- [x] Task 1：历史解析的测试（先红） — `test_map_view.py` 新增 `HistoryTest` 7 例（临时 git 仓库，固定提交时间）：勾选与挂起时间、改文字与取消勾选不算、未提交的勾选与标记看不到、挂起取最近一次写入、表格距今三种写法（用 `SPEC_GUARD_MAP_NOW` 固定当前时间）、没有提交为 unavailable、浅克隆为 shallow；非 git 仓库断言补 `history` 与提示；键集合加三个新字段。旧代码上 9 例失败。
- [x] Task 2：实现 — `map_view.py` 加 `history()`：一次 `git log -p -U0` 覆盖 `tasks/*/todo.md`，从新到旧取每个模块第一次已勾项变多的提交与第一次碰到挂起标记的提交；表格进行中与挂起两格及关键卡点加距今，表头末行加浅克隆／无历史提示。34 例全绿。两处变异各有断言变红：取消勾选也算勾选（1 例红）、挂起取最早一次写入（2 例红）。本仓库实跑 0.28 秒（94 个模块，含 git log）；13 个模块没有勾选时间，核对为 12 个早期模块没有 todo、本模块尚未勾选。
- [x] Checkpoint 1（report）：历史解析回归全绿 — 随本次提交跑 `verify-and-commit.sh` 全档。
- [x] Task 3：检查点规则与约定块模板 — `references/workflow-checkpoints.md` 的异常停点加“同一个 gate 因外部原因再次挡住”，另起一条写明外部原因的范围、第二次过不去就停、给出挂起（可用 `module-suspend --reason`）／接受风险／换方案及代价由用户决定、不按默认推荐继续重试；两份约定块模板、`docs/convention-block.md`、本仓库 `AGENTS.md` 各加一行指向它。`test_workflow_checkpoints.py` 加一例，先红后绿；`validate.sh --quick` 通过。
- [ ] Task 4：文档、实跑、CHANGELOG 与版本号
- [ ] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行
