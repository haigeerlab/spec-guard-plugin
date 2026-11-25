# Todo: verification-criteria

- [x] Task 0：提交 Spec（含修订）、Plan 与 todo（2026-11-25 用户「批准；Q1 A；Q2 A」，2026-11-26 Plan 与 Spec 修订「批准」）
- [x] Task 1：patchId 与作者记录
- [x] Task 2：校验器
- [x] Task 3：记录与读取
- [x] Task 4：阶段提示与最终 gate
- [x] Task 5：`/map --json` 与 review-mark
- [ ] Task 6：接口 1.24
- [ ] Checkpoint 1（report）：本机完整检查、老流程比对与变异
- [ ] Task 7：规则与文档
- [ ] Checkpoint 2（gate）：推送、开 PR、提议宿主 PR 监控、最终验收并同时问合并、拟回告

## 证据
- Task 1～3（2026-11-26）：新文件 `hooks/verification.py`：`author`（会话 id 只读环境变量，记在公共 git 目录 `spec-guard/authors/<id>.json`，同一会话一条）、`current_patch_id`（默认分支取 `origin/HEAD`，没有时 `main`）、`check`（Spec 假设 4 的全部问题代码，含修订后的 `patch-id-wrong`）、`record` 与 `verification_state`（`current` 看当前补丁与回归文档 sha256），联调回归 `--usage` 的作者为各模块作者的合集。`scripts/validate.sh` 登记 `test_verification.py`。
  用例：`test_verification.py` 15 例（作者 4、patchId 1、校验 6、无作者 1、记录 2、联调 1）；用例先写，挪开 `verification.py` 时 25 个失败或出错。`patch-id-wrong` 的样本最初用 `base..base`（空补丁，只会进「未核验」），改成从 base 另开一个提交当 head。
- Task 4（2026-11-26）：`module_stage`：`author_line`（新流程模块构建中、没有作者记录时一行，给出 `verification.py author` 命令）；`verification_line`（最终 gate 时四种状态：没有结论、过期、不通过、通过（含意见数），按 `merge` 档位写下一步，Q1 A：`merge=human` 没有结论时由用户决定）；两者进状态码与 `_role_facts`。
  `final_gate_accepted` 对新流程模块只认当前、通过的验证结论且 `merge=auto`；`acceptance_record`、`acceptance_step` 对新流程模块返回空。
  用例：`test_flow_v2.py` `VerificationHintTest` 6 例，实现前 6 个失败；`test-phase-guard.sh` 加 2 例（551 例通过）。其中一例最初断言整段提示里没有「最终验收交 Codex」，但这句也在 `node-rules.md` 的固定停点规则里（Task 7 才改），改为断言 `acceptance_step` 特有的句子。
- Task 5（2026-11-26）：`/map --json` 每个模块加 `verification`（老流程模块与没有记录为 `null`），顶层加 `usageVerification`（每个 `spec/usage/*.regression.md` 一项，没有时 `{}`）；新流程模块的 `acceptance` 为 `null`。review-mark `--target acceptance` 对新流程模块退出 2 `acceptance-flow-v2`。
  用例：`test_map_view.py` `VerificationMapTest` 2 例（实现前 2 个出错），`TOP_KEYS`／`MODULE_KEYS` 加新键；`test_review_marker.py` `AcceptanceFlowV2` 1 例（实现前失败）。
  旧用例改动及原因：`AcceptanceFlowScope` 两例（plan-auto-approve）原本断言新流程 `merge=auto` 模块的 Codex 最终验收按技术方案影响面查越界；Spec 假设 8 起新流程模块不再走 Codex 验收，改为断言 `acceptance-flow-v2`。新流程模块构建中的越界检查（`scope_overreach`）不变。
