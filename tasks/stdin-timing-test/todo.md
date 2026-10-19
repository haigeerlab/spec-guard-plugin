# Todo: stdin-timing-test

- [x] Task 0：提交已批准的 Plan 与 todo — Plan 经用户批准（2026-10-18），与本 todo 一次提交（252efe5）。
- [x] Task 1：改写这条用例并做反向验证 — 第 9 段那条改为先以 `stdin=DEVNULL` 量 base，再以不关闭的 `stdin=PIPE` 跑并用 15 秒 `threading.Timer` 兜底，断言 `open - base < 2`；当前代码上通过，phase-guard 回归 404 例不变。反向验证（`git archive HEAD` 出的草稿副本，覆盖新测试文件，跑完即删）：`INPUT_WAIT = 4` 时失败，信息为 `extra wait 3.85 s (open 5.44 s, base 1.59 s)`；`select` 不设超时时 15 秒后失败，信息为 `hook hung with stdin left open (killed after 15 s)`；两次整套都在 46 秒内结束，没有卡死。
- [x] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无告警 — 随 Task 1 的提交跑 `verify-and-commit.sh` 全档：phase-guard 404 例、verify-artifacts 68 例、repo-artifacts 5 通过、ShellCheck 无告警。
- [x] Task 2：CHANGELOG — 顶部新增 `## [未发布]` 一节，记一条维护者工具（插件包里只有测试脚本变化）；版本号不变；`validate.sh` 随提交跑过。
- [x] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行 — 2026-10-18 在对话里列出相对 811341d 的 6 个文件（均在 Plan 范围内）、用例差异、反向验证结果与未验证项（CI 上的结果、未做独立代码评审），拟回告为无；完整 `validate.sh` 通过；用户验收通过，确认推送与开 PR。
- [x] 合并后的 CI 核对 — 2026-10-18，#359 合并为 66e845f，main 等于合并提交；main CI 39113737682 第一次运行即通过（success，attempt 1），日志里这条用例为「✅ 标准输入不关闭时只多等约 1 秒并照常输出」，phase-guard 404 例通过。用例通过时不打印耗时，所以 CI 上的具体耗时没有记录。不单独发版。
- [x] Task 3：改写判法并在高负载下验证（返工，见 plan.md 末节） — 用例改为 `measure()` 每轮量 base 与 open，超限时最多 3 轮，按最小 open − 最小 base 判断，阈值仍为 2 秒；挂住在第一轮即判失败。当前代码上空载通过；高负载（8 核；10 个 `yes` 忙循环 + `npx shellcheck@4.1.0` 循环 + `validate.sh` 循环）下单独连跑 30 次，0 次失败（更正：第一次连跑时直接调用的 `shellcheck` 本机没装、每次立即退出，那组负载里没有真实 ShellCheck，按 npx 重跑后才记这个结果）。全档 3 次：提交 51ab4c8 时的 `verify-and-commit.sh` 一次，之后同样四套（含 npx ShellCheck）并行再跑两次，都通过，phase-guard 413 例。反向验证（`git archive HEAD` 出的草稿副本，覆盖新测试文件，跑完即删）：`INPUT_WAIT = 4` 空载 `extra wait 4.11 s after 3 rounds`、高负载 `4.01 s`、整套 36 秒结束且只有这条红；`select` 不设超时时空载与高负载都在 15 秒后以 `hook hung with stdin left open (killed after 15 s)` 失败，整套 49 秒结束且只有这条红，没有卡死。CHANGELOG 顶部新增 `## [未发布]`，记一条维护者工具；版本号不变。
- [ ] Checkpoint 3（gate）：返工验收；推送与开 PR 在此由用户确认，合并由用户进行
