# Todo: local-check-dedup

- [x] Task 0：`.gitignore` 忽略 `.agent/state.json`（用户选 A，改仓库而非本机 exclude）
- [x] Task 1：`validate.sh --quick` — `scripts/test_validate_quick.py` 4 例（只跑结构节、能拦结构错误、未知参数退出 2、全量各节仍在），旧脚本上 2 例红；实测 `--quick` 11 秒（逐文件循环占大头）
- [x] Task 2：`verify-and-commit.sh` 分档、并行与记录 — 判断集中在新文件 `scripts/verified_trees.py`；`test_verify_and_commit.py` 15 例（旧脚本上 9 例红）。变异均被抓到：快档放进 `scripts/`、失败也写记录、有未跟踪文件仍写记录
- [x] Task 3：pre-push 按记录跳过 — `test_pre_push_environment.py` 12 例（真实本地推送；旧钩子上 3 条跳过用例红；照常全跑的 6 种情况各自只留一个触发条件）。变异均被抓到：只看最新提交、去掉工作区检查、合并提交接受快档记录；原计划的“去掉父提交检查”在逐个从旧到新判断时不会生效，已删去这段多余代码
- [x] Task 4：本仓库改回分开审与文档 — `.agent/config.json` 去掉 `reviewCadence`；`docs/maintainer-workflow.md`“提交前”、`CLAUDE.md`“最小验证”
- [x] Checkpoint 1（report）：全部回归通过，ShellCheck 无告警；本模块的提交用改进后的脚本
- [ ] Task 5：实测验收（纯文档与脚本改动各走一遍提交 → 推送并计时）
- [ ] Checkpoint 2（gate）：模块评审；Plan 获批即授权推送与开 PR、合并后重装本机钩子，合并由用户进行
- [ ] Task 6：下次发版时补证据
