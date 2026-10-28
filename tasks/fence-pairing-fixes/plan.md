# Plan: fence-pairing-fixes

<!-- spec-guard: review approved -->

依据 [`spec/fence-pairing-fixes.md`](../../spec/fence-pairing-fixes.md)（2026-10-28 用户在本会话批准：「能力图 批准。Spec 批准；Q1 A；Q2 A；Q3 A」）。
分支 `claude/fence-pairing-fixes`（从 `origin/main` `00cf11c9` 开出），worktree `distracted-morse-46ef70`。串行，在本会话做。
本模块改版本号到 0.85.2；合并后的发版按 Spec Q3 A 的授权一次做完。

## Overview

三处各一个任务，每个任务先写在旧代码上失败的测试，再改成调用 `capability_map._visible_lines`；批准标记那处另补两边脚本的正反回归，
并逐个比对本仓库 Spec / Plan 的批准状态。最后改版本号与 CHANGELOG，跑完整检查，交最终验收。

## Architecture Decisions

1. **复用而不是再写一份**：三处都改为调用 `capability_map._visible_lines`（它返回与输入等长的行列表，代码块里的行置空，行号不变）。
   - `documentation_baseline._visible_lines` 保留这个名字，改成从 `capability_map` 导入后再导出：`documentation_impact`、`documentation_verification`
     从它导入，不改它们的 import。`capability_map` 只依赖 `re`，不会形成循环导入。
   - `module_stage.review_marker_lines`：先 `_visible_lines` 再找标记；输入是 `splitlines(keepends=True)`，行尾的 `\n` 不影响判定（实现时用测试确认）。
   - `proposal_submit._headings`：先 `_visible_lines` 再找 `## ` 标题，返回的下标不变。
2. **红的用例**：每处两种写法——外层 4 个反引号包着 3 个反引号的示例；代码块里有一行 ```` ```python ````（旧代码在这里提前结束代码块）。
   用例放在各自已有的测试文件里（`test_documentation_baseline.py`、`test_documentation_impact.py`、`test_documentation_verification.py`、
   `test_review_marker.py`、`test_proposal_submit.py`），照邻近 fenced 用例的写法。
3. **两边脚本的正反回归**（Q2 A）：`test-phase-guard.sh` 一正一反——「4 包 3」代码块里写着 pending 示例、代码块外没有标记时，不出 `awaiting the user's review`；
   代码块外有真的 pending 标记时照常出。`test-verify-artifacts.sh` 一正一反——同样的代码块不算标记；代码块外的真标记照常识别（照 `review-fenced` 用例写）。
4. **批准状态比对**（AC4）：改动前用 `main` 的代码对本仓库每份 `spec/*.md`、`tasks/*/plan.md` 算 `review_state`，存到 scratchpad；改动后再算一次，逐个比对，
   要求全部一致，差异数写进 todo。
5. **发版**照 0.85.1：CHANGELOG 0.85.2 写「修复」三处与「文档」#424；README 中英 `--ref v0.85.2`；发版、宿主核对、证据、收尾 PR 同 config-text-fixes 的做法，
   Codex 那一步先请你在命令行版 `codex` 的 `/hooks` 重新批准再跑 smoke；最后关闭账本 B5WE8BZ。

## Task List

### Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿

- 验证：verify-artifacts 0 失败；快档提交。

### Task 1：文档基线（AC1）

- 文件：`documentation_baseline.py`；三个测试文件各加一个用例。
- 验证：三个新用例在改前红、改后绿；三个测试文件全部通过。

### Task 2：批准标记（AC2、AC4）

- 先记下改前的批准状态；改 `module_stage.review_marker_lines`；`test_review_marker.py` 加用例；两边脚本各加一正一反。
- 验证：新用例改前红、改后绿；`test_review_marker.py`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 通过；批准状态比对 0 差异。

### Task 3：Proposal 标题（AC3）

- 文件：`proposal_submit.py`、`test_proposal_submit.py`。
- 验证：新用例改前红、改后绿；`test_proposal_submit.py` 通过。

### Task 4：版本号与 CHANGELOG（AC5，PR 最后一个内容提交）

- 文件：两份 `plugin.json`、`README.md`、`README.en.md`、`CHANGELOG.md`。
- 验证：`check-readme-sync.py`、`check-manifests.py` 通过。

### Checkpoint 1（report）：发布前完整检查（AC5）

- macOS 系统 `/bin/bash` 跑 `validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 并记录主机；改了 `.sh` 跑 ShellCheck；
  改了 Codex 用的 hook，跑 `evals/codex-plugin-smoke.sh --selftest`。

### Checkpoint 2（gate）：最终验收

- 呈现做了什么、AC1～AC5 证据、文档表、改动与提交表、Spec 中途改动（如有）。通过即同时授权（Q3 A）：推送、开 PR；你合并后由我核对合并并按发版步骤一次做完。

### 发版（合并后，按 Q3 A 授权，AC6）

- 核对 PR 已合并、`main` 指向合并提交；打 `v0.85.2`、推 tag；打包、发 Release、下载比对 SHA-256；
- 刷新 Claude 与 Codex 安装副本并核对（挑一处本版确实改了的代码核对安装副本）；Codex 先请你重新批准 hook，再跑真实 smoke；
- `proposal_closeout.py scan`；写四份证据、开收尾 PR；关闭账本 B5WE8BZ。任一步失败就停下说明。

## Files likely touched

- 插件包：`hooks/documentation_baseline.py`、`hooks/module_stage.py`、`hooks/proposal_submit.py`；测试 `hooks/test_documentation_baseline.py`、
  `hooks/test_documentation_impact.py`、`hooks/test_documentation_verification.py`、`hooks/test_review_marker.py`、`hooks/test_proposal_submit.py`、
  `hooks/test-phase-guard.sh`、`hooks/test-verify-artifacts.sh`；两份 `plugin.json`
- 文档：`README.md`、`README.en.md`、`CHANGELOG.md`；收尾 PR：`docs/releases/v0.85.2-*.json`
- 记录：`spec/CAPABILITY-MAP.md`（已写入）、`spec/fence-pairing-fixes.md`、本 Plan、`tasks/fence-pairing-fixes/todo.md`
- 新增依赖、锁文件改动：无。不碰 `capability_map.py`、`module_scope.py`、`spec-digest.py`。

## 风险

- **批准指纹变化**：`review_digest` 排除的是 `review_marker_lines` 找到的行；只在错误写法下会变，用 AC4 的逐个比对兜住，有差异就停下问你（Spec「先问」）。
- **`review_mark.py` 也调用它**：写批准标记时据此定位；`test_review_marker.py` 里 review_mark 的用例照常要过。
- **两边脚本很慢**（phase-guard 约 2.5 分钟）：开发中只跑新增的那几例附近，完整跑放在提交时的完整档。
- **Codex 0.164 重新批准**：发版时那一步要你在命令行版 `codex` 里点，否则 smoke 返回 2。
