# Todo: plugin-spec-compliance

- [x] Task 0：提交 Plan 与 todo（2026-11-24 用户「Plan 批准」）
- [x] Task 1：Python 3.9 兼容
- [x] Task 2：check-frontmatter.py 与回归
- [x] Task 3：清单过 --strict
- [x] Task 4：workflow、dependabot、LICENSE，test_ci_workflow.py
- [x] Task 5：CONTRIBUTING、维护文档、CHANGELOG
- [x] Checkpoint 1（report）：本机完整检查与变异
- [ ] Checkpoint 2（gate）：推送、开 PR、CI 实测与 AC2 变异
- [ ] Checkpoint 3（gate）：最终验收；合并由用户进行，合并后经用户原话切主干保护

## 证据

- Checkpoint 1（2026-11-24，提交 1c69405 上，macOS `/bin/bash`）：`validate.sh` 默认 Python 3.10.7 与 `/usr/bin/python3` 3.9.6 各一次，都退出 0「校验通过 ✅」；
  `test-phase-guard.sh`「passed (541 cases)」；`test-verify-artifacts.sh`「passed (120 cases)」；`claude plugin validate --strict`（CLI 2.1.328）插件目录与 marketplace 都退出 0；
  ShellCheck（npm 4.1.0）退出 0；`check-frontmatter.py` 本仓库 31 个文件通过。
- 汇总任务判定（本机用 PyYAML 取出 `CI required` 的脚本，喂四组 needs）：全 success → 0；有 failure → 1；有 cancelled／skipped → 1；空 → 1。
- 变异（各自还原）：`check-frontmatter.py` 不查 `name` → `test_check_frontmatter` 2 例失败（skill、agent 缺 name）；`ci.yml` 删掉 `if: always()` → `test_ci_workflow.test_summary_job_needs_every_other_job` 失败。
- Python 3.9：全仓库 AST 扫描只有 `scripts/check-local-paths.py` 一处 `X | None` 注解，Task 1 已改。

