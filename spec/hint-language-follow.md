# Spec: hint-language-follow

<!-- spec-guard: review approved b9854eb5a8b0 -->

## Objective

项目在 `.agent/config.json` 设了 `"artifactLanguage": "zh-CN"`，phase-guard 在 UserPromptSubmit / SessionStart 注入的阶段提示里，
除了「当前阶段」标签外，说明文字都是固定英文：`Location: …`、`Suggested next step: …`、`Review: …`、
`External review (from delegate, installed): …`、`Next gate: …`、`Artifact language: …` 等。用户反馈：设了中文的项目里，Claude 会话
好几次直接用英文回复，怀疑是每条消息后面都跟着这段英文提示造成的。

本模块让提示的说明文字跟随 `artifactLanguage`：设为 `zh-CN` 时用简体中文；未设、设为英文或其他语言时，输出与 0.67.0 逐字节相同。

**根因目前只是推测。**「英文提示把回复语言带偏」没有实测证据；回复语言还受全局 CLAUDE.md、用户提问语言、会话里已有内容等影响。
验收时做一次对照实测（见 Testing strategy 第 5 项）来佐证；做不成就在验收记录里照实写「未验证」，不把推测写成结论。
即使对照实测没看到差别，中文项目里的提示用中文本身也合理，本模块不以证实根因为前提。

登记：2026-10-18 经 `/spec-guard:add-module` 插入能力图。来源：用户本人，经 decision-inbox 负责人会话转报（2026-10-18），按 bug 处理。
版本按补丁版 0.67.1。

## Assumptions

1. **直接跟随 `artifactLanguage`，不另加 `hintLanguage`。** `artifactLanguage` 已经表达了「这个项目用什么语言写东西」，另设一个键
   要用户多配一处，两个值不一致时也说不清该听谁的。代价是：想要中文 Spec、英文提示的项目做不到。目前没有人提过这种需要；
   真有了再加 `hintLanguage`，不设时沿用 `artifactLanguage`，可以向后兼容地补上。
2. **只做简体中文和英文。** 只有值恰好是 `zh-CN`（区分大小写，与 project-config 的标签校验一致）时出中文；
   `en`、`en-US`、`ja`、`zh-TW`、`zh-Hans` 等其他合法值一律出英文，和 0.67.0 一样。`zh-TW` 不出简体，免得给繁体项目注入简体；
   以后要支持更多语言，再按需加一份对照。
3. **语言只从 `project_config.load` 取。** 配置文件无效（不是 JSON、标签不合规等）时整份不生效，提示出英文，并照旧带
   `Project config: invalid (…)` 那一行，与 verify-artifacts 判无效同一判据。跟随指向（linked project）时用目标项目的配置。
4. **保持原样、不翻译的部分**（实测依据见下面「依赖英文原文的地方」）：
   - 标题行 `## spec-guard local workflow`：`evals/codex-plugin-smoke.sh`、`scripts/self_report.py` 靠它识别注入；
   - `当前阶段: **<代码>**` 这一行（本来就是中文）：smoke、`evals/module-namespace.sh`、`project_link.py`、`self_report.py` 靠它取阶段；
   - 阶段代码（`IDLE`、`MAP_ONLY`、`NEEDS_SPEC`、`NEEDS_PLAN`、`BUILDING`、`MODULE_DONE`、`DONE`、`UNKNOWN`、`MAP_INVALID`）；
   - 命令、技能名、路径、模块 id、分支名、文件名、标记行（`<!-- spec-guard: … -->`）、小节名
     `## 外部审查意见` / `## External review`、todo 里的 `gate` / `report`、`activeModule` 这类键名；
   - 来自仓库内容、经清洗后引用的片段（能力图诊断原文等），照旧原样引用。
5. **建议前缀用 `建议下一步: `。** 旧版提示用过这个写法，`scripts/self_report.py` 已同时认 `Suggested next step:` 和 `建议下一步:`，
   不用改它。其他字段标签也沿用「当前阶段: 」的写法：中文标签加半角冒号和空格。
6. **`Location:` 那一行也翻。** 实测（见下）没有别的插件或检查按 `Location:` / `State this location` 原文匹配，只有本仓库自己的测试和
   文档。中文时写成 ``位置: 分支 `<分支>` · worktree `<目录>`。请用户审阅或确认时，向用户说明这个位置。``
   （分离 HEAD 时 ``分离于 `<短 sha>` ``）。
7. **不顺带加「请用中文回复」之类的新指令。** `artifactLanguage` 说的是产物语言，不是对话语言；本模块只换提示自身的语言，
   不新增行为。
8. 已经是中文、与语言无关的诊断（缺 python3、python3 跑不起来、指向文件失效、`activeModule 不是有效的 module id`）保持不变；
   这几句在英文模式下本来就是中文，改了就破坏逐字节相同。

### 依赖英文原文的地方（2026-10-18 实测）

在 `~/Documents/haigeerlab` 下除本仓库外的所有项目（agent-relay、delegate-plugin、decision-inbox、module-crew、session-protocol、
tier-guard 等）里搜 `Suggested next step`、`State this location`、`Location: `、`Current module`、`Capability map: `、`Next gate`、
`External review (from`、`Artifact language`、`Module boundary`、`Session context:`、`spec-guard local workflow`：
命中的只有存档的证据文件（`docs/verification/*.json`、`.agent/acceptance/**`、`docs/acceptance/*.md`），没有代码或检查按原文匹配。
本仓库里按原文匹配的是：上面第 4 条列出的标题行和阶段行使用方，以及 `test-phase-guard.sh`、`test_session_context.py` 等测试和
`commands/phase.md` 等文档。测试里的英文断言在英文模式下继续成立，中文模式另加断言。

## Contract

### 语言判定

- 一个判据：`project_config.load(root)` 无问题且 `artifactLanguage == "zh-CN"` 时为中文，否则为英文。放在 `module_stage.py`
  （或它导入的一个小模块）里，phase-guard.sh 自己输出的几句也向它取，不在 bash 里另写判据。
- 读配置失败、python3 取语言失败时按英文。

### 翻译范围（中文模式）

phase-guard 注入的全部说明文字，包括：
- `phase-guard.sh`：IDLE、MAP_ONLY、读不到能力图（UNKNOWN）、模块阶段算不出来（UNKNOWN）四种输出的字段与建议；
  `Linked project: …` 两种说明；压缩后的核对提醒（SessionStart）；
- `session_context.py`：位置行；
- `module_stage.py`：字段行（`Capability map`、`Current module`、计数行、`Suspended`、`Paused`、`Plan without todo`、
  `activeModule …` 几句英文说明、`This branch has N commit(s)…`）、项目配置行（`Artifact language`、`Review cadence`、
  `Project config: invalid`）、`Module boundary` / `Session context` 两行及 `COMMANDS` 里的 `free-next` / `free-current` 说明、
  `Review` 行与随之替换的建议、`External review` 行、`Next gate` 行、各阶段的 `Suggested next step`、
  MAP_INVALID 与读不到能力图两句。

英文模式下以上每一句与 0.67.0 逐字节相同。

### 文档

- `commands/phase.md`、`references/workflow-checkpoints.md` 里描述提示原文的地方补一句：`artifactLanguage` 为 `zh-CN` 时说明文字为中文，
  标题行、阶段行、命令和标记不变。
- `commands/config.md`（及 Codex 的 `spec-guard-ops` 对应一节）说明 `artifactLanguage` 也决定阶段提示的语言。
- `docs/design.md` 提示一节补一句；CHANGELOG 记一条「修复」。
- 版本 0.67.1：两份 `plugin.json`、CHANGELOG、README 中英的 `--ref`。

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 -B plugins/spec-guard/hooks/test_session_context.py
```

## Testing strategy

1. **英文不变（回归证明）。** 写一个差分脚本：同一组夹具项目分别跑 0.67.0（`git archive` 出基线 hooks）和新代码，逐字节比较
   `additionalContext`。夹具覆盖：没有配置、`en`、`ja`、`zh-TW`、无效配置 × IDLE、MAP_ONLY、NEEDS_SPEC、NEEDS_PLAN（Spec 待审）、
   BUILDING（Plan 已批准、有下一个 gate）、MODULE_DONE、DONE（含挂起、有未合并提交）、MAP_INVALID、读不到能力图、跟随指向、
   SessionStart、Codex 宿主、上下文超阈值。验收时跑一次，结果记进 todo；现有 `test-phase-guard.sh` 的英文断言全部不改、保持通过。
2. **中文正例（`test-phase-guard.sh`）。** `zh-CN` 时每个阶段：出现 `建议下一步: `、中文字段标签；标题行、`当前阶段: **X**`、命令、
   路径、模块 id、标记原样在；整段不含 `Suggested next step`、`Capability map:` 等英文标签。
3. **中文反例。** `zh-TW`、`zh-Hans`、`en`、无效配置 → 英文；无效配置时仍有 `Project config: invalid`。
4. **verify-artifacts 一侧（`test-verify-artifacts.sh`）。** 共享判据仍是 `project_config.load`：`zh-CN` 配置判有效、不报问题；
   不合规标签判无效并报告——与阶段提示在同一份配置下出英文 + invalid 行对得上。verify-artifacts 自身输出不变。
5. **根因对照实测（佐证，不是硬门槛）。** 在临时消费者项目里（`evals/codex-plugin-smoke.sh` 同类做法，`--plugin-dir` 指向本分支），
   用同一条中文提问，分别在英文提示（不设 `artifactLanguage`）和中文提示（设 `zh-CN`）下各跑若干次 `claude -p`，统计回复语言。
   为排除个人全局配置的影响，尽量在不加载全局 CLAUDE.md 的环境里跑。结果照实记录；没跑或结果不清楚就写「未验证」。
6. **改坏验证。** 在草稿副本里把判据改成「`zh` 开头都算中文」，确认 `zh-TW` 反例变红；把某句英文模板改一个字，确认差分脚本变红。

## Boundaries

- Always：英文模式逐字节不变；只有说明文字随语言变，命令、路径、阶段代码、标记、标题行不变；判据只有一处。
- Ask first：增加 `hintLanguage`；支持 `zh-CN` 以外的语言；翻译 verify-artifacts 或其他命令的输出；在提示里加回复语言指令。
- Never：改标题行或 `当前阶段: **X**` 的格式；因为翻译让 hook 多读文件以外的东西（只多读已经在读的 `.agent/config.json`）；
  把对照实测的推测写成结论。

## Success criteria

1. `artifactLanguage` 为 `zh-CN` 的项目，每个阶段的注入里说明文字都是中文，标题行、阶段行、命令、路径、标记原样保留。
2. 未设、设为英文或其他语言、配置无效时，注入与 0.67.0 逐字节相同（差分脚本全部一致，现有回归不改且通过）。
3. smoke、`self_report.py`、`project_link.py` 在中文模式下仍能识别注入和阶段。
4. 根因对照实测有结果就写明结果，没有就写「未验证」。
