# Todo: ci-shellcheck-pin

- [x] Task 0：提交 Plan 与 todo（2026-11-24 用户「Plan 批准」）
- [x] Task 1：回归先红后绿，改 ci.yml 与 CHANGELOG
- [ ] Checkpoint 1（report）：本机完整检查与变异
- [ ] Checkpoint 2（gate）：推送、开 PR、AC4／AC5 实测、最终验收、按 F3 合并、重推 #488

## 证据
- Task 1（2026-11-24）：新回归 `test_shellcheck_is_pinned_release` 对旧 `ci.yml` 跑红（2 处：npx 调 shellcheck、没有下载发布包的一步）；改 `ci.yml` 后 `test_ci_workflow` 8 例全绿，`yaml.safe_load` 通过。
