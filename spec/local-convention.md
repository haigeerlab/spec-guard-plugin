# Spec: local-convention

## Objective

在使用 agent-skills 的项目里落地一个小的本地多模块目录约定，防止不同模块的 Spec、Plan 与任务清单互相覆盖：能力图
`spec/CAPABILITY-MAP.md`、模块 Spec `spec/<module-id>.md`、模块计划 `tasks/<module-id>/plan.md` 与
`tasks/<module-id>/todo.md`，以及只记录本地 active module 的 `.agent/state.json`。约定写入宿主说明文件中的一个受管
声明块，也可以完整移除。

登记：本模块是既有能力，由 2026-09-28 的一次性人工登记纳入能力图，未经 Proposal 流程
（`docs/decisions/2026-09-28-single-capability-map.md`）。

## Contract

- `setup-convention.sh [local] [--host=codex] [--dry-run] [--replace]` 只支持本地约定；GitHub/GitLab tracker 模式已
  退役，脚本拒绝它们且不写文件，没有回退。Claude 写入 `CLAUDE.md` 的 `agent-skills-convention` 块，Codex 写入
  `AGENTS.md` 的 `spec-guard-codex-convention` 块；内容来自 `templates/claude-block-local.md`、
  `templates/codex-block-local.md`，能力图模板为 `templates/CAPABILITY-MAP.md`。
- `--dry-run` 只报告将要做的改动。已有声明块时拒绝覆盖，只有 `--replace` 才升级该块。已有 `.agent/state.json`
  时不改写它。
- `teardown-convention.sh [--dry-run] [--keep-state]` 只移除受管声明块，把 `.agent/state.json` 改名为
  `.agent/state.json.disabled`（`--keep-state` 时保留，hook 会继续激活），不碰 `spec/`、`tasks/` 中的用户内容；
  完成后实际运行一次 `phase-guard.sh` 核对 hook 已停止注入。
- 声明块标记必须独占一行；标记缺失、重复或顺序错误时，`managed-block.py` 拒绝移除。
- 模板中的检查点指令指向 `spec-guard-ops` 的共享检查点规则（`references/workflow-checkpoints.md`）。

## Commands

```text
CLAUDE_PROJECT_DIR=<project> /bin/bash plugins/spec-guard/hooks/setup-convention.sh local --dry-run
CLAUDE_PROJECT_DIR=<project> /bin/bash plugins/spec-guard/hooks/teardown-convention.sh --dry-run
python3 plugins/spec-guard/hooks/managed-block.py validate|remove <file> <begin> <end>
python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
python3 scripts/check-readme-sync.py
/bin/bash scripts/validate.sh
```

## Project structure

```text
plugins/spec-guard/hooks/setup-convention.sh     -> 写入约定目录、能力图模板与受管声明块
plugins/spec-guard/hooks/teardown-convention.sh  -> 移除受管声明块并停用本地状态
plugins/spec-guard/hooks/managed-block.py        -> 声明块标记的校验与移除
plugins/spec-guard/templates/                    -> 写入消费者项目的声明块与能力图模板
plugins/spec-guard/commands/{setup,teardown}-convention.md, skills/spec-guard-ops/SKILL.md
```

## Testing strategy

- `test_workflow_checkpoints.py` 核对模板中的检查点指令可达；`check-readme-sync.py` 核对 README 内嵌的声明块与模板
  一致。
- 已知缺口：setup 与 teardown 没有回归测试（审计 P2-14）；`--replace` 前不做标记校验，teardown 往返会多出一个换行。

## Boundaries

- Always：先 `--dry-run`；只改受管声明块与约定目录；保留用户的 Spec、Plan 与任务内容。
- Ask first：改变目录约定、声明块标记或 `.agent/state.json` 的激活含义。
- Never：恢复远端 tracker 模式；删除 `spec/` 或 `tasks/` 中的用户内容；覆盖用户改过的声明块而不经 `--replace`。

## Success criteria

- 在新项目中 setup 后，`/phase` 与 verify-artifacts 能识别约定；teardown 后 hook 不再注入，用户内容保持不变。
