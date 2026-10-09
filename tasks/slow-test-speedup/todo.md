# Todo: slow-test-speedup

- [x] Task 1：改前基线（负载、三个测试计时与用例数、validate 整体计时）— 2026-10-09 本机 8 核，负载 18.7→21.7；`/usr/bin/time -p` 计墙钟与 CPU（user+sys）：
  - `test_module_cost_report`：149 例，墙钟 56.4s，CPU 39.3s（18.3+21.0）
  - `test_proposal_promotion_proof`：59 例，墙钟 35.5s，CPU 28.3s（11.8+16.5）
  - `test_local_ticket_portability`：52 例，墙钟 25.3s，CPU 21.3s（10.2+11.1）
  - 三个合计：墙钟 117.2s，CPU 88.9s；`validate.sh` 整体墙钟 315.5s，CPU 220.7s
- [x] Task 2：并行运行器 `scripts/run_tests_parallel.py` 与其回归 — `scripts/test_run_tests_parallel.py` 6 例（全过、类失败、类报错、少跑一个、`--jobs`、零用例），运行器不存在时 4 例红；变异（去掉总数核对、忽略失败进程）均变红；系统 Python 3.9.6 通过；登记进 `validate.sh`
- [x] Task 3：`test_module_cost_report` 夹具瘦身与变异证明 — 提交者身份改用环境变量（每个仓库少 2 次 `git config`，共约 300 次）；`add`+`commit` 未合并（新文件必须先 `add`）；用例仍 149。变异：切窗口改用提交者时间（`%cI`）→ `ReviewFixTests` 变红，已还原
- [x] Task 4：`test_local_ticket_portability` 夹具瘦身与变异证明 — `setUpClass` 建一次仓库加 state worktree，每个用例复制后 `git worktree repair`（每例 8 次 git 调用变 1 次）；用例仍 52。变异：`eventFileCount` 少算一个 → `SourceInventoryTests` 变红，已还原
- [x] Task 5：`test_proposal_promotion_proof` 夹具瘦身与变异证明 — 夹具已是共享模板（git-fixture-template 模块），时间主要在被测代码读远端快照，夹具不再改，只靠并行；用例仍 59。变异：去掉“晋级提交改了别的行”的检查 → `OtherRowPromotionTests` 变红，已还原
- [x] Task 6：接入 validate，3.9 验证，改后实测并对照 40 秒目标 — `validate.sh` 用 `scripts/run_tests_parallel.py` 跑这三个测试；运行器增加“一个类太大就按方法拆”（`test_local_ticket_portability` 只有一个类），对应用例在旧运行器上为红。系统 Python 3.9.6 直接跑三个文件都通过。改后实测（负载 20.7→25.3）：
  - `test_module_cost_report`：墙钟 16.3s（改前 56.4），CPU 45.1s（改前 39.3）
  - `test_proposal_promotion_proof`：墙钟 16.6s（改前 35.5），CPU 35.4s（改前 28.3）
  - `test_local_ticket_portability`：墙钟 23.9s（改前 25.3），CPU 26.8s（改前 21.3）；同日稍早单独测得 8.7s，这一次明显受排队影响
  - 三个合计墙钟 56.8s（改前 117.2），CPU 107.3s（改前 88.9）；`validate.sh` 整体墙钟 254.5s（改前 315.5），CPU 241.9s（改前 220.7）
  - **未达到“合计 40 秒以内”**：本机负载 20 以上时墙钟波动大（同一测试 8.7s 与 23.9s）；分开测时合计约 35s。并行用多核换墙钟，CPU 合计反而增加约 18s（多进程的导入与类级准备重复）。是否接受由用户决定
- [x] Checkpoint 1（gate）：模块评审；全部回归通过、ShellCheck 无告警，Plan 获批即授权推送与开 PR，合并由用户进行
- [ ] Task 7：下次发版时补证据
