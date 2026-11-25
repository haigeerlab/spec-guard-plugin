# Plan: verification-criteria

<!-- spec-guard: review approved -->

Spec：[spec/verification-criteria.md](../../spec/verification-criteria.md)（2026-11-25 批准，Q1 A、Q2 A）。写 Plan 时修订 Spec 假设 4 的一条（`head-unknown` 改为 `patch-id-wrong`，见下），所以本 Plan 连同修订交用户；2026-11-26 用户「批准」。

## 预先声明

- 公共路径：无
- 外部依赖：无
- 质量与工作区配置：无
- 补丁：无

## 架构决定

- **一个新脚本，三个子命令**（`hooks/verification.py`）：
  - 公共 git 目录下两个子目录：`spec-guard/authors/<id>.json`（作者列表）、`spec-guard/verification/<id>.json`（结论；联调回归为 `usage-<name>.json`）。路径函数复用 `module_stage._git` 与 `acceptance_path` 的取法（`git rev-parse --git-common-dir`），不进提交。
  - `current_patch_id(root)`：默认分支取 `git symbolic-ref refs/remotes/origin/HEAD`，读不到用 `main`，再读不到返回 None（判不了，退出 3）；`git diff <merge-base> HEAD | git patch-id --stable` 的第一列，空补丁为 None。
  - `patch_id(root, base, head)`：同样算 `base..head`，提交读不到返回 None。
  - `author`：会话 id 只读环境变量 `CLAUDE_CODE_SESSION_ID`（宿主 `claude-code`）或 `CODEX_THREAD_ID`（`codex`），用 `project_link.SESSION_ID` 校验格式；读不到退出 2 `no-session-id`。模块要是新流程模块且在能力图上。原子写、读回核对；同一会话已在就不改。没有 `--confirm` 也直接写（这是会话自己的事实，不是批准）——与 review-mark 不同，在命令帮助与文档里写明。
  - `check`：读报告（UTF-8 JSON，最大 1 MiB）→ 按 Spec 假设 4 逐条判，问题代码固定（`PROBLEM_CODES`）；用例以 `regression_view.module_report`／`usage_report` 为准（Markdown 只在那里解析）。
    证据文件：`path` 为绝对路径或相对报告所在目录；读得到才核 sha256，读不到列进 `unverified`。`baseline-fail` 的 `baselineCommit` 用 `git merge-base --is-ancestor <commit> <base>` 判；读不到提交也列进 `unverified`。
    联调回归（Q2 A）：作者取 `usage_report` 的「涉及的模块」各自作者记录的合集；任一模块没有作者记录 → 退出 3 `author-unknown`。
  - `record`：调同一个 `check`，成立才写；预览打印将写入的 JSON。记录里的 `reportSha256` 是报告文件字节的 sha256。
- **读结论**（`verification_state(root, module | usage)`，verification.py 里，module_stage 与 map_view 共用）：返回 `None`（没有记录）或 `{verdict, patchId, notes, reportSha256, current}`；
  `current` = 记录的 patchId 等于 `current_patch_id` 且 `regressionSha256` 等于当前回归文档的 sha256。`passed` = `current` 且 `verdict != "fail"`。
- **module_stage**（Spec C2）：
  - `author_line`：新流程模块 `BUILDING`、没有任何作者记录时一行，给出 `verification.py author` 命令（带插件根目录的写法同阶段提示里其他命令）；进状态码。
  - `verification_line`：新流程模块在最终 gate 时一行，四种状态（没有、过期、不通过、通过及意见数）；进状态码。
  - `final_gate_accepted`：新流程模块只看验证结论——`merge=auto` 且 `passed` 为真才算过；Codex 验收记录对新流程模块不算。老模块逻辑不变。
  - `acceptance_record` 与 `acceptance_step` 对新流程模块返回 None（`/map --json` 的 `acceptance` 对它们为 `null`）。
  - 依赖方向：verification.py 导入 module_stage；module_stage 在函数内延迟导入 verification，避免循环（同 regression_view）。
- **map_view**（Spec C3）：每个模块加 `verification`（老模块 `null`）；顶层加 `usageVerification`：`spec/usage/*.regression.md` 每个一项，`{<name>: 记录或 null}`，没有这类文件时为 `{}`。
- **review_mark**（Spec C4）：`--target acceptance` 遇到新流程模块退出 2 `acceptance-flow-v2`，说明改用合并前验证。
- **接口 1.24**：`interface.json` 加 `verification`（`authorCommand`、`checkCommand`、`recordCommand`、`usageArgs`、`exitCodes`、`values.problem`、`values.report` 字段表、`values.record`）、`mapView.verification`、`mapView.usageVerification`；
  命令模板原样可跑（regression-doc-check 的教训），可选参数另列。`check-interface.py` 比对问题代码与 `verification.PROBLEM_CODES`、脚本存在；`scripts/test-checkers.sh` 的接口夹具加 `verification`。
- **Spec 修订（假设 4 的一条）**：原文「`head` 是 HEAD 或其祖先（`head-unknown`）」在 rebase 后不成立，与 AC5（rebase 后照样成立）冲突。改为：`base`、`head` 在本仓库读得到时，`patchId` 要等于 `base..head` 的 patchId（`patch-id-wrong`），读不到只记为「未核验」。当前补丁的比对（`patch-mismatch`）不变。
- **测试放哪**：新建 `hooks/test_verification.py`（Spec 边界已列，在 `scripts/validate.sh` 登记）放 verification.py 的用例；阶段提示与最终 gate 的用例放 `test_flow_v2.py`；`/map` 放 `test_map_view.py`；review-mark 放 `test_review_marker.py`；`test-phase-guard.sh` 加端到端两例。

## 任务

- **Task 0**：提交 Spec（含修订）、本 Plan 与 todo。验证：`verify-and-commit` 快档。
- **Task 1**：patchId 与作者记录。先写会红的 `test_verification.py`：读不到会话 id 拒绝、同一会话记两次只一条、两个会话两条、老流程模块拒绝；`current_patch_id` 在多一个提交时变、rebase 到新 main 上不变（AC4 后半、AC5 前半）。再实现，并在 `validate.sh` 登记。验证：`test_verification.py`。
- **Task 2**：校验器。用例：一份合格报告成立（含 `manual` 用户原话、`baseline-fail`、意见，AC1）；每个问题代码一份反例（AC2）；结论一致性（AC3）；`executor-is-author`、没有作者记录退出 3（AC4）；`patch-mismatch`、rebase 后成立、`regression-changed`、`patch-id-wrong`（AC5）；证据读不到只进 `unverified`。先红后实现。验证：同上。
- **Task 3**：记录与读取。用例：不成立不写、预览不写、写到公共 git 目录且 `git status` 干净、读回 `current`，补丁变了 `current` 为假（AC6）；`--usage` 校验与记录、作者合集（AC9 的一半）。先红后实现。验证：同上。
- **Task 4**：阶段提示与最终 gate。`test_flow_v2.py`：作者提示行出现与消失；最终 gate 四种状态；`merge=auto` 有当前、通过的记录时最终 gate 算过，`fail`、过期、只有 Codex 验收记录时不算；`merge=human` 照旧停下（AC7）；新流程模块不出 Codex 验收的下一步（AC8 的一半）；状态码随状态变。`test-phase-guard.sh` 两例。先红后实现。验证：这两个文件。
- **Task 5**：`/map --json` 与 review-mark。`test_map_view.py`：`verification` 的键集合、老模块 `null`、`current`；`usageVerification`（AC6、AC9）；新流程模块 `acceptance` 为 `null`。`test_review_marker.py`：新流程模块 `--target acceptance` 拒绝，老模块照旧（AC8）。先红后实现。验证：这两个文件。
- **Task 6**：接口 1.24。`interface.json`、`check-interface.py`、`test-checkers.sh` 夹具；一条用例按模板代入真实路径跑 `check`，输出与说明一致（AC10 前半）。验证：`check-interface.py`、`test-checkers.sh`、`test_verification.py`。
- **Checkpoint 1（report）**：完整档三条检查全绿；老流程输出比对（已安装的 0.95.0 对本分支，本仓库与老流程夹具，阶段提示、`/map --json` 去掉 `generatedAt` 与新增的 `usageVerification` 顶层键、verify-artifacts 逐字相同，AC10）；
  变异（临时副本）：不查执行者是否作者、patchId 用 HEAD 的 sha 代替、`current` 不看回归文档、`final_gate_accepted` 认 Codex 记录、`record` 不先校验，各自让对应用例变红，还原后全绿。
- **Task 7**：规则与文档。新文件 `references/verification-report.md`（字段表、问题代码、一份完整例子）；共享检查点规则与 `node-rules.md` 的最终验收写明新流程模块的合并前验证（`merge=auto` 要当前、通过的结论；`merge=human` 写明结论或没有结论，Q1 A）；`docs/commands.md` 加 `verification.py`；CHANGELOG「未发布」加一条。验证：快档（含读规则文件的现有回归）。
- **Checkpoint 2（gate）**：最后一次改动后重跑完整档三条并全绿；推送、开 PR、提议宿主 PR 监控；最终验收与合并合成一问；给出给 autopr-design 与 mc-coord 的拟回告（报告字段名、校验规则、命令），发出要用户同意；发 0.96.0 另取授权。
