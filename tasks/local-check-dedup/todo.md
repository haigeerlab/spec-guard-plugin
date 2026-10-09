# Todo: local-check-dedup

- [ ] Task 0：本机准备（`.agent/state.json` 加进共用 `.git/info/exclude`，不入库）
- [ ] Task 1：`validate.sh --quick`
- [ ] Task 2：`verify-and-commit.sh` 分档、并行与记录
- [ ] Task 3：pre-push 按记录跳过
- [ ] Task 4：本仓库改回分开审与文档
- [ ] Checkpoint 1（report）：全部回归通过，ShellCheck 无告警；本模块的提交用改进后的脚本
- [ ] Task 5：实测验收（纯文档与脚本改动各走一遍提交 → 推送并计时）
- [ ] Checkpoint 2（gate）：模块评审；Plan 获批即授权推送与开 PR、合并后重装本机钩子，合并由用户进行
- [ ] Task 6：下次发版时补证据
