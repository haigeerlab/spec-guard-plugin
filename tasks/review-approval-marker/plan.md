# Plan: review-approval-marker

依据 [`spec/review-approval-marker.md`](../../spec/review-approval-marker.md)（2026-10-13 用户评审通过）。本仓库评审节奏为
分开审：本 Plan 单独评审。分支 `claude/current-plugin-owner-aa5b98`，worktree
`.claude/worktrees/current-plugin-owner-aa5b98`，从 `d2506cd`（v0.56.0 验证记录合并）开出。
按发版节奏，本模块一个 PR，含 0.57.0 版本号；合并后的 tag、Release、两边宿主同步与验证记录按
`docs/release-process.md` 另走，不在本 Plan 内。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Overview

先加文本指纹入口，再把"评审状态"判定放进 `module_stage.py` 这一处，阶段提示、写标记的命令与 `verify-artifacts`
都只调用它。之后是命令与规则文本，最后是版本号和在本模块自己的 Spec、Plan 上实际用一次新命令。

## Architecture Decisions

- **判定只有一处。** 标记的解析、五种状态与 Spec 指纹比对都在 `module_stage.py`；`review_mark.py` 和
  `verify-artifacts.sh` 导入它，不各写一份。
- **指纹只有一处。** `spec-digest.py` 新增按文本求指纹的函数与 `text <file>` 子命令，复用现有 `_h`；调用方按仓库既有
  做法用 `importlib` 载入。去掉标记行这一步在 `module_stage.py` 做，`spec-digest.py` 只管对给定文本求值。
- **无标记路径不动。** 状态为 `none` 时不进入任何新分支，既有用例的期望输出不改（NEEDS_PLAN 那半句除外）。
- **hook 仍只读。** 写入只发生在 `review_mark.py --confirm`，沿用 `module_suspend.py` 的预览、原子写入与读回。
- 共同验证命令：

  ```bash
  python3 -B plugins/spec-guard/hooks/test_review_marker.py
  /bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
  /bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
  ```

## 依赖与顺序

```text
Task 1 指纹入口 ─→ Task 2 状态判定 ─┬→ Task 3 阶段提示 ─→ Task 4 下一个 gate
                                    ├→ Task 5 写标记的命令 ─→ Task 7 命令文件与路由
                                    └→ Task 6 verify-artifacts
Task 8 规则文本与文档 ─→ Task 9 版本号与自用
```

## Task List

### Task 1：文本指纹入口（先红）

`spec-digest.py` 的 `--selftest` 先加断言并确认失败：同一文本指纹稳定、改一个字符即变、长度与能力图指纹一致；
再加函数与 `text <file>` 子命令（读不了文件退出 1 并在 stderr 说明）。

- 验收：`--selftest` 通过；`scripts/test-checkers.sh` 的 digest-single-source 仍放行。
- 文件：`hooks/spec-digest.py`。

### Task 2：标记解析与评审状态（先红）

新增 `hooks/test_review_marker.py`：`none`／`pending`／`approved`／`revised`／`invalid` 各一例，含 Spec 的 approved 缺
digest、Plan 的 approved 带 digest、重复标记、正文里提到标记不算；指纹不受标记行影响、受其余任一字符影响。
再在 `module_stage.py` 加状态函数。变异：标记改为"包含即可"、指纹不排除标记行、`revised` 判成 `approved`。

- 验收：新单测全绿，三处变异各有断言变红。
- 文件：`hooks/module_stage.py`、`hooks/test_review_marker.py`。

### Task 3：阶段提示的 Review 行与建议语（先红）

`test-phase-guard.sh` 按 Spec「阶段提示」表逐行加用例并确认失败；再改 `describe`。同时加两类反向用例：
无标记项目的 NEEDS_SPEC／BUILDING／MODULE_DONE／DONE 逐字不变；非当前模块的标记不影响输出。
`combined` 节奏的那一行读 `load_config` 的 `reviewCadence`。

- 验收：phase-guard 回归全绿；既有用例除 NEEDS_PLAN 建议语外期望值未改；注入是合法 JSON。
- 文件：`hooks/module_stage.py`、`hooks/test-phase-guard.sh`。

### Task 4：下一个 gate（先红）

`test-phase-guard.sh` 加四例：有 `gate`、只有 `report`（不输出）、未标注（按 `gate`）、没有检查点或标题异常（不输出）；
另加一例：建议语不是"继续 build"时不输出。标题走现有的清洗与截断。

- 验收：phase-guard 回归全绿。
- 文件：`hooks/module_stage.py`、`hooks/test-phase-guard.sh`。

### Checkpoint 1（report）：判定与阶段提示回归全绿，ShellCheck 无警告

### Task 5：`review_mark.py`（先红）

`test_review_marker.py` 加命令用例并确认失败：预览不写文件；`--confirm` 只改标记行、其余逐字不变、重复执行结果相同；
`both` 同时写两份；四种拒绝各一例；没有标记时插在第一行标题之后。再实现脚本，复用 Task 2 的判定与现有原子写入。

- 验收：单测全绿；在临时项目里实跑一次 pending → approved → 改 Spec → 阶段提示显示已修订。
- 文件：`hooks/review_mark.py`、`hooks/test_review_marker.py`。

### Task 6：`verify-artifacts`（先红）

`test-verify-artifacts.sh` 加：标记无效失败、待审核却有勾选项警告、Spec 已修订警告、标记有效通过、检查未正常运行报
未验证、无标记项目输出逐字不变。再改 `verify-artifacts.sh`，判据从 `module_stage` 导入。

- 验收：verify-artifacts 回归全绿。
- 文件：`hooks/verify-artifacts.sh`、`hooks/test-verify-artifacts.sh`。

### Checkpoint 2（report）：三套核心回归与新单测全绿，ShellCheck 无警告

### Task 7：命令文件与 Codex 路由

新增 `commands/review-mark.md`（规范引导段；写明 `approved` 只在用户于当前对话明确批准后才写）；`spec-guard-ops` 新增
`review-mark` 一节；`docs/commands.md` 登记。command-parity、command-names、command-table 检查器兜底。

- 验收：`scripts/test-checkers.sh` 通过。
- 文件：`commands/review-mark.md`、`skills/spec-guard-ops/SKILL.md`、`docs/commands.md`。

### Task 8：规则文本、模板与文档（先红）

`test_workflow_checkpoints.py` 先加断言并确认失败：合同含「评审状态标记」一节与关键约束（"不是授权来源"、
"修订后须复审"、"连续执行到下一个 `gate`"），两份约定块模板各有一行指向它。再改文本；`docs/workflow.md` 一段，
`docs/design.md` 补一句，CHANGELOG `## [未发布]`。在本仓库运行一次 `setup-convention --replace` 更新约定块。

- 验收：`test_workflow_checkpoints.py` 与 `check-readme-sync` 通过；本仓库约定块已更新。
- 文件：`references/workflow-checkpoints.md`、两份 `templates/*-block-local.md`、`hooks/test_workflow_checkpoints.py`、
  `docs/workflow.md`、`docs/design.md`、`CHANGELOG.md`、`AGENTS.md`／`CLAUDE.md` 的约定块。

### Task 9：版本号与自用

两份清单与 marketplace 版本改为 0.57.0，README 的 `--ref`、CHANGELOG 标题随之更新。用工作区源码里的
`review_mark.py` 预览把本模块的 Spec 与 Plan 标为 `approved`，把预览结果带到 Checkpoint 3，由用户在那里确认后再写入。

- 验收：`validate.sh` 的清单一致性通过；预览输出已保存待展示。
- 文件：两份 `plugin.json`、`marketplace.json`、`README.md`、`README.en.md`、`CHANGELOG.md`。

### Checkpoint 3（gate）：模块评审

推送前在同一条 `&&` 链里跑 `validate.sh`、两套 hook 断言、新单测与 ShellCheck；提交走
`scripts/verify-and-commit.sh`，pre-push 钩子兜底。展示：全部验证结果、未验证项、Task 9 的标记预览。
批准本 Plan 即授权推送本分支并开本模块的 PR；合并由用户进行。发版后的宿主行为验证见 Spec「Testing strategy」
最后一条，属于合并后的步骤。

## Risks and Mitigations

| 风险 | 应对 |
|---|---|
| 改 `describe` 影响既有阶段输出 | 无标记用例期望值不改；依赖 `module_stage` 的 module-insert、cost-report、suspend 单测全部重跑 |
| 标记写法被误改后静默失效 | 只认完全匹配的一行，前缀相同而写法不符即 `invalid` 并报失败；变异覆盖"包含即可" |
| 指纹因换行或编码差异误判为已修订 | 指纹对去掉标记行后的原文计算，不做其他规范化；单测覆盖标记行前后空行与文件末尾换行 |
| 新增子命令被 digest-single-source 检查器当成第二份实现 | Task 1 即跑 `scripts/test-checkers.sh`；实现只在 `spec-digest.py` 内 |
| 本仓库在用的是已安装的 0.56.0，自己的阶段提示看不到新行为 | 用工作区源码直接跑 `phase-guard.sh` 与临时项目验证，不把本仓库的注入当回归结果 |

## Open Questions

- 无。
