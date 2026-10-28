# Plan: config-text-fixes

<!-- spec-guard: review approved -->

依据 [`spec/config-text-fixes.md`](../../spec/config-text-fixes.md)（2026-10-28 用户在本会话批准：「Spec 批准；Q1 A」）。批准节奏为分开审，本 Plan 单独交审。
分支 `claude/config-text-fixes`（从 `origin/main` `153a8286` 开出），worktree `distracted-morse-46ef70`。串行，在本会话做。
本模块改版本号到 0.85.1；合并后的发版按 Spec Q1 A 的授权一次做完。

## Overview

先改三处文字，跑锁定这两个文件的测试；再改版本号与 CHANGELOG（PR 的最后一个提交）；发布前在 macOS 系统 `/bin/bash` 跑完整检查；
最终验收通过后推送、开 PR；你合并后我核对合并，再打 tag、发 Release、刷新并核对两个宿主、开收尾 PR。

## Architecture Decisions

1. **文字改动最小**：「从本版起，新版本遇到不认识的键只忽略那个键」→「0.84.0 起遇到不认识的键只忽略那个键」，与 README 并行一节的写法一致；
   frontmatter 描述在括号里补「自治档位」。不加新测试：这是措辞，不是判据；改完用 `grep` 确认插件包里 `从本版起` 为 0 次。
2. **CHANGELOG 0.85.1**：开头一句写本版范围（两个模块、插件包只改文字、interface 不变），然后「变更」（三处文字）、「文档」（#417、#418、#419、#421）、
   「维护者工具」（#420）；日期写提交当天，发版跨日时在发版时更正。
3. **发布包**按惯例从 tag 打：`git archive --prefix=spec-guard-v0.85.1/ v0.85.1 .claude-plugin plugins/spec-guard`，加 `ARTIFACT-MANIFEST.json`，
   `scripts/release-package.py validate`，`COPYFILE_DISABLE=1 tar --no-mac-metadata -czf` 打包，解开再验一次；`gh release create v0.85.1 --verify-tag`
   带上发布包与 CHANGELOG 这一节，下载回来比对 SHA-256。
4. **宿主核对挑一个这一版确实改变的事实**：0.85.1 不改阶段注入，状态码不会变，所以核对安装副本里 `commands/config.md` 的描述含「自治档位」、
   `skills/spec-guard-ops/SKILL.md` 不再含「从本版起」，再加 manifest 版本号与来源路径。Codex 另跑真实 smoke（`evals/codex-plugin-smoke.sh`，`--expected-source` 取
   `codex plugin list --json` 的 `source.path`）。
5. **证据**照 v0.85.0 的四个文件写 `docs/releases/v0.85.1-{source,package,claude,codex}.json`，每份用 `scripts/release-evidence.py validate` 校验；
   与本模块最后一个检查点的勾一起放进收尾 PR。只改这两处且 CI 通过时，按 `docs/release-process.md` 的 2026-10-13 长期授权由我合并，否则交你合并。

## Task List

### Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿

- 验证：verify-artifacts 0 失败；快档提交。

### Task 1：三处文字（AC1、AC2）

- 文件：`plugins/spec-guard/commands/config.md`、`plugins/spec-guard/skills/spec-guard-ops/SKILL.md`。
- 验证：`test_workflow_checkpoints.py` 通过；插件包里 `从本版起` 为 0 次；frontmatter 描述列出四项，与正文可配置项一致。

### Task 2：版本号与 CHANGELOG（AC3，本 PR 最后一个提交之前的内容提交）

- 文件：两份 `plugin.json`、`README.md`、`README.en.md`、`CHANGELOG.md`。
- 验证：`check-readme-sync.py`、`check-manifests.py` 通过。

### Checkpoint 1（report）：发布前完整检查（AC4）

- 在本机 macOS 用系统 `/bin/bash` 跑 `validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh`，记录主机与结果；`evals/codex-plugin-smoke.sh --selftest`；
  `git diff --stat origin/main -- plugins/spec-guard` 只含 config.md、SKILL.md、两份 plugin.json。

### Checkpoint 2（gate）：最终验收

- 呈现做了什么、AC1～AC4 证据、改动与提交表、Spec 中途改动（如有）。通过即同时授权（Spec Q1 A）：推送、开 PR；你合并后由我核对合并并按下面的发版步骤一次做完。

### 发版（合并后，按 Q1 A 授权，AC5）

- 核对 PR 已合并、`main` 指向合并提交；在合并提交上打 `v0.85.1`、推 tag；按决定 3 打包并发 Release；
- 刷新 Claude（`claude plugin marketplace update` + `claude plugin update`）与 Codex（`config.toml` 的 `ref` 改 `v0.85.1` + `codex plugin marketplace upgrade`）的安装副本，按决定 4 核对；Codex 真实 smoke；
- 跑一次 `proposal_closeout.py scan`（发布后核对的固定一步），`pending` 只列给你、不处理；
- 按决定 5 写四份证据并开收尾 PR。任一步失败就停下说明。

## Files likely touched

- 插件包：`plugins/spec-guard/commands/config.md`、`plugins/spec-guard/skills/spec-guard-ops/SKILL.md`、`plugins/spec-guard/.claude-plugin/plugin.json`、`plugins/spec-guard/.codex-plugin/plugin.json`
- 文档：`README.md`、`README.en.md`、`CHANGELOG.md`；收尾 PR：`docs/releases/v0.85.1-*.json`
- 记录：`spec/CAPABILITY-MAP.md`（已写入新行与变更记录）、`spec/config-text-fixes.md`、`tasks/config-text-fixes/plan.md`、`tasks/config-text-fixes/todo.md`
- 本机（不进仓库）：Claude 与 Codex 的插件安装副本、`~/.codex/config.toml` 的 `ref`。
- 新增依赖、锁文件改动：无。

## 风险

- **发版跨日**：CHANGELOG 日期写提交当天，发版时若跨日一并更正（放进收尾 PR）。
- **Codex 已开着的会话不换新版**：核对在新会话里做；smoke 用临时消费者项目，不在本仓库。
- **宿主刷新失败或版本不对**：按 Spec「先问」停下说明，不改用别的安装路子。
- **tag 打错提交**：打 tag 前核对 `main` 指向的就是 PR 的合并提交（发布流程「PR 节奏」第 5 条）。
