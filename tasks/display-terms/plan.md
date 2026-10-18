# Plan: display-terms

<!-- spec-guard: review approved -->

依据 [`spec/display-terms.md`](../../spec/display-terms.md)。本项目按分开审：Spec 已于 2026-10-19 批准，本 Plan 单独交审。
分支 `claude/display-terms`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 main 的 `c240046`（#368 合并）开出。
本模块一个 PR，含 0.75.0 版本号；按用户决定，发版等这一批做完、冻结前一次发。

所需工具：无 UI 改动。

## Overview

先加防回退断言（列出全部命中，作为待改清单），再按文件类别逐类改：hook 输出 → 规则与约定块 → 命令与 skill → README 与
docs。每类改完跑对应测试再提交，最后 CHANGELOG 与版本号。全程按 Spec 的对照表逐处改，不做全局字面替换。

## Architecture Decisions

- **防回退断言写进 `test_workflow_checkpoints.py`**：那里已有"规则可被找到"的同类断言；文件清单写死在测试里：
  `plugins/spec-guard/{commands,skills,templates,references}` 下全部 `.md`，`hooks/` 下非测试的 `.py` 与 `.sh`，`README.md`、
  `README.en.md`、`docs/*.md`（不含子目录）、`AGENTS.md`。测试文件与历史目录不在清单里。
- **节标题改名与引用一起改**：`## 评审节奏` → `## 批准节奏`、`## 评审状态标记` → `## 批准标记`；测试里按标题取节的
  `section()` 调用同步改。
- **英文分支与接口不动**：`module_stage.py` 只改中文串；`map_view.py` 只改表格用词，JSON 不变。

## Task List

### Task 1：防回退断言（先红）

新增 `test_user_facing_text_uses_the_shared_terms`：扫描上述清单，"评审""审核""审批"都不出现；失败信息列出文件与行号。

- 验收：在旧文字上失败，列出的命中即待改清单（约一百多处）。
- 验证：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py`。
- 文件：`hooks/test_workflow_checkpoints.py`。

### Task 2：hook 输出

`module_stage.py`（阶段提示的"- 评审:"行、等待用户审核、能力图评审、Proposal 提示）、`map_view.py`（表头与 `REVIEW_WORDS`）、
`verify-artifacts.sh`（评审标记各条）、`module-insert.py`、`proposal_promotion_proof.py`；对应测试（`test-phase-guard.sh`、
`test-verify-artifacts.sh`、`test_map_view.py`、`test_module_insert.py`、`test-setup-teardown.sh`）的中文断言改为新文字。

- 验收：这些测试全绿；英文分支的断言一条不改；`test_map_view.py` 的 JSON 期望不改。
- 验证：`verify-and-commit.sh` 全档（暂存了 `.sh`，加 ShellCheck）。
- 文件：上述 hook 与测试。

### Checkpoint 1（report）：hook 输出与回归全绿

### Task 3：共享规则、references 与约定块

`references/workflow-checkpoints.md`（含两节标题）与其他 references、两份约定块模板、`docs/convention-block.md`、`AGENTS.md`；
`test_workflow_checkpoints.py` 里按旧标题取节的地方同步。

- 验收：规则断言全绿；`validate.sh --quick` 的约定块一致性通过。
- 验证：`verify-and-commit.sh`。
- 文件：上述规则、模板、文档与测试。

### Task 4：命令、skill、README 与 docs

`commands/*.md`（含 frontmatter description）、`skills/*/SKILL.md`、`templates/CAPABILITY-MAP.md`、中英 README 的中文部分、`docs/*.md`。

- 验收：Task 1 的防回退断言转绿；`validate.sh` 通过。
- 验证：`verify-and-commit.sh`。
- 文件：上述命令、skill、模板、README、docs。

### Task 5：CHANGELOG 与版本号

CHANGELOG 新增 `[0.75.0]`，写明改了哪些叫法、哪些不变；两份 `plugin.json` 改为 0.75.0，中英 README 的 `--ref` 改为 v0.75.0。

- 验收与验证：`verify-and-commit.sh` 全档。
- 文件：`CHANGELOG.md`、两份 `plugin.json`、两份 README。

### Checkpoint 2（gate）：最终验收

按 AC1–AC4 逐条给证据，附对照表里每类改法的实际例子，展示未验证项、实际改动的文件清单与文档建议。推送与开 PR 在此由用户确认，
合并由用户进行。

## Risks

- **改动面大、容易漏改或改错意思**：Task 1 的断言兜住"漏改"；"改错意思"靠逐处按对照表判断，最终验收列出每类的实际例子供用户抽查。
- **测试断言与产品文字两边对不上**：每类改完立刻跑对应测试，不攒到最后。
- **本仓库 `CLAUDE.md` 有 1 处"评审"**：它是维护者说明，不在 Spec 的范围里，本模块不改，最终验收时说明。
