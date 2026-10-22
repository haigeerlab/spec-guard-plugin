# Plan: quiet-injection

依据 [`spec/quiet-injection.md`](../../spec/quiet-injection.md)：2026-10-22 批准（事项 C140，未决问题 Q1 A、Q2 A、Q3 A：停在节点上讨论时
进入那轮完整、之后一行；Claude 窗口按读数推算；已完成模块的能力图行不改）。

分支 `quiet-injection`，worktree `.claude/worktrees/current-plugin-owner-aa5b98-crew/quiet-injection`，从集成分支 `crew/fix-batch` 开出。
module-crew 模块会话：只本地提交，不推送、不开 PR；合并由模块协调按用户原话做。CHANGELOG 与版本号由模块协调整批合完后统一改，
本模块把拟写的更新说明记在 todo 末尾。

所需工具：Python 与 bash 回归；AC9 要在临时消费者项目里跑一次真实宿主（见 Task 6 与未决问题 Q1）。不访问远端，不新增依赖。

## 架构决定

- **状态码算在 Python，比较在 bash。** `module_stage.py` 负责算状态码与拼一行形式（它已经掌握阶段、模块、批准状态、停点等全部事实）；
  `session_context.py` 负责从会话记录取上一次的状态码（它已经在读同一份记录的尾部）；`phase-guard.sh` 只做比较与选择。不新建文件，
  所以不用在 `validate.sh` 登记新回归。
- **一次读记录。** `session_context.py` 现在输出「用量／位置／窗口／无人值守／宿主」五行，在末尾追加两行：上一次的状态码（读不到为空）、
  Claude 尾部读数是否超过 200k（`over-200k` 或空）。尾部 4MB 只读一次，三个事实同一遍扫出来。
- **IDLE／MAP_ONLY 的状态码也交给 `module_stage.py --state-key`**，bash 只把事实（阶段、附的节点、配置行、位置、关联项目、语言）作为参数传过去，
  算法只有一份。
- **诊断类输出不经降噪**（Spec 假设 8）：`MAP_INVALID`、`UNKNOWN` 不带状态码，比较时永远「不同」。

## 实现要点

- **状态码格式**：`<!-- spec-guard-state: [0-9a-f]{8} -->`，完整输出另起一行放在最后（压缩后的核对提醒之前，这样 `emit()` 追加的提醒
  不影响取码）；一行形式放在行尾。`last_state()` 用同一个正则，只认 Spec 假设 4 的两种记录：Claude `type == "attachment"` 且
  `attachment.type == "hook_additional_context"`（`content` 是字符串列表）；Codex `type == "response_item"`、`payload.type == "message"`、
  `payload.role == "developer"` 的 `input_text`。正文须以 `## spec-guard local workflow` 或 `spec-guard: ` 开头。
- **压缩判定**沿用 `_compacted()`：倒序扫描时先遇到压缩记录、后遇到注入记录，即压缩比注入新，返回空。
- **一行形式附件**：`emit()` 的 receipt hint 逻辑找的是「建议下一步」标记，一行形式没有它，就落到「末尾另起一段」分支，正好满足假设 7；
  边界行由 `module_stage.py --brief` 在需要时自己接在后面（它已经算好边界行）。
- **Claude 窗口**：`phase-guard.sh` 在 Codex 窗口为空且第七行是 `over-200k` 时传 `--context-window 1000000`，否则（Claude 且有读数）传
  `--context-window 200000`，再加 `--window-estimated` 让说明写「按 … 窗口估算」；Codex 不变。宿主判断不了（`HOST` 为空）时按 Claude 处理，
  与现在「无窗口即 Claude 折算」一致。
- **英文标签**：先写「英文输出不含中日韩文字」的检查（Task 4），用它把 `module_stage.py`、`phase-guard.sh` 英文分支里剩下的固定中文全部找出来，
  不靠记忆列清单。
- **Python 3.10 兼容**（`test_python_compat.py` 守着），bash 用 `/bin/bash` 3.2 能跑的写法，不引入 `jq`；`phase-guard.sh` 改完跑 ShellCheck。
- **与 `batch-insert-concurrency-hint` 的重叠**（用户批准 C140 时定下）：本模块独占 `references/workflow-checkpoints.md` 与
  `hooks/test_workflow_checkpoints.py`，那个模块只在「并行评估」一节与 `ConcurrencyAssessmentTests` 里追加；本模块不碰这两处，后合入的一方先 sync。

## Task List

### Task 0：同步批准标记

开工通知到后单独执行 `module-crew sync`，Spec、Plan、todo 取集成分支带批准标记的版本。

- 验收：sync 退出码 0；validate、phase-guard、verify-artifacts 全过。

### Task 1：删 80% 行、修 Claude 窗口（改动 2）

1. 先改回归（红）：`test-phase-guard.sh` 里 80% 的用例改为反向断言（`BUILDING`、`NEEDS_PLAN` 超过 80% 也不出 `Session context`／`会话上下文`）；
   Claude 用例分两条：尾部读数都不超过 200k 时 140k 起出边界行、写「按 200 k 窗口估算」，有读数超过 200k 时 700k 起、写「按 1 M 窗口估算」；
   中英各一。
2. `session_context.py` 追加「尾部读数是否超过 200k」一行；`module_stage.py` 删 `MID_SHARE`、`DEFAULT_WINDOW`、`context_line()`、`free-current`
   与 `describe()` 的 `context_note` 分支，`thresholds()` 只返回边界档，新增 `--window-estimated`；`phase-guard.sh` 按实现要点传窗口。
3. `test_workflow_checkpoints.py` 第 148 行短语清单去掉 `80%`；`references/workflow-checkpoints.md` 第 389～390 行按改动 4 改。

- 验收：AC5、AC6；新断言先红后绿，其余用例照旧绿。
- 验证：`/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh`；`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py`；
  `grep -n 'MID_SHARE\|context_line\|DEFAULT_WINDOW' plugins/spec-guard/hooks/*.py` 为空。

### Task 2：状态码（改动 1 前半）

1. 先写回归（红）：`test-phase-guard.sh` 新增一段，造 Claude 与 Codex 两种会话记录：完整输出末尾带状态码；同一项目同一状态两次算出的码相同；
   Spec 假设 2 每项事实单独改动时码不同（阶段、模块、Spec 批准、Plan 批准、停点、角色、挂起、未合提交、配置行、关联项目、位置、语言），
   未勾选数、用量改动时码相同；`MAP_INVALID`、`UNKNOWN` 不带码；IDLE、MAP_ONLY 带码。
2. `module_stage.py` 新增 `state_key()`、`--state-key`，`describe()` 完整输出末尾加码；`phase-guard.sh` 的 IDLE、MAP_ONLY 四个分支末尾加码。

- 验收：AC2 的「事实变→码变」部分；新断言先红后绿；现有用例只多出末尾一行（统一在取正文的辅助函数里去掉码行再比较，不逐个改用例）。
- 验证：同上，加 `python3 -B plugins/spec-guard/hooks/test_module_stage_sanitization.py`、`test_stop_rules.py`。

### Task 3：一行形式与选择（改动 1 后半）

1. 先写回归（红）：会话记录里有上一次注入且码相同时只给一行（格式按 Spec 假设 6，中英各一，IDLE／DONE 的模块写「—」、非 git 目录无分支段、
   分离 HEAD 写短 sha）；码不同给完整；没有记录路径、记录读不了、尾部找不到、压缩记录比注入新、码只出现在 user／assistant 消息里，都给完整；
   SessionStart 总是完整；一行形式附 receipt hint 与边界行各一条；停点：进入节点那轮完整并附停点规则、同一节点下一轮一行（AC4）。
2. `session_context.py` 新增 `last_state()` 并输出第六行；`module_stage.py` 新增 `--brief`；`phase-guard.sh` 比较后选择。

- 验收：AC1、AC2、AC3、AC4；新断言先红后绿。
- 验证：`/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh`；`shellcheck plugins/spec-guard/hooks/phase-guard.sh`。

### Task 4：英文标签（改动 3）与评测脚本（改动 5 的 evals）

1. 先改 `evals/hint-english-diff.sh`（红）：去掉与 0.67.0 逐字节比较，改为英文侧「除 Spec 假设 11 的例外不含中日韩文字」，中文侧原检查不变；
   `test-phase-guard.sh` 加英文各阶段标题是 `Current stage:` 的断言。
2. 改 `module_stage.py`、`phase-guard.sh` 英文分支里检查找出的固定中文；`project_link.py` 的 `_phase()` 认两种开头；
   `evals/codex-plugin-smoke.sh` 判决正则与自检样例、`evals/module-namespace.sh` 断言改认两种。

- 验收：AC7、AC8。
- 验证：`/bin/bash evals/hint-english-diff.sh`（基线参数不再需要）；`/bin/bash evals/codex-plugin-smoke.sh --selftest`；
  `python3 -B plugins/spec-guard/hooks/test_project_link.py`（存在则跑）；phase-guard 回归。

### Task 5：说明文字（改动 4）

`commands/phase.md`（上下文提醒一节、语言一节、新增一行形式说明并写明本命令总是完整输出）、`docs/design.md` 第 80～86 行、`README.md`、
`README.en.md`（英文示例的阶段行、「每轮注入」的说法）。

- 验收：`/bin/bash scripts/validate.sh --quick` 通过；`python3 scripts/check-readme-sync.py` 通过。

### Checkpoint 1（report）：变异核对

在 scratchpad 里 `mktemp -d` 建的副本（`git archive HEAD`）上分别：让 `last_state()` 也认 assistant 消息；让 `state_key()` 把未勾选数算进去；
把压缩判定去掉；把 `context_note` 分支放回。每种都应让对应断言变红，结果记进 todo。

### Task 6：真实宿主核对（AC9）

Claude Code：在 `mktemp -d` 的临时消费者项目里（`setup-convention` 落约定、造一张两模块的能力图），用 `claude -p --plugin-dir <本 worktree 的
plugins/spec-guard>` 发第一轮，再 `--resume` 同一会话发第二轮，从会话记录里取两次 spec-guard 注入的原文片段记进 todo。先确认本机已装的
spec-guard 在这次运行里不同时注入（两份注入会混在一起）；做不到就按未决问题 Q1 处理。
Codex：见未决问题 Q1。

- 验收：AC9（按 Q1 的答复）。

### Task 7：合入集成分支并跑完整检查

实现各提交走 `verify-and-commit.sh` 全套；单独执行 `module-crew sync`，再跑 validate、phase-guard、verify-artifacts、`test_stop_rules.py`、
`hint-english-diff.sh`、`codex-plugin-smoke.sh --selftest`；`module_scope.py check --module quiet-injection --base crew/fix-batch` 核对越界，
应为空（本模块独占清单覆盖所有改动文件）。todo 末尾写拟写的更新说明与对使用者的影响。

### 最终验收（gate）

按停点规则「最终验收」一节交审：做了什么、AC1～AC10 逐条证据、改动文件／提交／依赖表、Spec 中途改过吗；「拟回告：无」（需求来自用户本人）。
不含推送与开 PR；合并由模块协调按用户原话做。

## 风险

- **现有 phase-guard 回归数百条，都断言完整输出。** 它们不带会话记录，所以仍走完整分支；末尾多的状态码行在取正文的辅助函数里统一剥掉，
  不逐条改，避免大面积改断言掩盖回归。
- **宿主记录格式变了，取不到码。** 取不到就给完整（降级不误报），最坏回到现在的行为；回归用的两种格式取自 2026-10-22 实测记录。
- **状态码漏了某项事实，状态变了却只给一行。** Task 2 对 Spec 假设 2 的每项各写一条「变→码变」断言，Checkpoint 1 再做反向变异。
- **英文输出里的中文清不干净或误伤仓库内容。** 检查只放过 Spec 假设 11 的例外；仓库内容在测试项目里用纯 ASCII 的模块 id，避免误报。
- **Claude 用 `claude -p --plugin-dir` 跑真实宿主时，本机已装的 spec-guard 也会注入。** 两份注入的状态码互相干扰；先查清能否只加载工作区那份，
  做不到就停下（Q1）。
- **与 `batch-insert-concurrency-hint` 同碰 `workflow-checkpoints.md`、`test_workflow_checkpoints.py`。** 段落不同（本模块改第 389～390 行与第 148 行），
  后合入的一方先 `module-crew sync`。

## 中途会停下来问你的地方

没有中途 `gate`，做完直接交最终验收（不含推送与开 PR）。只在 Spec「先问再做」的情况停：状态码要写文件才能做、真实宿主记录格式与 Spec 假设 1 不符、
一行形式要多带别的内容、发现依赖英文逐字不变的外部使用方；以及 Task 6 做不到时（Q1）。

## 未决问题

- **Q1：AC9 真实宿主核对怎么做。** 本机 Claude Code 与 Codex 装的是已发布的 spec-guard，Spec 边界不许重装或更新本机插件，所以真实宿主跑的不是
  本分支的代码。A（推荐）：Claude 用 `claude -p --plugin-dir` 只加载本 worktree 的插件跑两轮（Task 6）；Codex 没有不安装就加载的办法，改用
  本机今天的真实 rollout（截取注入记录、去掉无关内容）喂给新 hook 证明格式认得，真正在 Codex 里连续两轮的核对放到发版后由模块协调做，
  最终验收里写明这一条未在 Codex 真机上做。B：两个宿主都放到发版后核对，本模块只交回归与真实记录片段。C：允许为核对临时把本 worktree 装进本机
  Codex（改宿主插件配置，核对完恢复）。
