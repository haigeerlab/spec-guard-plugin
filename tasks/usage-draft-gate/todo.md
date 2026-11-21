# Todo: usage-draft-gate

- [x] Task 0：提交 Plan 与 todo — 2026-11-22 用户批准 Spec（「批准」）与 Plan（「Plan 批准」）；能力图插入经用户「M1 A；说完了，确认插入」（S102，ecosystem-lead 登记）。
- [x] Task 1：usage_draft.missing 与单测 — `usage_draft.py` 新增 `batches`（一次 `git diff HEAD` 读工作区未提交的新行、一次 `git log -n 100 -p` 读能力图每个提交新加的行；同一行改写不算新增）与 `missing(project, done)`（一批 2 个及以上、未完成模块里有不在任何草案里程碑表的 → missing；不是 git 仓库或 git 出错 → unverified 带原因）。逐个提交 `git show` 的写法在本仓库实测 3.1 秒，改成一次 `log -p` 后 0.15 秒，结果相同。用本仓库真实完成状态跑结果为 ok。`test_usage_draft.py` 新增 `Missing` 6 例（实现前 6 错误），47 例全过。
- [x] Task 2：verify-artifacts 一项 — `usage_draft.py` 加 `missing --project` 子命令（完成状态按阶段提示的 `module_state` 判，延迟导入避免循环），`missing()` 另报 `checked`（有未完成模块的批数）；verify-artifacts 新增「多模块批次」一项：有覆盖 ✅（N 批）、缺草案每批 ⚠️（模块与提交，未提交写「未提交」，附先出草案的建议）、未判定 ⚠️ 带原因、没有这类批次不输出；只警告不判失败。测试夹具改成 git 仓库（`project()` 加 `git init`，`many_modules` 逐个模块提交），否则每个夹具都多一条未判定警告；新增 5 例（改前第一例即失败），105 例通过。本仓库跑出「多模块批次都有用法草案（1 批）」。
- [ ] Task 3：阶段提示
- [ ] Task 4：add-module 提醒
- [ ] Task 5：规则与说明
- [ ] Checkpoint 1（report）：完整检查、变异验证与实跑
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
