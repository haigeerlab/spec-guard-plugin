# Todo: runtime-state-layout

- [x] Task 1：`state_paths.py` 与单测（先红） — 先因模块不存在而红；默认根、覆盖、空覆盖、三种回退、不创建目录、`legacy_in_use` 共 7 例转绿。变异：回退条件写反、忽略环境变量，均被抓到。
- [x] Task 2：五个使用方改用 `state_paths`（先红） — 迁移项用例先红后绿；默认值不变的用例在改造前后都绿（守住逐字节不变）。hosted ticket、proposal closeout、local ledger、local ticket 共 13 个既有单测文件通过；3 个需要 `SPEC_GUARD_EPIQ_RUNTIME` 的验收测试照常跳过、未在本模块运行。
- [ ] Task 3：检查器 `check-state-paths.py`（先红）
- [ ] Checkpoint 1（report）：全部单测与检查器回归全绿，ShellCheck 无警告
- [ ] Task 4：`config show` 报告根目录与回退中的旧位置（先红）
- [ ] Task 5：文件布局文档与 CHANGELOG
- [ ] Checkpoint 2（gate）：模块评审；批准 Plan 即授权推送和开 PR，合并由用户进行
