# Plan: fact-fixes

依据 [`spec/fact-fixes.md`](../../spec/fact-fixes.md)（2026-10-22 用户批准，事项 C30）。评审节奏为分开审，本 Plan 单独交审。
分支 `fact-fixes`，worktree `.claude/worktrees/current-plugin-owner-aa5b98-crew/fact-fixes`，从集成分支 `crew/fix-batch` 切出。

用户批准 Spec 时的答复：「D4 A，D5 A」——按 Spec「待定」两条的推荐理解：`dependency-check` 退役归档（待定 1 的 A），
interface.json 写「values defined in contract v2.3 and unchanged through v2.5」（待定 2 的推荐写法）。另：「spec/CAPABILITY-MAP.md
与 interface.json 是公共文件，改动发【公共变更请求】由模块协调落地」。

CHANGELOG 与版本号由模块协调整批合完后统一改，本模块不碰，更新说明写在 todo 末尾。不推送、不开 PR；需要同步集成分支时运行
`module-crew sync`。

所需工具：没有 UI 改动，不需要浏览器或电脑操作；不装依赖。

## Overview

分三块：本模块自己的文件（`phase-guard.sh` 启动顺序与回归、README 中英、`install-by-scope` 的取代说明、退役说明）直接在本分支做；
能力图与 interface.json 的改动（Spec C1、C2 的能力图部分、C3、C5）连同 `dependency-check` 三份文件的归档移动，写成一份
【公共变更请求】由模块协调一次落地，落地后 `module-crew sync` 合进来再核对。

## Architecture Decisions

- **归档移动随能力图一起由模块协调落地。** verify-artifacts 对「能力图上没有的模块 spec」判失败（`verify-artifacts.sh:64-70`），
  反过来，图里有行而 Spec 不在会让 `dependency-check` 退回 NEEDS_SPEC。所以删行与 `git mv spec/dependency-check.md`、
  `tasks/dependency-check/` 必须在同一个提交里，不能拆到两边。请求里给出逐字的改法与命令，由模块协调执行。
- **退役说明与 `spec/install-by-scope.md` 的取代句在本分支做。** 它们先于归档存在无害（只是指向一个之后才出现的路径），
  合入集成分支时归档已落地。
- **Spec 并行边界的修订放到第一次 `module-crew sync` 之后。** 用户答复把能力图与 interface.json 定为公共文件，Spec 的并行边界
  要把这两项从「独占」挪到「公共」、`spec/dependency-check.md` 与 `tasks/dependency-check/` 改为随公共变更由模块协调移动。
  Spec 的已批准版本在集成分支上，先 sync 再改，免得冲突时被 sync 取集成分支版本覆盖；改后在 Spec 末尾写变更记录，最终验收附差异。
- **C7 的预检只用 bash 内建与 git。** 读输入用 `read -r -d '' -t 1`（macOS `/bin/bash` 3.2 支持，读到 EOF 返回非零但变量已赋值；
  超时返回码大于 128）；超时或超过 1MB（`LC_ALL=C` 下 `${#RAW}`）按「输入不可用」处理，和 `session_context.read_hook_input`
  超时、超限时一样：根目录不变、会话事实为空。`cwd` 用 bash 正则取 `"cwd"[[:space:]]*:[[:space:]]*"([^"\\]*)"`；文本里出现
  `"cwd"` 却匹配不上（含转义），或出现不止一次，算拿不准。
- **拿不准与已启用时，输入原样交给 python3。** `printf '%s' "$RAW" | python3 session_context.py --resolve-root "$ROOT"`，
  `session_context.py` 不改；它读到的字节与现在相同，所以根目录与会话事实逐字节相同。
- **激活判据不复制。** `has_block`／`has_state` 和指向文件判断改为接受一个目录参数（默认当前目录），预检与后面原有的判定共用同一份函数。
- **回归用 python3 替身计数。** 在测试目录里放一个名为 `python3` 的脚本，记一行后 `exec` 真 python3，用 `RUN_PATH` 放到 PATH 最前；
  断言未启用项目的记录为零行。

## Task List

### Task 0：提交已批准的 Plan 与 todo

Plan 获批后用 `/spec-guard:review-mark` 记批准，和 todo 一起提交（若模块协调在集成分支上记了批准，就用 `module-crew sync` 合进来）。

- 验收：`verify-and-commit.sh` 快档通过。

### Task 1：【公共变更请求】能力图与 interface.json

发一份【公共变更请求】给模块协调，「改什么」写全：C1 新段落全文、`module-insert` 一行改后全文、`install-by-scope` 依赖改为
`scope-authorization`、删 `dependency-check` 行与 Build order 里的 `dependency-check →`、变更记录一条（全文）、interface.json
那一处字符串改前改后、三条 `git mv`（`spec/dependency-check.md` → `docs/retirements/dependency-check/spec.md`，`tasks/dependency-check/plan.md`、
`todo.md` → 同目录）。发出前 `module-crew protocol check`。不在本分支改这些文件。等待期间做 Task 2、3。

- 验收：请求发出，协议自检合格；`bridge_outbox` 可见。

### Task 2：未启用项目不启动 python3（先红后绿）

先在 `test-phase-guard.sh` 写用例并确认是红的：
- python3 替身 + 无激活信号的项目，以含 `cwd` 的 JSON 作标准输入，分别跑 UserPromptSubmit、`SessionStart`（compact）、
  `SessionStart fresh`：退出码 0、无输出、替身零次调用（改前为红：现在每次都起一次）。
- 反向：`ROOT` 未启用、`cwd` 在已启用的 linked worktree 里——照旧注入阶段，内容与改前相同（用现有 worktree 用例的期望）。
- 反向：`cwd` 值带转义字符（如 `\"`）——退回 python3 解析，替身至少一次调用，输出与改前相同。
- 反向：未启用项目有指向文件——照旧跟随，与现有 link 用例输出相同。
- 输入超过 1MB 或不是 JSON——未启用项目仍静默、零调用；已启用项目输出与改前相同。

再改 `phase-guard.sh`：激活函数接受目录参数；在原 `--resolve-root` 调用之前插入 bash 预检；把已读输入用管道交给 python3。

- 验收：新用例全绿；现有 phase-guard 回归不改、全绿；ShellCheck 无告警；手工变异（在 scratchpad 的副本里把预检改成恒拿不准）
  零调用断言变红。

### Task 3：README 中英与取代说明、退役说明

- `README.md` 第 5～7 行与 `README.en.md` 第 5～8 行按 Spec C4 改写；两份 cost-report 说明按 C6 改写。
- `spec/install-by-scope.md` 第 5 条末尾加 C2 那句取代说明。
- 新增 `docs/retirements/dependency-check.md`：退役原因（决定 62、提交 `a42a7f1b` 删除了 `dependency_check.py` 与 verify-artifacts 对应段）、
  归档路径、只作历史证据。

- 验收：`check-readme-sync.py` 通过；两份 README 不再含「一个项目只有一份 Spec」与「只统计 token 与轮次」及其英文对应句。

### Checkpoint 1（report）：三套核心回归

`verify-and-commit.sh` 全档（validate、phase-guard、verify-artifacts，带 ShellCheck）通过，结果记入 todo。

### Task 4：公共变更落地后合入并核对

收到模块协调落地的回复后，单独运行 `module-crew sync`，然后：
- 核 AC1～AC3、AC5：能力图严格解析通过；verify-artifacts 不报图外 Spec；归档三份文件与改前 `HEAD` 的 blob 相同；
  阶段注入模块总数比改前少 1；`module-insert` 行无 `spec skeleton`；interface.json 合法、`version` 不变、只改那一处。
- 修订 Spec 并行边界（见 Architecture Decisions），Spec 末尾写变更记录。

- 验收：上述核对的命令输出记入 todo；`verify-and-commit.sh` 全档通过。若模块协调回复不落地或改法不同，停下发【等待其他会话】。

### Checkpoint 2（gate）：最终验收

按 Spec AC1～AC8 逐条给证据，附文件与提交表格、Spec 修订的差异，发最终验收【交审】给模块协调；合并与推送由模块协调按用户原话做。

## 风险

- bash 3.2 的 `read -t` 在不同输入方式下的返回码：Task 2 先在本机 `/bin/bash` 实测 EOF、超时、大输入三种情况，再写代码。
- 桌面版 worktree 场景的判定比现在多一次 `git rev-parse`（只在 bash 里），已启用项目的耗时略增；不改输出。
