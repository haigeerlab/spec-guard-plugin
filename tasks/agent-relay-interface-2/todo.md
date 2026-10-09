# Todo: agent-relay-interface-2

- [x] Task 1：放宽接口范围（回归先行、两项变异、系统 Python 3.9）— `test_agent_relay_probe.py`：范围外取值改为 `0.9、3.0、3.1`，新增 `2.0`、`2.4` 判 `ready`，两处范围断言改为 `>=1.0,<3.0`，改代码前红；`agent_relay_probe.py` 的 `REQUIRED`、`MAX_VERSION` 与文件头说明改为新范围；22 例在 python3 与系统 Python 3.9.6 下通过；变异：上限改回 `(2, 0)` → 2.0、2.4 两例红，上限改为 `(4, 0)` → 3.0、3.1 两例红，均已还原。
- [x] Task 2：文档（协作接口说明、迁移说明）— `docs/collaboration-interface.md` 探针输出里的范围；迁移说明写明 0.56.0 起为 `>=1.0,<3.0`（此前 `>=1.0,<2.0`），"接口 1.x 内"改为"接口 1.x、2.x 内"。
- [x] Task 3：0.56.0 发版改动（版本号、README `--ref`、CHANGELOG、拣入 a54ecdc、勾掉已合并的检查点）与发布前校验：
  - 两份清单 0.56.0，中英 README `--ref v0.56.0`（`check-readme-sync.py` 通过）；CHANGELOG `[0.56.0]`：修复 2 条、兼容 1 条、维护者工具 3 条；
  - 拣入 `a54ecdc`（本分支 `e5c630a`）；勾掉 validate-parallel-files、verify-and-commit-untracked-warning、phase-guard-test-parallel、codex-command-wording 的 Checkpoint 1（#282–#285 的合并提交），以及前两者写 CHANGELOG 的 Task 4；phase-guard-test-parallel Task 5 与 codex-command-wording Task 6 要在安装副本上核验，留到证据 PR；
  - 发布前校验（macOS Darwin 24.6.0，`/bin/bash` 3.2.57）：`evals/codex-plugin-smoke.sh --selftest` 通过；全档提交 955b178 在同一台机器的 `/bin/bash` 下跑完整 validate（82s）、phase-guard 回归（18s，208 例）、verify-artifacts 回归（13s）与本仓库 verify-artifacts，全部通过。
- [ ] Checkpoint 1（gate）：模块与发版评审；全部回归通过、ShellCheck 无告警，Plan 获批即授权推送并开 PR，合并由用户进行
- [ ] Task 4：发版后（tag、Release、两边安装副本核验、证据收尾 PR）
