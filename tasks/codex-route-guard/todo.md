# Todo: codex-route-guard

- [x] Task 0：提交能力图新行、Spec、Plan 与 todo
- [x] Task 1：review-mark 写 codex-approved 前的 codex_route 兜底与回归（Codex）
- [x] Task 2：/map --json 的 codexRoute、接口 1.16 与回归（Codex）
- [x] Task 3：验收记录放公共 git 目录、先新后旧读取与回归（Codex）
- [x] Task 4：命令说明、0.92.0 版本号、CHANGELOG、README
- [x] Checkpoint 1（report）：完整检查、变异与临时项目实跑
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开 PR，合并由用户进行

## Checkpoint 1 记录（2026-11-22）

- 编码由 Codex 完成（三次 `/delegate:run --write`：T1 run 20261122151622.31953、T2 run 20261122152327.19495、T3 run 20261122152954.5823），每次只改了派活说明允许的文件。
  Claude 验收：读全部差异，自己重跑 `test_review_marker`、`test_map_view`、`test_workflow_checkpoints`（246 例）与 `check-interface.py`，均通过。
- 变异（各让回归变红，均已还原）：去掉兜底的 `return 2`（4 例失败）；`codexRoute` 写死为 null（28 例失败）；验收记录只读旧位置（1 例失败）。
- 每个提交走 verify-and-commit 完整档，全绿。
- 本仓库实跑（工作区源码）：本仓库没有接管配置，`review_mark --target spec --state codex-approved --review <不存在的文件>` → 退出 2、`codex-route-takeover`，
  没有读报告，工作区不变；`/map --json` 里 codex-route-guard、codex-approval 的 `codexRoute` 都是 `{"spec": "takeover", "plan": "takeover"}`。
- 跨 worktree：回归 `AcceptanceWorktrees` 用真实 git 建 linked worktree，在其中经 `review_mark --target acceptance --confirm` 记录，主 checkout 的 `acceptance_record`
  与 `/map --json` 读得到；合入前 gate 不算过、快进后算过、再多一个提交仍算过；旧位置兼容、新位置优先、新位置无效时回退。
