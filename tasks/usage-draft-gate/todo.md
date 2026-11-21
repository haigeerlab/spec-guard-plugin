# Todo: usage-draft-gate

- [x] Task 0：提交 Plan 与 todo — 2026-11-22 用户批准 Spec（「批准」）与 Plan（「Plan 批准」）；能力图插入经用户「M1 A；说完了，确认插入」（S102，ecosystem-lead 登记）。
- [x] Task 1：usage_draft.missing 与单测 — `usage_draft.py` 新增 `batches`（一次 `git diff HEAD` 读工作区未提交的新行、一次 `git log -n 100 -p` 读能力图每个提交新加的行；同一行改写不算新增）与 `missing(project, done)`（一批 2 个及以上、未完成模块里有不在任何草案里程碑表的 → missing；不是 git 仓库或 git 出错 → unverified 带原因）。逐个提交 `git show` 的写法在本仓库实测 3.1 秒，改成一次 `log -p` 后 0.15 秒，结果相同。用本仓库真实完成状态跑结果为 ok。`test_usage_draft.py` 新增 `Missing` 6 例（实现前 6 错误），47 例全过。
- [x] Task 2：verify-artifacts 一项 — `usage_draft.py` 加 `missing --project` 子命令（完成状态按阶段提示的 `module_state` 判，延迟导入避免循环），`missing()` 另报 `checked`（有未完成模块的批数）；verify-artifacts 新增「多模块批次」一项：有覆盖 ✅（N 批）、缺草案每批 ⚠️（模块与提交，未提交写「未提交」，附先出草案的建议）、未判定 ⚠️ 带原因、没有这类批次不输出；只警告不判失败。测试夹具改成 git 仓库（`project()` 加 `git init`，`many_modules` 逐个模块提交），否则每个夹具都多一条未判定警告；新增 5 例（改前第一例即失败），105 例通过。本仓库跑出「多模块批次都有用法草案（1 批）」。
- [x] Task 3：阶段提示 — `module_stage.draft_gate()`：只在当前模块 NEEDS_SPEC 时读 git，模块属于缺草案的批时加一行「用法草案」事实、建议下一步换成先写草案（覆盖这批全部模块，已完成里程碑三选一、不自动记确认），节点改为 `map-review` 附「能力图审阅」规则；里程碑停点优先；读不到 git 时不变；批次写进状态码事实。`test-phase-guard.sh` 新增第 27 段 2 例（中英、补上草案后与逐个插入时逐字相同），PARTS=27；第 18 段 zh-CN 夹具原先两模块未提交，现在会被判为一批缺草案，改成分两次提交（规则本意如此，夹具跟着改）；526 例通过。
- [x] Task 4：add-module 提醒 — `module-insert.py` 普通确认写入后调 `_batch_reminder`：工作区未提交的新模块有 2 个及以上、又没有草案覆盖时，结果末尾提醒「写 Spec 前先出用法草案，覆盖这批全部模块，交用户审」；预览与 Proposal 晋级不提醒；读不到 git 时不提醒。`test_module_insert.py` 新增 2 例（连插两个有提醒；有草案或只插一个没有；改前 1 失败），88 例通过。
- [ ] Task 5：规则与说明
- [ ] Checkpoint 1（report）：完整检查、变异验证与实跑
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
