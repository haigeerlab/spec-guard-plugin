# Todo: project-sections

- [x] Task 0：提交 Plan 与 todo
- [x] Task 1：projectSections 配置键、校验与 set，回归
- [x] Task 2：追加章节的检查与提示，回归
- [x] Task 3：骨架与配置说明、0.94.0、CHANGELOG、README
- [x] Checkpoint 1（report）：完整检查、变异与实跑
- [x] Checkpoint 2（gate）：最终验收；通过后推送并开 PR，合并由用户进行
- [x] 合并后发 0.94.0 并通知 ecosystem-lead 与 S110 各方（2026-11-24 已发布、已安装，通知 #22410–#22413）

2026-11-24 用户「验收通过」。推送与开 PR 等 PR #483 合并后再做。

## 外部审查意见

- Plan 经 Codex（/delegate:review，对照 project_config.py、module_stage.py）审两轮：第 1 轮 5 条阻断，改进后第 2 轮 0 条阻断，按 takeover=plan 记 codex-approved（轮次行见 plan.md）。第 1 轮引出 Spec AC4 修订，用户 11-24「批准 AC4 修订」。
  第 2 轮建议：测试说明「前两类之外」易误读——实现时写成「bug、small 均忽略 design、regression 的追加章节」。

## 证据

- Checkpoint 1（2026-11-24，提交 d1065a5 上的 verify-and-commit 全套，macOS `/bin/bash`）：`validate.sh` 退出 0「校验通过 ✅」（含版本一致性）；`test-phase-guard.sh` 退出 0「phase-guard regression passed (540 cases)」；
  `test-verify-artifacts.sh` 退出 0「verify-artifacts regression passed (117 cases)」；两份 `plugin.json` 为 0.94.0。
- 变异（各自还原）：不读追加章节 → `test_flow_v2.ProjectSectionsTest` 3 例失败、`test-verify-artifacts.sh`「追加章节：技术方案缺声明的章节时失败」失败；校验不拦重复章节名 → `test_project_config.ProjectSections` 2 例失败。
- 本仓库新旧比对（旧代码取自 bdd527e）：`/map --json` 逐字相同、阶段提示逐字相同、verify-artifacts 输出与退出码（0）逐字相同（本仓库没有声明 projectSections）。
- 临时项目实跑：`project_config.py set --key projectSections --value '{"design": ["浏览器兼容"]}'` 先预览（未写）再 `--confirm` 写入；normal 档模块需求已批 → `NEEDS_DESIGN` 下一步末尾「另加本项目要求的章节：浏览器兼容。」；
  技术方案只有骨架章节时 verify-artifacts「缺章节：浏览器兼容」1 失败，补上标题后「5 通过 · 0 警告 · 0 失败」。
