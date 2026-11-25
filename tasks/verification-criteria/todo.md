# Todo: verification-criteria

- [x] Task 0：提交 Spec（含修订）、Plan 与 todo（2026-11-25 用户「批准；Q1 A；Q2 A」，2026-11-26 Plan 与 Spec 修订「批准」）
- [x] Task 1：patchId 与作者记录
- [x] Task 2：校验器
- [x] Task 3：记录与读取
- [x] Task 4：阶段提示与最终 gate
- [x] Task 5：`/map --json` 与 review-mark
- [x] Task 6：接口 1.24
- [x] Checkpoint 1（report）：本机完整检查、老流程比对与变异
- [x] Task 7：规则与文档
- [x] Checkpoint 2（gate）：推送、开 PR、提议宿主 PR 监控、最终验收并同时问合并、拟回告（用户「验收通过并合并」）

## 证据
- Task 1～3（2026-11-26）：新文件 `hooks/verification.py`：`author`（会话 id 只读环境变量，记在公共 git 目录 `spec-guard/authors/<id>.json`，同一会话一条）、`current_patch_id`（默认分支取 `origin/HEAD`，没有时 `main`）、`check`（Spec 假设 4 的全部问题代码，含修订后的 `patch-id-wrong`）、`record` 与 `verification_state`（`current` 看当前补丁与回归文档 sha256），联调回归 `--usage` 的作者为各模块作者的合集。`scripts/validate.sh` 登记 `test_verification.py`。
  用例：`test_verification.py` 15 例（作者 4、patchId 1、校验 6、无作者 1、记录 2、联调 1）；用例先写，挪开 `verification.py` 时 25 个失败或出错。`patch-id-wrong` 的样本最初用 `base..base`（空补丁，只会进「未核验」），改成从 base 另开一个提交当 head。
- Task 4（2026-11-26）：`module_stage`：`author_line`（新流程模块构建中、没有作者记录时一行，给出 `verification.py author` 命令）；`verification_line`（最终 gate 时四种状态：没有结论、过期、不通过、通过（含意见数），按 `merge` 档位写下一步，Q1 A：`merge=human` 没有结论时由用户决定）；两者进状态码与 `_role_facts`。
  `final_gate_accepted` 对新流程模块只认当前、通过的验证结论且 `merge=auto`；`acceptance_record`、`acceptance_step` 对新流程模块返回空。
  用例：`test_flow_v2.py` `VerificationHintTest` 6 例，实现前 6 个失败；`test-phase-guard.sh` 加 2 例（551 例通过）。其中一例最初断言整段提示里没有「最终验收交 Codex」，但这句也在 `node-rules.md` 的固定停点规则里（Task 7 才改），改为断言 `acceptance_step` 特有的句子。
- Task 5（2026-11-26）：`/map --json` 每个模块加 `verification`（老流程模块与没有记录为 `null`），顶层加 `usageVerification`（每个 `spec/usage/*.regression.md` 一项，没有时 `{}`）；新流程模块的 `acceptance` 为 `null`。review-mark `--target acceptance` 对新流程模块退出 2 `acceptance-flow-v2`。
  用例：`test_map_view.py` `VerificationMapTest` 2 例（实现前 2 个出错），`TOP_KEYS`／`MODULE_KEYS` 加新键；`test_review_marker.py` `AcceptanceFlowV2` 1 例（实现前失败）。
  旧用例改动及原因：`AcceptanceFlowScope` 两例（plan-auto-approve）原本断言新流程 `merge=auto` 模块的 Codex 最终验收按技术方案影响面查越界；Spec 假设 8 起新流程模块不再走 Codex 验收，改为断言 `acceptance-flow-v2`。新流程模块构建中的越界检查（`scope_overreach`）不变。
- Task 6（2026-11-26）：`interface.json` 升到 1.24：顶层加 `verification`（`authorCommand`、`checkCommand`、`recordCommand` 原样可跑，`usageArgs`、`confirmArgs` 另列，`schema`、`exitCodes`、问题代码、取值、记录与作者记录的位置），`mapView` 加 `verification`、`usageVerification`，`acceptance` 的说明写明新流程模块为 null。`check-interface.py` 加比对；`scripts/test-checkers.sh` 的接口夹具加 `verification`。
  用例：`test_verification.py` `InterfaceTest` 1 例（按模板代入真实路径依次运行三条命令，核对 `check --json` 的键集合）；`check-interface.py` 通过。
- Checkpoint 1（2026-11-26）：Task 1～6 的每次提交都走了完整档且全绿。老流程输出比对（AC10）：已安装的 0.95.0 与本分支各跑本仓库和老流程夹具，阶段提示与 verify-artifacts 逐字相同；`/map --json` 去掉 `generatedAt` 与本模块新增的两个键（顶层 `usageVerification`、模块的 `verification`）后，逐字段比对只有 `generator.version` 不同（0.95.0 → 0.96.0，regression-doc-check 升的版本号）。
  变异（临时副本）：不查执行者是否作者、patchId 用 HEAD 的 sha、`current` 不看回归文档、最终 gate 不走新流程分支（认 Codex 记录）、`record` 不先校验、`acceptance_step` 不跳过新流程模块，各自让对应用例变红。`current` 不看回归文档那处第一次没拦住（现有用例改文档时也改了提交，补丁一变 `current` 本来就假），补一例只在工作区改回归文档后拦住。还原后全绿。
- Task 7（2026-11-26）：新文件 `references/verification-report.md`（三步、字段表、怎样算成立、一份完整例子、记下之后）；共享检查点规则新增「新流程模块按回归文档做合并前验证」一条，Codex 最终验收一条写明不用于新流程模块；`node-rules.md` 最终验收停点把 Codex 验收限定到老流程模块，新流程模块看「合并前验证」一行（Q1 A）；`docs/commands.md` 加 `verification.py` 一节、`/map` 段落补 1.24 的字段；CHANGELOG「未发布」加一条。
  `test_workflow_checkpoints.py`（边界外）断言停点规则里有「最终验收交 Codex」，这句保留、只加了「老流程」限定，该测试不改照样通过；快档校验通过。
- Checkpoint 2（2026-11-26）：基于 main `bbd12171` 推送，开 PR #501 并绑定到会话；验收消息里提了宿主 PR 监控，由用户决定，没有打开。最终验收与合并合成一问，用户回「验收通过并合并」。拟回告发给 autopr-design 与 mc-coord。收尾文档建议：README「自动接管」一节对新流程模块的最终验收描述已过时，建议合并后单开只改两份 README 的小 PR（另问用户）。
