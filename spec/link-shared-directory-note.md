# Spec: link-shared-directory-note

<!-- spec-guard: review approved 3f799c881bd8 -->

## Objective

0.58.0 的会话目录指向以目录为键：`.agent/spec-guard-link.json` 写在会话目录里，在这个目录运行的每个会话都会跟随它。
发版当天的实地使用里出现了没预料到的用法：三个会话共用同一个需求文档目录，各自开发不同的仓库。其中一个建立指向后，
另外两个会收到被指向项目的阶段提示，而它们实际在做别的仓库。这比静默更糟：静默时 agent 知道没有注入、会手动核对；
错误的注入带着权威的格式出现。建立指向的预览与注入里都没有提示这一点。

本模块让这件事在建立指向之前、以及每一轮的注入里都看得见，并写清这种工作方式不该建立指向。

登记：2026-10-13 经 `/spec-guard:add-module` 插入能力图。

## Assumptions

用户已于 2026-10-13 确认：

1. 只改文字，不改指向的判定。
2. 不按会话或线程标识区分多个目标：会话标识每开一个新会话就变，用户得为每个会话重新登记，指向就失去“登记一次、之后每轮
   都有”的意义；还要为两种宿主各写一套会话标识的解析。
3. 不检测“当前目录有几个会话”：钩子无从可靠得知。
4. 多个会话共用一个目录、各做不同项目时的建议是：不建立指向，把会话开在各自的项目目录里，或显式带项目路径。
5. 版本 0.58.2，一个 PR。

## Contract

- `phase-guard.sh` 的 `Linked project` 一行在现有文字之后加一句：这个指向对在该目录运行的每一个会话生效；本会话做的若是
  别的项目，忽略这段阶段提示并显式带上自己的项目路径。其余文字、行的位置与出现条件不变。
- `project_link.py set` 的预览与写入输出多一句：指向对在该目录运行的所有会话生效；多个会话共用这个目录、各做不同项目时
  不要建立指向。`show` 在指向有效时输出同一句。退出码、拒绝条件与写入行为不变。
- `commands/link-project.md`、`spec-guard-ops` 的 link-project 一节、`docs/troubleshooting.md` 的 `Linked project` 一行：
  写清指向按目录生效，以及上面第 4 条的建议。CHANGELOG `[0.58.2]`；版本号 0.58.2。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_project_link.py
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
/bin/bash scripts/validate.sh
```

## Testing strategy

- 先改测试并确认在现有代码上失败，再改文字。
- `test-phase-guard.sh`：`Linked project` 行的逐字期望更新为带新句子的文字，仍恰好一行、位置不变。
- `test_project_link.py`：`set` 的预览与 `show`（有效时）含这句话；`show` 在没有指向或指向失效时不含；原有用例不改。
- 其余回归不改，全部通过即证明判定未变。
- 宿主行为：发版后在两份安装副本上各看一次 `Linked project` 行。这是固定文字，不另做真实会话验证。

## Boundaries

- Always：只改文字；指向的判定、拒绝条件、退出码不变。
- Ask first：按会话区分目标；让钩子检测同目录的其他会话；在共用目录时拒绝建立指向。
- Never：在 Spec、代码、测试、提交信息或 PR 中写入消费者项目的名称、路径、模块或编号。

## Success criteria

- 预览、`show` 与 `Linked project` 行三处都写明指向对同目录的所有会话生效。
- 指向的判定与其余输出逐字不变。
- 三条最小验证与 ShellCheck 全部通过。

## Open questions

- 无。
