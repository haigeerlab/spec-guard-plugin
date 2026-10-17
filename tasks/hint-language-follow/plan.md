# Plan: hint-language-follow

<!-- spec-guard: review approved -->

依据 [`spec/hint-language-follow.md`](../../spec/hint-language-follow.md)。本仓库评审节奏为分开审：Spec 已于 2026-10-18 单独批准，
本 Plan 单独交审。分支 `claude/practical-lalande-567c30`，worktree `.claude/worktrees/practical-lalande-567c30`，从 origin/main
`bcdf009`（v0.67.0 证据合并）开出。并行规划层那批改动在另一个分支，也在 Build order 末尾追加模块，合并时的冲突由那边处理。
本模块一个 PR，含 0.67.1 版本号；推送、开 PR 先问用户，合并由用户做，合并后的发版另行安排。

所需工具：无 UI 改动，不需要浏览器或电脑操作。根因对照实测要跑 `claude -p`（Task 5）。

## Overview

先定一个语言判据，再把 `session_context.py`、`module_stage.py`、`phase-guard.sh` 里的说明文字按语言二选一，英文那一份原地不动。
然后用差分脚本对 0.67.0 证明英文逐字节不变，补 verify-artifacts 一侧的回归，做一次根因对照实测，最后补文档和版本号。

## Architecture Decisions

- **判据：`module_stage.hint_language(root) -> "zh-CN" | "en"`。** 调 `load_config`（即 `project_config.load`），无问题且
  `artifactLanguage == "zh-CN"` 时返回 `zh-CN`，其余一律 `en`。命令行加 `--hint-language`，打印这个值，给 phase-guard.sh 用。
- **英文原文留在原处，旁边并排写中文。** 每处改成 `_t(lang, "<原英文>", "<中文>")` 这样的二选一；英文字面量一个字不改，
  diff 里一眼能看出英文没动。`COMMANDS` 里的说明性条目（`free-next`、`free-current`、`delegate-review` 的说明部分）加一份中文覆盖，
  命令本身不变。
- **phase-guard.sh 只多起一个 python3 进程。** 在跟随指向、`cd` 到目标项目之后、读会话事实之前，用 `--hint-language` 取一次语言；
  取不到按 `en`。shell 自己输出的几句（IDLE、MAP_ONLY、两种 UNKNOWN、两种 Linked project、压缩后提醒）用 `if` 分两份写。
  位置行由 `session_context.py` 生成，phase-guard 把语言作为参数传给它（`--lang zh-CN`），不传时与现在相同。
- **差分脚本 `evals/hint-english-diff.sh <基线 ref>`。** 用 `git archive` 取基线的 `plugins/spec-guard/hooks`，在同一组夹具上
  分别跑基线和工作区的 phase-guard，逐字节比较 `additionalContext`。它要 git 历史里的基线，不进 `validate.sh`，验收时手动跑。
  名字不以 `test-` 开头，避开测试登记检查。

### 中文措辞（关键标签）

| 英文 | 中文 |
|---|---|
| `Suggested next step:` | `建议下一步:` |
| `Location: branch … · worktree ….` + `State this location …` | ``位置: 分支 `…` · worktree `…`。请用户审阅或确认时，向用户说明这个位置。`` |
| `Capability map: present / absent / present but unreadable (…)` | `能力图: 已有 / 没有 / 已有但读不了（…）` |
| `Module specs: N / absent` | `模块 Spec: N / 没有` |
| `Current module: x (next in Build order / activeModule)` | `当前模块: x（Build order 中下一个 / activeModule）` |
| `Modules · Specs · Plans · In progress · Done · Suspended` | `模块 · Spec · Plan · 进行中 · 已完成 · 挂起` |
| `Review:` / `External review (from delegate, installed):` | `评审:` / `外部审查（delegate，已安装）:` |
| `Next gate:` | `下一个 gate:` |
| `Artifact language:` / `Review cadence:` / `Project config: invalid` | `产物语言:` / `评审节奏:` / `项目配置: 无效` |
| `Module boundary:` / `Session context:` | `模块边界:` / `会话上下文:` |
| `Suspended:` / `Paused:` / `Linked project:` | `挂起:` / `暂停:` / `关联项目:` |

句子按原意直译，不增删要求；命令、路径、代码标识原样嵌在中文句子里。

## Task List

### Task 0：提交 Spec、能力图、已批准的 Plan 与 todo

Plan 获批后用 `review_mark` 记批准，和能力图、Spec、todo 一起提交。

- 验收：`verify-and-commit.sh` 快档通过。

### Task 1：语言判据、项目配置行与位置行（先红后绿）

先写失败用例：
- `test-phase-guard.sh` 新开一段：`zh-CN` 时 IDLE 项目的注入里有 `产物语言: `zh-CN``、``位置: 分支``，没有 `Artifact language`、
  `State this location`；`zh-TW`、`zh-Hans`、`en`、无效配置时仍是英文，无效配置时仍有 `Project config: invalid`；
- `test_session_context.py`：`location_line(root, "zh-CN")` 的中文原文、分离 HEAD 的中文原文；不传语言时与现在相同。

再实现 `hint_language`、`--hint-language`、`config_lines` 的语言参数、`location_line` 的语言参数，以及 phase-guard.sh 取语言、传参。

- 验收：新用例全绿，原有用例不改、全绿。

### Task 2：`module_stage.describe` 的全部说明文字（先红后绿）

在 Task 1 那一段里给每个阶段写中文正例：NEEDS_SPEC、NEEDS_PLAN（Spec 待审）、BUILDING（Plan 已批准、有 gate；Plan 无标记、有 gate）、
MODULE_DONE（含暂停模块）、DONE（含挂起、未合并提交、全部完成）、MAP_INVALID、读不到能力图、上下文超阈值（模块边界、会话上下文）、
装了 delegate 时的外部审查行、Codex 宿主。每例断言：有 `建议下一步: ` 和对应的中文标签；标题行、`当前阶段: **X**`、命令、路径、
模块 id 原样在；整段不含 `Suggested next step`、`Capability map:` 等英文标签。确认是红的，再改 `module_stage.py`。

- 验收：新用例全绿，原有用例不改、全绿。

### Task 3：phase-guard.sh 自己输出的几句（先红后绿）

先写失败用例：`zh-CN` 时 IDLE、MAP_ONLY、读不到能力图、阶段算不出来、两种 Linked project、SessionStart 压缩后提醒，都是中文。
再改 phase-guard.sh。

- 验收：新用例全绿，原有用例不改、全绿；ShellCheck 无警告。

### Checkpoint 1（report）：英文逐字节不变的差分证明，加改坏验证

- 写 `evals/hint-english-diff.sh`，对基线 `v0.67.0` 跑一遍。夹具矩阵按 Spec 测试策略第 1 项：没有配置、`en`、`ja`、`zh-TW`、无效配置，
  乘以各个阶段、SessionStart、Codex 宿主、上下文超阈值、跟随指向。全部逐字节一致，结果（夹具数、一致数）记进 todo。
- 改坏验证：在草稿副本里把判据改成「`zh` 开头都算中文」，确认 `zh-TW` 反例变红；把一句英文模板改一个字，确认差分脚本报不一致。
  都复原。

### Task 4：verify-artifacts 一侧的正反回归

`test-verify-artifacts.sh` 补两例（已有就复用并注明）：`artifactLanguage` 为 `zh-CN` 的配置判有效、不报问题；`zh_CN` 这类不合规
标签判无效并报告。verify-artifacts 自身代码不改。

- 验收：verify-artifacts 回归全绿。

### Task 5：根因对照实测（佐证，不是硬门槛）

在临时消费者项目里，同一条中文提问（例如「这个项目现在该做什么？」），分别在英文提示（不设 `artifactLanguage`）和中文提示
（设 `zh-CN`）下，各跑 5 次 `claude -p`，统计回复是中文还是英文。

- 注入来自本分支的 phase-guard（用临时 settings 的 hook 指向工作区脚本），并想办法关掉本机已装的 0.67.0，免得注入两份；
- 尽量排除个人全局 CLAUDE.md（它要求用中文回复，会掩盖差别）。排除不掉就照实写明，结论相应降级。

结果（每组几次中文、几次英文、环境怎么隔离的）记进 todo 和 PR 描述。做不成或结果分不清，就写「未验证」。

- 验收：有一条照实的记录。

### Task 6：文档、CHANGELOG 与版本号

- `commands/phase.md`、`references/workflow-checkpoints.md` 描述提示原文处补一句：`artifactLanguage` 为 `zh-CN` 时说明文字为中文，
  标题行、阶段行、命令和标记不变；
- `commands/config.md` 和 Codex `spec-guard-ops` 的 config 一节：`artifactLanguage` 也决定阶段提示的语言；
- `docs/design.md` 提示一节补一句；
- CHANGELOG `[0.67.1]` 记一条「修复」；
- 两份 `plugin.json` 改为 0.67.1，README 中英的 `--ref` 改为 v0.67.1。

- 验收：`validate.sh` 全档通过。

### Checkpoint 2（gate）：模块验收；推送与开 PR 先问用户，合并由用户进行

在正文列出：
- 实际改动的文件，取自版本库；
- 中文模式下各阶段的注入原文（至少 NEEDS_PLAN、BUILDING、DONE 各一份）；
- 差分结果、验证结果、未验证项；
- 根因对照实测的结果，或「未验证」；
- 文档建议。

- 验收：用户验收通过；经用户同意后推送并开 PR，等用户合并。

## 影响面

- 修改：`hooks/module_stage.py`、`hooks/session_context.py`、`hooks/phase-guard.sh`、`hooks/test-phase-guard.sh`、
  `hooks/test_session_context.py`、`hooks/test-verify-artifacts.sh`、`commands/phase.md`、`commands/config.md`、
  `skills/spec-guard-ops/SKILL.md`、`references/workflow-checkpoints.md`、`docs/design.md`、CHANGELOG、两份 `plugin.json`、README 中英；
- 新增：`evals/hint-english-diff.sh`；
- 本模块的能力图行、Spec、Plan 与 todo。

## Risks and Mitigations

- **改动面大，英文悄悄变了。** 英文字面量原地不动，加上对 0.67.0 的逐字节差分和原有英文断言，两层兜底。
- **每轮多一个 python3 进程。** 只多一次很短的配置读取；Checkpoint 1 顺带记一下前后耗时。
- **中文措辞有歧义，误导 agent。** 关键标签见上表，交审时你可以改；句子直译，不增删要求。
- **对照实测被全局 CLAUDE.md 掩盖。** 尽量隔离；隔离不了就照实写，不当结论用。

## Open Questions

- 无。
