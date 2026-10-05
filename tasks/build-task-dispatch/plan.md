# Plan: build-task-dispatch

依据 [`spec/build-task-dispatch.md`](../../spec/build-task-dispatch.md)。三个 task 串行，每个 task 一条提交；
先写能在当前代码上失败的测试并记录失败输出，再修改到通过。

分支 `claude/build-task-dispatch`，基于已合并的 `origin/main`（`45ba1d0`）；能力图插入与 Spec 已在 `d529d97`。

每个 task 完成时运行下面四条，并用 `PATH=/usr/bin:/bin` 下的 `python3`（3.9）再跑一次：

```bash
/bin/bash plugins/spec-guard/hooks/test-setup-teardown.sh
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

**本模块默认关闭**：每个 task 的验收都包含「不带开关时写入的约定块与基础模板逐字相同」这一条。
`claude-block-local.md`、`codex-block-local.md`、`teardown-convention.sh`、阶段判断全部不动。

## Task 1：规则段模板（C1）

- 新增 `templates/claude-dispatch-rule.md`、`templates/codex-dispatch-rule.md`。首行都是
  `<!-- spec-guard: build-task-dispatch -->`，正文 2–4 个列表项，覆盖 Spec C1 的四点：何时派、子代理只做
  RED → GREEN → 回归 → 构建且不提交不勾选、prompt 必含（task 原文、spec 路径、独占一行的 tier-guard 标记，
  重试带 `failures=N`，todo 行已有标记原样带上）、停止条件交回与主代理收尾。
- Codex 段用 `spawn_agent`，并写明 tier-guard 在 Codex 上（含 Codex worker）只作建议。
- 内容断言加到 `test-setup-teardown.sh`：两份首行是标记；包含 `tier-guard: tier=`、`failures=N`、`Checkpoint`、
  不提交；Codex 段含 `spawn_agent` 与「只作建议」。**先红**：文件不存在。
- 措辞以 agent-skills 0.6.11 `.claude/commands/build.md` 第 35–36 行为准，不自造步骤名。
- **验收：** 内容断言先红后绿；现有 18 例逐字保留通过。
- **文件：** 两份模板、`test-setup-teardown.sh`。

## Task 2：`setup-convention --dispatch / --no-dispatch`（C2）

- 解析两个互斥参数，同时给出时退出 2 且不改文件；`usage` 行同步。
- 期望状态：显式参数 > 已有块内标记行（独占一行、去首尾空白后相等，复用 `managed-block.py` 读块或在块范围内匹配）> 关。
- 组装写入内容：基础模板，开启时其后接规则段模板，写入临时文件后交给 `managed-block.py replace` 或追加路径；
  新建与 `--replace` 共用同一组装。
- 已有块且无 `--replace`：行为不变，提示中说明开关需配合 `--replace`。
- `--dry-run` 多一行 `build-task-dispatch rule: <on|off> (<来源>)`，四种状态见 Spec C2。
- 回归按 Spec Testing strategy 的清单，Claude 与 Codex 各一遍；其中「默认新建逐字等于基础模板」「开启块
  `--replace` 保持开启」「`--dispatch --no-dispatch` 退出 2」「正文提到标记不算开启」四条先红（或在当前代码上
  因参数未知而失败），记录失败输出。
- **验收：** 新增用例先红后绿；`snapshot` 证明拒绝与跳过路径什么都没改；现有用例逐字通过。
- **文件：** `setup-convention.sh`、`test-setup-teardown.sh`。

## Task 3：文档（C3）

- `commands/setup-convention.md`：`argument-hint` 与正文加两个参数；默认关闭、状态存在块里、关闭需 `--no-dispatch`。
- `skills/spec-guard-ops/SKILL.md` 的 setup 路由同步参数。
- `docs/workflow.md`：一段说明可选规则、与 tier-guard 的关系，写明只是引导、不检测。
- `CHANGELOG.md` 未发布节 `### 新增`。
- **验收：** `check-command-parity.py` 与 `check-readme-sync.py` 通过；反向自查 Spec 每条契约都已落地。
- **文件：** 上述四份。

## Checkpoint

- 两种 Python、系统 `/bin/bash` 3.2 下全量通过；在一个临时消费者项目里手跑：默认 setup → 块无标记；
  `--dispatch` → 有；`--replace` → 仍有；`--replace --no-dispatch` → 无，与基础模板逐字相同。
- 牙齿检查：在草稿副本上分别改坏「状态保留」与「默认不含规则段」，确认对应断言变红。
- 代码审查（`/review`）；推分支、开 PR 等 CI，不自行合并。
- 把分支与 commit 告诉 tier-guard 会话，请其按 Spec Success criteria 跑真实宿主验收；结果回报后记入 Spec。
