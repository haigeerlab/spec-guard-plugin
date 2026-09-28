# Plan: audit-remediation

依据 [`spec/audit-remediation.md`](../../spec/audit-remediation.md)。十个 task 严格串行，每个 task 一条提交；
每个 task 先写能在当前代码上失败的测试并记录失败输出，再修复到通过。每个 task 都在 `CHANGELOG.md` 的
Unreleased 下记一条用户可见的修复（纯维护者文档的 Task 10 除外）。

排序：改动最复杂、最可能暴露新问题的 Proposal 修复放在最前；文档类放在最后，因为 Task 7 会改变 Codex 路由的事实。

每个 task 完成时都运行三条最小验证：

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Phase 1：Proposal 与快速插入

### Task 1：晋级证明的状态与判据（R2 前半）

- `proposal_promotion_proof.py` 的 `prove`：没有 first-parent 提交包含新模块时，返回 `not-promoted`
  （诊断 `promotion-not-found`），不再落到 `invalid`；晋级白名单允许额外包含 `tasks/<id>/todo.md`。
- `test_proposal_promotion_proof.py` 新增反例：尚未晋级；依赖与声明不符；`end` 锚点不在最后；Spec 头部错误；
  以及正例：晋级提交带 `todo.md` 时 `proved`。
- **验收：** 三条判据反例在修复前后都能分辨（审计中存活的三个变异体现在会被杀死）；尚未晋级不再报 `invalid`。
- **验证：** `python3 -B plugins/spec-guard/hooks/test_proposal_promotion_proof.py`；手工把 `_matches` 中的
  依赖比较改成恒真，确认测试变红后还原（在 scratchpad 副本上做）。
- **文件：** `proposal_promotion_proof.py`、`test_proposal_promotion_proof.py`、`commands/proposal-promotion-proof.md`、
  `CHANGELOG.md`。

### Task 2：预检与证明透传下层诊断（R2 后半）

- `preflight_as_json` 与 `as_json` 保留下层诊断（发布层 `publication-*`、tracker 层 `tracker-*`、验收记录层），
  不再覆盖成 `promotion-preflight-<state>` / `promotion-<state>`；做法与 `proposal_mainline_review.as_json` 一致。
- 测试：缺 tracker Issue、缺 Proposal、验收记录无效三种情况给出三个不同的诊断。
- `commands/proposal-promotion-preflight.md` 与 `-proof.md` 的状态说明同步。
- **验收：** 三种原因在输出中可区分；已有用例的 `state` 不变。
- **验证：** `test_proposal_promotion_proof.py`；`test_proposal_mainline_review.py`。
- **文件：** `proposal_promotion_proof.py`、`test_proposal_promotion_proof.py`、两个命令文档、`CHANGELOG.md`。

### Task 3：主链裁决输出可复制的验收记录（R3）

- `proposal_mainline_review.py`：结果为 `accepted-candidate` 时，输出附带 `attestation` 对象（7 个字段，
  `policyDigest` 用现有的规范化 JSON 摘要函数计算）和建议路径 `spec/proposal-acceptances/<id>-<revision>.json`；
  命令仍不写文件。
- 测试：`accepted-candidate` 时附带的记录能被 `accepted()` 读取的同一校验函数接受；其他结果不附带。
- `references/proposal-mainline-review.md` 写明字段、路径与"不可改写"规则；`docs/workflow.md` 第 6 步引用它。
- **验收：** 在临时仓库里，把输出的记录原样写入路径后，预检不再因验收记录报阻断。
- **验证：** `test_proposal_mainline_review.py`；`test_proposal_promotion_proof.py`。
- **文件：** `proposal_mainline_review.py`、`test_proposal_mainline_review.py`、`references/proposal-mainline-review.md`、
  `docs/workflow.md`、`CHANGELOG.md`。

### Task 4：快速插入不再假成功，保留文件权限（R1）

- `module-insert.py`：定位模块表与 Build order 行时跳过代码围栏（复用 `capability_map` 的可见行规则，不复制）；
  预览与写入都断言新 id 出现在新能力图的模块行与 Build order 中；写入后恢复原文件的权限位。
- 测试：能力图在真实模块表前有围栏示例表时，要么正确插入真实表、要么非零退出且不写文件，且示例原样不动；
  写入前后 `stat` 权限位一致。
- **验收：** 审计复现的场景不再输出"已写入"却没插入；0644 保持 0644。
- **验证：** `python3 -B plugins/spec-guard/hooks/test_module_insert.py`（默认 `python3` 与 `/usr/bin/python3`）。
- **文件：** `module-insert.py`、`test_module_insert.py`、`CHANGELOG.md`。

### Checkpoint A：Task 1–4 之后

- 三条最小验证通过；Proposal 七个聚焦套件全部通过。
- 向用户汇报：新增状态与诊断的实际输出示例，确认措辞后再继续。

## Phase 2：校验器与历史

### Task 5：历史孤立目录覆盖三棵树（R5）

- `verify-history.sh`：期望目录集合改为账本中所有记录（能力图、Spec、Plan、state）的所在目录；
  `spec/history`、`tasks/history`、`.agent/history` 下任何含文件但不在集合中的目录都报 `orphan history evidence`。
- 测试（`test-history-verification.sh`）：在 `tasks/history` 与 `.agent/history` 下各放一个未登记目录，分别断言
  非零退出；本仓库真实历史证据仍通过。
- **验收：** 审计复现的两个场景从"通过"变为失败；`validate.sh` 中的历史回归仍通过。
- **验证：** `/bin/bash plugins/spec-guard/hooks/test-history-verification.sh`；
  `/bin/bash plugins/spec-guard/hooks/verify-history.sh .`。
- **文件：** `verify-history.sh`、`test-history-verification.sh`、`CHANGELOG.md`。

### Task 6：归档不留下 `-shm` 临时文件（R7）

- `native_collaboration_archive.py`：备份与改 journal 模式后，确保临时数据库的连接已关闭、SQLite 附属文件
  不会留在归档目录；只在归档目录里留下 `messages.sqlite`。具体做法以不改变备份内容与校验为前提，在实现时确定。
- 红灯：`/usr/bin/python3`（SQLite 3.43.2）下现有用例
  `test_archive_keeps_uncheckpointed_wal_mail_and_unread_state` 已失败，作为本 task 的失败测试。
- **验收：** 该用例在默认 `python3`（SQLite 3.37.2）与 `/usr/bin/python3` 下都通过；归档内容校验不变。
- **验证：** 两种解释器各跑一次 `test_native_collaboration_cutover.py`；另跑 `test_native_collaboration_rollback.py`。
- **文件：** `native_collaboration_archive.py`、`CHANGELOG.md`（必要时 `test_native_collaboration_cutover.py`）。

### Task 7：Codex 补 teardown 与 history correct 路由（R4 前半）

- `skills/spec-guard-ops/SKILL.md`：新增 teardown 一节（先 `--dry-run` 并展示，用户确认后执行；Codex 宿主参数与
  `commands/teardown-convention.md` 一致）；history 一节补 `correct`（必须带 `--confirm` 并先经用户确认）。
- `docs/workflow.md` 命令对照：与实际路由一致。
- 测试：`evals/test-codex-command-roots.sh` 或新增断言，确认 skill 中的 teardown 命令行与命令文档使用同一脚本与参数。
- **验收：** Codex 用户只按 skill 即可预览并执行 teardown。
- **验证：** `/bin/bash evals/test-codex-command-roots.sh`；`test-setup-teardown.sh`。
- **文件：** `skills/spec-guard-ops/SKILL.md`、`docs/workflow.md`、`CHANGELOG.md`（必要时一个测试文件）。

### Task 8：命令与 skill 入口对应检查，扩大退役扫描（R4 后半 + R6）

- 新增 `scripts/check-command-parity.py`：`commands/*.md` 引用的每个 `hooks/<脚本>` 至少出现在一个 skill 中；
  刻意不对称的入口列在显式允许清单并写理由；零个命令文件不算通过。
- `test-retire-legacy-tracker-bridge.sh`：接受根目录参数；扫描 `plugins/spec-guard/` 下所有非测试文件中的已退役
  标识与写 Issue 命令；两处现行的否定说明用带理由的显式允许清单放行。
- `scripts/test-checkers.sh`：两个检查器各一正一反（反例分别是：新增一个无 Codex 路由的命令；新增一个含
  `gh issue create` 的命令文件）。`validate.sh` 接入入口对应检查。
- **验收：** 两个反例都被拦下；当前仓库两个检查都通过。
- **验证：** `/bin/bash scripts/test-checkers.sh`；`validate.sh`。
- **文件：** `scripts/check-command-parity.py`、`test-retire-legacy-tracker-bridge.sh`、`scripts/test-checkers.sh`、
  `scripts/validate.sh`。

### Checkpoint B：Task 5–8 之后

- 三条最小验证通过；`/usr/bin/python3` 下 cutover、rollback、module-insert 套件通过。
- 向用户汇报后再进入文档阶段。

## Phase 3：文档一致性（R8）

### Task 9：用户与规约文档

- `spec/documentation-verification.md`：删去 verify-artifacts 集成的承诺及对应测试条目。
- `commands/phase.md`：DONE 的含义与建议和 `module_stage.py` 一致。
- `docs/decisions/2026-09-28-quick-insert.md`：状态改为已实现（0.24.0）。
- `spec/collaboration-messaging.md`：Commands 与测试清单补齐已存在的脚本和测试。
- **验收：** 用 grep 断言旧说法不再出现（"仅显示这项事实"与 verify-artifacts 同句、"尚未实现"、phase.md 中
  "新需求走 Proposal" 作为默认）。
- **验证：** `validate.sh`；`check-readme-sync.py`。
- **文件：** 上述四个文件、`CHANGELOG.md`。

### Task 10：维护者文档

- `CLAUDE.md`：最小验证一节不再承诺变异测试工具；在"作用域与自引用边界"中提到 `.epiq/` 是有意保留的自用状态。
- `docs/lenses.md`：引用 `scripts/mutation-check.py`、`evals/next-redo.sh` 的地方标明已删除（历史条目保留）。
- `CONTRIBUTING.md`：CI 描述改为不断言运行次数的准确说法；修正发版锚点为 `docs/release-process.md`；
  "加新命令"补上 Codex skill 路由与 `docs/workflow.md` 命令对照。
- `scripts/install-git-hooks.sh`：注释中的 CI 运行次数说法改为准确说法。
- `docs/migration-strict-serial.md`：去掉"待发布候选"的过时说法。
- **验收：** grep 断言失效锚点与已删除工具不再作为现有事物出现。
- **验证：** `validate.sh`（包含 shell 语法与 bash 3.2 检查）。
- **文件：** 五个文档/脚本注释（仅注释改动，不改脚本行为）。

### Checkpoint C：完成

- 三条最小验证在默认 `python3` 与 `/usr/bin/python3` 下都通过。
- Spec 的 Success criteria 逐条核对并记录证据。
- `tasks/audit-remediation/todo.md` 全部勾选，阶段变为 DONE；向用户汇报，由用户决定是否推送与开 PR。

## 风险

| 风险 | 影响 | 缓解 |
|---|---|---|
| Task 2 改诊断会破坏依赖旧诊断字符串的测试或文档 | 中 | 先 grep 所有 `promotion-preflight-`、`promotion-` 使用点；只改诊断，不改 `state` |
| Task 4 修围栏定位时改动与严格解析器不一致 | 中 | 复用 `capability_map` 的可见行逻辑；以"已有行摘要不变"测试兜底 |
| Task 6 的修复依赖 SQLite 版本行为 | 中 | 两个解释器都跑；不改变备份内容校验 |
| Task 8 扩大扫描后误报现行否定说明 | 低 | 显式允许清单带理由，并有正例测试 |
| 已安装版插件与工作区源码不同 | 低 | 一律用仓库测试与临时消费者项目验证，不引用本仓库 hook 输出 |
