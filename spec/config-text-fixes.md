# Spec: config-text-fixes

<!-- spec-guard: review approved 172671e734c2 -->

## 目标

「0.85.1 文档收尾」需求的第二个、也是最后一个模块：修插件包里 config 说明的过时文字，并发 0.85.1，把 0.85.0 之后合并进 `main` 的
文档改进（#417～#421）一并作为一个版本发出。

要改的文字（2026-10-28 核对）：

1. `plugins/spec-guard/commands/config.md` 第 62 行 `moduleConcurrency` 一行：「从本版起，新版本遇到不认识的键只忽略那个键」——
   「本版」已说不清是哪一版；逐键容错是 0.84.0（config-per-key）开始的。
2. `plugins/spec-guard/skills/spec-guard-ops/SKILL.md` 第 189 行：Codex 用的同一句，同一个问题（需求总结时只提到 config.md，核对时发现这一处）。
3. `plugins/spec-guard/commands/config.md` 的 frontmatter 描述「（产物语言、批准节奏、多模块并行开关）」漏了 0.85.0 新增的自治档位；
   这段描述就是宿主命令列表里显示的那句。

给谁用：读 config 说明的 agent，以及在命令列表里看描述的用户。

登记：需求来自用户本人（2026-10-28，确认需求总结「说完了」），不需要回告。

## 边界

**总是做**

- 改完跑 `test_workflow_checkpoints.py`（它锁定 config.md 与 SKILL.md 的「0.67.1 及更早」「不控制协调会话」「`coordinator up`」等说法），确认不受影响。
- 发版前按 `docs/release-process.md`「发布前」：manifest 两份版本一致、README 中英 `--ref` 同步（`check-readme-sync.py`）、写 CHANGELOG、
  在 macOS 用系统 `/bin/bash` 跑三条最小验证并记录主机与结果；改了 Codex 用的技能，跑 `evals/codex-plugin-smoke.sh --selftest`。
- 发版后按「发布」「发布后核对」做，证据写进 `docs/releases/v0.85.1-*.json`（照 v0.85.0 的四个文件：source、package、claude、codex）。

**先问**

- 发版的任一步失败（tag 已存在、Release 建不出来、宿主装不上新版、smoke 不通过）时，停下说明，不自行重试别的路子。
- 发现要改插件行为才能对齐时。

**不做**

- 不改插件行为，不顺手改 config 说明的其他段落。
- `docs/commands.md`、`docs/getting-started.md` 里的「0.85.0」是有意义的版本（「团队都升级到 0.85.0 后再设」「输出取自 0.85.0」），不改。

## 要你确认的假设

1. **补丁版本 0.85.1**：插件包里只改文字，行为不变。
2. **CHANGELOG 0.85.1 一节**写插件包里这三处，再加「文档」一节概括 0.85.0 之后合进 `main` 的文档改进（#417 对齐现状、#418 上手文档、
   #419 新手复测修正、#421 选用指引场景）与「维护者工具」一节（#420 快档跑文档回归）；不写升级须知（没有行为变化）。
3. **README 的 Codex `--ref` 改成 `v0.85.1`**；Claude 的安装命令不带版本，不用改。
4. 分支 `claude/config-text-fixes`，从 #421 合并后的 `main`（`153a8286`）开出；一个 PR，版本号改动放在最后一个提交（发布流程「PR 节奏」第 1 条）。

## 验收标准

- AC1：`config.md` 与 `SKILL.md` 的 `moduleConcurrency` 一行不再出现「从本版起」，改为「0.84.0 起」；插件包里 `从本版起` 出现 0 次。
- AC2：`config.md` frontmatter 描述列出自治档位（例如「产物语言、批准节奏、多模块并行开关、自治档位」），与正文可配置项一致。
- AC3：两份 `plugin.json` 为 `0.85.1`；README 中英 `--ref v0.85.1`；`check-readme-sync.py`、`check-manifests.py` 通过；CHANGELOG 有 `## [0.85.1] - <日期>` 一节（按假设 2）。
- AC4：`validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 在 macOS 系统 `/bin/bash` 上通过并记录主机；`evals/codex-plugin-smoke.sh --selftest` 通过。
- AC5（合并后）：在合并提交上打 `v0.85.1` tag、发 GitHub Release；Claude 与 Codex 的安装副本刷新后版本为 0.85.1、来源路径正确；
  四份发布证据与本模块最后一个检查点的勾在一个收尾 PR 里提交。

## 未决问题

- **Q1：合并后的发版几步，要不要你逐步点头？** 打 tag、发 Release 是远端写入，而且不可逆。
  - A（推荐）：你批准本模块最终验收时，同时授权「合并后按发布流程一次做完」：我先自己核对合并状态（PR 已合并、`main` 指向合并提交），然后打 tag、
    发 Release、刷新并核对两个宿主、开收尾 PR；只在某一步失败时停下。收尾 PR 只改 `docs/releases/` 和 todo 末行、CI 通过时，按 2026-10-13 的长期授权可由我合并，否则交你合并。
  - B：合并后打 tag、发 Release、开收尾 PR 每一步都单独问你。

**已定（2026-10-28，用户）：Q1 A。**

## 文档建议

README 中英只改 `--ref`（AC3）；CHANGELOG 写 0.85.1 一节。项目没有文档基线。

## 变更记录
