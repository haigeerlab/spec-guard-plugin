# Plan: sibling-rules-out

<!-- spec-guard: review approved -->

依据 [`spec/sibling-rules-out.md`](../../spec/sibling-rules-out.md)（2026-10-22 批准，事项 C70）。Spec 的三个待定项按用户答复都选 A
（协调的编号 D9、D10、D11 对应 Spec「待定」第 1、2、3 条）：
**待定 1 A**——通用一句同时管「在哪里答复」，复制块按所装协作插件的规定放或不放；
**待定 2 A**——与并行模块重叠的三个文件最后改；答复时 `config-per-key` 已合入，`history-slim` 随后也已合入集成分支（73bc990），
本分支 `module-crew sync` 到 3b2d2c0 后两者都在，所以不再需要等待的 gate，只把这三个文件放在最后一个改动任务里；
**待定 3 A**——「决策收件箱的卡片」改成「session-protocol 契约的交审小项」。

分支 `sibling-rules-out`，worktree `.claude/worktrees/current-plugin-owner-aa5b98-crew/sibling-rules-out`，从集成分支 `crew/fix-batch` 开出。
module-crew 模块会话：只本地提交，不推送、不开 PR；合并由模块协调按用户原话做。CHANGELOG 与版本号由模块协调整批合完后统一改，
本模块把拟写的更新说明记在 todo 末尾。

所需工具：只改文字与 Python 回归，不需要浏览器或电脑操作；不访问远端，不新增依赖。

## 实现要点

- **回归在 `hooks/test_workflow_checkpoints.py`**（`validate.sh` 第 168 行调用）。先改断言跑出红，再改文字转绿。
- **检查点规则的删改按 Spec C1、C2 逐字做**，改前把要删的段落原文记进 todo，便于最终验收给改前改后对照。
- **协调会话一节的 `ORIGINALS`**（逐字保留的句子清单）与 `test_three_pointers` 继续成立：「唯一例外」三个条件那段与三处指向不动。
- **通用一句的两种写法**：`approved` 条用「批准来源以所装协作插件的规定为准；没装只认当前对话里的明确批准」；「交审时说明怎么批准」
  条用「所装协作插件对在哪里答复另有规定时（例如只在它的收件箱答），以它为准，复制块按它的规定放或不放」。镜像文件用同样的关键短语，
  反向用例按短语检查。
- **`interface.json` 是公共文件**：按 C4 发【公共变更请求】，「文件」列 `plugins/spec-guard/interface.json`，由模块协调落地后 sync。

## Task List

### Task 0：同步批准标记、提交 Plan 与 todo

Spec 批准标记已经 `module-crew sync` 取回（HEAD 3b2d2c0，与交审版只差标记一行，指纹 6ddd5e80bc72）。Plan 获批后由模块协调带批准标记
提交到集成分支，开工通知到后 `module-crew sync` 合入。

- 验收：sync 退出码 0；validate、phase-guard、verify-artifacts 全过。

### Task 1：回归先红（C6）

改 `test_workflow_checkpoints.py`：
1. `test_how_to_approve_uses_one_copy_block` 去掉收件枢纽例外各短语，改为断言 C1 补的那句；
2. `test_review_sections_follow_the_card_order` 的「决策收件箱把这些缩成卡片」换成「session-protocol 契约的交审小项」；
3. `test_mirrors_follow_the_card_sections` 的「去决策收件箱答」换成「以所装协作插件的规定为准」；
4. 协调会话一节 `test_section_states_every_floor` 按 Spec C6 增删短语，加反向断言（不含「新提交撤回」「不 reset」「一次只合一个」「合并后跑」）；
5. `HubRelayedApprovalTests` 整类删除，换成反向用例：检查点规则、`review-mark.md`、`SKILL.md`、`docs/commands.md`、`docs/workflow.md`
   都不含「收件枢纽」「去决策收件箱答」「经收件枢纽转来的批准」，都含「以所装协作插件的规定为准」；检查点规则另不含「总协调」；
6. 新增：`config.md` 与 `SKILL.md` 的 `moduleConcurrency` 说明含「不控制协调会话」与「`coordinator up`」；约定块模板不含
   「收件枢纽」（AC6 的守护）。

- 验收：在现有文字上新断言为红，红的原因恰是旧文字还在、新文字还没有；其余用例为绿。
- 验证：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py`（预期失败，记下失败用例名）。

### Task 2：检查点规则（C1、C2）

改 `references/workflow-checkpoints.md`：需求确认的例子、`approved` 条、交审小项命名、复制块例外换成通用句、删「经收件枢纽转来的批准」
整节、协调会话一节按 C2 精简。

- 验收：`grep -n '收件枢纽\|去决策收件箱答\|总协调\|新提交撤回\|不 reset' plugins/spec-guard/references/workflow-checkpoints.md` 无输出
  （AC1、AC2 前半）；Task 1 里针对本文件的用例转绿。

### Task 3：独占范围内的镜像（C5 前半）

改 `commands/review-mark.md` 两处与 `docs/workflow.md`「批准要留下记录」一段。

- 验收：对应反向用例转绿；`validate.sh --quick` 通过。

### Task 4：与已合入模块重叠的三个文件（C3、C5 后半）

改 `skills/spec-guard-ops/SKILL.md`（review-mark 一节与 config 一节 `moduleConcurrency` 条）、`docs/commands.md`（review-mark 一段）、
`commands/config.md`（配置表 `moduleConcurrency` 一行）。只改这几句，其他段落不碰。

- 验收：`test_workflow_checkpoints.py` 全绿（AC3、AC5）；`git diff --stat` 不含 `project_config.py`、`templates/`、`docs/convention-block.md`（AC6）。

### Checkpoint 1（report）：变异核对

在 scratchpad 里 `mktemp -d` 建的副本上分别：把「新提交撤回、不 reset」一句放回协调会话一节；把「## 经收件枢纽转来的批准」节标题放回
检查点规则；把 `config.md` 的「不控制协调会话」删掉。每种都应让对应断言变红，结果记进 todo（AC7 后半）。

### Task 5：公共变更请求（C4）

发【公共变更请求】：`plugins/spec-guard/interface.json` 的 `reviewKinds.description`，把从「the recommended reply sits in one copyable
code block, except when」到「without an item number)」那一段改为「the recommended reply sits in one copyable code block unless the
installed collaboration plugin rules where the user answers」，其他字段与 `version` 不变。按模块协调答复处理，落地后 `module-crew sync`。

- 验收：sync 后 `python3 -c 'import json;json.load(open("plugins/spec-guard/interface.json"))'` 通过，`version` 与 `reviewKinds` 取值
  与改前相同，描述不含「去决策收件箱答」「hub」（AC4）；答复记进 todo。

### Task 6：合入集成分支并跑完整检查

先提交实现（`verify-and-commit.sh` 全套），再单独执行 `module-crew sync`，然后再跑 validate、phase-guard、verify-artifacts。

- 验收：sync 退出码 0（冲突按 sync 规则处理）；全套通过（AC7 前半、AC8）。

### Checkpoint 2（gate）：模块最终验收

发最终验收【交审】：按 AC1～AC8 逐条给证据、变异核对结果、改前改后对照（删去的段落原文）、改动统计与越界检查
（`module_scope.py check --module sibling-rules-out --base crew/fix-batch`，Task 4 的三个文件会标为超出并行边界，逐个说明）、
新增依赖（无）、提交表、拟写的更新说明。不推送、不开 PR，合并由模块协调按用户原话做。

## 风险

| 风险 | 影响 | 处理 |
| --- | --- | --- |
| 其他回归或脚本断言了被删的短语（本 Spec 写作时只查到 `test_workflow_checkpoints.py`） | 别的检查变红 | Task 1 前全仓 `grep` 被删短语（排除 `docs/reports/`、`docs/releases/`、`CHANGELOG.md`、`spec/`、`tasks/` 等历史记录）；Task 6 全套兜底 |
| 删掉复制块例外后，装了 decision-inbox 的使用者在模块会话里看到复制块 | 用户可能在两处各答一次 | 通用句明说以协作插件的规定为准；decision-inbox 规则段已规定只在收件箱答（D2 核实依据） |
| 后续 `rules-at-nodes`、`quiet-injection` 改同一份检查点规则 | 它们要基于本模块的版本 | 本模块合入后它们才开（开工说明），本模块不预先替它们改 |
| `interface.json` 落地慢于本模块其他改动 | 最终验收时 AC4 无法核对 | Task 5 放在 Task 6 之前；没落地就发【等待其他会话】，不自己改公共文件 |
