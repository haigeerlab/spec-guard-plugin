# Spec: merge-flow-f3

<!-- spec-guard: review approved f00f1fdd3830 -->

## Objective

用户认可的《插件开发规范》v1.5 F3（v1.5.1 补了第 3 步）统一了合并方式：会话问「可以合并吗」，用户在对话里回「合并」，会话执行合并（GitHub：
必需检查已全部通过时直接 `gh pr merge`，还没跑完时用 `gh pr merge --auto`、等必需检查通过后由 GitHub 合并），核实已合并、记下合并提交再告诉用户。用户不用去平台上点，也不用回来报「合完了」。

spec-guard 的共享检查点规则现在写的是「合并永远由用户进行，任何 Plan 都不能授权 agent 合并」，字面上就是要用户自己去点，和 F3 冲突；
这份规则随插件发到每个消费者项目。本模块把它改成 F3 的写法，同时改本仓库的发版流程文档和用法草案里 `merge: human` 的说明，升版本。

给谁用：所有用 spec-guard 的项目里做合并决定的用户与执行合并的会话；module-crew（它的协调会话本地合并引用了这条规则的「唯一例外」）。

对外接口与用法草案一致吗：不改命令、配置键、`/map --json` 字段；只改共享规则的文字和 `spec/usage/dev-flow-v2.md` 表格里一句说明，不动里程碑。

登记：ecosystem-lead #22515（F3）、#22543（五个仓库已开 Allow auto-merge）；账本 H46V1D5。需求确认：2026-11-24 用户在本会话回「单独小模块」「需求对」，
范围在补出共享规则三处后回「A 连共享规则一起改」。

## Assumptions

1. **新写法**（共享规则 `plugins/spec-guard/references/workflow-checkpoints.md` 第 137 行一处成段写全，第 152、474 行引用它）：
   「合并永远由用户在对话里决定：用户明确说『合并』后 agent 才执行；先看 PR 状态，必需检查已全部通过时直接合并（GitHub：`gh pr merge`），检查还没跑完时用平台的自动合并（GitHub：`gh pr merge --auto`），由平台等必需检查通过后合并；平台不支持自动合并时，等必需检查全部通过后再合并；合并方式按本仓库习惯；合并后核实已合并、记下合并提交，再告诉用户。任何 Plan 都不能代替用户这句话。」
   （2026-11-24 按 v1.5.1 修订：必需检查已全部通过时 GitHub 拒绝 `--auto`，所以先看 PR 状态。）
2. **「Plan 不能授权合并」保留**：Plan 的 `gate` 检查点仍可免问推送、开 PR，但不能写成「获批即合并」。
3. **协调会话的本地合并例外不变**：三个条件（开关 `on`、当前协调会话执行、合并的是用户刚批准最终验收的那一个模块）照旧；只把它引用的那句改成新说法。
4. **接管档位 `merge: auto` 不碰**：它由 autopilot 读、按 autopilot 的规则放行，规则里已有的那几句不改。
5. **本仓库文档**：
   - `docs/release-process.md` 第 4 条改为 F3 四步（第 3 步按 v1.5.1：`CI required` 已通过时 `gh pr merge --squash`，还没跑完时 `--auto --squash`）；2026-10-13 的长期授权（只改 `docs/releases/` 与 todo 末行、CI 通过的收尾 PR 由 agent 自行合并）原样保留；
     第 5 条「agent 自己核对已合并」不变。
   - `spec/usage/dev-flow-v2.md` 第 58 行 `merge` 的 `human` 说明由「人合」改为「用户在对话里说『合并』，会话执行（GitHub `--auto`）」。
   - `README.md` 第 223 行「远端合并始终由你来做」改为「远端合并始终由你在对话里决定，你说『合并』后由会话执行」。
   - `README.en.md` 只改安装命令的 `--ref`：`validate.sh` 要求中英两份 README 与清单版本一致（2026-11-24 用户批准补入）。
6. **回归**：`plugins/spec-guard/hooks/test_workflow_checkpoints.py` 里锁住旧句的三处（第 133、856、857 行）改成锁新句；另加一条：共享规则里不再出现
   「合并永远由用户进行」，且新句含「明确说『合并』」「必需检查已全部通过时直接合并」「任何 Plan 都不能代替」「核实已合并」「必需检查」；禁用「自动合并」的旧断言放过这一句。
7. **版本**：两份清单升到 `0.95.0`，CHANGELOG 记在 `[未发布]`（与 plugin-spec-compliance 的条目一起进 0.95.0）。发版在合并后另取用户授权。
8. **不做**：改代码；改 autopilot 或 module-crew；改历史记录（`tasks/`、`docs/reports/`、`docs/releases/`、`docs/retirements/`）；GitLab 的具体命令（规则只写「平台的自动合并」）。

## Contract

- **C1** 共享规则三处（假设 1～3）。
- **C2** `test_workflow_checkpoints.py` 同步并新增断言（假设 6）。
- **C3** `docs/release-process.md`、`spec/usage/dev-flow-v2.md`、`README.md`（假设 5）。
- **C4** 版本 0.95.0 与 CHANGELOG（假设 7）。

## Acceptance criteria

- **AC1** 共享规则里「合并永远由用户进行」一句都不剩；第 137 行附近是假设 1 的新句，第 152、474 行引用新说法。
- **AC2** 协调会话例外的三个条件、`merge: auto` 的那几句原样未改（diff 只动上述三处）。
- **AC3** `test_workflow_checkpoints.py` 通过；把任一处改回旧句，或删掉新句里「任何 Plan 都不能代替」，回归变红。
- **AC4** `docs/release-process.md` 第 4 条是 F3 四步且保留长期授权；`dev-flow-v2.md` 第 58 行、`README.md` 第 223 行说明已改。
- **AC5** 两份清单版本都是 `0.95.0`；`validate.sh`、phase-guard、verify-artifacts 全绿；PR 上 `CI required` 通过。
- **AC6** PR 号回给 ecosystem-lead（replyTo #22515）；告诉 mc-coord 共享规则那句措辞改了、例外条件没变。

## Boundaries

- **会做**：C1～C4 及回归；推送、开 PR；合并按新规则问用户；回复 ecosystem-lead 与 mc-coord。
- **先问再做**：合并；发版（tag、Release、宿主安装）；任何超出假设 1～5 的规则改动。
- **不做**：假设 8 列出的事。

## 并行边界

- 独占：`spec/merge-flow-f3.md`、`tasks/merge-flow-f3/`、`plugins/spec-guard/references/workflow-checkpoints.md`、`plugins/spec-guard/hooks/test_workflow_checkpoints.py`、`docs/release-process.md`、`spec/usage/dev-flow-v2.md`、`README.md`、`README.en.md`、`plugins/spec-guard/.claude-plugin/plugin.json`、`plugins/spec-guard/.codex-plugin/plugin.json`、`CHANGELOG.md`
- 公共：无

## 文档建议

`docs/release-process.md`、`README.md` 第 223 行本身就是本模块的改动对象；`docs/workflow.md` 没写合并由谁做，不用改。项目没有文档基线。
