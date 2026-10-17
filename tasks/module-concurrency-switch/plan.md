# Plan: module-concurrency-switch

<!-- spec-guard: review approved -->

依据 [`spec/module-concurrency-switch.md`](../../spec/module-concurrency-switch.md)。本仓库评审节奏为分开审：Spec 已于 2026-10-18
单独批准（用户决定不做外部审查，Spec 里已写拒绝标记），本 Plan 单独交审。分支 `claude/module-concurrency`，worktree
`.claude/worktrees/current-plugin-owner-aa5b98`，从 `origin/main` `bcdf009` 开出。

按用户确认的发版节奏，多模块并行规划层的 7 个模块在这一条分支上依次完成、合成一个 PR，最后统一升到 0.68.0。本模块不改版本号，
不推送、不开 PR；模块验收后直接进入下一个模块 `concurrency-assessment`。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Overview

先给 `project_config.py` 加这个键和读取函数（单元测试先红后绿），再用阶段提示与 verify-artifacts 的回归证明 off、未设置、on
三种情况输出不变，最后同步命令说明、Codex 技能、设计文档与 CHANGELOG。

## Architecture Decisions

- **只动 `VALIDATORS` 和 `DEFAULTS` 两张表。** `load`、`summary`、`render`、`set`／`unset` 都是遍历这两张表实现的，新键自动获得
  校验、汇总、规范化写入与固定错误代码，不需要新分支逻辑。
- **新函数 `module_concurrency(root)` 放在 `project_config.py`，紧挨 `load`。** 只做一件事：`load` 无问题且值为 `"on"` 时
  返回 True。后续模块统一调用它。
- **`config_lines` 不改代码。** 它只对 `artifactLanguage` 和 `reviewCadence == "combined"` 出行，新键天然不注入；用回归测试锁住，
  不加注释性的分支。
- **`commands/config.md` 的 description 会改动 skill 列表里的一行文字。** 这属于 config 命令自身的说明，在 Spec 假设 4 的例外范围内。

## Task List

### Task 0：提交已批准的 Plan 与 todo

Plan 获批后用 `review_mark` 记批准，和 todo 一起提交。

- 验收：`verify-and-commit.sh` 快档通过。

### Task 1：配置键与读取函数（先红后绿）

先在 `test_project_config.py` 写失败用例并确认是红的：
- `on`、`off` 通过校验；`true`、`"ON"`、`1`、`""` 报 `moduleConcurrency-invalid`，整份配置不生效；
- `module_concurrency`：文件不存在、`{"version": 1}`、`off`、无效文件（`on` 加一个未知键）都是 False，有效的 `on` 是 True；
- `summary`：未设置时值 `off`、来源 `default`；设置后来源 `.agent/config.json`；
- `set --key moduleConcurrency --value on` 预览不写文件、`--confirm` 写入并读回一致；`unset` 后汇总回到默认。

再改 `VALIDATORS`、`DEFAULTS`，加 `module_concurrency`。

- 验收：新旧用例全绿；兼容 Python 3.9（`test_python_compat` 通过）。

### Task 2：off 与 on 输出不变的回归（先写断言，预期直接绿）

- `test-phase-guard.sh` project-config 段：同一夹具分别用无配置文件、`{"version": 1}`、`moduleConcurrency: off`、
  `moduleConcurrency: on` 跑阶段提示，四份输出逐字节相同；`on` 与 `artifactLanguage` 同设时只多出语言那一行。
- `test-verify-artifacts.sh`：含 `moduleConcurrency: on` 的有效配置不报问题；`moduleConcurrency: "yes"` 报
  `moduleConcurrency-invalid`。

这些断言在 Task 1 之后应直接是绿的（Task 1 之前 `on` 会因 `unknown-key` 变成 invalid 行，可以先在 Task 1 前跑一次确认断言会红）。

- 验收：两套回归全绿，原有用例不变。

### Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告，并做两次改坏验证

- 让 `module_concurrency` 在未设置时也返回 True，确认「未设置为 False」一例变红；
- 让 `config_lines` 在 `on` 时多出一行，确认「四份逐字节相同」一例变红。

两处都复原，结果记进 todo。

### Task 3：命令说明、Codex 技能、设计文档与 CHANGELOG

- `commands/config.md`：description 加「多模块并行开关」；「可配置项」表加一行（取值 `off`／`on`、默认 `off`、作用：打开规划层的并行
  规则，本身不开会话、不建 worktree；旧版本插件会把整份配置判为无效，团队都升级后再设置）；「设置了的项会在每轮阶段提示里各出现一行」
  改为写明 `moduleConcurrency` 不注入；
- `skills/spec-guard-ops/SKILL.md` 的配置一节同步列出这个键；
- `docs/design.md` 的 `.agent/config.json` 一段补上这个键与 `module_concurrency()` 是唯一读取入口；`docs/commands.md` 若列了
  config 的可配置项，同步一行；
- CHANGELOG 顶部新建 `## [未发布]` 小节，记一条「新增」。

- 验收：`validate.sh` 全档通过。

### Checkpoint 2（gate）：模块验收

在正文列出：
- 实际改动的文件，取自版本库，标出超出 Plan 预计影响面的文件；
- `/spec-guard:config` 汇总在未设置与 `on` 时的原文；
- 验证结果和未验证项；
- 文档建议。

用户验收后勾选并提交；不推送、不开 PR（7 个模块合成一个 PR，最后一个模块验收后再问）。

- 验收：用户验收通过。

## 影响面

- 修改：`hooks/project_config.py`、`hooks/test_project_config.py`、`hooks/test-phase-guard.sh`、`hooks/test-verify-artifacts.sh`、
  `commands/config.md`、`skills/spec-guard-ops/SKILL.md`、`docs/design.md`、可能的 `docs/commands.md`、CHANGELOG；
- 本模块的 Plan 与 todo。

## Risks and Mitigations

- **旧版本插件把整份配置判为无效。** 插件侧补救不了，写进 config 说明；本仓库自己的 `.agent/config.json` 在本模块里不设这个键，
  避免本机已安装的 0.67.0 读坏本仓库配置。
- **以后有人给 `config_lines` 加了「设置即注入」的通用逻辑。** Task 2 的逐字节断言会拦下。

## Open Questions

- 无。
