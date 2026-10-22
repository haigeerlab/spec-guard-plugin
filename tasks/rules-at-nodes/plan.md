# Plan: rules-at-nodes

<!-- spec-guard: review approved -->

依据 [`spec/rules-at-nodes.md`](../../spec/rules-at-nodes.md)：2026-10-22 批准（事项 C102，11 条前提认可，附带小决定 D12 选 A：兜底一句写
「停在 gate 前、交审前或要停下问用户前，先读停点规则里对应的一节」）；同日按事项 C105 修订、经 C107 复审批准（前提 12、13 认可，
C7 对照表里我补的各行全部认可）。C105 时交审的上一版 Plan 作废，本版加入 C7。

分支 `rules-at-nodes`，worktree `.claude/worktrees/current-plugin-owner-aa5b98-crew/rules-at-nodes`，从集成分支 `crew/fix-batch` 开出。
module-crew 模块会话：只本地提交，不推送、不开 PR；合并由模块协调按用户原话做。CHANGELOG 与版本号由模块协调整批合完后统一改，
本模块把拟写的更新说明记在 todo 末尾。

所需工具：只改文字、Python 与 bash 回归，不需要浏览器或电脑操作；不访问远端，不新增依赖。

## 实现要点

- **先写停点规则，再瘦约定块。** 规则先在 `node-rules.md` 落地、回归断言转到它身上，再从模板里删；这样任何时刻同一条规则至少有一处
  被断言守着。
- **`node-rules.md` 从 `workflow-checkpoints.md` 摘句，不另写新说法。** 关键短语逐字取自检查点规则，一致性回归（AC6）按短语对照。
- **阶段注入只加一段，不动已有行。** `describe()` 在拼好的输出末尾追加「停点规则（<节点名>）：」段；`stop_node` 只组合现有的
  `review_hint` 结果、`next_gate`、`at_final_gate`，不改它们。英文输出其余部分逐字不变（`test-phase-guard.sh` 现有用例守着）。
- **`phase-guard.sh` 只在 IDLE／MAP_ONLY 的 `emit` 文本末尾拼上 `--node-rules` 的输出**，取不到为空时文本与改前逐字相同；不碰
  「关联项目」四段（`cost-slim-link-follow` 的范围）。
- **Python 3.10 兼容**（本机就是 3.10，`test_python_compat.py` 守着）：不用 3.11 才有的语法与库函数。
- **本仓库 `AGENTS.md`** 用工作区脚本 `bash plugins/spec-guard/hooks/setup-convention.sh local --host=codex --replace --dry-run` 先预览、
  再 `--replace --accept-removals`，本地段原样保留；不跑已安装版插件。
- **体积**用 `wc -c` 量，写进 todo。
- **C7 对照表照 Spec 的表逐行抄进检查点规则**，上游章节名保持英文原文（Objective、Boundaries 等），回归按这些原文断言；不加任何读取或判定
  上游章节名的代码（AC10）。

## Task List

### Task 0：同步批准标记、提交 Plan 与 todo

Plan 获批后由模块协调带批准标记提交到集成分支；开工通知到后单独执行 `module-crew sync` 合入，Spec 与 Plan、todo 取集成分支版本。

- 验收：sync 退出码 0；validate、phase-guard、verify-artifacts 全过。

### Task 1：停点规则与检查点规则（C2、C4）

1. 先写回归（红）：`test_workflow_checkpoints.py` 新增用例——`node-rules.md` 五节标题齐全、每节含 C2 列的规则要素（交审呈现「确认框之前」
   「只给链接」、Spec 五项、Plan 四项、中途 gate 三项、最终验收四项与「文档改动：无」「新增依赖、锁文件改动：无」、拟回告「可以原样发送的
   完整文字」、「项目自己的规则」「更严」、「同一模块、同一目标」、「直接写它的 Spec」等）；各节体积（普通 ≤ 2600 字节、最终验收 ≤ 3200）；
   一致性：每节关键短语在 `workflow-checkpoints.md` 也出现；检查点规则开头有指向 `node-rules.md` 的一行、D19① 一句、D19② 三个短语。
2. 新建 `references/node-rules.md`（五节，开头两句）。
3. 改 `references/workflow-checkpoints.md`：开头加指向行；「批 Plan 按范围授权」条末加 D19①；「回告」段按 C4 改写。

- 验收：新用例先红（文件与句子还不存在）后绿；`test_workflow_checkpoints.py` 其余用例照旧绿。
- 验证：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py`。

### Task 1b：交审小项对上游章节（C7）

1. 先写回归（红）：「交审要让用户看到内容」条含 Spec C7 表里每个上游章节名（Objective、Boundaries、ASSUMPTIONS、Success Criteria、
   Open Questions、Capability Map、Build order、Files likely touched、Risks and Mitigations、Checkpoint、Keeping the Spec Alive）与规则短语
   「对应上游的哪一节」「只能作为附加项追加」；`node-rules.md` 的 Spec 交审一节含 Objective、Boundaries、ASSUMPTIONS、Success Criteria、
   Open Questions，Plan 交审一节含 Checkpoint；小项名称与现行一致（现有 `CARD_SECTIONS` 用例照旧绿）。
2. 在检查点规则「交审要让用户看到内容」条五类小项之后加 C7 表与规则；`node-rules.md` 各节小项名后括注上游章节。

- 验收：新用例先红后绿；AC9；`git diff` 里没有读取上游章节名的代码（AC10）。
- 验证：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py`；`wc -c` 复核各节体积。

### Task 2：阶段注入附停点规则（C3 `module_stage.py`）

1. 新建 `hooks/test_stop_rules.py`（红）：用临时项目（`mktemp -d` 固定前缀，case 守卫后删除）造出五种节点与 `None`（构建途中、
   `MODULE_DONE`、`DONE`），断言 `stop_node` 结果；`node_rules` 对缺文件、缺节返回空串；`describe()` 串行最终验收含「停点规则（最终验收）：」
   与「可以原样发送的完整文字」，标了模块或协调角色时不含，构建途中不含；`--node-rules map-review` 打印该节、未知节点不打印且退出 0。
2. 在 `scripts/validate.sh` 的检查清单里按 `test_gate_tick.py` 的写法登记一行。
3. 实现 `stop_node`、`node_rules`、`describe()` 末尾附段、`--node-rules` 参数。

- 验收：新用例先红后绿；`test_module_stage_sanitization.py`、`test_gate_tick.py`、`test_map_view.py` 照旧绿；`git diff` 不含
  `review_state`、`next_gate`、`at_final_gate`、`gate_checkpoints` 函数体与 `spec-digest.py`（AC7）。
- 验证：`python3 -B plugins/spec-guard/hooks/test_stop_rules.py`；`/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh`（确认现有输出没变）。

### Task 3：IDLE／MAP_ONLY 附停点规则（C3 `phase-guard.sh`）

1. `test-phase-guard.sh` 加断言（红）：`IDLE` 输出含「停点规则（能力图审阅）：」、`MAP_ONLY` 含「停点规则（Spec 交审）：」，中英各一；
   把 `node-rules.md` 挪走的插件副本上两者都不出、退出码 0、JSON 合法。
2. 改 `phase-guard.sh` 四个分支的 `emit` 文本末尾。

- 验收：新断言先红后绿，原有用例全绿；macOS 用 `/bin/bash` 跑；暂存了 `.sh`，按 CI 跑 ShellCheck。
- 验证：`/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh`；`shellcheck plugins/spec-guard/hooks/phase-guard.sh`。

### Task 4：约定块瘦身（C1）

1. 改回归（红）：`test_workflow_checkpoints.py` 里对 `*-block-local.md` 断言停点短语的用例，改为断言 `node-rules.md` 对应一节；
   对模板改为断言常驻短句（UI 自验三短语、`report` 记入 todo、不可逆要停、按范围授权、「项目自己的规则更严时以项目为准」、兜底一句、
   批准标记一句、`hosted-ticket-workflow`、`spec-guard:ticket`）与「不含」AC1 列出的八个已移出短语；两份模板体积上限（4000／3800 字节）。
   `test_the_review_rules_live_in_the_convention_block` 改为断言这三条在 `node-rules.md` 的交审各节与最终验收一节（前提 2）。
2. 按 C1 的表改两份模板。
3. 同步 `docs/convention-block.md` 内嵌块；用工作区脚本升级本仓库 `AGENTS.md` 的 Codex 块（先 `--dry-run`，把 `will remove` 与本地段保留情况记进 todo）。
4. 跑 `test_ticket_entry.py`、`test_hosted_ticket_entry.py`，失败才按保留条目调整断言。

- 验收：AC1、AC2；`python3 scripts/check-readme-sync.py` 通过。
- 验证：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py`；`wc -c plugins/spec-guard/templates/*-block-local.md`。

### Task 5：与 `cost-slim-link-follow` 重叠的说明文字（C5）

先看 `cost-slim-link-follow` 是否已合入集成分支：已合入就先单独执行 `module-crew sync` 再改。改 `docs/workflow.md` 第 94 行附近那一段、
`commands/setup-convention.md` 加升级时 `--accept-removals` 一句；核对 README 中英两份不描述约定块内容（预计不改）。

- 验收：`validate.sh --quick` 通过；`git diff --stat` 这几个文件只有所列段落。

### Checkpoint 1（report）：变异核对

在 scratchpad 里 `mktemp -d` 建的副本（`git archive HEAD`）上分别：从 `node-rules.md` 删去最终验收的「文档改动：无」；从 Claude 模板删去兜底一句；
把「单独一张表放在最前」放回 Claude 模板；把 `describe()` 附段的条件改成角色视图也附。每种都应让对应断言变红，结果记进 todo（AC6）。

### Task 6：合入集成分支并跑完整检查

先提交实现（`verify-and-commit.sh` 全套），再单独执行 `module-crew sync`，然后再跑 validate、phase-guard、verify-artifacts 与 `test_stop_rules.py`；
`module_scope.py check --module rules-at-nodes --base crew/fix-batch` 核对越界，越界文件只能是 Spec「与在开模块的重叠」列出的那几份。
在 todo 末尾写拟写的更新说明与对使用者的影响。

### 最终验收（gate）

按停点规则「最终验收」一节交审：做了什么、AC1～AC10 逐条证据、改动文件／提交／依赖表、Spec 中途改过吗；「拟回告：无」（需求来自用户本人）。
不含推送与开 PR；合并由模块协调按用户原话做。

## 风险

- **与 `cost-slim-link-follow` 同改 `phase-guard.sh`、`test-phase-guard.sh`、`docs/workflow.md`、`commands/setup-convention.md`。** 段落不同，
  后合入的一方 sync 时手工合并；本模块的 `phase-guard.sh` 改动只在四个 `emit` 文本末尾，冲突面小。
- **`test_workflow_checkpoints.py` 对模板的断言很多（十几个用例）。** 逐个迁到 `node-rules.md`，改前列出全部受影响用例名记进 todo，防止
  漏迁导致某条规则既不在模板也没被断言。
- **体积目标压不到。** 先按 C1 表写，超了再压措辞；仍超就停下问（Spec 边界「先问再做」）。括注上游章节会让 Spec、Plan 两节变长，最先可能超。
- **sync 会把交审中的 Spec 盖回集成分支版本。** 本模块 Spec 修订交审期间那次 sync 已发生过一次，已按交审内容恢复（2d901fa）。
  之后 sync 前先核对：集成分支里的 Spec 若已是 C107 批准版就无事；不是就先停下问模块协调。
- **一轮中途到达节点时注入看不到。** 兜底一句覆盖，前提 4 已批准；不在本模块另加机制。

## 中途会停下来问你的地方

没有中途 `gate`，做完直接交最终验收。只有 Spec「先问再做」里的三种情况（要改 `phase-guard.sh` 其他结构、体积压不到、条目归属拿不准）才停。
