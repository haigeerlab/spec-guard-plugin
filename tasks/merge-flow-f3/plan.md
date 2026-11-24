# Plan: merge-flow-f3

<!-- spec-guard: review approved -->

Spec：[spec/merge-flow-f3.md](../../spec/merge-flow-f3.md)（2026-11-24 批准）。

## 架构决定

- **只在一处写全，另两处引用**：`plugins/spec-guard/references/workflow-checkpoints.md`「Plan 检查点分级」一节第 137 行把旧句
  「合并永远由用户进行，任何 Plan 都不能授权 agent 合并。」整句换成 Spec 假设 1 的新句；「批准节奏」第 152 行改成
  「两种节奏下人工闸门都在，合并永远由用户在对话里决定（见「Plan 检查点分级」）。」；「协调会话的批准与合并」第 474 行只把引号里的
  「合并永远由用户进行」换成「合并永远由用户在对话里决定」，三个条件一个字不动。
- **回归锁新句**：`test_workflow_checkpoints.py` 第 133 行的短语改为「合并永远由用户在对话里决定」；`CoordinatorApprovalTests.ORIGINALS`
  第 856、857 行换成新的两句；新增一个用例：全文不含「合并永远由用户进行」，第 137 行所在一节含「明确说『合并』」「任何 Plan 都不能代替用户这句话」
  「核实已合并」「必需检查」「`gh pr merge --auto`」。
- **本仓库文档**：
  - `docs/release-process.md` 第 4 条：「**合并由用户在对话里决定**：agent 问『可以合并吗』，用户回『合并』后，agent 执行
    `gh pr merge --auto --squash`，GitHub 等必需检查 `CI required` 通过后合并；agent 核实已合并（第 5 条）再告诉用户合并提交。」
    其后「下面一种情况除外……」的长期授权原文保留，「照常交用户合并」改为「照常按上面问用户」。
  - `spec/usage/dev-flow-v2.md` 第 58 行：「人合，或 ⑦ 通过后自动合」→「用户在对话里说『合并』后会话执行（GitHub `--auto`），或 ⑦ 通过后自动合」。
  - `README.md` 第 223 行：「远端合并始终由你来做」→「远端合并始终由你在对话里决定，你说『合并』后由会话执行」。
- **版本**：两份清单 `0.94.0` → `0.95.0`；CHANGELOG `[未发布]` 的「变更」下加一条本模块。发版不在本 PR。

## 任务

- **Task 0**：提交本 Plan 与 todo。验证：`validate.sh --quick`。
- **Task 1**：共享规则与回归（C1、C2）。先改 `test_workflow_checkpoints.py` 跑红（旧规则下新断言失败），再改规则三处跑绿。
  验证：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py`；`git diff` 只动三行规则。
- **Task 2**：本仓库文档（C3）。验证：`validate.sh`。
- **Task 3**：版本与 CHANGELOG（C4）。验证：`validate.sh`（含清单一致性）。

## 会改哪些文件

- 新增：`tasks/merge-flow-f3/{plan,todo}.md`。
- 修改：`plugins/spec-guard/references/workflow-checkpoints.md`、`plugins/spec-guard/hooks/test_workflow_checkpoints.py`、`docs/release-process.md`、
  `spec/usage/dev-flow-v2.md`、`README.md`、`plugins/spec-guard/.claude-plugin/plugin.json`、`plugins/spec-guard/.codex-plugin/plugin.json`、`CHANGELOG.md`。

## 风险

- **别处锁着旧句**：已 grep 全仓库，只有上面三处规则和测试三处；实现时再 grep 一次 `合并永远由用户进行`，有漏网就停下说明。
- **消费者项目没开自动合并**：新句写了「否则等必需检查全部通过后再合并」；没有在这样的项目上实测，验收时如实说明。

## 检查点

- Checkpoint 1（report）：本机证据——`validate.sh`、phase-guard、verify-artifacts 的退出码与末行；变异：规则第 137 行改回旧句 → 回归变红；
  删掉「任何 Plan 都不能代替用户这句话」→ 回归变红。记进 todo。
- Checkpoint 2（gate）：本 Plan 获批即授权推送并开模块 PR；看 PR 上 `CI required`。然后交最终验收（AC1～AC5 证据），
  验收通过后按新规则问「可以合并吗」，你回「合并」再执行 `gh pr merge --auto --squash`，核实后告诉你合并提交；之后回复 ecosystem-lead 与 mc-coord（AC6）。

## 预先声明

- 公共路径：无
- 外部依赖：无
- 质量与工作区配置：无
- 补丁：无

## 未决问题

- 无。
