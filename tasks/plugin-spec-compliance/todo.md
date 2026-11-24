# Todo: plugin-spec-compliance

- [x] Task 0：提交 Plan 与 todo（2026-11-24 用户「Plan 批准」）
- [x] Task 1：Python 3.9 兼容
- [x] Task 2：check-frontmatter.py 与回归
- [x] Task 3：清单过 --strict
- [x] Task 4：workflow、dependabot、LICENSE，test_ci_workflow.py
- [x] Task 5：CONTRIBUTING、维护文档、CHANGELOG
- [x] Checkpoint 1（report）：本机完整检查与变异
- [x] Checkpoint 2（gate）：推送、开 PR、CI 实测与 AC2 变异
- [x] Checkpoint 3（gate）：最终验收；合并由用户进行，合并后经用户原话切主干保护

## 证据

- Checkpoint 1（2026-11-24，提交 1c69405 上，macOS `/bin/bash`）：`validate.sh` 默认 Python 3.10.7 与 `/usr/bin/python3` 3.9.6 各一次，都退出 0「校验通过 ✅」；
  `test-phase-guard.sh`「passed (541 cases)」；`test-verify-artifacts.sh`「passed (120 cases)」；`claude plugin validate --strict`（CLI 2.1.328）插件目录与 marketplace 都退出 0；
  ShellCheck（npm 4.1.0）退出 0；`check-frontmatter.py` 本仓库 31 个文件通过。
- 汇总任务判定（本机用 PyYAML 取出 `CI required` 的脚本，喂四组 needs）：全 success → 0；有 failure → 1；有 cancelled／skipped → 1；空 → 1。
- 变异（各自还原）：`check-frontmatter.py` 不查 `name` → `test_check_frontmatter` 2 例失败（skill、agent 缺 name）；`ci.yml` 删掉 `if: always()` → `test_ci_workflow.test_summary_job_needs_every_other_job` 失败。
- Python 3.9：全仓库 AST 扫描只有 `scripts/check-local-paths.py` 一处 `X | None` 注解，Task 1 已改。

- Checkpoint 2（2026-11-24，PR #487，base main）：
  - 第一轮（b7cd0c6）：`validate`、`plugin` 通过（CI 上 npx 拉 CLI 2.1.328 跑 `--strict` 两处都通过）；`python (3.9)` 失败——`ubuntu-latest` 已是 26.04，
    actions/python-versions 的 3.9.25 只有 22.04、24.04 的包；`CI required` 随之失败（needs 里 python: failure）。
  - 修复 e19cac6：`python` 任务钉 `ubuntu-24.04`，`test_ci_workflow` 断言它只能是 22.04／24.04（改回 `ubuntu-latest` 时变红）。第二轮五项全绿。
  - AC2 临时提交 bc7531f（删 `commands/phase.md` 的 description，`--no-verify` 只用于这一个故意坏的提交）：`plugin` 失败「No description in frontmatter」
    「Validation failed (--strict treats warnings as errors)」；`validate` 失败于 `test_check_frontmatter.py`（runner 自带 PyYAML）；`CI required` 失败。
    同轮 `python (3.13)` 另有一处与本提交无关的偶发失败：`test_proposal_promotion_proof.DriftedPromotionBaseTests` 的 `copytree` 撞上模板仓库后台维护的
    `objects/maintenance.lock`（`shutil.Error`），记作模块外跟进。
  - 撤回 0535068（走完整检查）：与 e19cac6 的树相同；这一轮五项全绿（CI required、plugin、python 3.9／3.13、validate）。
  - 越界说明：`commands/phase.md` 只在 AC2 临时提交里动过，撤回后与 main 相同；`scripts/check-local-paths.py`、`scripts/test_ci_workflow.py` 见 Plan「文件」段。
- Checkpoint 3（2026-11-24）：用户原话「验收通过」（AC1～AC8，PR #487 五项全绿于 1e54853）。AC9（主干保护只要求 `CI required`）在合并后、用户原话后执行，读回结果记在下一个模块的 todo。
