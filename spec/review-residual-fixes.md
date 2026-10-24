# Spec: review-residual-fixes

<!-- spec-guard: review approved 26f7d1a0a7ed -->

## Objective

0.84.1 发布后，Codex（gpt-5.6-sol high）做了两批只读复评，本会话逐条读码核实，留下 9 条遗留问题，另有一行过时注释（账本 QV6KWMJ、
HT9AJX2）。本模块一次修完，发 0.84.2。每一条都是「现有行为与已定规则或说法不一致」，不加新功能：

1. **review-mark 输出的转交说法过时（F5 残留）。** `sibling-rules-out`（D2）已把批准来源改成通用的一句：「批准来源以所装协作插件的规定为准；
   没装只认当前对话里的明确批准」（`references/workflow-checkpoints.md:149`、`commands/review-mark.md:73`）。`hooks/review_mark.py:136-138`
   写 `approved` 时打印的提醒，以及文件头 `:4` 的说明，还写「registered decision hub」「session-protocol format」「hub's item number」。
2. **create 类文档凭非空证据就算 ready（F17 残留）。** `hooks/documentation_verification.py:165` 只对 `update` 调 `_check`；声明为
   `create` 的文档只要结果写成 delivered、证据非空，就算 `ready`，文件根本不存在也不报。
3. **`setup-convention.sh --replace` 被拒时留下部分写入。** 脚本 `:153-164` 先建 `spec/`、`tasks/`、`.agent/`、`state.json`、能力图，
   之后 `install_block` 里的 `managed-block.py replace` 才可能因「要删模板外的行、没给 `--accept-removals`」拒绝（退出 3）。拒绝时报
   「was not changed」，但目录和文件已经建好了。脚本开头的注释写的正是「任何写入之前先校验……不留下半完成的目录或文件」。
4. **静默注入的状态码漏了「文档基线是否存在」。** quiet-injection 只在状态码变了时输出完整内容。`hooks/module_stage.py:1089` 的 facts
   不含文档基线是否存在；而最终 gate 的「文档核验」一行（`:1087`，模块会话视图 `:794`）只在有基线时出现。于是停在最终 gate 时
   新建了基线，状态码不变，只出一行，文档核验那行就漏了。
5. **module_scope 的代码围栏不按 Markdown 配对。** `hooks/module_scope.py:58` 的 `_visible` 遇到任意 ```` ``` ```` 或 `~~~` 开头的行都翻转
   「在围栏内」。` ~~~ ` 包着的示例里出现 ```` ``` ````、或 ```` ```` ```` 四个反引号包着三个的写法，都会把后面的正文当成围栏内（反之亦然），
   「并行边界」一节可能被漏读或把示例当真。
6. **projectId 判据不一致。** `hooks/local_ledger_runtime.py:184` 允许 `[A-Za-z0-9_-]{1,64}`；`hooks/local_ticket_bind.py:212` 与
   `hooks/local_ticket_journal.py:46` 用 `isalnum()`，含 `-` 或 `_` 的 projectId 在账本里合法，绑定与离线归档却必失败
   （`isalnum()` 还接受非 ASCII 字母数字，比 runtime 宽）。
7. **history-migration 失败时不删临时事件文件。** `hooks/history-migration.py:87-97` 在 `capability-history.py create` 失败时删了目标目录和
   复制的能力图，却留下 `.history-migration-*` 临时文件在项目根。
8. **spec-guard-ops 的 Proposal 一节自相矛盾。** `skills/spec-guard-ops/SKILL.md:357` 写「Proposal 步骤均为只读……也不写 Issue、标签」，
   同一节 `:384` 起的「收尾」经用户授权会写收尾记录、改阶段标签并关闭事项。
9. **批量插入后的「只评估一次」没有跨会话记录（D20）。** `references/workflow-checkpoints.md:324-329` 说一批只评估一次、之后不再提，
   但没有任何持久记录；换了会话（或压缩后），新会话无从知道这一批评估过没有。
10. **过时注释（HT9AJX2）。** `hooks/module_stage.py:351-353` 写 phase-guard.sh 估算窗口为「200k, or 1M once a reading went over 200k」；
    0.84.1 起读数都不超过 200k 时不设窗口、不出边界行（`phase-guard.sh:345-350`）。

登记：用户 2026-10-23 原话「先把核实的 9 条遗留问题交协调会话修成 0.84.2」；2026-10-24 在本会话确认做法与假设（「可以」）。
能力图依赖 `quiet-injection, doc-chain, module-scope-boundary, history-slim`。

## Assumptions

2026-10-24 已在本会话交用户确认（第 1～6 条）；第 7～9 条是写 Spec 时补的，请批准时一并确认：

1. **单模块，在本会话做，不用 module-crew。** 9 条散在 8 个已完成模块里，逐个返工要把 8 份 Plan 都改回待批准；照
   `audit-small-cleanups`、`fact-fixes` 的先例开一个修复模块。
2. **第 2 条只查存在，不查内容。** create 类声明 delivered 时，`Planned artifact` 路径（去掉 `#` 之后部分）须是项目里的普通文件；
   外部文档（与 update 用同一判据）标未核验。不比 git 差异、不判内容。
3. **第 6 条统一成 `[A-Za-z0-9_-]{1,64}`，用一个共用判据。** bind、journal、runtime 三处引用同一份定义；只放宽了 `-`、`_`，
   收紧了非 ASCII 与超过 64 位。
4. **第 4 条只补 facts。** 只把「文档基线是否存在」加进状态码的 facts，不改任何输出文字和判定。
5. **`interface.json` 不升。** 这批不碰对外接口的字段与取值。
6. **版本 0.84.2，separate 节奏：** 先审 Spec，批准后再审 Plan。
7. **第 3 条的修法是「先校验后写入」，不是「失败后回滚」。** 需要 `--replace` 且已有声明块时，在建任何目录或文件之前先跑一次与真正写入
   相同的拒绝判定；会被拒就照现在的提示退出 1，什么都不建。回滚要分辨哪些是本次新建的，容易误删用户原有文件。
8. **第 9 条只写进文档，不加记录文件。** 在「批量插入之后」补一句：「只评估一次」靠本会话记得；新会话（或压缩后）拿不准这一批评估过没有时，
   不主动重评，用户要求时再评。加持久记录要新文件和新判据，是新功能，D20 本身也是软规则。
9. **第 5 条按 CommonMark 的围栏配对：** 开围栏是行首（前面最多 3 个空格）3 个及以上 ```` ` ```` 或 `~~~`；闭围栏须同一字符、个数不少于开围栏、
   后面只能有空白。只改 `module_scope.py` 的 `_visible`；`documentation_baseline._visible_lines` 也不完全配对，但不在复评核实的范围内，
   记账本不顺手改。

## Contract

### C1 review-mark 提醒（`hooks/review_mark.py`）

- `approved` 的提醒改成与 `commands/review-mark.md:73` 同义：「`approved` 记录用户的明确批准：批准来源以所装协作插件的规定为准；
  没装只认当前对话里的明确批准。不要为了消掉阶段提示而写；标记是给后来的会话看的记录，不是授权来源。」（英文输出，与现有提醒同语言。）
- 上一句提醒里的「(or in the message sent to the hub)」改为「(or in the message the installed collaboration plugin relays)」。
- 文件头 `:4` 的说明同步去掉 decision hub、session-protocol。
- 其余输出、拒绝条件、写入行为不变。

### C2 create 类文档核验（`hooks/documentation_verification.py`）

- delivered 的 `create`：路径取自 Plan「Documentation delivery」表的 `Planned artifact`（去掉 `#` 及之后）。
  - 外部文档（与 update 用同一 `EXTERNAL` 判据）：`check` 为 `unverified`，不进 attention；
  - 路径是项目内的普通文件：`check` 为 `present`；
  - 不存在、是目录、是符号链接、或越出项目根：`check` 为 `missing`，attention 加一条「`<concern>` is declared delivered, but `<path>`
    does not exist in the project」，结果为 `attention`。
- `update` 的判定、其余状态和 JSON 字段不变（`check` 只多两个取值）。

### C3 setup-convention 先校验（`hooks/setup-convention.sh`、`hooks/managed-block.py`）

- 已有声明块且带 `--replace`、非 dry-run 时，在 `mkdir` 之前先做一次与 `replace` 相同的拒绝判定（缺 `--accept-removals` 而要删模板外的行）。
  会被拒：照现在的 stderr 列出这些行，加「未改动任何文件」，退出 1；`spec/`、`tasks/`、`.agent/`、`state.json`、能力图一个都不建。
- 不被拒时输出与写入逐字节同现在。dry-run 不变。

### C4 状态码含文档基线（`hooks/module_stage.py`）

- `facts` 增加一项 `documentation_baseline_present(root)`。只影响状态码；任何输出文字不变。
- 效果：在最终 gate 新建或删除 `docs/DOCUMENTATION-BASELINE.md`，下一轮状态码变，注入完整内容（含或不含文档核验一行）。

### C5 围栏配对（`hooks/module_scope.py`）

- `_visible` 按假设 9 配对；围栏行本身仍记为空行，未闭合的围栏到文末都算围栏内（同 CommonMark）。
- 只有普通 ```` ``` ```` / `~~~` 成对的 Spec，解析结果与现在相同。

### C6 projectId 共用判据

- 一份定义 `[A-Za-z0-9_-]{1,64}`（放在 `local_ledger_runtime.py` 或三者都已导入的模块里，Plan 定）；`local_ledger_runtime.py:184`、
  `local_ticket_bind.py:212`、`local_ticket_journal.py:46` 都用它。错误信息不变。
- `proposal_closeout_local.py`、`proposal_tracker_read.py`、`tracker_default.py` 已经是同一正则，不在本模块改。

### C7 history-migration 清理（`hooks/history-migration.py`）

- 失败分支（`OSError`、`CalledProcessError`）里，已创建的临时事件文件也删掉；删除失败不掩盖原来的失败退出码 1。
- 成功路径不变。

### C8 Proposal 一节说法（`skills/spec-guard-ops/SKILL.md`）

- `:357` 改为：Proposal 的审查、预检、证明都是只读；只有「收尾」在用户针对这一条 Proposal 明确同意后写收尾记录、改阶段并关闭事项（见下文）。
  只读那几步仍不读其他 worktree 或 `.agent/state.json`，不写能力图、分支或任务。
- 已查：`commands/` 与其他 skill 里没有同样的说法，只改这一处。

### C9 批量插入只评估一次（`references/workflow-checkpoints.md`）

- 「批量插入之后」一段末尾补一句（中文）：「只评估一次靠本会话记得，插件不留记录；新会话或压缩后拿不准这一批评估过没有时，不主动重评，
  用户要求时再评。」这份规则只有中文版，没有英文对应段落。
- 现有回归 `test_workflow_checkpoints.py` 的断言照旧，必要时加这句的断言。

### C10 过时注释（`hooks/module_stage.py:351-353`）

- 改为与 `phase-guard.sh:345-350` 一致：只有尾部有读数超过 200k 时才按 1M 估算并写明是估算；否则不设窗口、不出边界行。只改注释。

## Acceptance criteria

- **AC1** `test_review_marker.py`：`approved` 的提醒含「collaboration plugin」与「current conversation」，不含 `decision hub`、`session-protocol`、
  `item number`；`review_mark.py` 全文不再含这三个词。改回旧文字断言变红。
- **AC2** `test_documentation_verification.py` 新增：create 声明 delivered、文件存在 → `ready`、`check=present`；文件不存在 → `attention`、
  `check=missing`、attention 含路径；外部文档 → `unverified`。手工变异：去掉 create 分支，「不存在」用例变红。
- **AC3** setup-convention 回归新增：已有声明块含模板外行、`--replace` 不带 `--accept-removals`、项目里没有 `spec/` `tasks/` `.agent/`
  → 退出 1，三个目录都不存在，目标文件逐字节不变。带 `--accept-removals` 的现有用例照旧全绿。
- **AC4** `module_stage` 回归新增：同一项目停在最终 gate，有无 `docs/DOCUMENTATION-BASELINE.md` 两次的状态码不同；其余事实相同时状态码与
  改前相同（现有状态码用例不改、全绿）。
- **AC5** `module_scope` 回归新增：`~~~` 包着 ```` ``` ```` 的示例、四个反引号包三个的示例、两种情况后面的真「并行边界」一节都能读到，
  示例里的假一节不读；现有用例全绿。
- **AC6** 账本回归新增：projectId `my-ledger_1` 能通过 bind 与 journal 的判据；`a/b`、65 位、非 ASCII 字母被拒；三处引用同一定义（断言源码里
  不再有 `isalnum`）。
- **AC7** history-migration 回归新增：让 `capability-history.py create` 失败（例如替身或坏账本），项目根没有 `.history-migration-*` 残留，
  退出码 1。
- **AC8** SKILL.md 与 workflow-checkpoints 的文字如 C8、C9；`scripts/validate.sh` 的文档检查通过。
- **AC9** `scripts/validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 全绿；改到 `.sh` 时 ShellCheck 通过；Claude 与 Codex 清单
  版本都是 0.84.2，CHANGELOG 有 0.84.2 一节。

## Boundaries

- **会做**：上述十项及其回归（要加用例的测试文件在 Plan 里按实际文件列出）；能力图变更记录一条；版本号升到 0.84.2（两份清单与 marketplace）、CHANGELOG；PR 内附模块验收。
- **先问再做**：核对中发现别的文档与实现不一致——记账本、交用户，不顺手修；任何会改变已有输出文字的改动（C1、C3 的提示除外）。
- **不做**：改 `interface.json`；动 S32／接口 1.11 的内容；改 `documentation_baseline._visible_lines`；给批量插入加记录文件；重装本机插件
  （发版后另走发布流程）；改别的仓库。

## 并行边界

- 独占：`spec/review-residual-fixes.md`、`tasks/review-residual-fixes/`、`plugins/spec-guard/hooks/review_mark.py`、`plugins/spec-guard/hooks/documentation_verification.py`、`plugins/spec-guard/hooks/setup-convention.sh`、`plugins/spec-guard/hooks/managed-block.py`、`plugins/spec-guard/hooks/module_stage.py`、`plugins/spec-guard/hooks/module_scope.py`、`plugins/spec-guard/hooks/local_ledger_runtime.py`、`plugins/spec-guard/hooks/local_ticket_bind.py`、`plugins/spec-guard/hooks/local_ticket_journal.py`、`plugins/spec-guard/hooks/history-migration.py`、`plugins/spec-guard/skills/spec-guard-ops/SKILL.md`、`plugins/spec-guard/references/workflow-checkpoints.md`
- 公共：无

## 文档建议

只改规则说明（SKILL.md、workflow-checkpoints）与 CHANGELOG；项目没有文档基线，不需要文档影响登记。

## 变更记录

- 2026-10-24（构建中，范围内补充）：C2 的说明同步。`commands/documentation-verification.md` 与 `references/documentation-verification.md`
  原写「`create` 为 `not-checked`」，与 C2 冲突，按 C2 改为 `present`／`missing`／`unverified`；`test_documentation_verification.py` 原
  `test_create_is_not_checked` 断言旧行为，改为 `test_create_only_checks_existence`。两份说明不在原并行边界里，是 C2 的直接后果，范围不变。
- 2026-10-24（构建中，偏离 Spec 一处）：C5／假设 9 写「开围栏是行首（前面最多 3 个空格）」。实现时发现原 `FENCE` 接受任意缩进，而列表项里缩进 4 格以上的
  围栏按 CommonMark 仍是围栏；只认 3 格会让这类示例里的标题被当成正文，比现在更差。改为缩进照旧不限，只改配对（同字符、不短于开围栏、后面只有空白），
  并加列表内围栏的用例。目标与范围不变，最终验收时交用户确认。
