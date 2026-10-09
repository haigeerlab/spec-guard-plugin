# Todo: slow-test-speedup

- [x] Task 1：改前基线（负载、三个测试计时与用例数、validate 整体计时）— 2026-10-09 本机 8 核，负载 18.7→21.7；`/usr/bin/time -p` 计墙钟与 CPU（user+sys）：
  - `test_module_cost_report`：149 例，墙钟 56.4s，CPU 39.3s（18.3+21.0）
  - `test_proposal_promotion_proof`：59 例，墙钟 35.5s，CPU 28.3s（11.8+16.5）
  - `test_local_ticket_portability`：52 例，墙钟 25.3s，CPU 21.3s（10.2+11.1）
  - 三个合计：墙钟 117.2s，CPU 88.9s；`validate.sh` 整体墙钟 315.5s，CPU 220.7s
- [x] Task 2：并行运行器 `scripts/run_tests_parallel.py` 与其回归 — `scripts/test_run_tests_parallel.py` 6 例（全过、类失败、类报错、少跑一个、`--jobs`、零用例），运行器不存在时 4 例红；变异（去掉总数核对、忽略失败进程）均变红；系统 Python 3.9.6 通过；登记进 `validate.sh`
- [ ] Task 3：`test_module_cost_report` 夹具瘦身与变异证明
- [ ] Task 4：`test_local_ticket_portability` 夹具瘦身与变异证明
- [ ] Task 5：`test_proposal_promotion_proof` 夹具瘦身与变异证明
- [ ] Task 6：接入 validate，3.9 验证，改后实测并对照 40 秒目标
- [ ] Checkpoint 1（gate）：模块评审；全部回归通过、ShellCheck 无告警，Plan 获批即授权推送与开 PR，合并由用户进行
- [ ] Task 7：下次发版时补证据
