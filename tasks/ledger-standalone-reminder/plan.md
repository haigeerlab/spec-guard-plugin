# Plan: ledger-standalone-reminder

依据 [`spec/ledger-standalone-reminder.md`](../../spec/ledger-standalone-reminder.md)：2026-10-22 批准（事项 C187，未决问题 Q1 A、Q2 A：
只启用账本时三处提醒都出；卸载只写文档步骤，不加移除命令；仓库根 `CLAUDE.md` 与 `docs/design.md` 的不变量措辞按 Spec 改）。

分支 `ledger-standalone-reminder`，worktree `.claude/worktrees/current-plugin-owner-aa5b98-crew/ledger-standalone-reminder`，从集成分支
`crew/fix-batch` 开出。module-crew 模块会话：只本地提交，不推送、不开 PR；合并由模块协调按用户原话做。CHANGELOG 与版本号由模块协调
整批合完后统一改，本模块把拟写的更新说明记在 todo 末尾。

所需工具：bash 回归、ShellCheck；AC6 要在临时 `CLAUDE_CONFIG_DIR`／`CODEX_HOME` 里跑 `claude mcp` 与 `codex mcp`；AC9 要在临时项目里跑一次
`claude -p --plugin-dir`。不访问远端，不新增依赖，不碰本机真实的宿主配置。

## 架构决定

- **「只有账本」是 `phase-guard.sh` 里的一个独立分支，在 `LINKED` 判定处分出去后直接退出。** 已启用、跟随指向、指向失效的代码路径
  一行不动；这样 AC4 的「已启用项目逐字相同」由现有用例直接守住。
- **三处提醒的文字复用现有函数**：`fresh_out`、`receipt_hint`、`ledger_root_note`。只新增一个压缩后账本核对提醒的中英两句（Spec 假设 2）。
- **`receipt_hint` 依赖 `ZH` 与 `EVENT`、在 `ZH` 算出之后定义。** 只有账本的分支要用它，所以把语言判定（`ZH`）与 `receipt_hint` 的定义
  挪到分支之前、仍在 `fresh_out` 之后；逻辑不变，只是位置前移。挪动后跑一遍全量回归确认已启用项目逐字相同。
- **bash 快速判定**：`inactive_before_python` 的两处 `has_block || has_state || has_link` 加上 `has_ledger`；只有账本、事件是
  UserPromptSubmit 时，在启动任何 python3 之前用 bash 看 `RAW` 里 `"prompt"` 字段是否以 `<cross-session-message ` 开头
  （`[[ $RAW =~ \"prompt\"[[:space:]]*:[[:space:]]*\"\<cross-session-message\  ]]`），不是就退出 0。RAW 只读了前 64KB，`prompt` 落在后面时
  按「拿不准」交给 `receipt_hint` 准确判定，不会误静默一个该提醒的消息之外的东西（误差只在多跑一次 python3）。
- **回归放进新的第 23 段**，第 19 段只把「未激活的目录有账本文件时 fresh 也静默」那一条翻成反向断言（它本身就是本模块要改的行为）。
  新段要在 `PARTS` 里登记（`PARTS=23`）。

## 实现要点

- 压缩后只有账本的核对提醒：
  - 中文：`上下文刚被压缩：摘要里较早的请求可能已经做完；重做之前先核对账本里未关闭的 \`waiting-on-*\` 事项。` ＋ `ledger_root_note zh`
  - 英文：`Context was just compacted: earlier requests in the summary may already be done; check the open \`waiting-on-*\` issues in the ledger before redoing anything.` ＋ `ledger_root_note`
- 只有账本的输出 JSON：`fresh` 沿用 `fresh_out` 的手写 JSON；`compact` 与 UserPromptSubmit 用 `python3 -c json.dumps` 生成（与 `emit()` 同法，
  但不经 `emit()`，免得接上 `COMPACT_NOTE` 与 `RECEIPT` 的拼接逻辑）；python3 生成失败就静默（Spec 假设 4：这里本来没有阶段注入）。
- 缺 python3：`fresh` 走 `fresh_out` 原有的英文降级；`compact`、UserPromptSubmit 静默退出 0。
- 卸载步骤的两条宿主命令先实测再写：
  - `CLAUDE_CONFIG_DIR=<临时目录> claude mcp add --scope user spec-guard-local-ledger -- /bin/true` 后 `claude mcp remove --scope user spec-guard-local-ledger`，
    看条目是否消失（`claude mcp list` 或读临时目录里的配置）；
  - `CODEX_HOME=<临时目录>` 下写一份 `local_ledger_adapters.py codex` 打印的表，`codex mcp remove spec_guard_local_ledger </dev/null`，看表是否删掉、
    其他内容是否原样。
  - ask 规则名单写法：`python3 -B "$ROOT/hooks/local_ledger_adapters.py" claude` 的只读输出里列有规则（构建时核对它确实打印；没有就在文档里
    写「以 `mcp__spec-guard-local-ledger__` 开头的规则」这个可核对的前缀判据）。
  - 实测不符（命令删不掉或误删其他内容）就停下，按 Spec Boundaries 发【等待用户】。
- 临时目录一律 `mktemp -d` 建在本会话 scratchpad 下，带固定前缀；用完按前缀守卫删除。

## Task List

### Task 0：同步批准标记

开工通知到后单独执行 `module-crew sync`，Spec、Plan、todo 取集成分支带批准标记的版本。

- 验收：sync 退出码 0；validate、phase-guard、verify-artifacts 全过。

### Task 1：只有账本时的三处提醒（改动 1）

1. 先写回归（红）：第 19 段那条翻成反向（只有账本的目录 `fresh` 出读回提醒，repoRoot 是该目录）；新增第 23 段——
   只有账本时 `fresh` 中英各一（中文用只含 `artifactLanguage: zh-CN` 的 `.agent/config.json`，不含 activeModule，不算激活）；
   `compact` 只出账本核对提醒中英各一、不含 `## spec-guard local workflow` 与 `spec-guard-state`；普通 UserPromptSubmit 无输出、退出 0；
   提示词以 `<cross-session-message from-name="x" from-session="local_y">` 开头时只出记账提醒一行（中英各一）；缺 python3（受限 `PATH`）时
   `fresh` 出英文提醒、`compact` 与 UserPromptSubmit 静默；宿主 ROOT 指向无关目录、hook 输入 cwd 在只有账本的仓库子目录里时 `fresh` 也认得；
   无账本无信号的目录三种事件都静默。
2. 实现：`has_ledger`；`inactive_before_python` 加判；`ZH`／`receipt_hint` 前移；`LINKED` 处的只有账本分支；bash 快速判定。
3. `PARTS=23`；ShellCheck `phase-guard.sh` 与 `test-phase-guard.sh`。

- 验收：AC1～AC5；新断言先红后绿；第 1～22 段原样全绿（AC4 的「已启用逐字相同」）。

### Checkpoint 1（report）：变异核对

在 scratchpad 的 `git archive` 副本上各改一处跑第 23 段：① 只有账本的分支对普通 UserPromptSubmit 也出一行；② 压缩后提醒带上「接着做建议
下一步」半句；③ `inactive_before_python` 不认 `.epiq/project.json`（cwd 子目录那条应红）；④ 只有账本的输出带上状态码。记下各自变红的断言名。
只报告，不停。

### Task 2：宿主移除命令实测（AC6 的证据）

按实现要点在临时配置目录里实测 `claude mcp remove --scope user` 与 `codex mcp remove`，记下命令、输出与前后差异（只记条目名，不记路径以外的
本机信息）。不符就停下发【等待用户】。

- 验收：两条命令的实测记录写进 todo，供最终验收引用。

### Task 3：说明文字（改动 2）

- `README.md`、`README.en.md` 卸载一节插入第 2 步（接入过宿主的先移除账本宿主配置；账本数据不用删）；隐私一节补「没有启用约定也会出读回提醒」。
- `commands/local-ticket-ledger.md` 末尾加「移除宿主配置」小节；`skills/local-ticket-ledger-ops/SKILL.md` 对应加一段（英文，随该文件原语言）；
  `references/local-ticket-ledger-runtime.md` 宿主接入一节加一句指向。
- `docs/optional-features.md` 本地事项账本一节加一句；`commands/teardown-convention.md` 加一句（Spec 假设 9）。
- `docs/design.md` 只改第 159 行不变量那一句、仓库根 `CLAUDE.md` 不变量一条，按 Spec 假设 6 改。`docs/design.md` 其余部分（含第 69～74 行
  SessionStart／激活说明）归 `doc-chain` 独占（用户批准 C190 时定的分工），本模块不动；那几行里「未激活时静默」与新行为的出入在最终验收里写明，
  交模块协调转 `doc-chain` 或后续处理。
- 命令名、条目名、表名与 `local_ledger_adapters.py` 的 `MCP_SERVER_NAME`、`CODEX_TABLE_NAME` 逐字核对。

- 验收：AC6、AC7；`check-readme-sync.py` 与 `validate.sh --quick` 通过。

### Task 4：真实宿主核对（AC9）

scratchpad 下临时项目：`git init`，只放 `.epiq/project.json`（`{"projectId":"x"}`），没有约定块与 state。用
`claude -p --model haiku --plugin-dir <本 worktree 的 plugins/spec-guard> --settings '{"enabledPlugins":{"spec-guard@spec-guard-marketplace":false}}'`
开一个新会话发一句话，从会话记录里取 SessionStart 注入原文，确认是读回提醒、只有一条 spec-guard 注入；同一会话第二轮确认 UserPromptSubmit
没有 spec-guard 注入。Codex 真机核对放到发版后由模块协调做，最终验收写明。

- 验收：AC9；会话记录片段记进 todo。

### Task 5：合入集成分支并跑完整检查

单独执行 `module-crew sync`，再跑 `validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh`；`module_scope.py check --module
ledger-standalone-reminder --base crew/fix-batch` 核对越界。

- 验收：AC8；越界检查结果写进 todo。

### 最终验收（gate）

模块最终验收：发最终验收【交审】，附「验收标准与证据」、改动统计与越界检查；不含推送与开 PR，合并由模块协调按用户原话做。

## 风险

| 风险 | 影响 | 应对 |
|---|---|---|
| 前移 `ZH`／`receipt_hint` 改变已启用项目输出 | 中 | 只挪位置不改逻辑；第 1～22 段全量回归守住 |
| bash 正则误判 `prompt` 开头 | 低 | 只用来提前退出；拿不准时交给 `session_context.py --received`，回归覆盖两种开头 |
| `codex mcp remove` 改写 config.toml 时动了别的内容 | 中 | Task 2 实测前后逐字比对；不符就写手动删表的步骤并先问 |
| 与 `doc-chain` 同改 `phase-guard.sh`／README／design.md | 中 | 按用户批准 C190 的分工：`docs/design.md` 归 doc-chain、本模块只改不变量一句；`docs/optional-features.md` 归本模块、doc-chain 只改基线路径的说法；其余只动账本分支与卸载一节；后合入的一方 `module-crew sync` 解冲突 |
