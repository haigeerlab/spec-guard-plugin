# Todo: fence-pairing-fixes

- [x] Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿 — 2026-10-28 用户批准 Spec（「能力图 批准。Spec 批准；Q1 A；Q2 A；Q3 A」）与 Plan（「Plan 批准」），能力图新行经预览确认后写入。
- [x] Task 1：文档基线（AC1） — `documentation_baseline._visible_lines` 删去自写判定，改为从 `capability_map` 导入再导出（impact、verification 的 import 不变）；基线、影响、核验三个测试文件各加 `test_fence_closes_only_on_a_matching_bare_fence`（4 包 3、代码块里带语言名的行两个子用例），改前 3 个都报「不止一张表」，改后三个文件全部通过。
- [x] Task 2：批准标记（AC2、AC4） — `module_stage.review_marker_lines` 改为先过 `capability_map._visible_lines` 再找标记，删去不再使用的 `FENCES`；`test_review_marker.py` 加 4 包 3 与带语言名两个子用例（改前 `'pending' != 'none'`，改后通过，review_mark 用例照常通过）；
  `test-phase-guard.sh` 与 `test-verify-artifacts.sh` 各加一正一反，改前两边都在新用例上失败。批准状态比对：本仓库 327 份 Spec／Plan 用 `main` 的旧判定与新判定逐个算 `review_state` 与标记行号，0 处差异（approved 170、none 153、revised 4）。
- [x] Task 3：Proposal 标题（AC3） — `proposal_submit._headings` 改为先过 `_visible_lines`（文件已从 `capability_map` 导入）再找 `## ` 标题；`test_proposal_submit.py` 加两个子用例，改前把代码块里的「Capability map baseline」当成标题，改后整个文件通过。
- [x] Task 4：版本号与 CHANGELOG（AC5） — 两份 `plugin.json` 改 0.85.2；README 中英 `--ref v0.85.2`；CHANGELOG 加 `## [0.85.2] - 2026-10-28`（修复三处、文档 #424，无升级须知）。`check-readme-sync.py`、`check-manifests.py` 通过。
- [ ] Checkpoint 1（report）：发布前完整检查（AC5）
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
- [ ] 发版（合并后按 Q3 A 授权）：核对合并、打 tag、发 Release、刷新并核对两个宿主、证据收尾 PR、关闭账本 B5WE8BZ（AC6）
