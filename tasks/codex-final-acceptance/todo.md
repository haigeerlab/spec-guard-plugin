# Todo: codex-final-acceptance

- [x] Task 0：提交 Plan 与 todo
- [x] Task 1：inspect_final、inspect_check 与单测
- [x] Task 2：review-mark --target acceptance 与 git 目录记录
- [x] Task 3：阶段提示与 /map 的 acceptance、接口
- [x] Task 4：规则与说明
- [x] Task 5：0.91.0 版本号、README、CHANGELOG
- [x] Checkpoint 1（report）：完整检查、变异验证与实跑
- [x] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行

## Checkpoint 1 记录（2026-11-22）

- 完整检查：每次提交都走 verify-and-commit 完整档（validate、phase-guard 536 例、verify-artifacts 105 例，暂存 `.sh` 时加 ShellCheck），全绿。
  Task 4 第一次提交时 `test_proposal_promotion_proof` 因并行测试的临时模板目录被提前删除而失败，与本模块无关，重跑通过。
- 变异：证据② 不看 `non_author` → `test_codex_review` 2 例、`test_review_marker.Acceptance` 1 例变红；记录不看祖先关系 → phase-guard 第 31 段
  「记录的提交不是 HEAD 的祖先时，最终 gate 不算通过」变红。均已还原。
- 临时项目实跑（工作区源码，HOME 指向临时目录；档位 `{"merge": "auto"}`，能力图 alpha → beta）：
  1. 到最终 gate：建议下一步为「最终验收交 Codex……不要自己验收。拟回告写进 todo，不发出」。
  2. 手写最终审查报告、还没有检查证据：`check-invalid: no check evidence for HEAD …`，退出 2。
  3. 写好 `autopilot.check-evidence/v1` 后预览：列出报告、证据路径与将写的记录（`report` 为绝对路径），未写入。
  4. `--confirm`：记录写到 `.git/spec-guard/acceptance/alpha.json`，`git status --porcelain` 为空，HEAD 不变。
  5. 阶段提示：当前模块转到 `beta`（最终 gate 当作已过）。
  6. `/map --json`：alpha `done`，`acceptance` 为 `{marker: codex-approved, sha: <HEAD>}`；beta 为 `null`。

<!-- spec-guard: external-review declined -->

2026-11-22 用户「验收通过」。
