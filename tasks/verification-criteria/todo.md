# Todo: verification-criteria

- [x] Task 0：提交 Spec（含修订）、Plan 与 todo（2026-11-25 用户「批准；Q1 A；Q2 A」，2026-11-26 Plan 与 Spec 修订「批准」）
- [x] Task 1：patchId 与作者记录
- [x] Task 2：校验器
- [x] Task 3：记录与读取
- [ ] Task 4：阶段提示与最终 gate
- [ ] Task 5：`/map --json` 与 review-mark
- [ ] Task 6：接口 1.24
- [ ] Checkpoint 1（report）：本机完整检查、老流程比对与变异
- [ ] Task 7：规则与文档
- [ ] Checkpoint 2（gate）：推送、开 PR、提议宿主 PR 监控、最终验收并同时问合并、拟回告

## 证据
- Task 1～3（2026-11-26）：新文件 `hooks/verification.py`：`author`（会话 id 只读环境变量，记在公共 git 目录 `spec-guard/authors/<id>.json`，同一会话一条）、`current_patch_id`（默认分支取 `origin/HEAD`，没有时 `main`）、`check`（Spec 假设 4 的全部问题代码，含修订后的 `patch-id-wrong`）、`record` 与 `verification_state`（`current` 看当前补丁与回归文档 sha256），联调回归 `--usage` 的作者为各模块作者的合集。`scripts/validate.sh` 登记 `test_verification.py`。
  用例：`test_verification.py` 15 例（作者 4、patchId 1、校验 6、无作者 1、记录 2、联调 1）；用例先写，挪开 `verification.py` 时 25 个失败或出错。`patch-id-wrong` 的样本最初用 `base..base`（空补丁，只会进「未核验」），改成从 base 另开一个提交当 head。
