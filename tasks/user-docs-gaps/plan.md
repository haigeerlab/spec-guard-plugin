# Plan: user-docs-gaps

<!-- spec-guard: review approved -->

依据 [`spec/user-docs-gaps.md`](../../spec/user-docs-gaps.md)（2026-11-04 用户在本会话批准：「批准」，能力图新行同时确认写入）。
分支 `claude/user-docs-gaps`（从 `origin/main` `f6b94592` 开出），worktree `distracted-morse-46ef70`。串行，在本会话做。
本模块改版本号到 0.86.4。

## Overview

按 Spec 假设 1–9 分三批改文档：先改会让人照做出错的（能力图审阅记录、`activeModule`），再改命令参数与包内断链，最后补说明性的几处。
每批改完跑快档；最后改版本号与 CHANGELOG，交最终验收。

## Architecture Decisions

1. **只改文字**：命令文件只改 `argument-hint` 与正文，不改 bash 代码块；模板只加一行 HTML 注释，复选框原样保留。
2. **`activeModule` 一个说法**：「agent 按阶段提示直接编辑 `.agent/state.json`，用户也可以自己改；没有专门写它的命令」。各处只把「提醒用户改」「建议改」
   换成这个说法，`phase.md` 表格里的阶段含义不变。
3. **包内链接**：统一写 `https://github.com/haigeerlab/spec-guard-plugin/blob/main/docs/<路径>`。hook 脚本注释不改。
4. **英文 README** 只改功能表里「关键卡点」那一格，与中文一一对应（`check-readme-sync.py` 要求）。
5. **发版**照 0.86.3：合并后核对、打 tag、打包、Release、两个宿主核对（Codex 升级后先请你在 `/hooks` 重新批准，批完我先看一眼还有没有
   标 `[!]` 的再跑 smoke）、证据收尾 PR。需求经 ecosystem-lead 转来，发版后回告它。

## Task List

### Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿

- 验证：verify-artifacts 0 失败；快档提交。

### Task 1：能力图审阅记录与 activeModule（假设 1、2）

- 文件：`templates/CAPABILITY-MAP.md`、`docs/concepts.md`、`commands/add-module.md`、`commands/phase.md`、`skills/spec-guard-ops/SKILL.md`、
  `docs/workflow.md`、`docs/troubleshooting.md`。
- 验证：`test-verify-artifacts.sh`、`test-phase-guard.sh` 通过（模板注释不改变「能力图仍是模板」等判定）；grep 不再有「提醒用户把」「建议把 `activeModule`」。

### Task 2：命令参数与包内链接（假设 3、4）

- 文件：`commands/setup-convention.md`、`commands/teardown-convention.md`、`docs/commands.md`；`commands/add-module.md`、`commands/phase.md`、
  `commands/verify-artifacts.md`、`skills/spec-guard-ops/SKILL.md`（5 处 `docs/` 引用）。
- 验证：两个 `argument-hint` 与脚本 usage 的参数一致；grep 包内 `commands/`、`skills/`、`references/` 无 `` `docs/ `` 或 `(docs/` 相对引用；快档通过。

### Task 3：补说明（假设 5–9）

- 文件：`docs/design.md`、`docs/concepts.md` 或 `docs/workflow.md`、`README.md`、`README.en.md`、`docs/commands.md`、`commands/map.md`、
  `references/workflow-checkpoints.md`、`docs/getting-started.md`。
- 验证：`check-readme-sync.py` 通过；快档通过；getting-started 里列出的 4 种标记各自链接到存在的说明处。

### Task 4：版本号与 CHANGELOG（PR 最后一个内容提交）

- 文件：两份 `plugin.json`、README 中英 `--ref`、`CHANGELOG.md`（0.86.4：文档）。
- 验证：`check-readme-sync.py`、`check-manifests.py` 通过。

### Checkpoint 1（report）：发布前完整检查

- macOS 系统 `/bin/bash` 跑 `validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 并记录主机；`evals/codex-plugin-smoke.sh --selftest`。
- 收尾 grep 三项（`docs/` 相对引用、`activeModule` 说法、参数行），结果写进 todo。

### Checkpoint 2（gate）：最终验收

- 呈现做了什么、对照 Spec 假设 1–9 的改动表、提交表、Spec 中途改动（如有）。通过即同时授权：推送、开 PR；你合并后由我核对合并并按发版步骤一次做完。

### 发版（合并后，按 Checkpoint 2 的授权）

- 核对合并、打 `v0.86.4`、打包、Release、比对 SHA-256；刷新并核对 Claude 与 Codex 安装副本；收尾扫描、证据收尾 PR；回告 ecosystem-lead。任一步失败就停下说明。

## Files likely touched

- 插件包：`templates/CAPABILITY-MAP.md`、`commands/{add-module,phase,setup-convention,teardown-convention,verify-artifacts,map}.md`、
  `skills/spec-guard-ops/SKILL.md`、`references/workflow-checkpoints.md`、两份 `plugin.json`
- 仓库：`docs/{concepts,workflow,troubleshooting,commands,design,getting-started}.md`、`README.md`、`README.en.md`、`CHANGELOG.md`；
  收尾 PR：`docs/releases/v0.86.4-*.json`
- 记录：`spec/CAPABILITY-MAP.md`（已写入）、`spec/user-docs-gaps.md`、本 Plan、`tasks/user-docs-gaps/todo.md`
- 新增依赖、锁文件改动：无。不碰 hook 脚本、`interface.json`、阶段判定。

## 风险

- **读文档的回归测试**：有回归逐字读命令文件或 README（例如约定块同步、README 同步、命令说明里的固定句子）。改前 grep 测试里引用的句子；有用例变红就在 todo 写明原因再改。
- **模板注释被当成内容**：`templates/CAPABILITY-MAP.md` 参与「能力图仍是模板」的判定和指纹底本；注释放在「审阅记录」标题下、不进 `## 目标` 段，并用回归确认。
