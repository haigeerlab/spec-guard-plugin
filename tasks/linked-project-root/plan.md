# Plan: linked-project-root

<!-- spec-guard: review approved -->

依据 [`spec/linked-project-root.md`](../../spec/linked-project-root.md)（2026-10-13 用户评审通过，批准标记已写入）。
本仓库评审节奏为分开审：本 Plan 单独评审。分支 `claude/linked-project-root`，worktree
`.claude/worktrees/current-plugin-owner-aa5b98`，从 `7c11ae6`（v0.57.1 验证记录合并）开出。本模块一个 PR，含 0.58.0 版本号；
合并后的 tag、Release、两边宿主同步与验证记录按 `docs/release-process.md` 另走。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Overview

指向文件的解析与校验放在一个 Python 模块里，钩子与命令共用；`phase-guard.sh` 只在“没有激活信号”的出口前多问一次这个模块。
之后是命令、文档与版本号。

## Architecture Decisions

- **判定只有一处。** `project_link.py` 提供 `resolve(session_root)`，返回“没有指向／有效及目标／失效及原因代码”；
  `phase-guard.sh` 以子命令调用它，`show`／`set`／`unset` 用同一个函数。
- **激活信号的判据不复制。** 目标是否已启用，由 `phase-guard.sh` 现有的 `has_block`／`has_state` 判（钩子侧 `cd` 到目标后重用），
  命令侧用同一条正则的 Python 版并以回归测试对齐两边。
- **无指向文件的路径零开销。** 钩子先用 bash 内建判断指向文件是否存在，不存在就照旧 `exit 0`，不启动 python3。
- **自己已启用的路径不碰。** 判断顺序是先看自己的激活信号，命中即走现行流程。
- 共同验证命令：

  ```bash
  python3 -B plugins/spec-guard/hooks/test_project_link.py
  /bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
  /bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
  ```

## 依赖与顺序

```text
Task 1 指向解析 ─┬→ Task 2 钩子跟随 ─→ Task 3 Linked project 行与诊断
                 └→ Task 4 命令脚本 ─→ Task 5 命令文件与 Codex 路由
Task 6 文档 ─→ Task 7 版本号
```

## Task List

### Task 1：指向文件的解析与校验（先红）

新增 `hooks/test_project_link.py`：没有文件、有效（绝对与相对路径）、格式无效的各种写法（多余的键、版本不对、不是对象、
`project` 为空或不是字符串）、目标不存在、目标不是目录。再写 `hooks/project_link.py` 的 `resolve`。

- 验收：单测全绿。
- 文件：`hooks/project_link.py`、`hooks/test_project_link.py`。

### Task 2：钩子跟随指向（先红）

`test-phase-guard.sh` 新增一段：Spec「钩子」表四行各一例；没有指向文件的无关目录静默；自己已启用时有无指向文件输出逐字
相同；不连环跟随；相对路径。确认失败后改 `phase-guard.sh`：没有激活信号时先看指向文件，有效则把项目根换成目标并继续。
变异：自己已启用时也读指向、目标未启用也放行、连环跟随。

- 验收：phase-guard 回归全绿；三处变异各有断言变红。
- 文件：`hooks/phase-guard.sh`、`hooks/test-phase-guard.sh`。

### Task 3：`Linked project` 行与失效诊断（先红）

同一段再加：`Linked project` 行恰好一行、含目标与会话目录、位置行是目标项目的；三种失效各输出固定文字的合法 hook JSON、
不含指向文件原文；两边宿主各一例；指向文件存在而 python3 不可用时不静默。再实现。

- 验收：phase-guard 回归全绿；注入是合法 JSON。
- 文件：`hooks/phase-guard.sh`、`hooks/module_stage.py`（接收并输出这一行）、`hooks/test-phase-guard.sh`。

### Checkpoint 1（report）：钩子回归全绿，ShellCheck 无警告

### Task 4：`show`／`set`／`unset`（先红）

`test_project_link.py` 加命令用例：`show` 三种状态；`set` 预览不写文件、`--confirm` 写入并读回、相对路径原样保存、重复执行
结果相同；`unset`；Spec 列出的全部拒绝。再实现，复用现有原子写入。

- 验收：单测全绿；在临时目录结构上实跑一次建立 → 钩子输出 → 解除 → 钩子静默。
- 文件：`hooks/project_link.py`、`hooks/test_project_link.py`。

### Task 5：命令文件与 Codex 路由

新增 `commands/link-project.md`（规范引导段）；`spec-guard-ops` 新增 link-project 一节并在项目定位说明里补一句；
`docs/commands.md` 登记；`validate.sh` 登记新单测。

- 验收：`scripts/test-checkers.sh` 与 `validate.sh --quick` 通过。
- 文件：`commands/link-project.md`、`skills/spec-guard-ops/SKILL.md`、`docs/commands.md`、`scripts/validate.sh`。

### Checkpoint 2（report）：三套核心回归与新单测全绿，ShellCheck 无警告

### Task 6：文档

`docs/troubleshooting.md` 加“会话目录不是项目目录”与三条诊断；`docs/design.md` 的激活信号一节补指向文件；
`docs/workflow.md` 一段；CHANGELOG `[未发布]`。

- 验收：`validate.sh --quick` 通过。
- 文件：上述四个文件。

### Task 7：版本号

两份 `plugin.json` 改为 0.58.0，中英 README 的 `--ref` 改为 v0.58.0，CHANGELOG 标题 `[0.58.0]`。

- 验收：`validate.sh` 的清单一致性通过。
- 文件：两份 `plugin.json`、`README.md`、`README.en.md`、`CHANGELOG.md`。

### Checkpoint 3（gate）：模块评审

提交走 `scripts/verify-and-commit.sh`，一个任务做完并提交后再开始下一个；pre-push 钩子兜底。展示全部验证结果与未验证项。
批准本 Plan 即授权推送本分支并开本模块的 PR；合并由用户进行。发版后的真实宿主验证属于合并后的步骤。

## Risks and Mitigations

| 风险 | 应对 |
|---|---|
| 改激活判断误伤无关目录的静默 | 无指向文件时在启动 python3 之前就退出；“无关目录仍静默”的现有用例全部保留并新增一例 |
| 钩子与命令对“目标已启用”的判据不一致 | 回归里用同一组目标夹具分别喂给钩子和命令，结论必须相同 |
| 指向文件内容进入注入造成伪造 | 只输出固定文字与清洗后的路径；格式无效时不回显内容 |
| 目标路径含空格或多字节字符 | 夹具用带空格与中文的目录名；bash 里变量后接多字节字符写 `${VAR}` |
| 本仓库在用的是已安装的 0.57.1，看不到工作区的新行为 | 用工作区源码与临时目录结构验证 |

## Open Questions

- 无。
