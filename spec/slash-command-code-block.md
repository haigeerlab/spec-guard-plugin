# Spec: slash-command-code-block

<!-- spec-guard: review approved c350d655bfa7 -->

## Objective

阶段提示在模块完成或上下文很大时，让 agent 给用户一条可直接复制的 `/compact` 或 `/clear`，并要求“单独放进一个代码块”
（`codex-command-wording`，0.56.0）。2026-10-13 一位用户在 Claude 桌面应用里遇到：agent 把这条命令放进了标着 `bash` 的代码块，
桌面应用给带 shell 语言标签的代码块加“运行”按钮，用户点了之后这行字被送进终端执行，报 `no such file or directory: /compact`，
上下文没有被压缩。

原因是两条指令叠加：提示只说“放进单独的代码块”，没有说这是斜杠命令、也没有规定代码块的语言；而宿主要求 agent 把给用户的
shell 命令放进带 shell 语言标签的代码块。agent 很自然地套用了后者。报告方实测：同样的内容改用 `text` 标签后，桌面应用只显示
复制按钮。

本模块只改提示文字：写明这是发到对话输入框的斜杠命令，以及代码块该怎么标。不改提示出现的时机、阈值与其余内容。

登记：2026-10-13 经 `/spec-guard:add-module` 插入能力图。与 `review-marker-legacy-projects` 一起随 0.57.1 发出。

## Assumptions

用户已于 2026-10-13 确认：

1. 要改的是 `module_stage.py` 里的三句：Claude 的模块完成行（`free-next`）、Claude 的上下文行（`free-current`）、Codex 两行
   共用的那一句（`CODEX_COMPACT`）。没有别处要求 agent 把斜杠命令放进代码块。
2. 加的内容三点：这是输入到对话输入框的斜杠命令，不是 shell 命令；代码块不带语言标签或标 `text`，不标 `bash`、`sh`、`zsh`、
   `shell`；用一句话告诉用户发到消息输入框，不要在终端里运行。
3. Codex 的写法加同样的话。Codex 桌面应用里只含 `/compact` 的无标签代码块可以直接点按运行（2026-10-10 用户实测），无标签写法
   不影响它；带 shell 标签在 Codex 里的表现没有实测过，统一禁止。
4. 行内出现的斜杠命令（`/spec-guard:verify-artifacts`、“continue `/build`” 等）不改：它们不是独立代码块，宿主不会给运行按钮。
5. 不改时机：提示每轮出现、阈值、无人值守时不出现等都不变。“未压缩成功就每轮重复”是另一个设计决定，不在本模块。
6. 宿主判断不了时的那句（`FREE_BOUNDARY` 与 `free-current` 的默认写法）不改：它只要求用一句话说明，不要求代码块。
7. 版本 0.57.1 由本模块的 PR 带，CHANGELOG 把两个模块写在同一版下。
8. Claude 桌面应用里“没有运行按钮”这一点只能由用户查看（电脑操作不能用于 Claude 桌面应用自身）；agent 先在真实会话里确认
   输出的代码块不带 shell 语言标签。

## Contract

三句提示在现有文字的“in its own code block”之后各加一段固定说明，意思为：

> 这是发到对话消息输入框的斜杠命令，不是 shell 命令；代码块不带语言标签或标 `text`，不要标 `bash`、`sh`、`zsh`、`shell`；
> 并用一句话告诉用户把它发到消息输入框，不要在终端里运行。

- 说明只写一份常量，三句共用；Claude 与 Codex 的其余文字（Claude 带填好的聚焦说明、Codex 的 `/compact` 不带参数）不变。
- 宿主判断不了时的输出逐字不变。
- 行的数量、位置、出现条件不变：模块完成行仍恰好一行且在 `Suggested next step` 之前。
- `references/workflow-checkpoints.md`「按需求批量前置审」里讲 80% 提示的那句补半句：给出 `/compact` 或 `/clear` 时放进不带
  shell 语言标签的代码块，并说明是发到消息输入框。
- `docs/troubleshooting.md` 加一行：点了代码块的“运行”、终端报找不到 `/compact` 时的原因与处理。CHANGELOG `[0.57.1]`。
- 版本号 0.57.1：两份 manifest、中英 README 的 `--ref`、CHANGELOG 标题。

## Commands

```text
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
/bin/bash scripts/validate.sh
```

## Testing strategy

- 先改测试并确认在现有代码上失败，再改文字。
- `test-phase-guard.sh`：Claude 的模块完成行与上下文行、Codex 的两行都含这段说明（断言“不是 shell 命令”“不标 shell 语言”
  “发到消息输入框”三个要点的英文原文）；宿主判断不了时两行逐字不变；模块完成行仍恰好一行且位置不变。现有硬编码整行的
  期望值随之更新。
- `test_workflow_checkpoints.py`：共享检查点规则里那半句在场。
- 自观测报告与 Codex smoke 判决器若匹配这些行的开头，确认仍能识别（跑 `validate.sh`）。
- 宿主行为：发版后在两边各一次真实会话里触发模块完成行，确认 agent 输出的代码块不带 shell 语言标签；Claude 桌面应用里
  是否还出现“运行”按钮由用户查看，记为用户确认或未验证，不由 agent 代答。

## Boundaries

- Always：只改提示文字与对应的测试、文档；说明只有一份常量；宿主判断不了时逐字不变。
- Ask first：改提示出现的时机或阈值；改行内出现的斜杠命令的写法；让提示不再要求代码块。
- Never：把静态断言或 `claude -p` 的结果说成桌面应用的显示验收；在 Spec、代码、测试、提交信息或 PR 中写入消费者项目的
  名称、模块或编号。

## Success criteria

- 两边宿主的模块完成行与上下文行都写明：斜杠命令、不是 shell 命令、代码块不带 shell 语言标签、发到消息输入框。
- 宿主判断不了时的输出、各行的数量与出现条件不变。
- 真实会话里 agent 给出的 `/compact` 代码块不带 shell 语言标签。
- 三条最小验证与 ShellCheck 全部通过；0.57.1 的 CHANGELOG 同时写明两个模块。

## Open questions

- 无。
