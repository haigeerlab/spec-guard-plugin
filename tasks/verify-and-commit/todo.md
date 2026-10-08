# Todo: verify-and-commit

- [x] Task 1：回归先行（先红）— `scripts/test_verify_and_commit.py` 9 例：全部通过才提交且提交内容等于暂存内容；三套基础检查任一失败不提交并报出套件与日志；失败桩最后一行打印“校验通过 ✅”仍不提交；未暂存改动、无暂存内容拒绝；缺 `--`、未知套件退出 2；按暂存路径加跑 setup-teardown / pre-push / shellcheck；`--suite` 手动加跑且可拦截；npx 不可用判失败。脚本不存在时 9 例全红
- [x] Task 2：脚本实现 — `scripts/verify-and-commit.sh`（`set -euo pipefail`，成败只看退出码，输出进临时日志）；登记进 `validate.sh`；9 例通过。变异均被抓到：失败后仍提交、改成看输出末行判断成败、去掉未暂存检查。实现中又踩到一次变量后接全角字符（`$LOG_DIR）`），已改为 `${LOG_DIR}`
- [x] Task 3：文档 — `docs/maintainer-workflow.md` “提交前”、`CLAUDE.md` “最小验证”
- [x] Checkpoint 1（report）：全部套件通过，ShellCheck 无告警；本模块自己的提交从这里起改用新脚本 — 本次提交即由新脚本完成
- [ ] Checkpoint 2（gate）：模块评审；Plan 获批即授权推送与开 PR，合并由用户进行
- [ ] Task 4：0.55.0 统一发版时补证据
