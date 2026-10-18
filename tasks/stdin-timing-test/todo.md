# Todo: stdin-timing-test

- [x] Task 0：提交已批准的 Plan 与 todo — Plan 经用户批准（2026-10-18），与本 todo 一次提交（252efe5）。
- [x] Task 1：改写这条用例并做反向验证 — 第 9 段那条改为先以 `stdin=DEVNULL` 量 base，再以不关闭的 `stdin=PIPE` 跑并用 15 秒 `threading.Timer` 兜底，断言 `open - base < 2`；当前代码上通过，phase-guard 回归 404 例不变。反向验证（`git archive HEAD` 出的草稿副本，覆盖新测试文件，跑完即删）：`INPUT_WAIT = 4` 时失败，信息为 `extra wait 3.85 s (open 5.44 s, base 1.59 s)`；`select` 不设超时时 15 秒后失败，信息为 `hook hung with stdin left open (killed after 15 s)`；两次整套都在 46 秒内结束，没有卡死。
- [x] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无告警 — 随 Task 1 的提交跑 `verify-and-commit.sh` 全档：phase-guard 404 例、verify-artifacts 68 例、repo-artifacts 5 通过、ShellCheck 无告警。
- [x] Task 2：CHANGELOG — 顶部新增 `## [未发布]` 一节，记一条维护者工具（插件包里只有测试脚本变化）；版本号不变；`validate.sh` 随提交跑过。
- [x] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行 — 2026-10-18 在对话里列出相对 811341d 的 6 个文件（均在 Plan 范围内）、用例差异、反向验证结果与未验证项（CI 上的结果、未做独立代码评审），拟回告为无；完整 `validate.sh` 通过；用户验收通过，确认推送与开 PR。
- [ ] 合并后的 CI 核对
